"""Tests for Feature 2.4 — Apprentissage par feedback (RLHF-like).

Tests: FeedbackEntry (5), FeedbackPattern (3), FeedbackCollector (17), PromptOptimizer (15) = 40 tests.
"""

import json
import pytest

from apps.backend.agents.feedback_learning import (
    FeedbackCategory,
    FeedbackCollector,
    FeedbackEntry,
    FeedbackPattern,
    FeedbackRating,
    FeedbackSummary,
    PatternType,
    PromptAdjustment,
    PromptOptimizer,
    CATEGORY_PROMPT_RULES,
    PHASE_PROMPT_RULES,
    AgentPhase,
)


# ---------------------------------------------------------------------------
# FeedbackEntry tests
# ---------------------------------------------------------------------------

class TestFeedbackEntry:
    def test_create_entry(self):
        entry = FeedbackEntry(
            feedback_id="fb-1", session_id="s-1", action_id="a-1",
            project_id="proj-1", rating="positive",
            categories={"code_quality": 5, "relevance": 4},
        )
        assert entry.rating == FeedbackRating.POSITIVE
        assert entry.is_positive
        assert not entry.is_negative
        assert entry.timestamp != ""

    def test_average_score(self):
        entry = FeedbackEntry(
            feedback_id="fb-1", session_id="s-1", action_id="a-1",
            project_id="proj-1", rating="neutral",
            categories={"code_quality": 4, "relevance": 2, "style": 3},
        )
        assert entry.average_score == 3.0

    def test_average_score_empty(self):
        entry = FeedbackEntry(
            feedback_id="fb-1", session_id="s-1", action_id="a-1",
            project_id="proj-1", rating="negative",
        )
        assert entry.average_score == 0.0

    def test_to_dict(self):
        entry = FeedbackEntry(
            feedback_id="fb-1", session_id="s-1", action_id="a-1",
            project_id="proj-1", rating="positive",
            categories={"code_quality": 5},
        )
        d = entry.to_dict()
        assert d["rating"] == "positive"
        assert d["average_score"] == 5.0
        assert d["feedback_id"] == "fb-1"

    def test_from_dict(self):
        d = {
            "feedback_id": "fb-1", "session_id": "s-1", "action_id": "a-1",
            "project_id": "proj-1", "rating": "negative",
            "categories": {"style": 2}, "comment": "Bad style",
            "agent_type": "coder", "agent_phase": "coding",
            "task_type": "feature", "prompt_used": "", "output_snippet": "",
            "timestamp": "2026-01-01T00:00:00+00:00", "user_id": "u1",
        }
        entry = FeedbackEntry.from_dict(d)
        assert entry.is_negative
        assert entry.comment == "Bad style"


# ---------------------------------------------------------------------------
# FeedbackPattern tests
# ---------------------------------------------------------------------------

class TestFeedbackPattern:
    def test_create_pattern(self):
        p = FeedbackPattern(
            pattern_type=PatternType.CATEGORY_WEAKNESS,
            description="Low code quality scores",
            confidence=0.8,
            affected_category="code_quality",
            sample_size=10,
            recommendation="Improve code quality prompts",
        )
        assert p.pattern_type == PatternType.CATEGORY_WEAKNESS
        assert p.confidence == 0.8

    def test_to_dict(self):
        p = FeedbackPattern(
            pattern_type=PatternType.CONSISTENT_NEGATIVE,
            description="test", confidence=0.5, sample_size=5,
        )
        d = p.to_dict()
        assert d["pattern_type"] == "consistent_negative"

    def test_phase_issue_pattern(self):
        p = FeedbackPattern(
            pattern_type=PatternType.PHASE_ISSUE,
            description="High neg rate in coding",
            confidence=0.7,
            affected_phase="coding",
            sample_size=8,
        )
        assert p.affected_phase == "coding"


# ---------------------------------------------------------------------------
# FeedbackCollector tests
# ---------------------------------------------------------------------------

class TestFeedbackCollector:
    def test_record_feedback_basic(self):
        collector = FeedbackCollector(project_id="proj-1")
        fb = collector.record_feedback("s-1", "a-1", rating="positive")
        assert fb.feedback_id == "fb-0001"
        assert fb.is_positive
        assert fb.project_id == "proj-1"

    def test_record_feedback_with_categories(self):
        collector = FeedbackCollector()
        fb = collector.record_feedback(
            "s-1", "a-1", rating="negative",
            categories={"code_quality": 2, "relevance": 1},
        )
        assert fb.average_score == 1.5
        assert fb.is_negative

    def test_record_feedback_invalid_score_raises(self):
        collector = FeedbackCollector()
        with pytest.raises(ValueError, match="Category score must be 1-5"):
            collector.record_feedback("s-1", "a-1", rating="positive",
                                       categories={"code_quality": 6})

    def test_record_feedback_invalid_score_zero(self):
        collector = FeedbackCollector()
        with pytest.raises(ValueError):
            collector.record_feedback("s-1", "a-1", rating="positive",
                                       categories={"x": 0})

    def test_get_feedback_all(self):
        collector = FeedbackCollector()
        collector.record_feedback("s-1", "a-1", rating="positive")
        collector.record_feedback("s-1", "a-2", rating="negative")
        assert len(collector.get_feedback()) == 2

    def test_get_feedback_filtered_by_session(self):
        collector = FeedbackCollector()
        collector.record_feedback("s-1", "a-1", rating="positive")
        collector.record_feedback("s-2", "a-2", rating="negative")
        result = collector.get_feedback(session_id="s-1")
        assert len(result) == 1
        assert result[0].session_id == "s-1"

    def test_get_feedback_filtered_by_rating(self):
        collector = FeedbackCollector()
        collector.record_feedback("s-1", "a-1", rating="positive")
        collector.record_feedback("s-1", "a-2", rating="negative")
        collector.record_feedback("s-1", "a-3", rating="positive")
        result = collector.get_feedback(rating="positive")
        assert len(result) == 2

    def test_get_feedback_filtered_by_phase(self):
        collector = FeedbackCollector()
        collector.record_feedback("s-1", "a-1", rating="positive", agent_phase="coding")
        collector.record_feedback("s-1", "a-2", rating="negative", agent_phase="review")
        result = collector.get_feedback(agent_phase="coding")
        assert len(result) == 1

    def test_get_feedback_with_limit(self):
        collector = FeedbackCollector()
        for i in range(10):
            collector.record_feedback("s-1", f"a-{i}", rating="positive")
        assert len(collector.get_feedback(limit=3)) == 3

    def test_get_feedback_by_id(self):
        collector = FeedbackCollector()
        fb = collector.record_feedback("s-1", "a-1", rating="positive")
        found = collector.get_feedback_by_id(fb.feedback_id)
        assert found is not None
        assert found.session_id == "s-1"

    def test_get_feedback_by_id_not_found(self):
        collector = FeedbackCollector()
        assert collector.get_feedback_by_id("nonexistent") is None

    def test_get_summary_empty(self):
        collector = FeedbackCollector()
        summary = collector.get_summary()
        assert summary.total_feedback == 0

    def test_get_summary_with_data(self):
        collector = FeedbackCollector()
        collector.record_feedback("s-1", "a-1", rating="positive",
                                   categories={"code_quality": 5})
        collector.record_feedback("s-1", "a-2", rating="negative",
                                   categories={"code_quality": 2})
        collector.record_feedback("s-1", "a-3", rating="positive",
                                   categories={"code_quality": 4})
        summary = collector.get_summary()
        assert summary.total_feedback == 3
        assert summary.positive_count == 2
        assert summary.negative_count == 1
        assert summary.positive_rate == pytest.approx(66.7, abs=0.1)

    def test_export_import_feedback(self):
        collector = FeedbackCollector(project_id="proj-1")
        collector.record_feedback("s-1", "a-1", rating="positive",
                                   categories={"code_quality": 5})
        collector.record_feedback("s-1", "a-2", rating="negative")
        exported = collector.export_feedback()
        data = json.loads(exported)
        assert len(data["feedback"]) == 2

        collector2 = FeedbackCollector(project_id="proj-1")
        count = collector2.import_feedback(exported)
        assert count == 2
        assert len(collector2.get_feedback()) == 2

    def test_get_stats(self):
        collector = FeedbackCollector()
        collector.record_feedback("s-1", "a-1", rating="positive",
                                   agent_phase="coding", agent_type="coder",
                                   categories={"code_quality": 5})
        collector.record_feedback("s-1", "a-2", rating="negative",
                                   agent_phase="review", agent_type="reviewer",
                                   categories={"style": 2})
        stats = collector.get_stats()
        assert stats["total"] == 2
        assert stats["positive"] == 1
        assert stats["negative"] == 1
        assert stats["categories_tracked"] == 2
        assert stats["phases_covered"] == 2
        assert stats["agent_types_covered"] == 2

    def test_get_stats_empty(self):
        collector = FeedbackCollector()
        stats = collector.get_stats()
        assert stats["total"] == 0


# ---------------------------------------------------------------------------
# Pattern Analysis tests
# ---------------------------------------------------------------------------

class TestPatternAnalysis:
    def test_no_patterns_with_few_entries(self):
        collector = FeedbackCollector()
        collector.record_feedback("s-1", "a-1", rating="negative")
        collector.record_feedback("s-1", "a-2", rating="negative")
        patterns = collector.analyze_patterns()
        assert len(patterns) == 0  # Not enough data

    def test_consistent_negative_pattern(self):
        collector = FeedbackCollector()
        for i in range(8):
            collector.record_feedback("s-1", f"a-{i}", rating="negative")
        collector.record_feedback("s-1", "a-8", rating="positive")
        collector.record_feedback("s-1", "a-9", rating="positive")
        patterns = collector.analyze_patterns()
        types = [p.pattern_type for p in patterns]
        assert PatternType.CONSISTENT_NEGATIVE in types

    def test_consistent_positive_pattern(self):
        collector = FeedbackCollector()
        for i in range(9):
            collector.record_feedback("s-1", f"a-{i}", rating="positive")
        collector.record_feedback("s-1", "a-9", rating="negative")
        patterns = collector.analyze_patterns()
        types = [p.pattern_type for p in patterns]
        assert PatternType.CONSISTENT_POSITIVE in types

    def test_category_weakness_pattern(self):
        collector = FeedbackCollector()
        for i in range(5):
            collector.record_feedback("s-1", f"a-{i}", rating="negative",
                                       categories={"code_quality": 1, "relevance": 5})
        patterns = collector.analyze_patterns()
        weakness_patterns = [p for p in patterns
                             if p.pattern_type == PatternType.CATEGORY_WEAKNESS]
        assert len(weakness_patterns) >= 1
        cats = [p.affected_category for p in weakness_patterns]
        assert "code_quality" in cats

    def test_category_strength_pattern(self):
        collector = FeedbackCollector()
        for i in range(5):
            collector.record_feedback("s-1", f"a-{i}", rating="positive",
                                       categories={"relevance": 5})
        patterns = collector.analyze_patterns()
        strength_patterns = [p for p in patterns
                             if p.pattern_type == PatternType.CATEGORY_STRENGTH]
        assert len(strength_patterns) >= 1

    def test_phase_issue_pattern(self):
        collector = FeedbackCollector()
        for i in range(4):
            collector.record_feedback("s-1", f"a-{i}", rating="negative",
                                       agent_phase="coding")
        collector.record_feedback("s-1", "a-4", rating="positive", agent_phase="coding")
        patterns = collector.analyze_patterns()
        phase_patterns = [p for p in patterns if p.pattern_type == PatternType.PHASE_ISSUE]
        assert len(phase_patterns) >= 1
        assert phase_patterns[0].affected_phase == "coding"


# ---------------------------------------------------------------------------
# PromptOptimizer tests
# ---------------------------------------------------------------------------

class TestPromptOptimizer:
    def _make_collector_with_weakness(self, category: str, score: int = 1) -> FeedbackCollector:
        collector = FeedbackCollector()
        for i in range(5):
            collector.record_feedback("s-1", f"a-{i}", rating="negative",
                                       categories={category: score})
        return collector

    def test_generate_adjustments_from_category_weakness(self):
        collector = self._make_collector_with_weakness("code_quality")
        optimizer = PromptOptimizer(collector)
        adjustments = optimizer.generate_adjustments()
        assert len(adjustments) >= 1
        assert any("code" in a.adjusted_instruction.lower() for a in adjustments)

    def test_generate_adjustments_from_phase_issue(self):
        collector = FeedbackCollector()
        for i in range(5):
            collector.record_feedback("s-1", f"a-{i}", rating="negative",
                                       agent_phase="coding")
        optimizer = PromptOptimizer(collector)
        adjustments = optimizer.generate_adjustments()
        phase_adjs = [a for a in adjustments if a.source_pattern == "phase_issue"]
        assert len(phase_adjs) >= 1

    def test_generate_adjustments_consistent_negative(self):
        collector = FeedbackCollector()
        for i in range(8):
            collector.record_feedback("s-1", f"a-{i}", rating="negative")
        optimizer = PromptOptimizer(collector)
        adjustments = optimizer.generate_adjustments()
        neg_adjs = [a for a in adjustments if a.source_pattern == "consistent_negative"]
        assert len(neg_adjs) >= 1

    def test_optimize_prompt_no_feedback(self):
        collector = FeedbackCollector()
        optimizer = PromptOptimizer(collector)
        result = optimizer.optimize_prompt("Write a login page")
        assert result == "Write a login page"

    def test_optimize_prompt_with_adjustments(self):
        collector = self._make_collector_with_weakness("style")
        optimizer = PromptOptimizer(collector)
        result = optimizer.optimize_prompt("Write a login page")
        assert "Feedback-driven instructions" in result
        assert "Write a login page" in result

    def test_optimize_prompt_preserves_base(self):
        collector = self._make_collector_with_weakness("security")
        optimizer = PromptOptimizer(collector)
        result = optimizer.optimize_prompt("Build an API endpoint")
        assert result.startswith("Build an API endpoint")

    def test_get_prompt_for_phase_with_issues(self):
        collector = FeedbackCollector()
        for i in range(5):
            collector.record_feedback("s-1", f"a-{i}", rating="negative",
                                       agent_phase="review")
        optimizer = PromptOptimizer(collector)
        instructions = optimizer.get_prompt_for_phase("review")
        assert "feedback" in instructions.lower() or "review" in instructions.lower()

    def test_get_prompt_for_phase_no_issues(self):
        collector = FeedbackCollector()
        for i in range(5):
            collector.record_feedback("s-1", f"a-{i}", rating="positive",
                                       agent_phase="coding")
        optimizer = PromptOptimizer(collector)
        instructions = optimizer.get_prompt_for_phase("coding")
        assert instructions == ""

    def test_get_adjustments(self):
        collector = self._make_collector_with_weakness("correctness")
        optimizer = PromptOptimizer(collector)
        optimizer.generate_adjustments()
        adjs = optimizer.get_adjustments()
        assert len(adjs) >= 1

    def test_get_applied_adjustments(self):
        collector = self._make_collector_with_weakness("completeness")
        optimizer = PromptOptimizer(collector)
        optimizer.optimize_prompt("test prompt")
        applied = optimizer.get_applied_adjustments()
        assert len(applied) >= 1
        assert all(a.applied for a in applied)

    def test_get_stats(self):
        collector = self._make_collector_with_weakness("readability")
        optimizer = PromptOptimizer(collector)
        optimizer.generate_adjustments()
        stats = optimizer.get_stats()
        assert stats["total_adjustments"] >= 1
        assert "feedback_stats" in stats

    def test_adjustment_to_dict(self):
        adj = PromptAdjustment(
            adjustment_id="adj-1",
            original_instruction="",
            adjusted_instruction="Test instruction",
            reason="Low quality",
            source_pattern="category_weakness",
            confidence=0.8,
        )
        d = adj.to_dict()
        assert d["adjustment_id"] == "adj-1"
        assert d["confidence"] == 0.8

    def test_category_prompt_rules_coverage(self):
        """Ensure all FeedbackCategory values have rules."""
        for cat in FeedbackCategory:
            assert cat.value in CATEGORY_PROMPT_RULES, f"Missing rule for {cat.value}"

    def test_phase_prompt_rules_coverage(self):
        """Ensure all AgentPhase values have rules (except general)."""
        for phase in AgentPhase:
            if phase != AgentPhase.GENERAL:
                assert phase.value in PHASE_PROMPT_RULES, f"Missing rule for {phase.value}"

    def test_feedback_summary_to_dict(self):
        collector = FeedbackCollector()
        collector.record_feedback("s-1", "a-1", rating="positive",
                                   categories={"code_quality": 5})
        summary = collector.get_summary()
        d = summary.to_dict()
        assert d["total_feedback"] == 1
        assert d["positive_count"] == 1
