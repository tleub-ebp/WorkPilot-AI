"""
pytest configuration for connector tests
"""
import sys
import os
import importlib.util
from pathlib import Path

# Add the project root to the Python path for connector tests
# When pytest runs tests in subdirectories, it needs explicit path configuration
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent.parent  # Go up from tests/connectors to project root
src_path = project_root / "src"

# Use absolute paths from the file location
conftest_file = Path(__file__).resolve()
project_root_abs = conftest_file.parent.parent.parent
src_path_abs = project_root_abs / "src"

# Ensure paths are in sys.path in correct order
# First add project root, then src (this matches the root conftest.py order)
if str(project_root_abs) not in sys.path:
    sys.path.insert(0, str(project_root_abs))
if str(src_path_abs) not in sys.path:
    sys.path.insert(0, str(src_path_abs))

print(f"Connector tests - Python path includes: {project_root_abs}")
print(f"Connector tests - Python path includes: {src_path_abs}")

# Helper function to import modules directly, bypassing __init__.py circular imports
def import_module_direct(module_name, file_path):
    """Import a module directly from file path, bypassing package __init__.py"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
