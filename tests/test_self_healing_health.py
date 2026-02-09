"""
Tests for Self-Healing Codebase - Health Checker
=================================================
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from apps.backend.self_healing.health_checker import (
    HealthChecker,
    HealthIssue,
    HealthStatus,
    IssueType,
)


@pytest.fixture
def temp_project():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Create some test files
        (project_dir / "README.md").write_text("# Test Project")
        
        # Python file with issues
        (project_dir / "bad_code.py").write_text('''
def long_function():
    """A function with many statements."""
    x = 1
    y = 2
    # ... 50+ more statements
    for i in range(100):
        for j in range(100):  # Nested loop
            print(i * j)
    
    password = "hardcoded123"  # Security issue
    eval("dangerous")  # Security issue
    
    # TODO: Fix this later
    return x + y

def function_with_many_params(a, b, c, d, e, f, g):
    """Too many parameters."""
    return a + b + c + d + e + f + g
''')
        
        yield project_dir


@pytest.mark.asyncio
async def test_health_checker_basic(temp_project):
    """Test basic health check."""
    checker = HealthChecker(temp_project)
    report = await checker.check_health()
    
    assert report is not None
    assert 0 <= report.overall_score <= 100
    assert report.status in HealthStatus
    assert report.total_files > 0


@pytest.mark.asyncio
async def test_health_checker_detects_quality_issues(temp_project):
    """Test detection of code quality issues."""
    checker = HealthChecker(temp_project)
    report = await checker.check_health()
    
    # Should find quality issues
    quality_issues = [
        issue for issue in report.all_issues
        if issue.type == IssueType.CODE_SMELL
    ]
    
    assert len(quality_issues) > 0
    
    # Check for specific issues
    titles = [issue.title for issue in quality_issues]
    assert any("parameter" in title.lower() for title in titles)
    assert any("TODO" in title for title in titles)


@pytest.mark.asyncio
async def test_health_checker_detects_security_issues(temp_project):
    """Test detection of security issues."""
    checker = HealthChecker(temp_project)
    report = await checker.check_health()
    
    # Should find security issues
    security_issues = [
        issue for issue in report.all_issues
        if issue.type == IssueType.SECURITY
    ]
    
    assert len(security_issues) > 0
    
    # Check for specific issues
    titles = [issue.title for issue in security_issues]
    assert any("password" in title.lower() for title in titles)
    assert any("eval" in title.lower() for title in titles)


@pytest.mark.asyncio
async def test_health_checker_detects_performance_issues(temp_project):
    """Test detection of performance issues."""
    checker = HealthChecker(temp_project)
    report = await checker.check_health()
    
    # Should find performance issues
    perf_issues = [
        issue for issue in report.all_issues
        if issue.type == IssueType.PERFORMANCE
    ]
    
    assert len(perf_issues) > 0


@pytest.mark.asyncio
async def test_health_status_determination():
    """Test health status determination."""
    checker = HealthChecker(".")
    
    assert checker._determine_status(95) == HealthStatus.EXCELLENT
    assert checker._determine_status(80) == HealthStatus.GOOD
    assert checker._determine_status(60) == HealthStatus.FAIR
    assert checker._determine_status(40) == HealthStatus.POOR
    assert checker._determine_status(20) == HealthStatus.CRITICAL


@pytest.mark.asyncio
async def test_health_report_critical_issues(temp_project):
    """Test getting critical issues from report."""
    checker = HealthChecker(temp_project)
    report = await checker.check_health()
    
    critical = report.get_critical_issues()
    high_priority = report.get_high_priority_issues()
    
    assert isinstance(critical, list)
    assert isinstance(high_priority, list)
    assert len(high_priority) >= len(critical)


@pytest.mark.asyncio
async def test_health_report_to_dict(temp_project):
    """Test converting report to dictionary."""
    checker = HealthChecker(temp_project)
    report = await checker.check_health()
    
    report_dict = report.to_dict()
    
    assert "overall_score" in report_dict
    assert "status" in report_dict
    assert "scores" in report_dict
    assert "total_issues" in report_dict
    assert report_dict["overall_score"] == report.overall_score


def test_health_issue_to_dict():
    """Test converting health issue to dictionary."""
    issue = HealthIssue(
        type=IssueType.SECURITY,
        severity="critical",
        title="Test Issue",
        description="Test description",
        file="test.py",
        line=42,
        suggestion="Fix it",
        effort="low",
    )
    
    issue_dict = issue.to_dict()
    
    assert issue_dict["type"] == "security"
    assert issue_dict["severity"] == "critical"
    assert issue_dict["title"] == "Test Issue"
    assert issue_dict["line"] == 42


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
