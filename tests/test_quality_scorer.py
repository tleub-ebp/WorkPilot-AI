"""Tests for AI Code Review Quality Scorer"""

import sys
import tempfile
from pathlib import Path

import pytest

# Ajouter le backend au path
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from review.quality_scorer import (
    IssueSeverity,
    QualityCategory,
    QualityIssue,
    QualityScorer,
)


@pytest.fixture
def temp_project():
    """Crée un projet temporaire pour les tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        yield project_dir


@pytest.fixture
def scorer(temp_project):
    """Crée un QualityScorer pour les tests."""
    return QualityScorer(temp_project)


class TestQualityScorer:
    """Tests pour QualityScorer."""

    def test_scorer_initialization(self, scorer, temp_project):
        """Test initialisation du scorer."""
        assert scorer.project_dir == temp_project
        assert len(scorer.issues) == 0

    def test_score_empty_pr(self, scorer):
        """Test scoring d'une PR vide."""
        score = scorer.score_pr("", [], "")

        assert score.overall_score == 100
        assert score.grade == "A+"
        assert score.total_issues == 0
        assert score.is_passing

    def test_score_python_syntax_error(self, scorer, temp_project):
        """Test détection d'erreur de syntaxe Python."""
        # Créer un fichier Python avec erreur de syntaxe
        bad_file = temp_project / "bad.py"
        bad_file.write_text("def broken(\n  print('missing closing paren')")

        score = scorer.score_pr("", ["bad.py"], "")

        assert score.critical_issues > 0
        assert score.overall_score < 100
        assert not score.is_passing

    def test_detect_bare_except(self, scorer, temp_project):
        """Test détection de bare except."""
        code = """
try:
    something()
except:
    pass
"""
        test_file = temp_project / "test.py"
        test_file.write_text(code)

        scorer._analyze_file("test.py")

        # Doit détecter le bare except
        bare_except_issues = [
            i
            for i in scorer.issues
            if "bare except" in i.title.lower()
        ]
        assert len(bare_except_issues) > 0

    def test_detect_complex_function(self, scorer, temp_project):
        """Test détection de fonction complexe."""
        code = """
def complex_function(x):
    if x > 0:
        if x < 10:
            for i in range(x):
                if i % 2 == 0:
                    if i > 5:
                        while i < 20:
                            if i == 15:
                                return i
                            i += 1
    return 0
"""
        test_file = temp_project / "complex.py"
        test_file.write_text(code)

        scorer._analyze_file("complex.py")

        # Doit détecter la complexité
        complexity_issues = [
            i for i in scorer.issues if i.category == QualityCategory.COMPLEXITY
        ]
        assert len(complexity_issues) > 0

    def test_detect_security_issues(self, scorer, temp_project):
        """Test détection de problèmes de sécurité."""
        code = '''
password = "hardcoded_secret"
eval(user_input)
'''
        test_file = temp_project / "insecure.py"
        test_file.write_text(code)

        scorer._analyze_file("insecure.py")

        # Doit détecter plusieurs problèmes de sécurité
        security_issues = [
            i for i in scorer.issues if i.category == QualityCategory.SECURITY
        ]
        assert len(security_issues) >= 2  # password + eval

    def test_calculate_grade(self, scorer):
        """Test calcul des grades."""
        assert scorer._calculate_grade(98) == "A+"
        assert scorer._calculate_grade(95) == "A"
        assert scorer._calculate_grade(91) == "A-"
        assert scorer._calculate_grade(85) == "B+"
        assert scorer._calculate_grade(75) == "C"
        assert scorer._calculate_grade(65) == "D"
        assert scorer._calculate_grade(50) == "F"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

