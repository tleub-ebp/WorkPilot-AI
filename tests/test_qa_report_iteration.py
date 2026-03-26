#!/usr/bin/env python3
"""
Tests for QA Report - Iteration Tracking
"""

import json
import sys
from pathlib import Path

import pytest

# Add tests directory and backend to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

# Setup mocks before importing auto-claude modules
from qa_report_helpers import cleanup_qa_report_mocks, setup_qa_report_mocks

# Setup mocks
setup_qa_report_mocks()

# Import report functions after mocking
from qa.criteria import (
    load_implementation_plan,
    save_implementation_plan,
)
from qa.report import (
    get_iteration_history,
    record_iteration,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(scope="module", autouse=True)
def cleanup_mocked_modules():
    """Restore original modules after all tests in this module complete."""
    yield
    cleanup_qa_report_mocks()


@pytest.fixture
def spec_with_plan(tmp_path: Path) -> Path:
    """Create a spec dir with a basic implementation plan."""
    spec = tmp_path / "spec"
    spec.mkdir()
    plan = {"spec_name": "test", "subtasks": []}
    save_implementation_plan(spec, plan)
    return spec


# =============================================================================
# ITERATION TRACKING TESTS
# =============================================================================


class TestGetIterationHistory:
    """Tests for get_iteration_history() function."""

    def test_empty_spec_dir(self, spec_dir: Path) -> None:
        history = get_iteration_history(spec_dir)
        assert history == []

    def test_no_plan_file(self, spec_dir: Path) -> None:
        history = get_iteration_history(spec_dir)
        assert history == []

    def test_plan_without_history_key(self, spec_dir: Path) -> None:
        plan = {"spec_name": "test"}
        save_implementation_plan(spec_dir, plan)
        history = get_iteration_history(spec_dir)
        assert history == []

    def test_with_history_data(self, spec_dir: Path) -> None:
        plan = {
            "spec_name": "test",
            "qa_iteration_history": [
                {"iteration": 1, "status": "rejected", "issues": []},
                {"iteration": 2, "status": "approved", "issues": []},
            ],
        }
        save_implementation_plan(spec_dir, plan)
        history = get_iteration_history(spec_dir)
        assert len(history) == 2
        assert history[0]["iteration"] == 1
        assert history[1]["status"] == "approved"


class TestRecordIteration:
    """Tests for record_iteration() function."""

    def test_creates_history(self, spec_with_plan: Path) -> None:
        issues = [{"title": "Test issue", "type": "error"}]
        result = record_iteration(spec_with_plan, 1, "rejected", issues, 5.5)
        assert result is True
        history = get_iteration_history(spec_with_plan)
        assert len(history) == 1
        assert history[0]["iteration"] == 1
        assert history[0]["status"] == "rejected"
        assert history[0]["issues"] == issues
        assert history[0]["duration_seconds"] == pytest.approx(5.5)

    def test_multiple_iterations(self, spec_with_plan: Path) -> None:
        record_iteration(spec_with_plan, 1, "rejected", [{"title": "Issue 1"}])
        record_iteration(spec_with_plan, 2, "rejected", [{"title": "Issue 2"}])
        record_iteration(spec_with_plan, 3, "approved", [])
        history = get_iteration_history(spec_with_plan)
        assert len(history) == 3
        assert history[0]["iteration"] == 1
        assert history[2]["iteration"] == 3

    def test_updates_qa_stats(self, spec_with_plan: Path) -> None:
        record_iteration(
            spec_with_plan, 1, "rejected", [{"title": "Error", "type": "error"}]
        )
        record_iteration(
            spec_with_plan, 2, "rejected", [{"title": "Warning", "type": "warning"}]
        )
        plan = load_implementation_plan(spec_with_plan)
        stats = plan.get("qa_stats", {})
        assert stats["total_iterations"] == 2
        assert stats["last_iteration"] == 2
        assert stats["last_status"] == "rejected"
        assert "error" in stats["issues_by_type"]
        assert "warning" in stats["issues_by_type"]

    def test_no_duration(self, spec_with_plan: Path) -> None:
        record_iteration(spec_with_plan, 1, "approved", [])
        history = get_iteration_history(spec_with_plan)
        assert "duration_seconds" not in history[0]

    def test_creates_plan_if_missing(self, spec_dir: Path) -> None:
        result = record_iteration(spec_dir, 1, "rejected", [])
        assert result is True
        plan = load_implementation_plan(spec_dir)
        assert "qa_iteration_history" in plan

    def test_rounds_duration(self, spec_with_plan: Path) -> None:
        record_iteration(spec_with_plan, 1, "rejected", [], 12.345678)
        history = get_iteration_history(spec_with_plan)
        assert history[0]["duration_seconds"] == pytest.approx(12.35)

    def test_includes_timestamp(self, spec_with_plan: Path) -> None:
        record_iteration(spec_with_plan, 1, "rejected", [])
        history = get_iteration_history(spec_with_plan)
        assert "timestamp" in history[0]
        assert "T" in history[0]["timestamp"]

    def test_counts_issues_by_type(self, spec_with_plan: Path) -> None:
        record_iteration(
            spec_with_plan,
            1,
            "rejected",
            [
                {"title": "Error 1", "type": "error"},
                {"title": "Error 2", "type": "error"},
                {"title": "Warning 1", "type": "warning"},
            ],
        )
        plan = load_implementation_plan(spec_with_plan)
        assert plan["qa_stats"]["issues_by_type"]["error"] == 2
        assert plan["qa_stats"]["issues_by_type"]["warning"] == 1

    def test_unknown_issue_type(self, spec_with_plan: Path) -> None:
        record_iteration(
            spec_with_plan,
            1,
            "rejected",
            [{"title": "Issue without type"}],
        )
        plan = load_implementation_plan(spec_with_plan)
        assert plan["qa_stats"]["issues_by_type"]["unknown"] == 1
