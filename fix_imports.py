import os
import re

# Define the mapping of old top-level modules to new prefixes
PREFIX_MAP = {
    "app.web.": ["backend", "websocket", "broker", "frontend"],
    "app.": ["core", "db", "utils", "algo"],
}

def get_new_module_path(module_path):
    if module_path.startswith('.'):
        return None # It's a relative import, don't touch it.

    # Special case for main
    if module_path == "main" or module_path.startswith("main."):
        if not module_path.startswith("app."):
             return "app." + module_path

    for prefix, modules in PREFIX_MAP.items():
        for module in modules:
            if module_path == module or module_path.startswith(module + '.'):
                if not module_path.startswith("app."):
                    return prefix + module_path
    return None

def process_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return

    lines = original_content.split('\n')
    new_lines = []
    
    for line in lines:
        # First, clean up errors from the previous script, like 'from .foo import app.bar'
        new_line = re.sub(r'(from\s+(\.\.?)\S*\s+import\s+.*)app\.web\.(\w+)', r'\1\3', line)
        new_line = re.sub(r'(from\s+(\.\.?)\S*\s+import\s+.*)app\.(\w+)', r'\1\3', new_line)
        
        stripped_new_line = new_line.strip()

        from_match = re.match(r'from\s+([.\w]+)\s+import\s+(.*)', stripped_new_line)
        import_match = re.match(r'import\s+(.*)', stripped_new_line)

        if from_match:
            module_path = from_match.group(1)
            import_names = from_match.group(2)
            new_module_path = get_new_module_path(module_path)
            if new_module_path:
                indent = new_line[:len(new_line) - len(new_line.lstrip())]
                new_line = f"{indent}from {new_module_path} import {import_names}"

        elif import_match:
            modules_str = import_match.group(1)
            modules = [m.strip() for m in modules_str.split(',')]
            new_modules = []
            made_change = False
            for module in modules:
                module_parts = module.split(' as ')
                module_name_to_check = module_parts[0]
                new_module_path = get_new_module_path(module_name_to_check)
                if new_module_path:
                    if len(module_parts) > 1:
                        new_modules.append(f"{new_module_path} as {module_parts[1]}")
                    else:
                        new_modules.append(new_module_path)
                    made_change = True
                else:
                    new_modules.append(module)
            if made_change:
                indent = new_line[:len(new_line) - len(new_line.lstrip())]
                new_line = f"{indent}import {', '.join(new_modules)}"

        new_lines.append(new_line)

    new_content = "\n".join(new_lines)

    if new_content != original_content:
        print(f'Updated: {file_path}')
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
        except Exception as e:
            print(f"Error writing to {file_path}: {e}")
    else:
        print(f'No changes needed for: {file_path}')

def main():
    with open('python_files.txt', 'r') as f:
        files = f.read().splitlines()
    
    for file_path in files:
        if os.path.isfile(file_path):
            process_file(file_path)
        else:
            print(f"Skipping directory: {file_path}")

if __name__ == "__main__":
    main()