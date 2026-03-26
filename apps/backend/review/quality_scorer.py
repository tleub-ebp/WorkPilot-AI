"""
AI Code Review - Quality Scorer
=======================================================

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
        """La PR est-elle de qualité suffisante?"""
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
        changed_files: list[str],
    ) -> QualityScore:
        """Score une Pull Request complète."""
        self.issues = []

        for file_path in changed_files:
            self._analyze_file(file_path)

        overall_score = self._calculate_score()
        grade = self._calculate_grade(overall_score)

        critical = sum(1 for i in self.issues if i.severity == IssueSeverity.CRITICAL)

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

        try:
            tree = ast.parse(content)
            self._check_python_issues(tree, content, file_path)
        except Exception:
            pass

    def _check_python_issues(self, tree: ast.AST, content: str, file_path: str) -> None:
        """Vérifie les problèmes Python spécifiques."""
        complexity_scores = {}

        # Security checks using regex
        if re.search(r'\bpassword\s*=\s*["\'][^"\']+["\']', content, re.IGNORECASE):
            self.issues.append(
                QualityIssue(
                    category=QualityCategory.SECURITY,
                    severity=IssueSeverity.CRITICAL,
                    title="Hardcoded password",
                    description="Hardcoded password detected in source code",
                    file=file_path,
                    suggestion="Use environment variables or configuration files for passwords",
                )
            )

        if re.search(r"\beval\s*\(", content):
            self.issues.append(
                QualityIssue(
                    category=QualityCategory.SECURITY,
                    severity=IssueSeverity.CRITICAL,
                    title="Use of eval()",
                    description="eval() can execute arbitrary code and is a security risk",
                    file=file_path,
                    suggestion="Use safer alternatives like ast.literal_eval or proper parsing",
                )
            )

        if re.search(r"\bexec\s*\(", content):
            self.issues.append(
                QualityIssue(
                    category=QualityCategory.SECURITY,
                    severity=IssueSeverity.CRITICAL,
                    title="Use of exec()",
                    description="exec() can execute arbitrary code and is a security risk",
                    file=file_path,
                    suggestion="Use safer alternatives or avoid dynamic code execution",
                )
            )

        if re.search(r"\bsubprocess\.call\s*\([^)]*\s*shell\s*=\s*True", content):
            self.issues.append(
                QualityIssue(
                    category=QualityCategory.SECURITY,
                    severity=IssueSeverity.HIGH,
                    title="Shell injection risk",
                    description="subprocess.call with shell=True can lead to shell injection",
                    file=file_path,
                    suggestion="Avoid shell=True or use proper input sanitization",
                )
            )

        for node in ast.walk(tree):
            # Check for bare except
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                self.issues.append(
                    QualityIssue(
                        category=QualityCategory.BUGS,
                        severity=IssueSeverity.HIGH,
                        title="Bare except",
                        description="Bare except clause catches all exceptions including SystemExit",
                        file=file_path,
                        line=node.lineno,
                        suggestion="Specify exception type",
                    )
                )

            # Calculate cyclomatic complexity for functions
            if isinstance(node, ast.FunctionDef):
                complexity = self._calculate_complexity(node)
                complexity_scores[node.name] = complexity

                # Flag functions with high complexity (>10)
                if complexity > 10:
                    self.issues.append(
                        QualityIssue(
                            category=QualityCategory.COMPLEXITY,
                            severity=IssueSeverity.MEDIUM,
                            title="High cyclomatic complexity",
                            description=f"Function '{node.name}' has cyclomatic complexity of {complexity}",
                            file=file_path,
                            line=node.lineno,
                            suggestion="Consider breaking down this function into smaller functions",
                        )
                    )

            # Check for deeply nested code
            if isinstance(node, (ast.If, ast.For, ast.While, ast.With)):
                nesting_depth = self._get_nesting_depth(node, tree)
                if nesting_depth > 4:
                    self.issues.append(
                        QualityIssue(
                            category=QualityCategory.COMPLEXITY,
                            severity=IssueSeverity.MEDIUM,
                            title="Deeply nested code",
                            description=f"Code nesting depth of {nesting_depth} detected",
                            file=file_path,
                            line=node.lineno,
                            suggestion="Consider extracting nested logic into separate functions",
                        )
                    )

    def _analyze_javascript_file(self, content: str, file_path: str) -> None:
        """Analyse un fichier JavaScript/TypeScript."""
        if re.search(r"\bconsole\.log\b", content):
            self.issues.append(
                QualityIssue(
                    category=QualityCategory.MAINTAINABILITY,
                    severity=IssueSeverity.LOW,
                    title="Debug output found",
                    description="console.log statements should be removed",
                    file=file_path,
                    suggestion="Remove console.log or use proper logging",
                )
            )

    def _analyze_jvm_file(self, content: str, file_path: str, extension: str) -> None:
        """Analyse un fichier Java/Kotlin."""
        pass

    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity for a function."""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            # Decision points that increase complexity
            if isinstance(
                child,
                (
                    ast.If,
                    ast.While,
                    ast.For,
                    ast.AsyncFor,
                    ast.ExceptHandler,
                    ast.With,
                    ast.And,
                    ast.Or,
                    ast.ListComp,
                    ast.DictComp,
                    ast.SetComp,
                    ast.GeneratorExp,
                ),
            ):
                complexity += 1

        return complexity

    def _get_nesting_depth(self, node: ast.AST, tree: ast.AST) -> int:
        """Calculate the nesting depth of a node."""
        depth = 0
        current = node

        while hasattr(current, "parent") or self._find_parent(current, tree):
            parent = self._find_parent(current, tree)
            if parent and isinstance(
                parent,
                (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.ExceptHandler),
            ):
                depth += 1
            current = parent

        return depth

    def _find_parent(self, node: ast.AST, tree: ast.AST) -> ast.AST | None:
        """Find the parent of a node in the AST."""
        for parent in ast.walk(tree):
            for attr in ["body", "orelse", "finalbody"]:
                if hasattr(parent, attr) and node in getattr(parent, attr, []):
                    return parent
        return None

    def _calculate_score(self) -> float:
        """Calcule le score de qualité global."""
        if not self.issues:
            return 100.0

        total_penalty = sum(
            self.SEVERITY_PENALTIES[issue.severity] for issue in self.issues
        )
        score = max(0, 100 - total_penalty)
        return float(score)

    def _calculate_grade(self, score: float) -> str:
        """Calcule la note letter basée sur le score."""
        if score >= 97:
            return "A+"
        elif score >= 93:
            return "A"
        elif score >= 90:
            return "A-"
        elif score >= 85:
            return "B+"
        elif score >= 80:
            return "B"
        elif score >= 75:
            return "C"
        elif score >= 70:
            return "C-"
        elif score >= 65:
            return "D"
        elif score >= 60:
            return "D-"
        else:
            return "F"
