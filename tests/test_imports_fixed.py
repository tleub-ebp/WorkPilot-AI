#!/usr/bin/env python3
"""
Quick test to verify imports work after fixing optional dependencies
"""
import sys
from pathlib import Path

import pytest

# Add backend to path
backend_dir = Path(__file__).parent.parent / "apps" / "backend"
sys.path.insert(0, str(backend_dir))


def test_auto_fix_loop_import():
    from qa.auto_fix_loop import AutoFixAttempt, AutoFixLoop, AutoFixTestResult
    assert AutoFixLoop is not None


def test_auto_fix_metrics_import():
    from qa.auto_fix_metrics import AutoFixMetricsTracker, get_auto_fix_stats
    assert AutoFixMetricsTracker is not None


def test_qa_package_exports():
    from qa import DEFAULT_MAX_AUTO_FIX_ATTEMPTS, AutoFixLoop
    assert DEFAULT_MAX_AUTO_FIX_ATTEMPTS > 0
