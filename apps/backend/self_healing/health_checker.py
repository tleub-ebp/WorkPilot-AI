"""
Health Checker Module
=====================

Analyzes codebase health across multiple dimensions:
- Code quality and maintainability
- Performance metrics
- Security vulnerabilities
- Code smells and anti-patterns
- Test coverage
- Documentation quality
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

try:
    from debug import debug, debug_section, debug_warning
except ImportError:
    def debug(module: str, message: str, **kwargs): pass
    def debug_section(module: str, message: str): pass
    def debug_warning(module: str, message: str, **kwargs): pass


class HealthStatus(str, Enum):
    """Overall health status."""
    
    EXCELLENT = "excellent"  # 90-100
    GOOD = "good"  # 70-89
    FAIR = "fair"  # 50-69
    POOR = "poor"  # 30-49
    CRITICAL = "critical"  # 0-29


class IssueType(str, Enum):
    """Types of health issues."""
    
    CODE_SMELL = "code_smell"
    PERFORMANCE = "performance"
    SECURITY = "security"
    COMPLEXITY = "complexity"
    DUPLICATION = "duplication"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    STYLE = "style"


@dataclass
class HealthIssue:
    """Represents a health issue found in the codebase."""
    
    type: IssueType
    severity: str  # critical, high, medium, low
    title: str
    description: str
    file: str
    line: int | None = None
    suggestion: str | None = None
    impact: str | None = None
    effort: str = "medium"  # low, medium, high
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type.value,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "file": self.file,
            "line": self.line,
            "suggestion": self.suggestion,
            "impact": self.impact,
            "effort": self.effort,
        }


@dataclass
class MetricScore:
    """Score for a specific metric."""
    
    name: str
    score: float  # 0-100
    weight: float  # How much this affects overall score
    issues: list[HealthIssue] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthReport:
    """Complete health report of the codebase."""
    
    timestamp: datetime
    overall_score: float  # 0-100
    status: HealthStatus
    
    # Metric scores
    quality_score: MetricScore
    performance_score: MetricScore
    security_score: MetricScore
    maintainability_score: MetricScore
    testing_score: MetricScore
    documentation_score: MetricScore
    
    # All issues found
    all_issues: list[HealthIssue] = field(default_factory=list)
    
    # Statistics
    total_files: int = 0
    total_lines: int = 0
    changed_files: int = 0
    
    # Comparison with previous
    score_change: float | None = None
    is_degrading: bool = False
    
    def get_critical_issues(self) -> list[HealthIssue]:
        """Get all critical issues."""
        return [i for i in self.all_issues if i.severity == "critical"]
    
    def get_high_priority_issues(self) -> list[HealthIssue]:
        """Get critical and high severity issues."""
        return [i for i in self.all_issues if i.severity in ["critical", "high"]]
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "overall_score": self.overall_score,
            "status": self.status.value,
            "scores": {
                "quality": self.quality_score.score,
                "performance": self.performance_score.score,
                "security": self.security_score.score,
                "maintainability": self.maintainability_score.score,
                "testing": self.testing_score.score,
                "documentation": self.documentation_score.score,
            },
            "total_issues": len(self.all_issues),
            "critical_issues": len(self.get_critical_issues()),
            "high_priority_issues": len(self.get_high_priority_issues()),
            "total_files": self.total_files,
            "total_lines": self.total_lines,
            "score_change": self.score_change,
            "is_degrading": self.is_degrading,
        }


class HealthChecker:
    """Main health checker for codebase analysis."""
    
    def __init__(self, project_dir: str | Path):
        self.project_dir = Path(project_dir)
        self.excluded_patterns = [
            "node_modules",
            ".venv",
            "__pycache__",
            ".git",
            "dist",
            "build",
        ]
    
    async def check_health(self) -> HealthReport:
        """Run complete health check."""
        debug_section("self_healing", "🧬 Running Health Check")
        
        timestamp = datetime.now()
        
        # Analyze different aspects
        quality = await self._check_quality()
        performance = await self._check_performance()
        security = await self._check_security()
        maintainability = await self._check_maintainability()
        testing = await self._check_testing()
        documentation = await self._check_documentation()
        
        # Collect all issues
        all_issues = (
            quality.issues
            + performance.issues
            + security.issues
            + maintainability.issues
            + testing.issues
            + documentation.issues
        )
        
        # Calculate overall score (weighted average)
        overall_score = (
            quality.score * quality.weight
            + performance.score * performance.weight
            + security.score * security.weight
            + maintainability.score * maintainability.weight
            + testing.score * testing.weight
            + documentation.score * documentation.weight
        )
        
        # Determine status
        status = self._determine_status(overall_score)
        
        # Get statistics
        stats = self._get_file_stats()
        
        report = HealthReport(
            timestamp=timestamp,
            overall_score=round(overall_score, 1),
            status=status,
            quality_score=quality,
            performance_score=performance,
            security_score=security,
            maintainability_score=maintainability,
            testing_score=testing,
            documentation_score=documentation,
            all_issues=all_issues,
            **stats,
        )
        
        debug("self_healing", f"Health Score: {report.overall_score}/100 ({status.value})")
        debug("self_healing", f"Total Issues: {len(all_issues)}")
        
        return report
    
    async def _check_quality(self) -> MetricScore:
        """Check code quality."""
        issues = []
        
        # Find Python files
        py_files = self._find_files("**/*.py")
        
        for file_path in py_files[:50]:  # Limit for performance
            file_issues = self._analyze_python_quality(file_path)
            issues.extend(file_issues)
        
        # Calculate score (100 - penalty for issues)
        score = max(0, 100 - len(issues) * 2)
        
        return MetricScore(
            name="quality",
            score=score,
            weight=0.25,
            issues=issues,
            details={"files_analyzed": len(py_files)},
        )
    
    def _analyze_python_quality(self, file_path: Path) -> list[HealthIssue]:
        """Analyze a Python file for quality issues."""
        issues = []
        
        try:
            content = file_path.read_text(encoding="utf-8")
            
            # Parse AST
            tree = ast.parse(content)
            
            # Check for common issues
            for node in ast.walk(tree):
                # Long functions
                if isinstance(node, ast.FunctionDef):
                    if len(node.body) > 50:
                        issues.append(
                            HealthIssue(
                                type=IssueType.CODE_SMELL,
                                severity="medium",
                                title="Long function",
                                description=f"Function '{node.name}' has {len(node.body)} statements",
                                file=str(file_path.relative_to(self.project_dir)),
                                line=node.lineno,
                                suggestion="Consider breaking this function into smaller pieces",
                                effort="medium",
                            )
                        )
                
                # Too many arguments
                if isinstance(node, ast.FunctionDef):
                    arg_count = len(node.args.args)
                    if arg_count > 5:
                        issues.append(
                            HealthIssue(
                                type=IssueType.CODE_SMELL,
                                severity="low",
                                title="Too many parameters",
                                description=f"Function '{node.name}' has {arg_count} parameters",
                                file=str(file_path.relative_to(self.project_dir)),
                                line=node.lineno,
                                suggestion="Consider using a dataclass or config object",
                                effort="low",
                            )
                        )
            
            # Check for TODO/FIXME comments
            for i, line in enumerate(content.split("\n"), 1):
                if "TODO" in line or "FIXME" in line:
                    issues.append(
                        HealthIssue(
                            type=IssueType.CODE_SMELL,
                            severity="low",
                            title="TODO comment",
                            description="Unresolved TODO/FIXME comment",
                            file=str(file_path.relative_to(self.project_dir)),
                            line=i,
                            suggestion="Resolve or track this TODO",
                            effort="low",
                        )
                    )
        
        except Exception as e:
            debug_warning("self_healing", f"Failed to analyze {file_path}: {e}")
        
        return issues
    
    async def _check_performance(self) -> MetricScore:
        """Check for performance issues."""
        issues = []
        
        py_files = self._find_files("**/*.py")
        
        for file_path in py_files[:50]:
            try:
                content = file_path.read_text(encoding="utf-8")
                
                # Check for inefficient patterns
                if "time.sleep" in content and "async" not in content:
                    issues.append(
                        HealthIssue(
                            type=IssueType.PERFORMANCE,
                            severity="medium",
                            title="Blocking sleep detected",
                            description="Using time.sleep() in synchronous code",
                            file=str(file_path.relative_to(self.project_dir)),
                            suggestion="Consider using asyncio.sleep() for async code",
                            effort="low",
                        )
                    )
                
                # Nested loops
                if re.search(r"for .+ in .+:\s+for .+ in", content, re.MULTILINE):
                    issues.append(
                        HealthIssue(
                            type=IssueType.PERFORMANCE,
                            severity="low",
                            title="Nested loops detected",
                            description="Potential O(n²) complexity",
                            file=str(file_path.relative_to(self.project_dir)),
                            suggestion="Consider optimizing with better data structures",
                            effort="medium",
                        )
                    )
            
            except Exception:
                pass
        
        score = max(0, 100 - len(issues) * 5)
        
        return MetricScore(
            name="performance",
            score=score,
            weight=0.15,
            issues=issues,
            details={"files_analyzed": len(py_files)},
        )
    
    async def _check_security(self) -> MetricScore:
        """Check for security issues."""
        issues = []
        
        py_files = self._find_files("**/*.py")
        
        for file_path in py_files[:50]:
            try:
                content = file_path.read_text(encoding="utf-8")
                
                # Hardcoded secrets patterns
                if re.search(r'password\s*=\s*["\'][^"\']+["\']', content, re.IGNORECASE):
                    issues.append(
                        HealthIssue(
                            type=IssueType.SECURITY,
                            severity="critical",
                            title="Hardcoded password",
                            description="Potential hardcoded password detected",
                            file=str(file_path.relative_to(self.project_dir)),
                            suggestion="Use environment variables or secrets manager",
                            effort="low",
                        )
                    )
                
                # SQL injection risk
                if "execute(" in content and "f\"" in content:
                    issues.append(
                        HealthIssue(
                            type=IssueType.SECURITY,
                            severity="high",
                            title="Potential SQL injection",
                            description="String formatting in SQL query",
                            file=str(file_path.relative_to(self.project_dir)),
                            suggestion="Use parameterized queries",
                            effort="medium",
                        )
                    )
                
                # Eval usage
                if "eval(" in content:
                    issues.append(
                        HealthIssue(
                            type=IssueType.SECURITY,
                            severity="high",
                            title="Use of eval()",
                            description="eval() can execute arbitrary code",
                            file=str(file_path.relative_to(self.project_dir)),
                            suggestion="Use ast.literal_eval() or safer alternatives",
                            effort="low",
                        )
                    )
            
            except Exception:
                pass
        
        score = max(0, 100 - len(issues) * 10)
        
        return MetricScore(
            name="security",
            score=score,
            weight=0.30,  # Security is most important
            issues=issues,
            details={"files_analyzed": len(py_files)},
        )
    
    async def _check_maintainability(self) -> MetricScore:
        """Check code maintainability."""
        issues = []
        
        py_files = self._find_files("**/*.py")
        
        for file_path in py_files[:50]:
            try:
                # Check file length
                content = file_path.read_text(encoding="utf-8")
                line_count = len(content.split("\n"))
                
                if line_count > 1000:
                    issues.append(
                        HealthIssue(
                            type=IssueType.COMPLEXITY,
                            severity="medium",
                            title="Large file",
                            description=f"File has {line_count} lines",
                            file=str(file_path.relative_to(self.project_dir)),
                            suggestion="Consider splitting into smaller modules",
                            effort="high",
                        )
                    )
                
                # Check for missing docstrings in classes/functions
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                        if not ast.get_docstring(node):
                            issues.append(
                                HealthIssue(
                                    type=IssueType.DOCUMENTATION,
                                    severity="low",
                                    title="Missing docstring",
                                    description=f"{node.__class__.__name__} '{node.name}' has no docstring",
                                    file=str(file_path.relative_to(self.project_dir)),
                                    line=node.lineno,
                                    suggestion="Add a docstring to explain the purpose",
                                    effort="low",
                                )
                            )
            
            except Exception:
                pass
        
        score = max(0, 100 - len(issues) * 1)
        
        return MetricScore(
            name="maintainability",
            score=score,
            weight=0.15,
            issues=issues,
            details={"files_analyzed": len(py_files)},
        )
    
    async def _check_testing(self) -> MetricScore:
        """Check test coverage and quality."""
        issues = []
        
        # Find test files
        test_files = self._find_files("**/test_*.py") + self._find_files("**/*_test.py")
        source_files = self._find_files("**/*.py")
        source_files = [f for f in source_files if "test" not in str(f)]
        
        if not test_files:
            issues.append(
                HealthIssue(
                    type=IssueType.TESTING,
                    severity="high",
                    title="No test files found",
                    description="Project appears to have no tests",
                    file=".",
                    suggestion="Add tests for critical functionality",
                    effort="high",
                )
            )
            score = 30.0
        else:
            # Calculate test ratio
            test_ratio = len(test_files) / max(len(source_files), 1)
            score = min(100, test_ratio * 200)  # Aim for 50% test files
        
        return MetricScore(
            name="testing",
            score=score,
            weight=0.10,
            issues=issues,
            details={
                "test_files": len(test_files),
                "source_files": len(source_files),
            },
        )
    
    async def _check_documentation(self) -> MetricScore:
        """Check documentation quality."""
        issues = []
        
        # Check for README
        has_readme = (self.project_dir / "README.md").exists()
        if not has_readme:
            issues.append(
                HealthIssue(
                    type=IssueType.DOCUMENTATION,
                    severity="medium",
                    title="Missing README",
                    description="Project has no README.md",
                    file=".",
                    suggestion="Add a README.md with project overview",
                    effort="medium",
                )
            )
        
        # Check for docs directory
        has_docs = (self.project_dir / "docs").exists()
        
        score = 100.0
        if not has_readme:
            score -= 40
        if not has_docs:
            score -= 20
        score = max(0, score - len(issues) * 10)
        
        return MetricScore(
            name="documentation",
            score=score,
            weight=0.05,
            issues=issues,
            details={
                "has_readme": has_readme,
                "has_docs": has_docs,
            },
        )
    
    def _find_files(self, pattern: str) -> list[Path]:
        """Find files matching pattern, excluding certain directories."""
        files = []
        for path in self.project_dir.rglob(pattern):
            if any(excl in str(path) for excl in self.excluded_patterns):
                continue
            if path.is_file():
                files.append(path)
        return files
    
    def _get_file_stats(self) -> dict[str, int]:
        """Get file statistics."""
        all_files = self._find_files("**/*.py")
        total_lines = 0
        
        for file_path in all_files:
            try:
                content = file_path.read_text(encoding="utf-8")
                total_lines += len(content.split("\n"))
            except Exception:
                pass
        
        return {
            "total_files": len(all_files),
            "total_lines": total_lines,
        }
    
    def _determine_status(self, score: float) -> HealthStatus:
        """Determine health status from score."""
        if score >= 90:
            return HealthStatus.EXCELLENT
        elif score >= 70:
            return HealthStatus.GOOD
        elif score >= 50:
            return HealthStatus.FAIR
        elif score >= 30:
            return HealthStatus.POOR
        else:
            return HealthStatus.CRITICAL
