#!/usr/bin/env python
import os

def fix_whitespace_errors(directory):
    """
    Fixes W293 (blank line contains whitespace) and W291 (trailing whitespace) errors
    in Python files within the specified directory.
    """
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        lines = f.readlines()

                    new_lines = []
                    changed = False
                    for line in lines:
                        original_line = line
                        # Fix W293: blank line contains whitespace
                        if line.strip() == '':
                            if line != '\n':
                                line = '\n'
                        # Fix W291: trailing whitespace
                        line = line.rstrip() + '\n'
                        
                        if original_line != line:
                            changed = True
                        new_lines.append(line)

                    if changed:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.writelines(new_lines)
                        print(f"Fixed whitespace errors in: {filepath}")
                    else:
                        print(f"No whitespace errors found in: {filepath}")

                except Exception as e:
                    print(f"Error processing {filepath}: {e}")

if __name__ == "__main__":
    print("Starting to fix whitespace errors in 'app' directory...")
    fix_whitespace_errors("app")
    print("Starting to fix whitespace errors in 'test' directory...")
    fix_whitespace_errors("test")
    print("Whitespace error fixing complete.")