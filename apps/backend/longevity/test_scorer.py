"""Tests for the LongevityScorer."""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from longevity import HealthGrade, LongevityScorer, score_codebase
from tech_debt.scanner import DebtItem, DebtReport, DebtTrendPoint


def _make_item(kind: str, file_path: str = "src/x.py", cost: float = 1.0) -> DebtItem:
    return DebtItem(
        id=f"{kind}-{file_path}",
        kind=kind,  # type: ignore[arg-type]
        file_path=file_path,
        line=1,
        message=f"{kind} signal",
        cost=cost,
        effort=0.5,
        roi=cost / 0.5,
    )


def _make_report(
    items: list[DebtItem] | None = None,
    trend: list[DebtTrendPoint] | None = None,
    project_path: str = "/tmp/fake-project",
) -> DebtReport:
    return DebtReport(
        project_path=project_path,
        scanned_at=time.time(),
        items=items or [],
        trend=trend or [],
        summary={},
    )


class TestGrade:
    def test_grade_thresholds(self) -> None:
        assert HealthGrade.from_score(95) == HealthGrade.A
        assert HealthGrade.from_score(80) == HealthGrade.B
        assert HealthGrade.from_score(65) == HealthGrade.C
        assert HealthGrade.from_score(50) == HealthGrade.D
        assert HealthGrade.from_score(10) == HealthGrade.F

    def test_grade_at_boundaries(self) -> None:
        assert HealthGrade.from_score(90) == HealthGrade.A
        assert HealthGrade.from_score(89.99) == HealthGrade.B
        assert HealthGrade.from_score(0) == HealthGrade.F


class TestScorer:
    def test_clean_report_scores_100(self) -> None:
        scorer = LongevityScorer()
        report = scorer.score_report(_make_report(items=[]), approx_loc=10_000)
        assert report.score == 100.0
        assert report.grade == HealthGrade.A

    def test_todos_below_saturation_partial_penalty(self) -> None:
        scorer = LongevityScorer()
        # 5 TODOs in 1 kLoC → half of saturation (10/kLoC)
        items = [_make_item("todo_fixme") for _ in range(5)]
        report = scorer.score_report(_make_report(items=items), approx_loc=1_000)
        assert 0 < report.penalties["todo_fixme"] < scorer.MAX_PENALTY_TODOS
        assert report.score < 100

    def test_penalty_saturates(self) -> None:
        scorer = LongevityScorer()
        # 100 TODOs in 1 kLoC → way past saturation, penalty must cap.
        items = [_make_item("todo_fixme") for _ in range(100)]
        report = scorer.score_report(_make_report(items=items), approx_loc=1_000)
        assert report.penalties["todo_fixme"] == pytest.approx(scorer.MAX_PENALTY_TODOS)

    def test_score_floors_when_all_signals_saturate(self) -> None:
        scorer = LongevityScorer()
        # Stack every signal at saturation — should hit the F grade.
        # Max combined penalties = 20+15+15+15+25 = 90, so floor is 10.
        items = (
            [_make_item("todo_fixme") for _ in range(100)]
            + [_make_item("long_function") for _ in range(100)]
            + [_make_item("deep_complexity") for _ in range(100)]
            + [_make_item("duplication") for _ in range(100)]
            + [_make_item("stale_deps") for _ in range(50)]
        )
        report = scorer.score_report(_make_report(items=items), approx_loc=1_000)
        assert report.score <= 10.0
        assert report.grade == HealthGrade.F

    def test_score_clamped_to_zero_with_negative_trend(self) -> None:
        scorer = LongevityScorer()
        # Same saturated signals + a degrading trend that pushes us below 0
        # — the clamp must hold.
        now = time.time()
        trend = [
            DebtTrendPoint(
                timestamp=now - 86400, total_items=10, total_cost=10.0, avg_roi=2.0
            ),
            DebtTrendPoint(
                timestamp=now, total_items=1_000, total_cost=1_000.0, avg_roi=2.0
            ),
        ]
        items = (
            [_make_item("todo_fixme") for _ in range(100)]
            + [_make_item("long_function") for _ in range(100)]
            + [_make_item("deep_complexity") for _ in range(100)]
            + [_make_item("duplication") for _ in range(100)]
            + [_make_item("stale_deps") for _ in range(50)]
        )
        report = scorer.score_report(
            _make_report(items=items, trend=trend), approx_loc=1_000
        )
        assert report.score == 0.0

    def test_stale_deps_uses_absolute_count_not_density(self) -> None:
        scorer = LongevityScorer()
        # 20 stale deps should fully saturate regardless of LoC.
        items = [_make_item("stale_deps") for _ in range(20)]
        small = scorer.score_report(_make_report(items=items), approx_loc=100)
        big = scorer.score_report(_make_report(items=items), approx_loc=1_000_000)
        assert small.penalties["stale_deps"] == pytest.approx(
            scorer.MAX_PENALTY_STALE_DEPS
        )
        assert big.penalties["stale_deps"] == pytest.approx(
            scorer.MAX_PENALTY_STALE_DEPS
        )

    def test_riskiest_files_aggregated_by_path(self) -> None:
        scorer = LongevityScorer()
        items = [
            _make_item("todo_fixme", file_path="src/hot.py", cost=5.0),
            _make_item("long_function", file_path="src/hot.py", cost=3.0),
            _make_item("todo_fixme", file_path="src/cold.py", cost=1.0),
        ]
        report = scorer.score_report(_make_report(items=items), approx_loc=1_000)
        assert len(report.riskiest_files) >= 1
        top = report.riskiest_files[0]
        assert top["file_path"] == "src/hot.py"
        assert top["items"] == 2
        assert top["total_cost"] == 8.0
        assert set(top["kinds"]) == {"todo_fixme", "long_function"}

    def test_no_trend_means_no_projection(self) -> None:
        scorer = LongevityScorer()
        report = scorer.score_report(_make_report(trend=[]), approx_loc=1_000)
        assert report.projection is None

    def test_growing_debt_projects_lower_score(self) -> None:
        scorer = LongevityScorer()
        now = time.time()
        # Two snapshots 4 weeks apart, debt doubled.
        trend = [
            DebtTrendPoint(
                timestamp=now - 4 * 7 * 86400,
                total_items=10,
                total_cost=10.0,
                avg_roi=2.0,
            ),
            DebtTrendPoint(timestamp=now, total_items=30, total_cost=30.0, avg_roi=2.0),
        ]
        report = scorer.score_report(
            _make_report(items=[_make_item("todo_fixme")], trend=trend),
            approx_loc=1_000,
        )
        assert report.projection is not None
        assert report.projection.direction == "degrading"
        assert (
            report.projection.projected_score_in_6_months
            < report.projection.current_score
        )

    def test_shrinking_debt_gets_bonus(self) -> None:
        scorer = LongevityScorer()
        now = time.time()
        trend = [
            DebtTrendPoint(
                timestamp=now - 4 * 7 * 86400,
                total_items=50,
                total_cost=50.0,
                avg_roi=2.0,
            ),
            DebtTrendPoint(timestamp=now, total_items=10, total_cost=10.0, avg_roi=2.0),
        ]
        report = scorer.score_report(
            _make_report(items=[_make_item("todo_fixme")], trend=trend),
            approx_loc=1_000,
        )
        assert report.projection.direction == "improving"
        assert report.bonuses.get("trend", 0) > 0

    def test_to_dict_serialisable(self) -> None:
        import json

        scorer = LongevityScorer()
        items = [_make_item("todo_fixme")]
        report = scorer.score_report(_make_report(items=items), approx_loc=1_000)
        # Must be JSON-serialisable for HTTP API consumption.
        encoded = json.dumps(report.to_dict())
        decoded = json.loads(encoded)
        assert decoded["grade"] in {"A", "B", "C", "D", "F"}
        assert "penalties" in decoded


class TestEndToEnd:
    def test_score_codebase_on_empty_dir(self, tmp_path: Path) -> None:
        # Should not crash on an empty project; expect a near-perfect score.
        report = score_codebase(tmp_path)
        assert report.score >= 95.0

    def test_score_codebase_with_real_todos(self, tmp_path: Path) -> None:
        # Drop a synthetic source file with TODOs and run the full pipeline.
        src = tmp_path / "src"
        src.mkdir()
        (src / "messy.py").write_text(
            "\n".join(
                [
                    "def f():",
                    "    # TODO: refactor this",
                    "    pass",
                    "",
                    "def g():",
                    "    # FIXME: broken",
                    "    pass",
                ]
            )
        )
        report = score_codebase(tmp_path)
        assert report.score < 100.0
        assert report.summary["by_kind"].get("todo_fixme", 0) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
