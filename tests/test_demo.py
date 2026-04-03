import sys
from pathlib import Path

import pytest

backend_dir = Path(__file__).parent.parent / "apps" / "backend"
sys.path.insert(0, str(backend_dir))


def test_quality_scorer_import():
    from review.quality_scorer import IssueSeverity, QualityCategory, QualityScorer
    assert QualityScorer is not None


def test_quality_scorer_creation():
    from review.quality_scorer import QualityScorer
    project_dir = Path(".")
    scorer = QualityScorer(project_dir)
    assert scorer is not None


def test_quality_scorer_empty_pr():
    from review.quality_scorer import QualityScorer
    project_dir = Path(".")
    scorer = QualityScorer(project_dir)
    score = scorer.score_pr("", [], "")
    assert score is not None


def test_quality_scorer_self_analysis():
    from review.quality_scorer import QualityScorer
    project_dir = Path(".")
    scorer = QualityScorer(project_dir)
    score = scorer.score_pr("", ["apps/backend/review/quality_scorer.py"], "")
    assert score is not None
