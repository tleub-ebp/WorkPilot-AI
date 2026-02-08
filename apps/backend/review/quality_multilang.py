"""
Multi-Language Support for Quality Scorer
==========================================

Détections pour Java, Kotlin, C#, Go, et Rust.
"""

from __future__ import annotations

import re
from pathlib import Path

from .quality_scorer import IssueSeverity, QualityCategory, QualityIssue


class JavaAnalyzer:
    """Analyseur pour Java."""

    def analyze(self, file_path: Path, content: str) -> list[QualityIssue]:
        """Analyse un fichier Java."""
        issues = []

        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            # Détection System.out.println
            if 'System.out.println' in line or 'System.err.println' in line:
                issues.append(QualityIssue(
                    category=QualityCategory.MAINTAINABILITY,
                    severity=IssueSeverity.LOW,
                    title="Debug print statement detected",
                    description="System.out.println should not be used in production",
                    file=str(file_path),
                    line=i,
                    suggestion="Use a proper logging framework (SLF4J, Log4j)",
                ))

            # Détection printStackTrace
            if '.printStackTrace()' in line:
                issues.append(QualityIssue(
                    category=QualityCategory.BUGS,
                    severity=IssueSeverity.HIGH,
                    title="printStackTrace() should not be used",
                    description="Printing stack traces is not production-ready",
                    file=str(file_path),
                    line=i,
                    suggestion="Use proper logging framework",
                ))

            # Détection catch (Exception e)
            if re.search(r'catch\s*\(\s*Exception\s+\w+\s*\)', line):
                issues.append(QualityIssue(
                    category=QualityCategory.BUGS,
                    severity=IssueSeverity.MEDIUM,
                    title="Catching generic Exception",
                    description="Catch specific exceptions instead of generic Exception",
                    file=str(file_path),
                    line=i,
                    suggestion="Catch specific exception types",
                ))

            # Détection hardcoded passwords/secrets
            if re.search(r'(password|secret|key|token)\s*=\s*["\'][^"\']+["\']', line, re.IGNORECASE):
                issues.append(QualityIssue(
                    category=QualityCategory.SECURITY,
                    severity=IssueSeverity.CRITICAL,
                    title="Hardcoded credentials detected",
                    description="Credentials should not be hardcoded",
                    file=str(file_path),
                    line=i,
                    suggestion="Use environment variables or configuration files",
                ))

        return issues


class KotlinAnalyzer:
    """Analyseur pour Kotlin."""

    def analyze(self, file_path: Path, content: str) -> list[QualityIssue]:
        """Analyse un fichier Kotlin."""
        issues = []

        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            # Détection println
            if 'println(' in line:
                issues.append(QualityIssue(
                    category=QualityCategory.MAINTAINABILITY,
                    severity=IssueSeverity.LOW,
                    title="Debug print statement detected",
                    description="println should not be used in production",
                    file=str(file_path),
                    line=i,
                    suggestion="Use a proper logging framework",
                ))

            # Détection !!
            if '!!' in line:
                issues.append(QualityIssue(
                    category=QualityCategory.BUGS,
                    severity=IssueSeverity.HIGH,
                    title="Non-null assertion operator (!!) detected",
                    description="!! can cause NullPointerException at runtime",
                    file=str(file_path),
                    line=i,
                    suggestion="Use safe call operator ?. or proper null checks",
                ))

            # Détection catch (e: Exception)
            if re.search(r'catch\s*\(\s*\w+\s*:\s*Exception\s*\)', line):
                issues.append(QualityIssue(
                    category=QualityCategory.BUGS,
                    severity=IssueSeverity.MEDIUM,
                    title="Catching generic Exception",
                    description="Catch specific exceptions instead",
                    file=str(file_path),
                    line=i,
                    suggestion="Catch specific exception types",
                ))

        return issues


class CSharpAnalyzer:
    """Analyseur pour C#."""

    def analyze(self, file_path: Path, content: str) -> list[QualityIssue]:
        """Analyse un fichier C#."""
        issues = []

        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            # Détection Console.WriteLine
            if 'Console.WriteLine' in line or 'Console.Write(' in line:
                issues.append(QualityIssue(
                    category=QualityCategory.MAINTAINABILITY,
                    severity=IssueSeverity.LOW,
                    title="Debug print statement detected",
                    description="Console.WriteLine should not be used in production",
                    file=str(file_path),
                    line=i,
                    suggestion="Use ILogger or logging framework",
                ))

            # Détection catch (Exception)
            if re.search(r'catch\s*\(\s*Exception\s*\w*\s*\)', line):
                issues.append(QualityIssue(
                    category=QualityCategory.BUGS,
                    severity=IssueSeverity.MEDIUM,
                    title="Catching generic Exception",
                    description="Catch specific exceptions instead",
                    file=str(file_path),
                    line=i,
                    suggestion="Catch specific exception types",
                ))

            # Détection hardcoded connection strings
            if 'connectionString' in line and '=' in line and ('"' in line or "'" in line):
                issues.append(QualityIssue(
                    category=QualityCategory.SECURITY,
                    severity=IssueSeverity.CRITICAL,
                    title="Hardcoded connection string",
                    description="Connection strings should not be hardcoded",
                    file=str(file_path),
                    line=i,
                    suggestion="Use configuration files or secret managers",
                ))

        return issues


class GoAnalyzer:
    """Analyseur pour Go."""

    def analyze(self, file_path: Path, content: str) -> list[QualityIssue]:
        """Analyse un fichier Go."""
        issues = []

        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            # Détection fmt.Println
            if 'fmt.Println' in line or 'fmt.Printf' in line:
                issues.append(QualityIssue(
                    category=QualityCategory.MAINTAINABILITY,
                    severity=IssueSeverity.LOW,
                    title="Debug print statement detected",
                    description="fmt.Println should not be used in production",
                    file=str(file_path),
                    line=i,
                    suggestion="Use proper logging package (log, logrus, zap)",
                ))

            # Détection panic()
            if 'panic(' in line:
                issues.append(QualityIssue(
                    category=QualityCategory.BUGS,
                    severity=IssueSeverity.HIGH,
                    title="panic() detected",
                    description="panic() should be avoided in production code",
                    file=str(file_path),
                    line=i,
                    suggestion="Return errors instead of panicking",
                ))

            # Détection _ = err (error ignoré)
            if re.search(r'_\s*=.*err', line):
                issues.append(QualityIssue(
                    category=QualityCategory.BUGS,
                    severity=IssueSeverity.HIGH,
                    title="Error silently ignored",
                    description="Errors should be properly handled",
                    file=str(file_path),
                    line=i,
                    suggestion="Handle or propagate errors properly",
                ))

        return issues


class RustAnalyzer:
    """Analyseur pour Rust."""

    def analyze(self, file_path: Path, content: str) -> list[QualityIssue]:
        """Analyse un fichier Rust."""
        issues = []

        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            # Détection println!
            if 'println!' in line or 'print!' in line:
                issues.append(QualityIssue(
                    category=QualityCategory.MAINTAINABILITY,
                    severity=IssueSeverity.LOW,
                    title="Debug print macro detected",
                    description="println! should not be used in production",
                    file=str(file_path),
                    line=i,
                    suggestion="Use proper logging crate (log, env_logger)",
                ))

            # Détection unwrap()
            if '.unwrap()' in line:
                issues.append(QualityIssue(
                    category=QualityCategory.BUGS,
                    severity=IssueSeverity.HIGH,
                    title="unwrap() can cause panic",
                    description="unwrap() will panic if value is None or Err",
                    file=str(file_path),
                    line=i,
                    suggestion="Use pattern matching, unwrap_or, or ? operator",
                ))

            # Détection expect()
            if '.expect(' in line:
                issues.append(QualityIssue(
                    category=QualityCategory.BUGS,
                    severity=IssueSeverity.MEDIUM,
                    title="expect() can cause panic",
                    description="expect() will panic if value is None or Err",
                    file=str(file_path),
                    line=i,
                    suggestion="Use pattern matching or ? operator",
                ))

            # Détection panic!()
            if 'panic!' in line:
                issues.append(QualityIssue(
                    category=QualityCategory.BUGS,
                    severity=IssueSeverity.HIGH,
                    title="panic! detected",
                    description="panic! should be avoided in library code",
                    file=str(file_path),
                    line=i,
                    suggestion="Return Result instead",
                ))

        return issues


# Map des extensions vers les analyseurs
LANGUAGE_ANALYZERS = {
    '.java': JavaAnalyzer,
    '.kt': KotlinAnalyzer,
    '.kts': KotlinAnalyzer,
    '.cs': CSharpAnalyzer,
    '.go': GoAnalyzer,
    '.rs': RustAnalyzer,
}


def get_analyzer(file_path: Path):
    """Retourne l'analyseur approprié pour un fichier."""
    suffix = file_path.suffix.lower()
    analyzer_class = LANGUAGE_ANALYZERS.get(suffix)
    if analyzer_class:
        return analyzer_class()
    return None

