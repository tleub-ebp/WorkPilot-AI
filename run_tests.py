#!/usr/bin/env python3
"""
Simple script to run tests with correct Python path
"""
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Run pytest with the correct path
os.system("pytest tests/ -v")
