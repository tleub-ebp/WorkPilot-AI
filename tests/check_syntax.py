"""
Syntax checker for auto-fix loop files
"""
import py_compile
import sys
from pathlib import Path

def check_syntax(filepath):
    """Check Python file for syntax errors."""
    try:
        py_compile.compile(str(filepath), doraise=True)
        print(f"✓ {filepath.name}")
        return True
    except py_compile.PyCompileError as e:
        print(f"✗ {filepath.name}: {e}")
        return False

def main():
    """Check all auto-fix loop files."""
    # From tests/ folder, go up to repo root, then to backend
    backend_dir = Path(__file__).parent.parent / "apps" / "backend"
    
    files_to_check = [
        backend_dir / "qa" / "auto_fix_loop.py",
        backend_dir / "qa" / "auto_fix_metrics.py",
        backend_dir / "qa" / "__init__.py",
        backend_dir / "qa_loop.py",
        backend_dir / "cli" / "qa_commands.py",
        backend_dir / "cli" / "main.py",
    ]
    
    print("Checking Python syntax...")
    print("=" * 60)
    
    results = []
    for filepath in files_to_check:
        if not filepath.exists():
            print(f"⚠ {filepath.name}: File not found at {filepath}")
            results.append(False)
        else:
            results.append(check_syntax(filepath))
    
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    
    print(f"\n{passed}/{total} files passed syntax check")
    
    if passed == total:
        print("✅ All files have valid Python syntax!")
        return 0
    else:
        print(f"❌ {total - passed} file(s) have syntax errors")
        return 1

if __name__ == "__main__":
    sys.exit(main())
