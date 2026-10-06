const grid = document.querySelector("#car-grid");
const count = document.querySelector("#listing-count");
const adminPanel = document.querySelector("#admin-panel");
const loginDialog = document.querySelector("#login-dialog");
const carDialog = document.querySelector("#car-dialog");
const carForm = document.querySelector("#car-form");
let cars = [];
let isAdmin = false;
let currentFilter = "all";

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || "Something went wrong.");
  return body;
}

function setAdmin(authenticated) {
  isAdmin = authenticated;
  adminPanel.classList.toggle("hidden", !authenticated);
  document.querySelector("#admin-button").classList.toggle("hidden", authenticated);
  document.querySelector("#logout-button").classList.toggle("hidden", !authenticated);
  renderCars();
}

function makeElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function renderCars() {
  const visible = cars.filter((car) => currentFilter === "all" || car.status === currentFilter);
  count.textContent = String(cars.length).padStart(2, "0");
  grid.replaceChildren();
  if (!visible.length) {
    const empty = makeElement("div", "empty-state");
    empty.append(makeElement("span", "empty-icon", "↗"));
    empty.append(makeElement("h3", "", cars.length ? "No cars in this filter." : "The lot is quiet."));
    empty.append(makeElement("p", "", cars.length
      ? "Try another filter to see the rest of the lineup."
      : (isAdmin ? "Add your first car and it’ll show up here." : "Check back soon for the next ride.")));
    grid.append(empty);
    return;
  }

  visible.forEach((car, index) => {
    const card = makeElement("article", `car-card${car.status === "sold" ? " is-sold" : ""}`);
    const imageWrap = makeElement("div", "car-image-wrap");
    if (car.image_url) {
      const image = makeElement("img", "car-image");
      image.src = car.image_url;
      image.alt = car.title;
      image.loading = "lazy";
      image.referrerPolicy = "no-referrer";
      image.addEventListener("error", () => imageWrap.classList.add("image-failed"), { once: true });
      imageWrap.append(image);
    } else {
      imageWrap.classList.add("no-image");
      imageWrap.append(makeElement("span", "image-placeholder", "09"));
      imageWrap.append(makeElement("span", "image-caption", "CPM GARAGE"));
    }
    const badge = makeElement("span", `status-badge ${car.status}`, car.status === "sold" ? "SOLD" : "AVAILABLE");
    imageWrap.append(badge);
    const number = makeElement("span", "card-number", `LOT / ${String(index + 1).padStart(2, "0")}`);
    imageWrap.append(number);
    const info = makeElement("div", "car-info");
    info.append(makeElement("p", "car-model", car.model));
    info.append(makeElement("h3", "car-title", car.title));
    if (car.description) info.append(makeElement("p", "car-description", car.description));
    const bottom = makeElement("div", "car-card-bottom");
    const price = makeElement("span", "car-price", car.price);
    bottom.append(price);
    if (!isAdmin && car.contact && car.status === "available") {
      const contact = makeElement("span", "contact-note", car.contact);
      contact.title = `Contact: ${car.contact}`;
      bottom.append(contact);
    }
    info.append(bottom);
    if (isAdmin) {
      const tools = makeElement("div", "card-admin-tools");
      const edit = makeElement("button", "text-button", "Edit listing");
      edit.type = "button";
      edit.addEventListener("click", () => openCarForm(car));
      const remove = makeElement("button", "text-button delete-button", "Delete");
      remove.type = "button";
      remove.addEventListener("click", () => deleteCar(car));
      tools.append(edit, remove);
      info.append(tools);
    }
    card.append(imageWrap, info);
    grid.append(card);
  });
}

async function loadCars() {
  try {
    cars = await api("/api/cars");
    renderCars();
  } catch (error) {
    grid.replaceChildren(makeElement("div", "empty-state", error.message));
  }
}

function openCarForm(car = null) {
  carForm.reset();
  document.querySelector("#car-error").textContent = "";
  document.querySelector("#car-id").value = car ? car.id : "";
  document.querySelector("#car-form-title").firstChild.textContent = car ? "Edit a car" : "Add a car";
  document.querySelector("#save-car-button").firstChild.textContent = car ? "Save changes " : "Publish listing ";
  for (const field of ["title", "model", "price", "image_url", "description", "contact", "status"]) {
    const input = document.querySelector(`#car-${field.replaceAll("_", "-")}`);
    input.value = car ? car[field] : field === "status" ? "available" : "";
  }
  carDialog.showModal();
}

document.querySelector("#admin-button").addEventListener("click", () => loginDialog.showModal());
document.querySelector("#add-car-button").addEventListener("click", () => openCarForm());
document.querySelectorAll("[data-close]").forEach((button) => {
  button.addEventListener("click", () => document.querySelector(`#${button.dataset.close}`).close());
});
document.querySelectorAll(".filter").forEach((button) => {
  button.addEventListener("click", () => {
    currentFilter = button.dataset.filter;
    document.querySelectorAll(".filter").forEach((item) => item.classList.toggle("active", item === button));
    renderCars();
  });
});

document.querySelector("#login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const errorMessage = document.querySelector("#login-error");
  errorMessage.textContent = "";
  try {
    await api("/api/login", {
      method: "POST",
      body: JSON.stringify({ password: document.querySelector("#admin-password").value }),
    });
    loginDialog.close();
    document.querySelector("#login-form").reset();
    setAdmin(true);
    showToast("You’re in. Welcome to the garage.");
  } catch (error) {
    errorMessage.textContent = error.message;
  }
});

document.querySelector("#logout-button").addEventListener("click", async () => {
  try {
    await api("/api/logout", { method: "POST", body: "{}" });
    setAdmin(false);
    showToast("You’ve been logged out.");
  } catch (error) {
    showToast(error.message);
  }
});

carForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const errorMessage = document.querySelector("#car-error");
  const saveButton = document.querySelector("#save-car-button");
  errorMessage.textContent = "";
  saveButton.disabled = true;
  const id = document.querySelector("#car-id").value;
  const data = Object.fromEntries(
    ["title", "model", "price", "image_url", "description", "contact", "status"]
      .map((field) => [field, document.querySelector(`#car-${field.replaceAll("_", "-")}`).value]),
  );
  try {
    await api(id ? `/api/cars/${id}` : "/api/cars", {
      method: id ? "PUT" : "POST",
      body: JSON.stringify(data),
    });
    carDialog.close();
    await loadCars();
    showToast(id ? "Listing updated." : "Your car is on the lot.");
  } catch (error) {
    errorMessage.textContent = error.message;
  } finally {
    saveButton.disabled = false;
  }
});

async function deleteCar(car) {
  if (!window.confirm(`Delete “${car.title}” from your listings? This cannot be undone.`)) return;
  try {
    await api(`/api/cars/${car.id}`, { method: "DELETE" });
    await loadCars();
    showToast("Listing deleted.");
  } catch (error) {
    showToast(error.message);
  }
}

let toastTimeout;
function showToast(message) {
  const toast = document.querySelector("#toast");
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => toast.classList.remove("show"), 2800);
}

async function start() {
  try {
    const session = await api("/api/session");
    setAdmin(session.authenticated);
  } catch (error) {
    setAdmin(false);
    showToast(error.message);
  }
  await loadCars();
}

start();
