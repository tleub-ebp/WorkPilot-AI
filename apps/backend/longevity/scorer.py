"""Longevity Scorer.

Computes a 0–100 health score for a codebase from the signals already
collected by `tech_debt.scanner`. Higher = healthier.

Scoring philosophy
------------------
We start at 100 and subtract penalties weighted by how predictive each
signal is of long-term maintainability:

* **TODO/FIXME density** (per 1k LoC)   → up to -20 points
* **Long functions density**             → up to -15 points
* **Deep nesting density**               → up to -15 points
* **Code duplication density**           → up to -15 points
* **Stale dependencies count**           → up to -25 points (heavy weight: stale deps
                                          rot fast and cause both security and CI pain)
* **Trend slope**                        → up to -10 points if debt is growing,
                                          or +5 bonus if shrinking

The exact thresholds are tunable and exposed as class attributes so callers
can re-grade an existing report without re-scanning.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from tech_debt.scanner import DebtItem, DebtReport, DebtTrendPoint, scan_project

logger = logging.getLogger(__name__)


class HealthGrade(str, Enum):
    """Letter grade for quick at-a-glance reporting."""

    A = "A"  # 90–100 — excellent
    B = "B"  # 75–89  — good
    C = "C"  # 60–74  — needs attention
    D = "D"  # 40–59  — poor
    F = "F"  # 0–39   — critical

    @classmethod
    def from_score(cls, score: float) -> HealthGrade:
        if score >= 90:
            return cls.A
        if score >= 75:
            return cls.B
        if score >= 60:
            return cls.C
        if score >= 40:
            return cls.D
        return cls.F


@dataclass
class LongevityProjection:
    """Linear extrapolation of where the score is heading."""

    weeks_observed: int
    current_score: float
    projected_score_in_6_months: float
    projected_grade_in_6_months: HealthGrade
    direction: str  # "improving" | "stable" | "degrading"
    weekly_delta: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "weeks_observed": self.weeks_observed,
            "current_score": round(self.current_score, 2),
            "projected_score_in_6_months": round(self.projected_score_in_6_months, 2),
            "projected_grade_in_6_months": self.projected_grade_in_6_months.value,
            "direction": self.direction,
            "weekly_delta": round(self.weekly_delta, 3),
        }


@dataclass
class LongevityReport:
    """Output of the scorer."""

    project_path: str
    score: float
    grade: HealthGrade
    penalties: dict[str, float]  # per-signal point deductions (positive numbers)
    bonuses: dict[str, float]
    summary: dict[str, Any]
    projection: LongevityProjection | None = None
    riskiest_files: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_path": self.project_path,
            "score": round(self.score, 2),
            "grade": self.grade.value,
            "penalties": {k: round(v, 2) for k, v in self.penalties.items()},
            "bonuses": {k: round(v, 2) for k, v in self.bonuses.items()},
            "summary": self.summary,
            "projection": self.projection.to_dict() if self.projection else None,
            "riskiest_files": self.riskiest_files,
        }


class LongevityScorer:
    """Aggregates `DebtReport` data into a health score."""

    # Penalty weights — max points removable per signal.
    MAX_PENALTY_TODOS = 20.0
    MAX_PENALTY_LONG_FUNCS = 15.0
    MAX_PENALTY_DEEP_NESTING = 15.0
    MAX_PENALTY_DUPLICATION = 15.0
    MAX_PENALTY_STALE_DEPS = 25.0
    MAX_PENALTY_TREND = 10.0
    MAX_BONUS_TREND = 5.0

    # Density thresholds (signals per 1k LoC where the penalty saturates).
    TODO_SATURATION_PER_KLOC = 10.0
    LONG_FUNC_SATURATION_PER_KLOC = 5.0
    DEEP_NESTING_SATURATION_PER_KLOC = 3.0
    DUPLICATION_SATURATION_PER_KLOC = 4.0
    STALE_DEPS_SATURATION = 20  # absolute count

    def score_report(
        self,
        report: DebtReport,
        approx_loc: int | None = None,
    ) -> LongevityReport:
        """Score a pre-computed `DebtReport`."""
        loc = approx_loc or self._estimate_loc(report)
        # Avoid division-by-zero edge cases in tests on synthetic projects.
        kloc = max(loc / 1000.0, 0.1)

        counts = _count_by_kind(report.items)
        penalties = self._penalties(counts, kloc)

        bonuses, projection = self._trend_signal(report)

        score = max(
            0.0, min(100.0, 100.0 - sum(penalties.values()) + sum(bonuses.values()))
        )
        grade = HealthGrade.from_score(score)

        riskiest = _riskiest_files(report.items, top_n=5)

        return LongevityReport(
            project_path=report.project_path,
            score=score,
            grade=grade,
            penalties=penalties,
            bonuses=bonuses,
            summary={
                "loc": loc,
                "total_debt_items": len(report.items),
                "by_kind": counts,
            },
            projection=projection,
            riskiest_files=riskiest,
        )

    # ------------------------------------------------------------------
    # Internal helpers

    def _penalties(self, counts: dict[str, int], kloc: float) -> dict[str, float]:
        return {
            "todo_fixme": _saturating_penalty(
                counts.get("todo_fixme", 0) / kloc,
                self.TODO_SATURATION_PER_KLOC,
                self.MAX_PENALTY_TODOS,
            ),
            "long_function": _saturating_penalty(
                counts.get("long_function", 0) / kloc,
                self.LONG_FUNC_SATURATION_PER_KLOC,
                self.MAX_PENALTY_LONG_FUNCS,
            ),
            "deep_complexity": _saturating_penalty(
                counts.get("deep_complexity", 0) / kloc,
                self.DEEP_NESTING_SATURATION_PER_KLOC,
                self.MAX_PENALTY_DEEP_NESTING,
            ),
            "duplication": _saturating_penalty(
                counts.get("duplication", 0) / kloc,
                self.DUPLICATION_SATURATION_PER_KLOC,
                self.MAX_PENALTY_DUPLICATION,
            ),
            "stale_deps": _saturating_penalty(
                counts.get("stale_deps", 0),
                self.STALE_DEPS_SATURATION,
                self.MAX_PENALTY_STALE_DEPS,
            ),
        }

    def _trend_signal(
        self, report: DebtReport
    ) -> tuple[dict[str, float], LongevityProjection | None]:
        """Compute trend bonus/penalty and a 6-month projection.

        We need at least two trend points to compute a slope. With one or
        zero, we return no bonus and no projection (the absence is the signal).
        """
        bonuses: dict[str, float] = {}
        if len(report.trend) < 2:
            return bonuses, None

        # Sort by timestamp just in case persistence didn't.
        trend = sorted(report.trend, key=lambda p: p.timestamp)
        first, last = trend[0], trend[-1]

        # Span in weeks; floor at 1 to avoid divide-by-zero on synthetic data.
        span_seconds = max(last.timestamp - first.timestamp, 1.0)
        span_weeks = max(span_seconds / (7 * 24 * 3600), 1.0 / 7.0)

        delta_items = last.total_items - first.total_items
        weekly_delta = delta_items / span_weeks  # positive = growing debt

        # Project current score 26 weeks out using a rough rule: each extra
        # debt item costs ~0.05 score points (saturates at the same caps).
        current_pseudo_score = 100.0 - min(60.0, last.total_items * 0.05)
        projected_items = max(0.0, last.total_items + weekly_delta * 26)
        projected_score = 100.0 - min(60.0, projected_items * 0.05)

        if weekly_delta < -0.1:
            direction = "improving"
            bonuses["trend"] = min(self.MAX_BONUS_TREND, abs(weekly_delta) * 1.0)
        elif weekly_delta > 0.1:
            direction = "degrading"
            # Use a penalty hidden as a *negative* bonus so callers see the
            # full picture in one place.
            bonuses["trend"] = -min(self.MAX_PENALTY_TREND, weekly_delta * 1.0)
        else:
            direction = "stable"

        projection = LongevityProjection(
            weeks_observed=int(span_weeks),
            current_score=current_pseudo_score,
            projected_score_in_6_months=projected_score,
            projected_grade_in_6_months=HealthGrade.from_score(projected_score),
            direction=direction,
            weekly_delta=weekly_delta,
        )
        return bonuses, projection

    def _estimate_loc(self, report: DebtReport) -> int:
        """Best-effort LoC estimate by walking the project tree."""
        from tech_debt.scanner import _iter_source_files

        root = Path(report.project_path)
        if not root.exists():
            return 1
        total = 0
        for path in _iter_source_files(root):
            try:
                total += sum(1 for _ in path.read_bytes().splitlines())
            except OSError:
                continue
        return max(total, 1)


def score_codebase(project_path: str | Path) -> LongevityReport:
    """Convenience entry point: scan + score in one call."""
    debt = scan_project(project_path)
    return LongevityScorer().score_report(debt)


# ----------------------------------------------------------------------
# Module-level helpers


def _saturating_penalty(value: float, saturation: float, max_penalty: float) -> float:
    """Linear penalty that caps at `max_penalty` once `value >= saturation`."""
    if value <= 0 or saturation <= 0:
        return 0.0
    return min(max_penalty, (value / saturation) * max_penalty)


def _count_by_kind(items: list[DebtItem]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        counts[item.kind] = counts.get(item.kind, 0) + 1
    return counts


def _riskiest_files(items: list[DebtItem], top_n: int = 5) -> list[dict[str, Any]]:
    """Aggregate debt by file, ranked by total cost."""
    by_file: dict[str, dict[str, Any]] = {}
    for item in items:
        entry = by_file.setdefault(
            item.file_path,
            {
                "file_path": item.file_path,
                "items": 0,
                "total_cost": 0.0,
                "kinds": set(),
            },
        )
        entry["items"] += 1
        entry["total_cost"] += item.cost
        entry["kinds"].add(item.kind)
    ranked = sorted(by_file.values(), key=lambda e: e["total_cost"], reverse=True)
    out = []
    for entry in ranked[:top_n]:
        entry["kinds"] = sorted(entry["kinds"])
        entry["total_cost"] = round(entry["total_cost"], 2)
        out.append(entry)
    return out


# Keep dataclass `asdict` importable for downstream callers.
__all_helpers__ = (asdict, DebtTrendPoint)
