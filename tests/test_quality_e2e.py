#!/usr/bin/env python
"""
Test End-to-End du Quality Scorer
"""
import sys
from pathlib import Path
import pytest

backend_dir = Path(__file__).parent.parent / "apps" / "backend"
sys.path.insert(0, str(backend_dir))


def test_quality_scorer_imports():
    from review.quality_scorer import (
        QualityScorer,
        QualityScore,
        QualityIssue,
        QualityCategory,
        IssueSeverity,
    )
    assert QualityScorer is not None


def test_quality_scorer_empty_pr_perfect_score():
    from review.quality_scorer import QualityScorer
    scorer = QualityScorer(Path("."))
    score = scorer.score_pr("", [], "")
    assert score.overall_score == 100.0
    assert score.grade == "A+"
    assert score.total_issues == 0
    assert score.is_passing


def test_quality_scorer_self_analysis():
    from review.quality_scorer import QualityScorer
    scorer = QualityScorer(Path("."))
    scorer_file = "apps/backend/review/quality_scorer.py"
    score = scorer.score_pr("", [scorer_file], "")
    assert score is not None


def test_quality_scorer_example_bad_code():
    from review.quality_scorer import QualityScorer
    example_file = Path("example_bad_code.py")
    if not example_file.exists():
        pytest.skip("example_bad_code.py not found")
    scorer = QualityScorer(Path("."))
    score = scorer.score_pr("", ["example_bad_code.py"], "")
    assert score.critical_issues > 0
    assert score.total_issues >= 3
    assert not score.is_passing
