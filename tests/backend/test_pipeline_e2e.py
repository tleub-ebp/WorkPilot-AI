"""End-to-end tests for the build pipeline's data flow.

These tests exercise the **state-machine / data-flow** side of the
Planner → Coder → QA → Merge pipeline without spawning a real LLM
agent. The goal is to catch regressions in how phases read and update
the shared artifacts (``implementation_plan.json``, subtask statuses,
progress counters, merge trigger conditions) — the part that's
deterministic, cheap to test, and has historically been where bugs
hide.

What's NOT covered here:

* Real Claude/OpenAI/… calls: those belong in manual smoke tests or
  nightly jobs with a test API key, not in the unit test suite.
* UI/Electron: covered by the vitest suite in ``apps/frontend``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[2] / "apps" / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from core.progress import (  # noqa: E402
    count_subtasks,
    count_subtasks_detailed,
    get_next_subtask,
    get_progress_percentage,
    is_build_complete,
)


def _make_plan(subtask_statuses: list[str]) -> dict:
    """Build an implementation plan with the given statuses in a single phase.

    The goal here is to mirror the real shape (phases → subtasks) without
    pulling in the planner — so we can replay arbitrary progress states.
    """
    return {
        "feature": "Test Feature",
        "workflow_type": "feature",
        "services_involved": ["backend"],
        "phases": [
            {
                "id": "phase-1",
                "name": "Implementation",
                "type": "implementation",
                "subtasks": [
                    {
                        "id": f"subtask-{i + 1}",
                        "description": f"Implement step {i + 1}",
                        "status": status,
                    }
                    for i, status in enumerate(subtask_statuses)
                ],
            }
        ],
    }


def _write_plan(spec_dir: Path, plan: dict) -> None:
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / "implementation_plan.json").write_text(
        json.dumps(plan), encoding="utf-8"
    )


class TestPlannerToCoderHandoff:
    """When the planner writes an implementation plan, the coder must be
    able to read it back and know which subtask to work on first."""

    def test_fresh_plan_is_not_complete(self, tmp_path: Path) -> None:
        _write_plan(tmp_path, _make_plan(["pending", "pending"]))
        assert is_build_complete(tmp_path) is False
        assert count_subtasks(tmp_path) == (0, 2)
        assert get_progress_percentage(tmp_path) == 0.0

    def test_next_subtask_points_at_first_pending(self, tmp_path: Path) -> None:
        _write_plan(tmp_path, _make_plan(["completed", "pending", "pending"]))
        next_task = get_next_subtask(tmp_path)
        assert next_task is not None, "coder must have something to work on"
        assert next_task["id"] == "subtask-2"

    def test_empty_plan_has_no_next_subtask(self, tmp_path: Path) -> None:
        _write_plan(tmp_path, _make_plan([]))
        assert get_next_subtask(tmp_path) is None
        assert is_build_complete(tmp_path) is False  # nothing to complete

    def test_missing_plan_file_defaults_to_zeros(self, tmp_path: Path) -> None:
        """A missing plan file must not crash downstream phases."""
        assert count_subtasks(tmp_path) == (0, 0)
        assert is_build_complete(tmp_path) is False


class TestCoderProgressTracking:
    """As the coder marks subtasks complete, progress counters must
    reflect that without any extra synchronization."""

    def test_partial_progress(self, tmp_path: Path) -> None:
        _write_plan(
            tmp_path, _make_plan(["completed", "completed", "pending", "pending"])
        )
        assert count_subtasks(tmp_path) == (2, 4)
        assert get_progress_percentage(tmp_path) == 50.0
        assert is_build_complete(tmp_path) is False

    def test_detailed_counts_split_by_status(self, tmp_path: Path) -> None:
        _write_plan(
            tmp_path,
            _make_plan(["completed", "in_progress", "pending", "failed"]),
        )
        detailed = count_subtasks_detailed(tmp_path)
        assert detailed["completed"] == 1
        assert detailed["in_progress"] == 1
        assert detailed["pending"] == 1
        assert detailed["failed"] == 1
        assert detailed["total"] == 4

    def test_unknown_status_falls_back_to_pending_bucket(
        self, tmp_path: Path
    ) -> None:
        """Forward compat: a new status we don't recognize yet shouldn't
        silently disappear from the UI — it should count as pending so
        the user sees there's still work left."""
        _write_plan(tmp_path, _make_plan(["completed", "blocked"]))
        detailed = count_subtasks_detailed(tmp_path)
        assert detailed["total"] == 2
        assert detailed["completed"] == 1
        assert detailed["pending"] == 1  # "blocked" falls into pending


class TestQaGatesBuildCompletion:
    """The merge phase should only see ``is_build_complete()`` go true
    once *every* subtask is in the ``completed`` state — including any
    QA-fix subtasks that may have been appended to the plan."""

    def test_all_completed_triggers_build_complete(self, tmp_path: Path) -> None:
        _write_plan(tmp_path, _make_plan(["completed", "completed", "completed"]))
        assert is_build_complete(tmp_path) is True
        assert count_subtasks(tmp_path) == (3, 3)
        assert get_progress_percentage(tmp_path) == 100.0

    def test_one_failed_blocks_build_complete(self, tmp_path: Path) -> None:
        _write_plan(
            tmp_path, _make_plan(["completed", "completed", "failed"])
        )
        assert is_build_complete(tmp_path) is False

    def test_qa_added_subtask_defers_build_complete(self, tmp_path: Path) -> None:
        """Simulates QA appending a fix subtask after the initial plan:
        the build must not be considered complete until that fix lands."""
        _write_plan(tmp_path, _make_plan(["completed", "completed"]))
        assert is_build_complete(tmp_path) is True

        # QA appends a new subtask while the build was "complete".
        plan = _make_plan(["completed", "completed"])
        plan["phases"][0]["subtasks"].append(
            {
                "id": "qa-fix-1",
                "description": "Fix QA regression",
                "status": "pending",
            }
        )
        _write_plan(tmp_path, plan)
        assert is_build_complete(tmp_path) is False
        assert get_next_subtask(tmp_path)["id"] == "qa-fix-1"


class TestPipelineArtifactResilience:
    """Malformed artifacts on disk must degrade gracefully — the pipeline
    should report zero progress rather than crashing the whole build."""

    def test_corrupted_json_returns_zero_progress(self, tmp_path: Path) -> None:
        (tmp_path / "implementation_plan.json").write_text(
            "{not valid json", encoding="utf-8"
        )
        assert count_subtasks(tmp_path) == (0, 0)
        assert is_build_complete(tmp_path) is False

    def test_plan_with_no_phases_key(self, tmp_path: Path) -> None:
        _write_plan(tmp_path, {"feature": "x"})  # no "phases" key
        assert count_subtasks(tmp_path) == (0, 0)


@pytest.mark.parametrize(
    ("statuses", "expected_pct"),
    [
        ([], 0.0),
        (["pending"], 0.0),
        (["completed"], 100.0),
        (["completed", "pending"], 50.0),
        (["completed", "completed", "completed", "pending"], 75.0),
    ],
)
def test_progress_percentage_matrix(
    tmp_path: Path, statuses: list[str], expected_pct: float
) -> None:
    _write_plan(tmp_path, _make_plan(statuses))
    assert get_progress_percentage(tmp_path) == pytest.approx(expected_pct)
