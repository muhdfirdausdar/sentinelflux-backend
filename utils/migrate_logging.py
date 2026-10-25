#!/usr/bin/env python3
"""
Script to help migrate print statements to proper logging in the codebase.
This will identify files that still use print() and suggest replacements.
"""

import os
import re
from pathlib import Path

def find_print_statements(directory):
    """Find all Python files with print statements"""
    print_files = []
    
    for root, dirs, files in os.walk(directory):
        # Skip certain directories
        if any(skip in root for skip in ['__pycache__', '.git', 'venv', 'env']):
            continue
            
        for file in files:
            if file.endswith('.py'):
                filepath = Path(root) / file
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Find print statements (excluding comments)
                    lines = content.split('\n')
                    print_lines = []
                    
                    for i, line in enumerate(lines, 1):
                        # Skip commented lines
                        stripped = line.strip()
                        if stripped.startswith('#'):
                            continue
                            
                        # Look for print statements
                        if re.search(r'\bprint\s*\(', line):
                            print_lines.append((i, line.strip()))
                    
                    if print_lines:
                        print_files.append((filepath, print_lines))
                        
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
    
    return print_files

def suggest_logging_replacement(print_line):
    """Suggest a logging replacement for a print statement"""
    # Basic patterns for common print usage
    if 'error' in print_line.lower() or 'failed' in print_line.lower():
        return print_line.replace('print(', 'logger.error(')
    elif 'warning' in print_line.lower() or 'warn' in print_line.lower():
        return print_line.replace('print(', 'logger.warning(')
    elif 'debug' in print_line.lower():
        return print_line.replace('print(', 'logger.debug(')
    else:
        return print_line.replace('print(', 'logger.info(')

def main():
    """Main function to find and suggest logging replacements"""
    directory = "/home/firdaus/backend"
    print(f"Scanning directory: {directory}")
    print("=" * 60)
    
    print_files = find_print_statements(directory)
    
    if not print_files:
        print("No print statements found!")
        return
    
    print(f"Found {len(print_files)} files with print statements:\n")
    
    for filepath, print_lines in print_files:
        rel_path = filepath.relative_to(Path(directory))
        print(f"📄 {rel_path}")
        print("-" * 40)
        
        for line_num, line in print_lines:
            print(f"  Line {line_num}: {line}")
            suggestion = suggest_logging_replacement(line)
            print(f"  Suggest: {suggestion}")
            print()
        
        print(f"  📝 Don't forget to add: from utils.async_log import get_logger")
        print(f"  📝 And add: logger = get_logger('{rel_path.stem}')")
        print("\n" + "=" * 60 + "\n")

if __name__ == "__main__":
    main()
