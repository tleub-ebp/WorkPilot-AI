#!/usr/bin/env python3
"""
Tests simplifiés pour auto-fix loop - sans dépendances externes
"""
import sys
import json
from pathlib import Path
import tempfile
import pytest

# Add backend to path
backend_dir = Path(__file__).parent.parent / "apps" / "backend"
sys.path.insert(0, str(backend_dir))


def test_basic_imports():
    from qa.auto_fix_loop import (
        DEFAULT_MAX_AUTO_FIX_ATTEMPTS,
        AutoFixLoop,
        AutoFixTestResult,
        AutoFixAttempt,
    )
    assert DEFAULT_MAX_AUTO_FIX_ATTEMPTS > 0


def test_metrics_imports():
    from qa.auto_fix_metrics import (
        AutoFixMetricsTracker,
        AutoFixStats,
        get_auto_fix_stats,
        record_auto_fix_run,
    )


def test_create_instance():
    from qa.auto_fix_loop import AutoFixLoop
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "project"
        project_dir.mkdir()
        spec_dir = Path(tmpdir) / "spec"
        spec_dir.mkdir()
        plan = {"spec_name": "test"}
        (spec_dir / "implementation_plan.json").write_text(json.dumps(plan))
        loop = AutoFixLoop(
            project_dir=project_dir,
            spec_dir=spec_dir,
            model="test-model",
            verbose=False,
        )
        assert loop.project_dir.name == "project"
        assert loop.spec_dir.name == "spec"
        assert loop.model == "test-model"


def test_dataclasses():
    from qa.auto_fix_loop import AutoFixTestResult, AutoFixAttempt
    result = AutoFixTestResult(
        executed=True,
        passed=False,
        output="test output",
        error="test error",
        duration=1.5,
        test_count=5,
        failed_count=2,
    )
    assert result.test_count == 5
    assert result.failed_count == 2

    attempt = AutoFixAttempt(
        attempt_number=1,
        test_result=result,
        fix_applied=True,
        fix_status="fixed",
        duration=30.0,
        error_pattern="assertion_failure",
        timestamp=1234567890.0,
    )
    assert attempt.attempt_number == 1
