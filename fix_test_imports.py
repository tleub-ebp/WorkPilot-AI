"""
Script to fix Python import paths in test files
"""
import os
import sys
from pathlib import Path

def fix_imports_in_file(file_path: Path):
    """Fix imports in a single test file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if file needs fixing
        if 'from src.' in content and 'sys.path.insert' not in content:
            lines = content.split('\n')
            new_lines = []
            import_added = False
            
            for line in lines:
                if line.startswith('from src.') and not import_added:
                    # Add sys.path setup before the first src import
                    depth = len(file_path.relative_to(Path.cwd()).parts) - 1
                    path_back = ".." * depth
                    new_lines.extend([
                        "import sys",
                        "import os",
                        "",
                        "# Add the project root to the Python path",
                        f"sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), \"{path_back}\")))",
                        ""
                    ])
                    import_added = True
                new_lines.append(line)
            
            # Write back the fixed content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(new_lines))
            
            print(f"Fixed imports in: {file_path}")
            return True
        else:
            print(f"No fixes needed for: {file_path}")
            return False
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Fix all test files"""
    test_dir = Path.cwd() / "tests"
    python_files = list(test_dir.rglob("*.py"))
    
    fixed_count = 0
    for file_path in python_files:
        if fix_imports_in_file(file_path):
            fixed_count += 1
    
    print(f"\nFixed imports in {fixed_count} files")

if __name__ == "__main__":
    main()
