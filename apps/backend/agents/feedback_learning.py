"""Feedback Learning (RLHF-like) — Collect user feedback on agent outputs to improve prompts.

Implements a structured feedback collection and analysis system that allows users
to rate agent actions (thumbs up/down), provide structured feedback (code quality,
relevance, style), and automatically adjusts system prompts based on feedback patterns.

Feature 2.4 — Apprentissage par feedback (RLHF-like).

Example:
    >>> from apps.backend.agents.feedback_learning import FeedbackCollector, PromptOptimizer
    >>> collector = FeedbackCollector(project_id="proj-1")
    >>> fb = collector.record_feedback("session-1", "action-3", rating="positive",
    ...     categories={"code_quality": 5, "relevance": 4, "style": 3})
    >>> patterns = collector.analyze_patterns()
    >>> optimizer = PromptOptimizer(collector)
    >>> improved = optimizer.optimize_prompt("Write a login page", task_type="coding")
"""

import json
import logging
import statistics
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class FeedbackRating(str, Enum):
    """Rating for an agent action."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class FeedbackCategory(str, Enum):
    """Categories for structured feedback."""
    CODE_QUALITY = "code_quality"
    RELEVANCE = "relevance"
    STYLE = "style"
    PERFORMANCE = "performance"
    CORRECTNESS = "correctness"
    COMPLETENESS = "completeness"
    READABILITY = "readability"
    SECURITY = "security"


class AgentPhase(str, Enum):
    """Phase of the agent pipeline."""
    PLANNING = "planning"
    CODING = "coding"
    REVIEW = "review"
    QA = "qa"
    DOCUMENTATION = "documentation"
    REFACTORING = "refactoring"
    GENERAL = "general"


class PatternType(str, Enum):
    """Type of feedback pattern detected."""
    CONSISTENT_NEGATIVE = "consistent_negative"
    CONSISTENT_POSITIVE = "consistent_positive"
    DECLINING_QUALITY = "declining_quality"
    IMPROVING_QUALITY = "improving_quality"
    CATEGORY_WEAKNESS = "category_weakness"
    CATEGORY_STRENGTH = "category_strength"
    PHASE_ISSUE = "phase_issue"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class FeedbackEntry:
    """A single feedback entry from a user on an agent action."""
    feedback_id: str
    session_id: str
    action_id: str
    project_id: str
    rating: FeedbackRating
    categories: dict[str, int] = field(default_factory=dict)
    comment: str = ""
    agent_type: str = ""
    agent_phase: str = ""
    task_type: str = ""
    prompt_used: str = ""
    output_snippet: str = ""
    timestamp: str = ""
    user_id: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if isinstance(self.rating, str):
            self.rating = FeedbackRating(self.rating)

    @property
    def average_score(self) -> float:
        """Average score across all category ratings (1-5 scale)."""
        if not self.categories:
            return 0.0
        return statistics.mean(self.categories.values())

    @property
    def is_positive(self) -> bool:
        return self.rating == FeedbackRating.POSITIVE

    @property
    def is_negative(self) -> bool:
        return self.rating == FeedbackRating.NEGATIVE

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["rating"] = self.rating.value
        d["average_score"] = self.average_score
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FeedbackEntry":
        data = dict(data)
        data.pop("average_score", None)
        return cls(**data)


@dataclass
class FeedbackPattern:
    """A pattern detected from analyzing feedback history."""
    pattern_type: PatternType
    description: str
    confidence: float  # 0.0 to 1.0
    affected_category: str = ""
    affected_phase: str = ""
    sample_size: int = 0
    recommendation: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["pattern_type"] = self.pattern_type.value
        return d


@dataclass
class PromptAdjustment:
    """An adjustment to apply to a system prompt based on feedback."""
    adjustment_id: str
    original_instruction: str
    adjusted_instruction: str
    reason: str
    source_pattern: str
    confidence: float
    applied: bool = False
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FeedbackSummary:
    """Summary of feedback for a project or session."""
    total_feedback: int = 0
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    positive_rate: float = 0.0
    average_scores: dict[str, float] = field(default_factory=dict)
    by_phase: dict[str, dict[str, int]] = field(default_factory=dict)
    by_agent_type: dict[str, dict[str, int]] = field(default_factory=dict)
    patterns: list[dict[str, Any]] = field(default_factory=list)
    top_strengths: list[str] = field(default_factory=list)
    top_weaknesses: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# FeedbackCollector
# ---------------------------------------------------------------------------

class FeedbackCollector:
    """Collects and analyzes user feedback on agent actions.

    Args:
        project_id: The project identifier.
    """

    def __init__(self, project_id: str = ""):
        self.project_id = project_id
        self._feedback: list[FeedbackEntry] = []
        self._patterns: list[FeedbackPattern] = []
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"fb-{self._counter:04d}"

    # -- Recording ----------------------------------------------------------

    def record_feedback(
        self,
        session_id: str,
        action_id: str,
        rating: str,
        categories: dict[str, int] | None = None,
        comment: str = "",
        agent_type: str = "",
        agent_phase: str = "",
        task_type: str = "",
        prompt_used: str = "",
        output_snippet: str = "",
        user_id: str = "",
    ) -> FeedbackEntry:
        """Record a feedback entry for an agent action.

        Args:
            session_id: The session in which the action occurred.
            action_id: The specific action being rated.
            rating: One of 'positive', 'negative', 'neutral'.
            categories: Optional dict of category scores (1-5 scale).
            comment: Optional free-text comment from the user.
            agent_type: The type of agent (coder, planner, qa, etc.).
            agent_phase: The pipeline phase (planning, coding, review, etc.).
            task_type: The type of task being performed.
            prompt_used: The prompt that generated the output.
            output_snippet: A snippet of the agent's output.
            user_id: The user providing the feedback.

        Returns:
            The created FeedbackEntry.
        """
        if categories:
            for key, val in categories.items():
                if not (1 <= val <= 5):
                    raise ValueError(f"Category score must be 1-5, got {val} for '{key}'")

        entry = FeedbackEntry(
            feedback_id=self._next_id(),
            session_id=session_id,
            action_id=action_id,
            project_id=self.project_id,
            rating=rating,
            categories=categories or {},
            comment=comment,
            agent_type=agent_type,
            agent_phase=agent_phase,
            task_type=task_type,
            prompt_used=prompt_used,
            output_snippet=output_snippet,
            user_id=user_id,
        )
        self._feedback.append(entry)
        logger.info("Recorded feedback %s: %s for session=%s action=%s",
                     entry.feedback_id, rating, session_id, action_id)
        return entry

    # -- Querying -----------------------------------------------------------

    def get_feedback(
        self,
        session_id: str | None = None,
        rating: str | None = None,
        agent_phase: str | None = None,
        agent_type: str | None = None,
        task_type: str | None = None,
        limit: int = 0,
    ) -> list[FeedbackEntry]:
        """Get feedback entries with optional filters."""
        results = list(self._feedback)
        if session_id:
            results = [f for f in results if f.session_id == session_id]
        if rating:
            results = [f for f in results if f.rating.value == rating]
        if agent_phase:
            results = [f for f in results if f.agent_phase == agent_phase]
        if agent_type:
            results = [f for f in results if f.agent_type == agent_type]
        if task_type:
            results = [f for f in results if f.task_type == task_type]
        if limit > 0:
            results = results[:limit]
        return results

    def get_feedback_by_id(self, feedback_id: str) -> FeedbackEntry | None:
        """Get a specific feedback entry by ID."""
        for fb in self._feedback:
            if fb.feedback_id == feedback_id:
                return fb
        return None

    # -- Analysis -----------------------------------------------------------

    def get_summary(
        self,
        agent_phase: str | None = None,
        agent_type: str | None = None,
    ) -> FeedbackSummary:
        """Get a summary of all feedback with optional filters."""
        entries = self.get_feedback(agent_phase=agent_phase, agent_type=agent_type)
        if not entries:
            return FeedbackSummary()

        positive = sum(1 for e in entries if e.is_positive)
        negative = sum(1 for e in entries if e.is_negative)
        neutral = len(entries) - positive - negative

        # Average scores per category
        cat_scores: dict[str, list[int]] = {}
        for e in entries:
            for cat, score in e.categories.items():
                cat_scores.setdefault(cat, []).append(score)
        avg_scores = {cat: statistics.mean(scores) for cat, scores in cat_scores.items()}

        # By phase
        by_phase: dict[str, dict[str, int]] = {}
        for e in entries:
            phase = e.agent_phase or "unknown"
            by_phase.setdefault(phase, {"positive": 0, "negative": 0, "neutral": 0})
            by_phase[phase][e.rating.value] += 1

        # By agent type
        by_agent: dict[str, dict[str, int]] = {}
        for e in entries:
            at = e.agent_type or "unknown"
            by_agent.setdefault(at, {"positive": 0, "negative": 0, "neutral": 0})
            by_agent[at][e.rating.value] += 1

        # Strengths and weaknesses
        sorted_cats = sorted(avg_scores.items(), key=lambda x: x[1], reverse=True)
        strengths = [c for c, s in sorted_cats if s >= 4.0][:3]
        weaknesses = [c for c, s in sorted_cats if s <= 2.5][:3]

        patterns = self.analyze_patterns()

        return FeedbackSummary(
            total_feedback=len(entries),
            positive_count=positive,
            negative_count=negative,
            neutral_count=neutral,
            positive_rate=round(positive / len(entries) * 100, 1) if entries else 0.0,
            average_scores=avg_scores,
            by_phase=by_phase,
            by_agent_type=by_agent,
            patterns=[p.to_dict() for p in patterns],
            top_strengths=strengths,
            top_weaknesses=weaknesses,
        )

    def analyze_patterns(self) -> list[FeedbackPattern]:
        """Analyze feedback history to detect patterns.

        Returns:
            List of detected feedback patterns.
        """
        patterns: list[FeedbackPattern] = []
        entries = self._feedback
        if len(entries) < 3:
            return patterns

        # Pattern: Consistent negative feedback
        negative_rate = sum(1 for e in entries if e.is_negative) / len(entries)
        if negative_rate >= 0.6 and len(entries) >= 5:
            patterns.append(FeedbackPattern(
                pattern_type=PatternType.CONSISTENT_NEGATIVE,
                description="More than 60% of feedback is negative",
                confidence=min(negative_rate, 0.95),
                sample_size=len(entries),
                recommendation="Review and adjust system prompts to address common complaints",
            ))

        # Pattern: Consistent positive feedback
        positive_rate = sum(1 for e in entries if e.is_positive) / len(entries)
        if positive_rate >= 0.8 and len(entries) >= 5:
            patterns.append(FeedbackPattern(
                pattern_type=PatternType.CONSISTENT_POSITIVE,
                description="More than 80% of feedback is positive",
                confidence=min(positive_rate, 0.95),
                sample_size=len(entries),
                recommendation="Current approach is working well, maintain current prompts",
            ))

        # Pattern: Category weaknesses
        cat_scores: dict[str, list[int]] = {}
        for e in entries:
            for cat, score in e.categories.items():
                cat_scores.setdefault(cat, []).append(score)

        for cat, scores in cat_scores.items():
            if len(scores) >= 3:
                avg = statistics.mean(scores)
                if avg <= 2.5:
                    patterns.append(FeedbackPattern(
                        pattern_type=PatternType.CATEGORY_WEAKNESS,
                        description=f"Low average score ({avg:.1f}/5) for category '{cat}'",
                        confidence=min(len(scores) / 10, 0.9),
                        affected_category=cat,
                        sample_size=len(scores),
                        recommendation=f"Add specific instructions to improve '{cat}' in prompts",
                    ))
                elif avg >= 4.0:
                    patterns.append(FeedbackPattern(
                        pattern_type=PatternType.CATEGORY_STRENGTH,
                        description=f"High average score ({avg:.1f}/5) for category '{cat}'",
                        confidence=min(len(scores) / 10, 0.9),
                        affected_category=cat,
                        sample_size=len(scores),
                        recommendation=f"Maintain current approach for '{cat}'",
                    ))

        # Pattern: Phase-specific issues
        phase_feedback: dict[str, list[FeedbackEntry]] = {}
        for e in entries:
            if e.agent_phase:
                phase_feedback.setdefault(e.agent_phase, []).append(e)

        for phase, phase_entries in phase_feedback.items():
            if len(phase_entries) >= 3:
                neg_rate = sum(1 for e in phase_entries if e.is_negative) / len(phase_entries)
                if neg_rate >= 0.5:
                    patterns.append(FeedbackPattern(
                        pattern_type=PatternType.PHASE_ISSUE,
                        description=f"High negative rate ({neg_rate:.0%}) in phase '{phase}'",
                        confidence=min(len(phase_entries) / 10, 0.85),
                        affected_phase=phase,
                        sample_size=len(phase_entries),
                        recommendation=f"Revise prompts for the '{phase}' phase",
                    ))

        # Pattern: Declining quality (last 5 entries trend)
        if len(entries) >= 6:
            recent = entries[-5:]
            older = entries[-10:-5] if len(entries) >= 10 else entries[:-5]
            if older:
                recent_pos = sum(1 for e in recent if e.is_positive) / len(recent)
                older_pos = sum(1 for e in older if e.is_positive) / len(older)
                if older_pos - recent_pos >= 0.3:
                    patterns.append(FeedbackPattern(
                        pattern_type=PatternType.DECLINING_QUALITY,
                        description=f"Positive rate dropped from {older_pos:.0%} to {recent_pos:.0%}",
                        confidence=0.7,
                        sample_size=len(recent) + len(older),
                        recommendation="Investigate recent changes that may have degraded quality",
                    ))
                elif recent_pos - older_pos >= 0.3:
                    patterns.append(FeedbackPattern(
                        pattern_type=PatternType.IMPROVING_QUALITY,
                        description=f"Positive rate improved from {older_pos:.0%} to {recent_pos:.0%}",
                        confidence=0.7,
                        sample_size=len(recent) + len(older),
                        recommendation="Recent changes are improving quality, continue this approach",
                    ))

        self._patterns = patterns
        return patterns

    # -- Export / Import ----------------------------------------------------

    def export_feedback(self) -> str:
        """Export all feedback as JSON."""
        data = {
            "project_id": self.project_id,
            "feedback": [fb.to_dict() for fb in self._feedback],
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }
        return json.dumps(data, indent=2)

    def import_feedback(self, json_str: str) -> int:
        """Import feedback from JSON. Returns number of entries imported."""
        data = json.loads(json_str)
        count = 0
        for fb_data in data.get("feedback", []):
            fb_data.pop("average_score", None)
            entry = FeedbackEntry.from_dict(fb_data)
            entry.feedback_id = self._next_id()
            self._feedback.append(entry)
            count += 1
        return count

    # -- Stats --------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Get global statistics."""
        entries = self._feedback
        if not entries:
            return {"total": 0, "positive": 0, "negative": 0, "neutral": 0,
                    "positive_rate": 0.0, "categories_tracked": 0, "patterns_detected": 0}

        positive = sum(1 for e in entries if e.is_positive)
        negative = sum(1 for e in entries if e.is_negative)
        cats = set()
        for e in entries:
            cats.update(e.categories.keys())

        return {
            "total": len(entries),
            "positive": positive,
            "negative": negative,
            "neutral": len(entries) - positive - negative,
            "positive_rate": round(positive / len(entries) * 100, 1),
            "categories_tracked": len(cats),
            "patterns_detected": len(self._patterns),
            "phases_covered": len(set(e.agent_phase for e in entries if e.agent_phase)),
            "agent_types_covered": len(set(e.agent_type for e in entries if e.agent_type)),
        }


# ---------------------------------------------------------------------------
# PromptOptimizer
# ---------------------------------------------------------------------------

# Prompt enhancement rules keyed by category weakness
CATEGORY_PROMPT_RULES: dict[str, str] = {
    "code_quality": "Ensure the generated code follows best practices: proper error handling, meaningful variable names, no code smells, and adherence to language conventions.",
    "relevance": "Focus strictly on the requirements stated in the task. Do not add unnecessary features or code that was not requested.",
    "style": "Follow the existing code style of the project. Match indentation, naming conventions, and architectural patterns already in use.",
    "performance": "Optimize for performance. Avoid unnecessary loops, prefer efficient data structures, and minimize memory allocations.",
    "correctness": "Double-check all logic for correctness. Handle edge cases, validate inputs, and ensure the code produces the expected output for all cases.",
    "completeness": "Ensure the implementation is complete. Include all necessary imports, error handling, type hints, and handle all edge cases mentioned in the requirements.",
    "readability": "Write clear, self-documenting code. Use descriptive names, keep functions short, and add comments only where the logic is non-obvious.",
    "security": "Follow security best practices. Sanitize inputs, avoid hardcoded secrets, use parameterized queries, and validate all external data.",
}

PHASE_PROMPT_RULES: dict[str, str] = {
    "planning": "Break down the task into clear, actionable steps. Each step should be specific and testable.",
    "coding": "Write production-quality code with proper error handling and tests.",
    "review": "Be thorough but constructive in reviews. Focus on correctness, security, and maintainability.",
    "qa": "Test thoroughly including edge cases, error conditions, and integration scenarios.",
    "documentation": "Write clear documentation with examples. Cover parameters, return values, and error conditions.",
    "refactoring": "Preserve existing behavior while improving code structure. Ensure all tests still pass.",
}


class PromptOptimizer:
    """Optimizes system prompts based on collected feedback patterns.

    Args:
        collector: A FeedbackCollector with recorded feedback.
    """

    def __init__(self, collector: FeedbackCollector):
        self.collector = collector
        self._adjustments: list[PromptAdjustment] = []
        self._adj_counter = 0

    def _next_adj_id(self) -> str:
        self._adj_counter += 1
        return f"adj-{self._adj_counter:04d}"

    def generate_adjustments(self) -> list[PromptAdjustment]:
        """Generate prompt adjustments from feedback patterns.

        Returns:
            List of PromptAdjustment objects to apply.
        """
        patterns = self.collector.analyze_patterns()
        adjustments: list[PromptAdjustment] = []

        for pattern in patterns:
            if pattern.pattern_type == PatternType.CATEGORY_WEAKNESS:
                cat = pattern.affected_category
                rule = CATEGORY_PROMPT_RULES.get(cat, "")
                if rule:
                    adj = PromptAdjustment(
                        adjustment_id=self._next_adj_id(),
                        original_instruction="",
                        adjusted_instruction=rule,
                        reason=pattern.description,
                        source_pattern=pattern.pattern_type.value,
                        confidence=pattern.confidence,
                    )
                    adjustments.append(adj)

            elif pattern.pattern_type == PatternType.PHASE_ISSUE:
                phase = pattern.affected_phase
                rule = PHASE_PROMPT_RULES.get(phase, "")
                if rule:
                    adj = PromptAdjustment(
                        adjustment_id=self._next_adj_id(),
                        original_instruction="",
                        adjusted_instruction=rule,
                        reason=pattern.description,
                        source_pattern=pattern.pattern_type.value,
                        confidence=pattern.confidence,
                    )
                    adjustments.append(adj)

            elif pattern.pattern_type == PatternType.CONSISTENT_NEGATIVE:
                adj = PromptAdjustment(
                    adjustment_id=self._next_adj_id(),
                    original_instruction="",
                    adjusted_instruction=(
                        "IMPORTANT: Previous outputs have received consistently negative feedback. "
                        "Pay extra attention to quality, correctness, and relevance. "
                        "Double-check your work before responding."
                    ),
                    reason=pattern.description,
                    source_pattern=pattern.pattern_type.value,
                    confidence=pattern.confidence,
                )
                adjustments.append(adj)

        self._adjustments.extend(adjustments)
        return adjustments

    def optimize_prompt(
        self,
        base_prompt: str,
        task_type: str = "",
        agent_phase: str = "",
    ) -> str:
        """Optimize a prompt by appending feedback-driven instructions.

        Args:
            base_prompt: The original prompt to optimize.
            task_type: Optional task type for context.
            agent_phase: Optional agent phase for context.

        Returns:
            The optimized prompt with appended instructions.
        """
        adjustments = self.generate_adjustments()
        if not adjustments:
            return base_prompt

        # Collect relevant adjustments
        additions: list[str] = []
        for adj in adjustments:
            if adj.confidence >= 0.5:
                additions.append(adj.adjusted_instruction)
                adj.applied = True

        if not additions:
            return base_prompt

        # Build enhanced prompt
        enhanced = base_prompt.rstrip()
        enhanced += "\n\n--- Feedback-driven instructions ---\n"
        for i, instruction in enumerate(additions, 1):
            enhanced += f"{i}. {instruction}\n"

        return enhanced

    def get_prompt_for_phase(self, phase: str) -> str:
        """Get optimized additional instructions for a specific pipeline phase.

        Args:
            phase: The agent phase (planning, coding, review, etc.).

        Returns:
            Additional instructions string based on feedback.
        """
        summary = self.collector.get_summary(agent_phase=phase)
        instructions: list[str] = []

        # Add phase-specific rule if phase has issues
        phase_data = summary.by_phase.get(phase, {})
        total_phase = sum(phase_data.values()) if phase_data else 0
        if total_phase > 0:
            neg_rate = phase_data.get("negative", 0) / total_phase
            if neg_rate >= 0.4:
                rule = PHASE_PROMPT_RULES.get(phase, "")
                if rule:
                    instructions.append(rule)

        # Add category-specific rules for weaknesses
        for weakness in summary.top_weaknesses:
            rule = CATEGORY_PROMPT_RULES.get(weakness, "")
            if rule:
                instructions.append(rule)

        if not instructions:
            return ""

        return "Based on user feedback:\n" + "\n".join(f"- {i}" for i in instructions)

    def get_adjustments(self) -> list[PromptAdjustment]:
        """Get all generated adjustments."""
        return list(self._adjustments)

    def get_applied_adjustments(self) -> list[PromptAdjustment]:
        """Get only applied adjustments."""
        return [a for a in self._adjustments if a.applied]

    def get_stats(self) -> dict[str, Any]:
        """Get optimizer statistics."""
        return {
            "total_adjustments": len(self._adjustments),
            "applied_adjustments": sum(1 for a in self._adjustments if a.applied),
            "feedback_stats": self.collector.get_stats(),
        }
