# Stack-Based Expression Evaluator

**Student Name:** Daniel Michael Fofanah
**ID** 905006072
**Course:** Data Structures & Algorithms  
**Faculty:** Faculty of Information & Communication Technology (FICT)  
**Institution:** Limkokwing University of Creative Technology  

---
# Stack-Based Expression Evaluator

A Python implementation of **Dijkstra's Shunting-Yard Algorithm** and a custom **Stack Data Structure** designed to parse, evaluate, and batch-process mathematical infix expressions from external files.

## Project Structure
* `main.py`: Contains the core `Stack` class, tokenization logic, Shunting-Yard algorithm, and file processing functions.
* `input.txt`: Source text file containing raw infix arithmetic expressions.
* `output.txt`: Generated output file storing evaluated results or error messages.

## Features
* Custom Stack data structure implementation.
* Full support for operator precedence (`+`, `-`, `*`, `/`) and nested parentheses `()`.
* Robust batch file processing with automatic input/output handling.

## How to Run
Run the main script using Python 3:
```bash
python main.py
