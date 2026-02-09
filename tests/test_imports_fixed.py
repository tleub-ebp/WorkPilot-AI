#!/usr/bin/env python3
"""
Quick test to verify imports work after fixing optional dependencies
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent / "apps" / "backend"
sys.path.insert(0, str(backend_dir))

print("Testing imports after optional dependency fix...\n")

# Test 1: Import auto_fix_loop
print("[1/3] Testing auto_fix_loop import...")
try:
    from qa.auto_fix_loop import AutoFixLoop, TestResult, AutoFixAttempt
    print("  ✓ AutoFixLoop imported successfully")
    print("  ✓ TestResult imported successfully")
    print("  ✓ AutoFixAttempt imported successfully")
except Exception as e:
    print(f"  ✗ Error: {e}")
    sys.exit(1)

# Test 2: Import auto_fix_metrics
print("\n[2/3] Testing auto_fix_metrics import...")
try:
    from qa.auto_fix_metrics import AutoFixMetricsTracker, get_auto_fix_stats
    print("  ✓ AutoFixMetricsTracker imported successfully")
    print("  ✓ get_auto_fix_stats imported successfully")
except Exception as e:
    print(f"  ✗ Error: {e}")
    sys.exit(1)

# Test 3: Import via qa package
print("\n[3/3] Testing qa package exports...")
try:
    from qa import AutoFixLoop, DEFAULT_MAX_AUTO_FIX_ATTEMPTS
    print("  ✓ AutoFixLoop exported via qa package")
    print(f"  ✓ DEFAULT_MAX_AUTO_FIX_ATTEMPTS = {DEFAULT_MAX_AUTO_FIX_ATTEMPTS}")
except Exception as e:
    print(f"  ✗ Error: {e}")
    sys.exit(1)

print("\n✅ All imports successful!")
print("✨ Optional dependencies handled correctly!")
