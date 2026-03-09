"""
Pattern Storage for the Autonomous Agent Learning Loop.

Reads/writes learning patterns to `.auto-claude/learning/patterns.json`.
Handles deduplication by merging similar patterns and increasing confidence.
"""

import json
import logging
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional

from .models import LearningPattern

logger = logging.getLogger(__name__)


class PatternStorage:
    """File-based storage for learning patterns, scoped per project."""

    SIMILARITY_THRESHOLD = 0.8

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)
        self.patterns_dir = self.project_dir / ".auto-claude" / "learning_loop"
        self.patterns_file = self.patterns_dir / "patterns.json"

    def load_patterns(self) -> list[LearningPattern]:
        """Load all patterns from disk."""
        if not self.patterns_file.exists():
            return []
        try:
            data = json.loads(self.patterns_file.read_text(encoding="utf-8"))
            return [LearningPattern.from_dict(p) for p in data]
        except Exception as e:
            logger.warning(f"Failed to load learning patterns: {e}")
            return []

    def save_patterns(self, patterns: list[LearningPattern]) -> None:
        """Save all patterns to disk."""
        self.patterns_dir.mkdir(parents=True, exist_ok=True)
        data = [p.to_dict() for p in patterns]
        self.patterns_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def add_patterns(self, new_patterns: list[LearningPattern]) -> list[LearningPattern]:
        """Add new patterns, merging duplicates. Returns the updated list."""
        existing = self.load_patterns()
        for new_p in new_patterns:
            merged = False
            for i, existing_p in enumerate(existing):
                if self._are_similar(existing_p, new_p):
                    existing[i] = self._merge_pattern(existing_p, new_p)
                    merged = True
                    break
            if not merged:
                existing.append(new_p)
        self.save_patterns(existing)
        return existing

    def delete_pattern(self, pattern_id: str) -> bool:
        """Delete a pattern by ID. Returns True if found and deleted."""
        patterns = self.load_patterns()
        original_len = len(patterns)
        patterns = [p for p in patterns if p.pattern_id != pattern_id]
        if len(patterns) < original_len:
            self.save_patterns(patterns)
            return True
        return False

    def toggle_pattern(self, pattern_id: str) -> Optional[bool]:
        """Toggle a pattern's enabled state. Returns new state or None if not found."""
        patterns = self.load_patterns()
        for p in patterns:
            if p.pattern_id == pattern_id:
                p.enabled = not p.enabled
                self.save_patterns(patterns)
                return p.enabled
        return None

    def get_patterns_for_phase(
        self, phase: str, min_confidence: float = 0.5
    ) -> list[LearningPattern]:
        """Get enabled patterns for a specific agent phase above confidence threshold."""
        patterns = self.load_patterns()
        return [
            p
            for p in patterns
            if p.enabled
            and p.agent_phase == phase
            and p.confidence >= min_confidence
        ]

    def get_top_patterns(
        self, limit: int = 10, min_confidence: float = 0.6
    ) -> list[LearningPattern]:
        """Get the top N patterns by confidence, filtered by minimum confidence."""
        patterns = self.load_patterns()
        filtered = [p for p in patterns if p.enabled and p.confidence >= min_confidence]
        filtered.sort(key=lambda p: p.confidence, reverse=True)
        return filtered[:limit]

    def record_application(self, pattern_ids: list[str]) -> None:
        """Increment applied_count for the given patterns."""
        patterns = self.load_patterns()
        changed = False
        for p in patterns:
            if p.pattern_id in pattern_ids:
                p.applied_count += 1
                changed = True
        if changed:
            self.save_patterns(patterns)

    def record_outcome(self, pattern_ids: list[str], success: bool) -> None:
        """Record the outcome of a build where patterns were applied."""
        if not success:
            return
        patterns = self.load_patterns()
        changed = False
        for p in patterns:
            if p.pattern_id in pattern_ids:
                p.success_after_apply += 1
                changed = True
        if changed:
            self.save_patterns(patterns)

    def _are_similar(self, a: LearningPattern, b: LearningPattern) -> bool:
        """Check if two patterns are similar enough to merge."""
        if a.category != b.category or a.agent_phase != b.agent_phase:
            return False
        ratio = SequenceMatcher(
            None, a.actionable_instruction, b.actionable_instruction
        ).ratio()
        return ratio >= self.SIMILARITY_THRESHOLD

    def _merge_pattern(
        self, existing: LearningPattern, new: LearningPattern
    ) -> LearningPattern:
        """Merge a new pattern into an existing one, boosting confidence."""
        existing.occurrence_count += new.occurrence_count
        # Boost confidence, capped at 0.99
        existing.confidence = min(
            0.99, existing.confidence + (1 - existing.confidence) * 0.15
        )
        existing.last_seen = new.last_seen
        # Merge source build IDs (dedup)
        for bid in new.source_build_ids:
            if bid not in existing.source_build_ids:
                existing.source_build_ids.append(bid)
        # Merge context tags
        for tag in new.context_tags:
            if tag not in existing.context_tags:
                existing.context_tags.append(tag)
        return existing
