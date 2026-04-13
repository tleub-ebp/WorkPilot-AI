"""
Incremental Spec Refinement — Iteratively improve specs via feedback loops.

After each agent run, collect signals (QA results, review comments,
cost delta, user edits) and refine the spec for the next iteration.
Tracks refinement history and convergence metrics.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class SignalType(str, Enum):
    QA_FAILURE = "qa_failure"
    REVIEW_COMMENT = "review_comment"
    USER_EDIT = "user_edit"
    COST_OVERRUN = "cost_overrun"
    TEST_FAILURE = "test_failure"
    SECURITY_VIOLATION = "security_violation"
    PERFORMANCE_REGRESSION = "performance_regression"
    LINT_ERROR = "lint_error"


class RefinementStatus(str, Enum):
    DRAFT = "draft"
    REFINING = "refining"
    CONVERGED = "converged"
    DIVERGING = "diverging"
    ABANDONED = "abandoned"


@dataclass
class FeedbackSignal:
    """A single feedback signal from an agent run."""

    signal_type: SignalType
    source: str
    message: str
    severity: str = "medium"
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class RefinementIteration:
    """A single iteration in the refinement cycle."""

    iteration: int
    spec_snapshot: str
    signals: list[FeedbackSignal] = field(default_factory=list)
    changes_made: list[str] = field(default_factory=list)
    quality_score: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class RefinementHistory:
    """Full history of spec refinement iterations."""

    spec_id: str
    iterations: list[RefinementIteration] = field(default_factory=list)
    status: RefinementStatus = RefinementStatus.DRAFT
    convergence_score: float = 0.0

    @property
    def current_iteration(self) -> int:
        return len(self.iterations)

    @property
    def is_converging(self) -> bool:
        if len(self.iterations) < 2:
            return False
        scores = [it.quality_score for it in self.iterations[-3:]]
        return all(scores[i] >= scores[i - 1] for i in range(1, len(scores)))

    @property
    def summary(self) -> str:
        return (
            f"Spec {self.spec_id}: {self.current_iteration} iterations, "
            f"status={self.status.value}, convergence={self.convergence_score:.2f}"
        )


class RefinementEngine:
    """Iteratively refine specs based on feedback signals.

    Usage::

        engine = RefinementEngine()
        history = engine.create_history("spec-001", initial_spec)
        engine.add_signals(history, signals)
        suggestions = engine.suggest_refinements(history)
        engine.apply_refinement(history, updated_spec, changes)
    """

    def __init__(self, max_iterations: int = 10, convergence_threshold: float = 0.85) -> None:
        self._max_iterations = max_iterations
        self._convergence_threshold = convergence_threshold
        self._histories: dict[str, RefinementHistory] = {}

    def create_history(self, spec_id: str, initial_spec: str) -> RefinementHistory:
        """Create a new refinement history for a spec."""
        history = RefinementHistory(spec_id=spec_id)
        history.iterations.append(RefinementIteration(
            iteration=0,
            spec_snapshot=initial_spec,
            quality_score=0.0,
        ))
        self._histories[spec_id] = history
        return history

    def add_signals(
        self, history: RefinementHistory, signals: list[FeedbackSignal]
    ) -> None:
        """Add feedback signals to the current iteration."""
        if not history.iterations:
            return
        history.iterations[-1].signals.extend(signals)

    def suggest_refinements(self, history: RefinementHistory) -> list[str]:
        """Suggest refinements based on accumulated signals."""
        if not history.iterations:
            return []

        current = history.iterations[-1]
        suggestions: list[str] = []

        signal_groups: dict[SignalType, int] = {}
        for signal in current.signals:
            signal_groups[signal.signal_type] = signal_groups.get(signal.signal_type, 0) + 1

        for signal_type, count in signal_groups.items():
            suggestion = _SIGNAL_SUGGESTIONS.get(signal_type)
            if suggestion:
                suggestions.append(f"[{count}x {signal_type.value}] {suggestion}")

        return suggestions

    def apply_refinement(
        self,
        history: RefinementHistory,
        updated_spec: str,
        changes: list[str],
        quality_score: float = 0.0,
    ) -> RefinementIteration:
        """Record a new refinement iteration."""
        iteration = RefinementIteration(
            iteration=history.current_iteration,
            spec_snapshot=updated_spec,
            changes_made=changes,
            quality_score=quality_score,
        )
        history.iterations.append(iteration)

        # Update convergence
        self._update_convergence(history)

        return iteration

    def _update_convergence(self, history: RefinementHistory) -> None:
        """Update convergence status based on iteration history."""
        if history.current_iteration >= self._max_iterations:
            history.status = RefinementStatus.ABANDONED
            return

        if len(history.iterations) < 2:
            history.status = RefinementStatus.REFINING
            return

        latest = history.iterations[-1].quality_score
        history.convergence_score = latest

        if latest >= self._convergence_threshold:
            history.status = RefinementStatus.CONVERGED
        elif history.is_converging:
            history.status = RefinementStatus.REFINING
        else:
            prev = history.iterations[-2].quality_score
            if latest < prev - 0.1:
                history.status = RefinementStatus.DIVERGING
            else:
                history.status = RefinementStatus.REFINING

    def get_history(self, spec_id: str) -> RefinementHistory | None:
        return self._histories.get(spec_id)


_SIGNAL_SUGGESTIONS: dict[SignalType, str] = {
    SignalType.QA_FAILURE: "Add explicit acceptance criteria or edge case handling to the spec.",
    SignalType.REVIEW_COMMENT: "Incorporate reviewer feedback into spec requirements.",
    SignalType.USER_EDIT: "The user made manual corrections — update the spec to match intent.",
    SignalType.COST_OVERRUN: "Simplify scope or split into smaller sub-specs to reduce token usage.",
    SignalType.TEST_FAILURE: "Add test-specific constraints or expected behaviour to the spec.",
    SignalType.SECURITY_VIOLATION: "Add security requirements (input validation, auth checks) to the spec.",
    SignalType.PERFORMANCE_REGRESSION: "Add performance budgets or constraints to the spec.",
    SignalType.LINT_ERROR: "Specify code style requirements or reference the project linter config.",
}
