#!/usr/bin/env python3
"""
Tests auto-fix simplifiés - Version SANS imports externes
"""
import py_compile
import sys
from pathlib import Path

import pytest

backend_dir = Path(__file__).parent.parent / "apps" / "backend"


def test_auto_fix_files_syntax():
    files = [
        backend_dir / "qa" / "auto_fix_loop.py",
        backend_dir / "qa" / "auto_fix_metrics.py",
    ]
    for f in files:
        assert f.exists(), f"{f.name} not found"
        py_compile.compile(str(f), doraise=True)


def test_auto_fix_file_structure():
    assert (backend_dir / "qa" / "auto_fix_loop.py").exists()
    assert (backend_dir / "qa" / "auto_fix_metrics.py").exists()
    assert (backend_dir / "qa" / "__init__.py").exists()

    content = (backend_dir / "qa" / "auto_fix_loop.py").read_text(encoding="utf-8")
    assert "@dataclass" in content
    assert "class AutoFixTestResult" in content
    assert "class AutoFixAttempt" in content


def test_auto_fix_constants_and_methods():
    content = (backend_dir / "qa" / "auto_fix_loop.py").read_text(encoding="utf-8")
    assert "DEFAULT_MAX_AUTO_FIX_ATTEMPTS" in content
    assert "TEST_EXECUTION_TIMEOUT" in content
    assert "async def run_until_green" in content
    assert "def _analyze_failure" in content
    assert "def _parse_test_counts" in content
