#!/usr/bin/env python3
"""
Intent Learning Module
======================

Tracks intent detection accuracy and learns from user feedback
to improve future classifications.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import IntentCategory

logger = logging.getLogger(__name__)


@dataclass
class IntentFeedback:
    """User feedback on intent detection."""

    task_id: str
    task_description: str
    detected_category: IntentCategory
    detected_confidence: float
    actual_category: IntentCategory  # User correction
    feedback_timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )
    user_notes: str = ""
    project_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "task_description": self.task_description,
            "detected_category": self.detected_category.value,
            "detected_confidence": self.detected_confidence,
            "actual_category": self.actual_category.value,
            "feedback_timestamp": self.feedback_timestamp,
            "user_notes": self.user_notes,
            "project_id": self.project_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IntentFeedback:
        """Create from dictionary."""
        return cls(
            task_id=data["task_id"],
            task_description=data["task_description"],
            detected_category=IntentCategory(data["detected_category"]),
            detected_confidence=data["detected_confidence"],
            actual_category=IntentCategory(data["actual_category"]),
            feedback_timestamp=data.get("feedback_timestamp", ""),
            user_notes=data.get("user_notes", ""),
            project_id=data.get("project_id", ""),
        )


@dataclass
class ProjectPatterns:
    """Intent patterns learned for a specific project."""

    project_id: str
    common_intents: dict[str, int] = field(default_factory=dict)
    accuracy_by_category: dict[str, float] = field(default_factory=dict)
    common_keywords: dict[str, list[str]] = field(default_factory=dict)
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "project_id": self.project_id,
            "common_intents": self.common_intents,
            "accuracy_by_category": self.accuracy_by_category,
            "common_keywords": self.common_keywords,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectPatterns:
        """Create from dictionary."""
        return cls(
            project_id=data["project_id"],
            common_intents=data.get("common_intents", {}),
            accuracy_by_category=data.get("accuracy_by_category", {}),
            common_keywords=data.get("common_keywords", {}),
            last_updated=data.get("last_updated", ""),
        )


class IntentLearner:
    """
    Learns from user feedback to improve intent detection.

    Tracks:
    - Detection accuracy per category
    - Common patterns per project
    - Frequently corrected intents
    - Project-specific keywords
    """

    def __init__(self, storage_dir: Path | None = None):
        """
        Initialize the intent learner.

        Args:
            storage_dir: Directory to store learning data (defaults to ~/.auto-claude/intent)
        """
        if storage_dir is None:
            storage_dir = Path.home() / ".auto-claude" / "intent"
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.feedback_file = self.storage_dir / "feedback.jsonl"
        self.patterns_file = self.storage_dir / "project_patterns.json"

        self._patterns_cache: dict[str, ProjectPatterns] = {}
        self._load_patterns()

    def record_feedback(
        self,
        task_id: str,
        task_description: str,
        detected_category: IntentCategory,
        detected_confidence: float,
        actual_category: IntentCategory,
        user_notes: str = "",
        project_id: str = "",
    ) -> None:
        """
        Record user feedback on intent detection.

        Args:
            task_id: Unique task identifier
            task_description: The task description
            detected_category: What we detected
            detected_confidence: Confidence score
            actual_category: What the user says it actually is
            user_notes: Optional notes from user
            project_id: Project this task belongs to
        """
        feedback = IntentFeedback(
            task_id=task_id,
            task_description=task_description,
            detected_category=detected_category,
            detected_confidence=detected_confidence,
            actual_category=actual_category,
            user_notes=user_notes,
            project_id=project_id,
        )

        # Append to feedback log (JSONL format)
        try:
            with open(self.feedback_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(feedback.to_dict()) + "\n")

            logger.info(
                f"Recorded intent feedback: {detected_category.value} -> {actual_category.value}"
            )

            # Update project patterns
            if project_id:
                self._update_project_patterns(project_id, feedback)

        except OSError as e:
            logger.error(f"Failed to record feedback: {e}")

    def get_project_patterns(self, project_id: str) -> ProjectPatterns:
        """
        Get learned patterns for a specific project.

        Args:
            project_id: Project identifier

        Returns:
            ProjectPatterns with learned data
        """
        if project_id in self._patterns_cache:
            return self._patterns_cache[project_id]

        # Create new patterns for unknown project
        return ProjectPatterns(project_id=project_id)

    def get_accuracy_metrics(
        self, project_id: str | None = None
    ) -> dict[str, Any]:
        """
        Get accuracy metrics for intent detection.

        Args:
            project_id: Optional project to filter by

        Returns:
            Dictionary with accuracy metrics
        """
        feedbacks = self._load_all_feedback()

        if project_id:
            feedbacks = [f for f in feedbacks if f.project_id == project_id]

        if not feedbacks:
            return {
                "total_feedbacks": 0,
                "overall_accuracy": 0.0,
                "by_category": {},
            }

        # Calculate overall accuracy
        correct = sum(
            1 for f in feedbacks if f.detected_category == f.actual_category
        )
        total = len(feedbacks)
        overall_accuracy = correct / total if total > 0 else 0.0

        # Calculate per-category accuracy
        category_stats: dict[str, dict[str, int]] = {}
        for f in feedbacks:
            cat = f.detected_category.value
            if cat not in category_stats:
                category_stats[cat] = {"correct": 0, "total": 0}
            category_stats[cat]["total"] += 1
            if f.detected_category == f.actual_category:
                category_stats[cat]["correct"] += 1

        by_category = {
            cat: {
                "accuracy": stats["correct"] / stats["total"],
                "total": stats["total"],
                "correct": stats["correct"],
            }
            for cat, stats in category_stats.items()
        }

        return {
            "total_feedbacks": total,
            "overall_accuracy": overall_accuracy,
            "correct_predictions": correct,
            "by_category": by_category,
        }

    def get_common_misclassifications(
        self, limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        Get the most common misclassifications.

        Args:
            limit: Maximum number of results

        Returns:
            List of common misclassification patterns
        """
        feedbacks = self._load_all_feedback()

        # Filter to incorrect predictions
        incorrect = [f for f in feedbacks if f.detected_category != f.actual_category]

        # Count patterns
        patterns: dict[tuple[str, str], int] = {}
        for f in incorrect:
            key = (f.detected_category.value, f.actual_category.value)
            patterns[key] = patterns.get(key, 0) + 1

        # Sort by frequency
        sorted_patterns = sorted(patterns.items(), key=lambda x: x[1], reverse=True)

        return [
            {
                "detected": detected,
                "actual": actual,
                "count": count,
            }
            for (detected, actual), count in sorted_patterns[:limit]
        ]

    def _load_all_feedback(self) -> list[IntentFeedback]:
        """Load all feedback records."""
        feedbacks = []
        if not self.feedback_file.exists():
            return feedbacks

        try:
            with open(self.feedback_file, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        feedbacks.append(IntentFeedback.from_dict(data))
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load feedback: {e}")

        return feedbacks

    def _update_project_patterns(
        self, project_id: str, feedback: IntentFeedback
    ) -> None:
        """Update project patterns based on new feedback."""
        patterns = self.get_project_patterns(project_id)

        # Update common intents
        actual = feedback.actual_category.value
        patterns.common_intents[actual] = patterns.common_intents.get(actual, 0) + 1

        # Update accuracy tracking
        if feedback.detected_category == feedback.actual_category:
            patterns.accuracy_by_category[actual] = (
                patterns.accuracy_by_category.get(actual, 0.0) + 1.0
            )

        patterns.last_updated = datetime.now(timezone.utc).isoformat()

        # Cache and save
        self._patterns_cache[project_id] = patterns
        self._save_patterns()

    def _load_patterns(self) -> None:
        """Load project patterns from disk."""
        if not self.patterns_file.exists():
            return

        try:
            with open(self.patterns_file, encoding="utf-8") as f:
                data = json.load(f)
                for project_id, pattern_data in data.items():
                    self._patterns_cache[project_id] = ProjectPatterns.from_dict(
                        pattern_data
                    )
            logger.debug(f"Loaded patterns for {len(self._patterns_cache)} projects")
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load patterns: {e}")

    def _save_patterns(self) -> None:
        """Save project patterns to disk."""
        try:
            data = {
                project_id: patterns.to_dict()
                for project_id, patterns in self._patterns_cache.items()
            }
            with open(self.patterns_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved patterns for {len(data)} projects")
        except OSError as e:
            logger.error(f"Failed to save patterns: {e}")

