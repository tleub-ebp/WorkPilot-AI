"""Tests for Quality Badge and Integration modules"""

import re
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import pytest

# Ajouter le backend au path
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from review.quality_badge import QualityBadgeFormatter
from review.quality_integration import QualityReviewIntegration
from review.quality_scorer import (
    IssueSeverity,
    QualityCategory,
    QualityIssue,
    QualityScore,
    QualityScorer,
)


@pytest.fixture
def temp_project():
    """Crée un projet temporaire pour les tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        yield project_dir


@pytest.fixture
def sample_score():
    """Crée un score d'exemple pour les tests."""
    issues = [
        QualityIssue(
            category=QualityCategory.SECURITY,
            severity=IssueSeverity.CRITICAL,
            title="Hardcoded password",
            description="Password found in code",
            file="test.py",
            line=10,
            suggestion="Use environment variables",
        ),
        QualityIssue(
            category=QualityCategory.BUGS,
            severity=IssueSeverity.HIGH,
            title="Complex function",
            description="Cyclomatic complexity too high",
            file="test.py",
            line=20,
            suggestion="Break down function",
        ),
    ]
    
    return QualityScore(
        overall_score=75.0,
        grade="C",
        total_issues=2,
        critical_issues=1,
        issues=issues,
    )


class TestQualityBadgeFormatter:
    """Tests pour QualityBadgeFormatter."""

    def test_shields_badge_url(self, sample_score):
        """Test génération URL shields.io."""
        formatter = QualityBadgeFormatter()
        url = formatter.generate_shields_badge_url(sample_score)
        
        assert "shields.io" in url
        assert "Quality" in url
        assert "C" in url
        assert "75" in url
        assert "orange" in url

    def test_markdown_badge(self, sample_score):
        """Test génération badge Markdown."""
        formatter = QualityBadgeFormatter()
        badge = formatter.generate_markdown_badge(sample_score)
        
        assert "![Code Quality]" in badge
        match = re.search(r"\]\(([^)]+)\)", badge)
        assert match is not None
        parsed = urlparse(match.group(1))
        assert parsed.hostname in {"shields.io", "www.shields.io"}
        assert "PASSING" in badge or "FAILING" in badge

    def test_markdown_summary(self, sample_score):
        """Test génération résumé Markdown."""
        formatter = QualityBadgeFormatter()
        summary = formatter.generate_markdown_summary(sample_score)
        
        assert "## 🧠 Code Quality Report" in summary
        assert "Score" in summary
        assert "75.0/100" in summary
        assert "Grade" in summary
        assert "C" in summary
        assert "Issues Breakdown" in summary
        assert "CRITICAL" in summary or "critical" in summary.lower()

    def test_terminal_output(self, sample_score):
        """Test génération output terminal."""
        formatter = QualityBadgeFormatter()
        output = formatter.generate_terminal_output(sample_score)
        
        assert "AI CODE REVIEW" in output
        assert "75" in output
        assert "C" in output
        assert "Critical" in output or "CRITICAL" in output

    def test_json_report(self, sample_score):
        """Test génération rapport JSON."""
        formatter = QualityBadgeFormatter()
        report = formatter.generate_json_report(sample_score)
        
        assert report['score'] == 75.0
        assert report['grade'] == "C"
        assert report['total_issues'] == 2
        assert report['critical_issues'] == 1
        assert 'badge_url' in report
        assert len(report['issues']) == 2

    def test_save_markdown_report(self, sample_score, temp_project):
        """Test sauvegarde rapport Markdown."""
        formatter = QualityBadgeFormatter()
        output_path = temp_project / "report.md"
        
        formatter.save_markdown_report(sample_score, output_path)
        
        assert output_path.exists()
        content = output_path.read_text(encoding='utf-8')
        assert "Code Quality Report" in content

    def test_save_json_report(self, sample_score, temp_project):
        """Test sauvegarde rapport JSON."""
        formatter = QualityBadgeFormatter()
        output_path = temp_project / "report.json"
        
        formatter.save_json_report(sample_score, output_path)
        
        assert output_path.exists()
        content = output_path.read_text(encoding='utf-8')
        assert '"score"' in content
        assert '"grade"' in content


class TestQualityReviewIntegration:
    """Tests pour QualityReviewIntegration."""

    def test_initialization(self, temp_project):
        """Test initialisation."""
        integration = QualityReviewIntegration(temp_project)
        
        assert integration.project_dir == temp_project
        assert integration.history_dir.exists()
        assert integration.scorer is not None
        assert integration.formatter is not None

    @pytest.mark.asyncio
    async def test_review_pr(self, temp_project):
        """Test review d'une PR."""
        # Créer un fichier de test
        test_file = temp_project / "test.py"
        test_file.write_text("def hello():\n    pass\n")
        
        integration = QualityReviewIntegration(temp_project)
        result = await integration.review_pr(
            pr_diff="",
            changed_files=["test.py"],
            pr_description="Test PR",
            provider="github",
            pr_id="123",
        )
        
        assert 'score' in result
        assert 'grade' in result
        assert 'is_passing' in result
        assert 'markdown' in result
        assert 'json' in result
        assert 'badge_url' in result

    def test_get_historical_scores_empty(self, temp_project):
        """Test récupération historique vide."""
        integration = QualityReviewIntegration(temp_project)
        history = integration.get_historical_scores()
        
        assert history == []

    def test_get_quality_trends_no_data(self, temp_project):
        """Test tendances sans données."""
        integration = QualityReviewIntegration(temp_project)
        trends = integration.get_quality_trends()
        
        assert trends['total_prs'] == 0
        assert trends['trend'] == 'no_data'

    def test_post_github_comment(self, temp_project, sample_score):
        """Test génération commentaire GitHub."""
        integration = QualityReviewIntegration(temp_project)
        comment = integration.post_github_comment(123, sample_score)
        
        assert comment['action'] == 'post_comment'
        assert comment['pr_number'] == 123
        assert 'body' in comment
        assert 'badge_url' in comment

    def test_post_azure_thread(self, temp_project, sample_score):
        """Test génération thread Azure."""
        integration = QualityReviewIntegration(temp_project)
        thread = integration.post_azure_thread(456, sample_score)
        
        assert thread['action'] == 'post_thread'
        assert thread['pr_id'] == 456
        assert 'content' in thread
        assert 'status' in thread


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

