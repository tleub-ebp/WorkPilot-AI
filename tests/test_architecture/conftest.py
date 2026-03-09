"""
Local conftest for architecture tests.

This prevents pytest from loading the parent conftest.py which has
Azure DevOps dependencies not always available.
"""

import sys
from pathlib import Path

# Add backend to sys.path so architecture package is importable
backend_path = str(Path(__file__).parent.parent.parent / "apps" / "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)
