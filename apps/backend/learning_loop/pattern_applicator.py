"""
Pattern Applicator for the Autonomous Agent Learning Loop.

Generates prompt augmentations from stored patterns and injects them
into agent system prompts before each build.
"""

import logging
from pathlib import Path
from typing import Optional

from .models import LearningPattern, PatternType
from .pattern_storage import PatternStorage

logger = logging.getLogger(__name__)


class PatternApplicator:
    """Generates prompt augmentations from stored learning patterns."""

    MAX_PATTERNS_PER_SECTION = 5
    MAX_TOTAL_PATTERNS = 10
    MIN_CONFIDENCE = 0.6

    def __init__(self, storage: PatternStorage):
        self.storage = storage

    def get_instructions_for_phase(
        self,
        phase: str,
        min_confidence: Optional[float] = None,
        task_context: Optional[dict] = None,
    ) -> str:
        """Generate a learning-based instruction block to append to agent prompts.

        Args:
            phase: The agent phase (planning, coding, qa_review, qa_fixing)
            min_confidence: Minimum confidence threshold (defaults to MIN_CONFIDENCE)
            task_context: Optional task context for filtering by tags

        Returns:
            Formatted markdown string to append to the agent system prompt,
            or empty string if no applicable patterns.
        """
        threshold = min_confidence or self.MIN_CONFIDENCE
        patterns = self.storage.get_patterns_for_phase(phase, min_confidence=threshold)

        if not patterns:
            return ""

        # Filter by context tags if task context is provided
        if task_context and task_context.get("tags"):
            task_tags = set(task_context["tags"])
            # Boost relevance for patterns matching task tags
            for p in patterns:
                if task_tags & set(p.context_tags):
                    p.confidence = min(0.99, p.confidence * 1.1)

        # Sort by confidence descending, then by occurrence_count
        patterns.sort(key=lambda p: (p.confidence, p.occurrence_count), reverse=True)

        # Split into success and failure patterns
        success_patterns = [p for p in patterns if p.pattern_type == PatternType.SUCCESS]
        failure_patterns = [p for p in patterns if p.pattern_type == PatternType.FAILURE]
        optimization_patterns = [p for p in patterns if p.pattern_type == PatternType.OPTIMIZATION]

        # Limit each section
        success_patterns = success_patterns[: self.MAX_PATTERNS_PER_SECTION]
        failure_patterns = failure_patterns[: self.MAX_PATTERNS_PER_SECTION]
        optimization_patterns = optimization_patterns[: self.MAX_PATTERNS_PER_SECTION]

        # Enforce total limit
        all_selected = (success_patterns + failure_patterns + optimization_patterns)[
            : self.MAX_TOTAL_PATTERNS
        ]
        if not all_selected:
            return ""

        # Track which patterns are being applied
        applied_ids = [p.pattern_id for p in all_selected]
        self.storage.record_application(applied_ids)

        # Build the instruction block
        total_builds = max(
            len(set(bid for p in all_selected for bid in p.source_build_ids)), 1
        )
        lines = [
            f"\n## Learning Insights (auto-generated from {total_builds} previous builds)\n"
        ]

        if success_patterns:
            lines.append("### Success Patterns (apply these):")
            for i, p in enumerate(success_patterns, 1):
                lines.append(
                    f"{i}. [confidence: {p.confidence:.2f}] {p.actionable_instruction}"
                )
            lines.append("")

        if failure_patterns:
            lines.append("### Failure Patterns (avoid these):")
            for i, p in enumerate(failure_patterns, 1):
                lines.append(
                    f"{i}. [confidence: {p.confidence:.2f}] {p.actionable_instruction}"
                )
            lines.append("")

        if optimization_patterns:
            lines.append("### Optimization Tips:")
            for i, p in enumerate(optimization_patterns, 1):
                lines.append(
                    f"{i}. [confidence: {p.confidence:.2f}] {p.actionable_instruction}"
                )
            lines.append("")

        return "\n".join(lines)

    def get_applied_pattern_ids(self, phase: str) -> list[str]:
        """Get pattern IDs that would be applied for the given phase."""
        patterns = self.storage.get_patterns_for_phase(phase, min_confidence=self.MIN_CONFIDENCE)
        patterns.sort(key=lambda p: p.confidence, reverse=True)
        return [p.pattern_id for p in patterns[: self.MAX_TOTAL_PATTERNS]]

    def record_outcome(self, pattern_ids: list[str], success: bool) -> None:
        """Record the outcome of a build where patterns were applied."""
        self.storage.record_outcome(pattern_ids, success)
