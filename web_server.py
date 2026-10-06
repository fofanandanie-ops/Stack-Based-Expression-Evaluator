"""Self-hosted Car Parking Multiplayer car listings website."""

import hmac
import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"
DATABASE = Path(os.environ.get("DATABASE_PATH", str(ROOT / "cars.sqlite3")))
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
SESSIONS = set()
MAX_BODY_SIZE = 1_000_000
COOKIE_NAME = "cpm_admin"
COOKIE_SECURE = os.environ.get("COOKIE_SECURE") == "1"


def session_cookie(token, max_age=None):
    cookie = f"{COOKIE_NAME}={token}; Path=/; HttpOnly; SameSite=Strict"
    if COOKIE_SECURE:
        cookie += "; Secure"
    if max_age is not None:
        cookie += f"; Max-Age={max_age}"
    return cookie


@contextmanager
def connect_database():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_database():
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    with connect_database() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS cars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                model TEXT NOT NULL,
                price TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                image_url TEXT NOT NULL DEFAULT '',
                contact TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'available',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


class CarSalesHandler(BaseHTTPRequestHandler):
    server_version = "CarSales/1.0"

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' https: data:; "
            "style-src 'self'; script-src 'self'; base-uri 'self'; "
            "frame-ancestors 'none'",
        )
        super().end_headers()

    def send_json(self, status, payload, extra_headers=()):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for name, value in extra_headers:
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ValueError("Invalid request size.") from None
        if length < 1 or length > MAX_BODY_SIZE:
            raise ValueError("Request must contain valid JSON under 1 MB.")
        try:
            payload = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise ValueError("Request body must be valid JSON.") from None
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")
        return payload

    def is_admin(self):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
            token = cookie[COOKIE_NAME].value
        except (KeyError, TypeError):
            return False
        return token in SESSIONS

    def require_admin(self):
        if not self.is_admin():
            self.send_json(HTTPStatus.UNAUTHORIZED, {"error": "Admin login required."})
            return False
        return True

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/cars":
            with connect_database() as connection:
                rows = connection.execute(
                    "SELECT * FROM cars ORDER BY created_at DESC, id DESC"
                ).fetchall()
            return self.send_json(HTTPStatus.OK, [dict(row) for row in rows])
        if path == "/api/session":
            return self.send_json(HTTPStatus.OK, {"authenticated": self.is_admin()})
        if path == "/":
            return self.serve_file("index.html")
        if path in ("/styles.css", "/app.js"):
            return self.serve_file(path.lstrip("/"))
        self.send_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})

    def serve_file(self, filename):
        file_path = WEB_DIR / filename
        try:
            content = file_path.read_bytes()
        except OSError:
            return self.send_json(HTTPStatus.NOT_FOUND, {"error": "Page not found."})
        content_type = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
        }.get(file_path.suffix, "application/octet-stream")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/login":
            return self.login()
        if path == "/api/logout":
            if not self.require_admin():
                return
            cookie = SimpleCookie()
            cookie.load(self.headers.get("Cookie", ""))
            token = cookie[COOKIE_NAME].value if COOKIE_NAME in cookie else ""
            SESSIONS.discard(token)
            return self.send_json(
                HTTPStatus.OK,
                {"authenticated": False},
                [("Set-Cookie", session_cookie("", max_age=0))],
            )
        if path == "/api/cars":
            if not self.require_admin():
                return
            try:
                car = self.validate_car(self.read_json())
            except ValueError as error:
                return self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            with connect_database() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO cars (title, model, price, description, image_url, contact, status)
                    VALUES (:title, :model, :price, :description, :image_url, :contact, :status)
                    """,
                    car,
                )
                car_id = cursor.lastrowid
                saved = connection.execute(
                    "SELECT * FROM cars WHERE id = ?", (car_id,)
                ).fetchone()
            return self.send_json(HTTPStatus.CREATED, dict(saved))
        self.send_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})

    def login(self):
        try:
            password = self.read_json().get("password")
        except ValueError as error:
            return self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
        if not isinstance(password, str) or not hmac.compare_digest(password, ADMIN_PASSWORD):
            return self.send_json(HTTPStatus.UNAUTHORIZED, {"error": "Incorrect password."})
        token = secrets.token_urlsafe(32)
        SESSIONS.add(token)
        return self.send_json(
            HTTPStatus.OK,
            {"authenticated": True},
            [("Set-Cookie", session_cookie(token))],
        )

    def do_PUT(self):
        if not self.require_admin():
            return
        path = urlparse(self.path).path
        parts = path.strip("/").split("/")
        if len(parts) != 3 or parts[:2] != ["api", "cars"]:
            return self.send_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})
        try:
            car_id = int(parts[2])
            car = self.validate_car(self.read_json())
        except (ValueError, TypeError) as error:
            return self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
        with connect_database() as connection:
            cursor = connection.execute(
                """
                UPDATE cars
                SET title = :title, model = :model, price = :price,
                    description = :description, image_url = :image_url,
                    contact = :contact, status = :status
                WHERE id = :id
                """,
                dict(car, id=car_id),
            )
            if cursor.rowcount == 0:
                return self.send_json(HTTPStatus.NOT_FOUND, {"error": "Car listing not found."})
            saved = connection.execute("SELECT * FROM cars WHERE id = ?", (car_id,)).fetchone()
        self.send_json(HTTPStatus.OK, dict(saved))

    def do_DELETE(self):
        if not self.require_admin():
            return
        parts = urlparse(self.path).path.strip("/").split("/")
        if len(parts) != 3 or parts[:2] != ["api", "cars"]:
            return self.send_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})
        try:
            car_id = int(parts[2])
        except ValueError:
            return self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid car listing ID."})
        with connect_database() as connection:
            cursor = connection.execute("DELETE FROM cars WHERE id = ?", (car_id,))
        if cursor.rowcount == 0:
            return self.send_json(HTTPStatus.NOT_FOUND, {"error": "Car listing not found."})
        self.send_json(HTTPStatus.OK, {"deleted": True})

    @staticmethod
    def validate_car(payload):
        fields = ("title", "model", "price", "description", "image_url", "contact", "status")
        car = {field: payload.get(field, "") for field in fields}
        for field in fields:
            if not isinstance(car[field], str):
                raise ValueError(f"{field.replace('_', ' ').title()} must be text.")
            car[field] = car[field].strip()
        for field in ("title", "model", "price"):
            if not car[field]:
                raise ValueError(f"{field.title()} is required.")
        if len(car["title"]) > 100 or len(car["model"]) > 100:
            raise ValueError("Title and model must be 100 characters or fewer.")
        if len(car["price"]) > 40 or len(car["description"]) > 2000:
            raise ValueError("Price or description is too long.")
        if len(car["image_url"]) > 2000 or len(car["contact"]) > 200:
            raise ValueError("Image URL or contact is too long.")
        if car["image_url"] and not car["image_url"].startswith(("https://", "http://")):
            raise ValueError("Image URL must start with http:// or https://.")
        if car["status"] not in ("available", "sold"):
            raise ValueError("Status must be available or sold.")
        return car


def main():
    if not ADMIN_PASSWORD:
        raise SystemExit(
            "Set the ADMIN_PASSWORD environment variable before starting the website."
        )
    initialize_database()
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer((host, port), CarSalesHandler)
    print(f"Car sales website running at http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping website.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
