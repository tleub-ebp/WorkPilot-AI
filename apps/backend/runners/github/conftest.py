"""
conftest.py for runners/github tests.
Adds the runners/github directory to sys.path so test modules
can import local modules directly by name.
"""

import sys
from pathlib import Path

# Add runners/github to sys.path so imports like `from context_gatherer import ...` work
sys.path.insert(0, str(Path(__file__).parent))
