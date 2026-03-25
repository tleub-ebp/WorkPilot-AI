"""
pytest configuration file
"""
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
src_path = project_root / "src"

# Ensure both project root and src are in the Python path
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

print(f"Python path includes: {project_root}")
print(f"Python path includes: {src_path}")
