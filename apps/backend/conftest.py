"""Root conftest.py — adds backend root to sys.path for all test modules."""

import sys
from pathlib import Path

# Ensure the backend root is on sys.path so absolute imports work
# (e.g. `from streaming.agent_wrapper import ...`, `from cli.main import ...`)
backend_root = str(Path(__file__).parent)
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)
