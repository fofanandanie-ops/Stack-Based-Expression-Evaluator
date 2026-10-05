"""
Data Structures and Algorithms Assignment
Stack-Based Mathematical Expression Evaluator

Author: Daniel Michael Fofanah
Description: Reads infix mathematical expressions from 'input.txt', translates
             them to postfix notation using Dijkstra's Shunting-Yard Algorithm via
             a custom Stack class, evaluates the postfix expressions, and writes
             the results to 'output.txt' preserving separator formatting.
"""

import os


class Stack:
    """
    A custom implementation of a Last-In, First-Out (LIFO) Stack data structure.
    """
    def __init__(self):
        """Initialize an empty stack internal storage list."""
        self._items = []

    def push(self, item):
        """Push an item onto the top of the stack."""
        self._items.append(item)

    def pop(self):
        """
        Remove and return the top item from the stack.
        Raises IndexError if the stack is empty.
        """
        if self.is_empty():
            raise IndexError("Stack Underflow: Cannot pop from an empty stack.")
        return self._items.pop()

    def peek(self):
        """
        Return the top item of the stack without removing it.
        Raises IndexError if the stack is empty.
        """
        if self.is_empty():
            raise IndexError("Stack Underflow: Cannot peek at an empty stack.")
        return self._items[-1]

    def is_empty(self):
        """Return True if the stack contains no items, False otherwise."""
        return len(self._items) == 0

    def size(self):
        """Return the total number of items currently in the stack."""
        return len(self._items)


def tokenize(expression_str):
    """
    Converts a raw mathematical expression string into a list of individual tokens.
    Handles multi-digit numbers, decimals, operators, and parentheses.
    """
    tokens = []
    i = 0
    expr = expression_str.strip()

    while i < len(expr):
        char = expr[i]

        # Ignore whitespace characters
        if char.isspace():
            i += 1
            continue

        # Extract multi-digit numbers and floating-point values
        if char.isdigit() or char == '.':
            num_str = ""
            while i < len(expr) and (expr[i].isdigit() or expr[i] == '.'):
                num_str += expr[i]
                i += 1
            tokens.append(num_str)
            continue

        # Extract operators and grouping symbols
        if char in "+-*/()":
            tokens.append(char)
            i += 1
            continue

        # Raise an error if an invalid character is encountered
        raise ValueError(f"Invalid character encountered in expression: '{char}'")

    return tokens


def infix_to_postfix(tokens):
    """
    Translates an infix token list into Postfix (Reverse Polish) Notation
    using Dijkstra's Shunting-Yard Algorithm and an Operator Stack.
    """
    precedence = {'+': 1, '-': 1, '*': 2, '/': 2}
    operator_stack = Stack()
    output_queue = []

    for token in tokens:
        # If token is a number, append directly to output queue
        if token.replace('.', '', 1).isdigit():
            output_queue.append(token)

        # Left parenthesis: Push onto operator stack
        elif token == '(':
            operator_stack.push(token)

        # Right parenthesis: Pop operators until matching '(' is found
        elif token == ')':
            while not operator_stack.is_empty() and operator_stack.peek() != '(':
                output_queue.append(operator_stack.pop())
            
            if operator_stack.is_empty():
                raise ValueError("Mismatched parentheses: Missing '('")
            
            operator_stack.pop()  # Discard the matching '('

        # Operator (+, -, *, /): Handle operator precedence
        elif token in precedence:
            while (not operator_stack.is_empty() and 
                   operator_stack.peek() != '(' and 
                   precedence[operator_stack.peek()] >= precedence[token]):
                output_queue.append(operator_stack.pop())
            
            operator_stack.push(token)

    # Pop remaining operators from the stack to the output queue
    while not operator_stack.is_empty():
        top_op = operator_stack.pop()
        if top_op == '(' or top_op == ')':
            raise ValueError("Mismatched parentheses detected in expression.")
        output_queue.append(top_op)

    return output_queue


def evaluate_postfix(postfix_tokens):
    """
    Evaluates a Postfix (RPN) token list using an Operand Stack.
    Returns the computed numerical value (float or int).
    """
    operand_stack = Stack()

    for token in postfix_tokens:
        # If token is a number, convert to float and push onto operand stack
        if token.replace('.', '', 1).isdigit():
            operand_stack.push(float(token))

        # Operator encountered: Pop two operands, perform arithmetic, and push result
        elif token in "+-*/":
            if operand_stack.size() < 2:
                raise ValueError("Malformed expression: Insufficient operands.")

            val2 = operand_stack.pop()  # Right operand
            val1 = operand_stack.pop()  # Left operand

            if token == '+':
                result = val1 + val2
            elif token == '-':
                result = val1 - val2
            elif token == '*':
                result = val1 * val2
            elif token == '/':
                if val2 == 0:
                    raise ZeroDivisionError("Division by zero error.")
                result = val1 / val2

            operand_stack.push(result)

    if operand_stack.size() != 1:
        raise ValueError("Malformed expression: Too many operands.")

    final_val = operand_stack.pop()
    
    # Format whole numbers as integers (e.g., 13.0 -> 13)
    if final_val.is_integer():
        return int(final_val)
    return final_val


def evaluate_expression(expression_str):
    """
    Master evaluator pipeline: Tokenizes, converts to postfix, and computes result.
    """
    tokens = tokenize(expression_str)
    postfix_tokens = infix_to_postfix(tokens)
    return evaluate_postfix(postfix_tokens)


def is_separator(line_str):
    """
    Determines if a given line is a separator (e.g., '-----') or non-mathematical delimiter.
    """
    cleaned = line_str.strip()
    if not cleaned:
        return True
    # If the line consists purely of delimiter symbols like '-' or '=' and contains no digits
    if all(char in "-=_*" for char in cleaned) and not any(char.isdigit() for char in cleaned):
        return True
    return False


def process_file(input_filename="input.txt", output_filename="output.txt"):
    """
    Reads mathematical expressions from input_filename, evaluates each,
    and writes results to output_filename while maintaining separator formatting.
    """
    if not os.path.exists(input_filename):
        print(f"Error: Input file '{input_filename}' not found.")
        return

    output_lines = []

    with open(input_filename, 'r') as infile:
        lines = infile.readlines()

    for line in lines:
        raw_line = line.strip()

        # If empty or delimiter separator line, preserve it directly
        if is_separator(raw_line):
            output_lines.append(line.rstrip('\n'))
        else:
            try:
                result = evaluate_expression(raw_line)
                output_lines.append(str(result))
            except Exception as e:
                output_lines.append(f"ERROR: {str(e)}")

    with open(output_filename, 'w') as outfile:
        for i, out_line in enumerate(output_lines):
            outfile.write(out_line + '\n')

    print(f"Successfully processed '{input_filename}' -> Written to '{output_filename}'.")


if __name__ == "__main__":
    process_file("input.txt", "output.txt")