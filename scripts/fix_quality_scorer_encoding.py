#!/usr/bin/env python3
"""Fix the encoding issue in quality_scorer.py"""

from pathlib import Path

# The corrected content
corrected_content = '''"""
AI Code Review - Quality Scorer
===================================

Système de scoring de qualité pour les Pull Requests.
Analyse automatique avec un score de 0 à 100.

Conformément au KILLING_FEATURES_ROADMAP.md - Tier 1, Feature 1
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class QualityCategory(str, Enum):
    """Catégories d'analyse de qualité."""

    BUGS = "bugs"
    SECURITY = "security"
    MAINTAINABILITY = "maintainability"
    COMPLEXITY = "complexity"


class IssueSeverity(str, Enum):
    """Niveau de sévérité des problèmes détectés."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class QualityIssue:
    """Représente un problème de qualité détecté."""

    category: QualityCategory
    severity: IssueSeverity
    title: str
    description: str
    file: str
    line: int | None = None
    suggestion: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "file": self.file,
            "line": self.line,
            "suggestion": self.suggestion,
        }


@dataclass
class QualityScore:
    """Score de qualité global d'une PR."""

    overall_score: float  # 0-100
    grade: str  # A+, A, B, C, D, F
    total_issues: int
    critical_issues: int
    issues: list[QualityIssue] = field(default_factory=list)

    @property
    def is_passing(self) -> bool:
        """La PR est-elle de qualité suffisante ?"""
        return self.overall_score >= 70 and self.critical_issues == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_score": round(self.overall_score, 2),
            "grade": self.grade,
            "total_issues": self.total_issues,
            "critical_issues": self.critical_issues,
            "is_passing": self.is_passing,
            "issues": [issue.to_dict() for issue in self.issues],
        }


class QualityScorer:
    """Analyseur de qualité de code pour PR."""

    SEVERITY_PENALTIES = {
        IssueSeverity.CRITICAL: 15,
        IssueSeverity.HIGH: 8,
        IssueSeverity.MEDIUM: 3,
        IssueSeverity.LOW: 1,
    }

    def __init__(self, project_dir: Path):
        """Initialize quality scorer."""
        self.project_dir = project_dir
        self.issues: list[QualityIssue] = []

    def score_pr(
        self,
        pr_diff: str,
        changed_files: list[str],
        pr_description: str = "",
    ) -> QualityScore:
        """Score une Pull Request complète."""
        self.issues = []

        # Analyse de chaque fichier modifié
        for file_path in changed_files:
            self._analyze_file(file_path)

        # Calcul du score
        overall_score = self._calculate_score()
        grade = self._calculate_grade(overall_score)

        # Comptage des issues par sévérité
        critical = sum(
            1 for i in self.issues if i.severity == IssueSeverity.CRITICAL
        )

        return QualityScore(
            overall_score=overall_score,
            grade=grade,
            total_issues=len(self.issues),
            critical_issues=critical,
            issues=self.issues,
        )

    def _analyze_file(self, file_path: str) -> None:
        """Analyse un fichier spécifique."""
        full_path = self.project_dir / file_path

        if not full_path.exists():
            return

        try:
            content = full_path.read_text(encoding="utf-8")
        except Exception:
            return

        extension = full_path.suffix.lower()

        if extension == ".py":
            self._analyze_python_file(content, file_path)
        elif extension in [".js", ".ts", ".jsx", ".tsx"]:
            self._analyze_javascript_file(content, file_path)
        elif extension in [".java", ".kt"]:
            self._analyze_jvm_file(content, file_path, extension)

    def _analyze_python_file(self, content: str, file_path: str) -> None:
        """Analyse un fichier Python."""
        # Check syntax
        try:
            ast.parse(content)
        except SyntaxError as e:
            self.issues.append(
                QualityIssue(
                    category=QualityCategory.BUGS,
                    severity=IssueSeverity.CRITICAL,
                    title="Syntax Error",
                    description=f"Python syntax error: {e.msg}",
                    file=file_path,
                    line=e.lineno,
                    suggestion="Fix the syntax error before submitting",
                )
            )
            return

        # Analyze AST
        try:
            tree = ast.parse(content)
            self._check_python_issues(tree, content, file_path)
        except Exception:
            pass

    def _check_python_issues(self, tree: ast.AST, content: str, file_path: str) -> None:
        """Vérifie les problèmes Python spécifiques."""
        lines = content.split("\\n")

        # Check for bare except
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    self.issues.append(
                        QualityIssue(
                            category=QualityCategory.MAINTAINABILITY,
                            severity=IssueSeverity.HIGH,
                            title="Bare Exception Handler",
                            description="Bare 'except:' catches all exceptions including system exits",
                            file=file_path,
                            line=node.lineno,
                            suggestion="Specify exception type: except SpecificException:",
                        )
                    )

        # Check for security issues
        self._check_python_security(lines, file_path)

        # Check for complexity
        self._check_python_complexity(tree, file_path)

        # Check for hardcoded credentials
        for i, line in enumerate(lines, 1):
            if re.search(r'(password|secret|token|api_key)\\s*=\\s*["\']', line, re.I):
                self.issues.append(
                    QualityIssue(
                        category=QualityCategory.SECURITY,
                        severity=IssueSeverity.CRITICAL,
                        title="Hardcoded Secret",
                        description="Hardcoded password/secret detected",
                        file=file_path,
                        line=i,
                        suggestion="Use environment variables or configuration files",
                    )
                )

    def _check_python_security(self, lines: list[str], file_path: str) -> None:
        """Vérifie les problèmes de sécurité."""
        dangerous_functions = ["eval", "exec", "pickle.loads", "__import__"]

        for i, line in enumerate(lines, 1):
            for func in dangerous_functions:
                if func + "(" in line and not line.strip().startswith("#"):
                    self.issues.append(
                        QualityIssue(
                            category=QualityCategory.SECURITY,
                            severity=IssueSeverity.CRITICAL,
                            title=f"Dangerous Function: {func}",
                            description=f"Use of {func} is a security risk",
                            file=file_path,
                            line=i,
                            suggestion=f"Replace {func} with safer alternatives",
                        )
                    )

    def _check_python_complexity(self, tree: ast.AST, file_path: str) -> None:
        """Vérifie la complexité du code."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                complexity = self._calculate_cyclomatic_complexity(node)
                if complexity > 10:
                    self.issues.append(
                        QualityIssue(
                            category=QualityCategory.COMPLEXITY,
                            severity=IssueSeverity.MEDIUM,
                            title="High Cyclomatic Complexity",
                            description=f"Function has cyclomatic complexity of {complexity}",
                            file=file_path,
                            line=node.lineno,
                            suggestion="Refactor function into smaller, simpler functions",
                        )
                    )

    def _calculate_cyclomatic_complexity(self, node: ast.FunctionDef) -> int:
        """Calcule la complexité cyclomatique."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(
                child,
                (
                    ast.If,
                    ast.While,
                    ast.For,
                    ast.ExceptHandler,
                    ast.BoolOp,
                ),
            ):
                complexity += 1
        return complexity

    def _analyze_javascript_file(self, content: str, file_path: str) -> None:
        """Analyse un fichier JavaScript/TypeScript."""
        # Check for console.log in production
        lines = content.split("\\n")
        for i, line in enumerate(lines, 1):
            if "console.log" in line and not line.strip().startswith("//"):
                self.issues.append(
                    QualityIssue(
                        category=QualityCategory.MAINTAINABILITY,
                        severity=IssueSeverity.LOW,
                        title="Console.log in code",
                        description="Debug console.log statement found",
                        file=file_path,
                        line=i,
                        suggestion="Remove or replace with proper logging",
                    )
                )

    def _analyze_jvm_file(self, content: str, file_path: str, extension: str) -> None:
        """Analyse un fichier JVM (Java, Kotlin)."""
        lines = content.split("\\n")

        if extension == ".java":
            self._check_java_issues(lines, file_path)
        elif extension == ".kt":
            self._check_kotlin_issues(lines, file_path)

    def _check_java_issues(self, lines: list[str], file_path: str) -> None:
        """Vérifie les problèmes Java spécifiques."""
        for i, line in enumerate(lines, 1):
            # Check for System.out.println
            if "System.out.println" in line and not line.strip().startswith("//"):
                self.issues.append(
                    QualityIssue(
                        category=QualityCategory.MAINTAINABILITY,
                        severity=IssueSeverity.LOW,
                        title="System.out.println in code",
                        description="Direct output to stdout found",
                        file=file_path,
                        line=i,
                        suggestion="Use proper logging framework",
                    )
                )

    def _check_kotlin_issues(self, lines: list[str], file_path: str) -> None:
        """Vérifie les problèmes Kotlin spécifiques."""
        for i, line in enumerate(lines, 1):
            # Check for println
            if "println(" in line and not line.strip().startswith("//"):
                self.issues.append(
                    QualityIssue(
                        category=QualityCategory.MAINTAINABILITY,
                        severity=IssueSeverity.LOW,
                        title="println in code",
                        description="Direct output found",
                        file=file_path,
                        line=i,
                        suggestion="Use proper logging framework",
                    )
                )

    def _calculate_score(self) -> float:
        """Calcule le score global de qualité."""
        if not self.issues:
            return 100.0

        total_penalty = sum(self.SEVERITY_PENALTIES[issue.severity] for issue in self.issues)
        score = max(0.0, 100.0 - total_penalty)
        return score

    def _calculate_grade(self, score: float) -> str:
        """Calcule la note lettre basée sur le score."""
        if score >= 95:
            return "A+"
        elif score >= 90:
            return "A"
        elif score >= 85:
            return "A-"
        elif score >= 80:
            return "B+"
        elif score >= 75:
            return "B"
        elif score >= 70:
            return "B-"
        elif score >= 65:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
'''

# Write the corrected content to the file
file_path = Path(__file__).parent.parent / "apps" / "backend" / "review" / "quality_scorer.py"
file_path.write_text(corrected_content, encoding="utf-8")
print(f"✓ Fixed {file_path}")
