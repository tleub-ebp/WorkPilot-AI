"""Codebase Longevity Score.

Aggregates the signals collected by `tech_debt.scanner` into a single
0–100 health score plus a 6-month linear extrapolation of where the
codebase is heading.

See `scorer.py` for the public API.
"""

from .scorer import (
    HealthGrade,
    LongevityProjection,
    LongevityReport,
    LongevityScorer,
    score_codebase,
)

__all__ = [
    "HealthGrade",
    "LongevityProjection",
    "LongevityReport",
    "LongevityScorer",
    "score_codebase",
]
