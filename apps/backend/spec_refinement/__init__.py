"""
Incremental Spec Refinement — Iteratively improve specs via feedback.

Collects QA results, review comments, cost deltas, and user edits
to refine specs over multiple iterations until convergence.
"""

from .refinement_engine import (
    FeedbackSignal,
    RefinementEngine,
    RefinementHistory,
    RefinementIteration,
    RefinementStatus,
    SignalType,
)

__all__ = [
    "RefinementEngine",
    "RefinementHistory",
    "RefinementIteration",
    "FeedbackSignal",
    "SignalType",
    "RefinementStatus",
]
