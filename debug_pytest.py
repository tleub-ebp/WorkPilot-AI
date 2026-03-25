#!/usr/bin/env python3
"""Debug script to understand pytest import issues"""
import sys
import os
from pathlib import Path

print("=== DEBUG: Python path during pytest ===")
print(f"Current working directory: {os.getcwd()}")
print(f"Python path entries:")
for i, p in enumerate(sys.path[:10]):
    print(f"  {i}: {p}")
    print(f"     Exists: {os.path.exists(p) if p != '<frozen importlib._bootstrap>' else 'N/A'}")

print("\n=== DEBUG: Trying direct import ===")
try:
    from src.connectors.azure_devops.exceptions import APIError
    print("✅ Direct import successful!")
except Exception as e:
    print(f"❌ Direct import failed: {e}")
    import traceback
    traceback.print_exc()

print("\n=== DEBUG: Checking src directory structure ===")
src_path = Path("./src")
if src_path.exists():
    print(f"src directory exists: {src_path}")
    connectors_path = src_path / "connectors"
    if connectors_path.exists():
        print(f"src/connectors directory exists: {connectors_path}")
        azure_devops_path = connectors_path / "azure_devops"
        if azure_devops_path.exists():
            print(f"src/connectors/azure_devops directory exists: {azure_devops_path}")
            exceptions_file = azure_devops_path / "exceptions.py"
            print(f"exceptions.py exists: {exceptions_file.exists()}")
        else:
            print(f"src/connectors/azure_devops directory does not exist")
    else:
        print(f"src/connectors directory does not exist")
else:
    print(f"src directory does not exist")
