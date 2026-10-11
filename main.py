import os
import re

class Stack:
    def __init__(self):
        self.items = []

    def push(self, item):
        self.items.append(item)

    def pop(self):
        if not self.is_empty():
            return self.items.pop()

    def peek(self):
        if not self.is_empty():
            return self.items[-1]

    def is_empty(self):
        return len(self.items) == 0

def tokenize(expression):
    return re.findall(r'\d+|\+|\-|\*|\/|\(|\)', expression)

def apply_op(values, ops):
    if ops.is_empty(): 
        return
    op = ops.pop()
    if values.is_empty(): 
        return
    right = values.pop()
    if values.is_empty(): 
        return
    left = values.pop()
    
    if op == '+': 
        values.push(left + right)
    elif op == '-': 
        values.push(left - right)
    elif op == '*': 
        values.push(left * right)
    elif op == '/': 
        values.push(int(left / right))

def evaluate_expression(expression):
    tokens = tokenize(expression)
    values = Stack()
    ops = Stack()
    
    precedence = {'+': 1, '-': 1, '*': 2, '/': 2}
    
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.isdigit():
            values.push(int(token))
        elif token == '(':
            ops.push(token)
        elif token == ')':
            while not ops.is_empty() and ops.peek() != '(':
                apply_op(values, ops)
            if not ops.is_empty():
                ops.pop()
        elif token in precedence:
            while (not ops.is_empty() and ops.peek() != '(' and
                   precedence.get(ops.peek(), 0) >= precedence[token]):
                apply_op(values, ops)
            ops.push(token)
        i += 1
        
    while not ops.is_empty():
        apply_op(values, ops)
        
    return values.pop()

def process_files(input_path, output_path):
    if not os.path.exists(input_path):
        with open(input_path, 'w') as f:
            f.write("3 + 5 * 2\n")
            f.write("-----\n")
            f.write("(8 / 4) + 7 * 2\n")
            f.write("-----\n")
            f.write("10 - (2 + 3) * 4\n")
            
    try:
        with open(input_path, 'r') as infile, open(output_path, 'w') as outfile:
            for line in infile:
                line = line.strip()
                if not line or line.startswith('---'):
                    outfile.write(line + '\n')
                    continue
                try:
                    result = evaluate_expression(line)
                    outfile.write(str(result) + '\n')
                except Exception as e:
                    outfile.write(f"Error evaluating '{line}': {e}\n")
    except FileNotFoundError:
        print(f"Error: Input file '{input_path}' not found.")

    print("\n" + "=" * 45)
    print("           INPUT SECTION (input.txt)")
    print("=" * 45)
    if os.path.exists(input_path):
        with open(input_path, 'r') as f:
            print(f.read().strip())
    
    print("\n" + "=" * 45)
    print("          OUTPUT SECTION (output.txt)")
    print("=" * 45)
    if os.path.exists(output_path):
        with open(output_path, 'r') as f:
            print(f.read().strip())
    print("=" * 45 + "\n")

if __name__ == "__main__":
    input_file = "input.txt"
    output_file = "output.txt"
    process_files(input_file, output_file)