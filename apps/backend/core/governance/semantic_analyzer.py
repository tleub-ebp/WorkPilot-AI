"""
Semantic Analyzer — AST-level diff analysis for policy enforcement.

Goes beyond simple pattern matching on file paths by analyzing the
*semantic intent* of a diff: deleted test functions, raw SQL usage,
TypeScript ``any`` casts, interface contournement, etc.

The analyzer is 100% algorithmic (no LLM) by default.  An optional
LLM enrichment layer can be enabled for ambiguous cases.
"""

from __future__ import annotations

import ast
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ViolationType(str, Enum):
    TEST_DELETION = "test_deletion"
    RAW_SQL = "raw_sql"
    TYPESCRIPT_ANY = "typescript_any"
    INTERFACE_BYPASS = "interface_bypass"
    SECURITY_SENSITIVE = "security_sensitive"
    DEPENDENCY_CHANGE = "dependency_change"


@dataclass
class SemanticViolation:
    """A semantic violation found by AST or pattern analysis."""

    violation_type: ViolationType
    description: str
    file_path: str
    line_number: int | None = None
    severity: str = "high"
    suggestion: str | None = None


class SemanticAnalyzer:
    """Analyze diffs for semantic policy violations.

    This analyzer works on the raw diff content (added/removed lines)
    and optionally on full file content for AST parsing.
    """

    # Patterns for Python test function/class detection
    _PYTHON_TEST_PATTERNS = [
        re.compile(r"^\s*def\s+test_\w+"),
        re.compile(r"^\s*class\s+Test\w+"),
        re.compile(r"^\s*async\s+def\s+test_\w+"),
    ]

    # Patterns for JS/TS test detection
    _JS_TEST_PATTERNS = [
        re.compile(r"""^\s*(?:it|test|describe)\s*\("""),
        re.compile(r"""^\s*(?:it|test)\.(?:only|skip)\s*\("""),
    ]

    # Raw SQL patterns
    _RAW_SQL_PATTERNS = [
        re.compile(r"cursor\.execute\s*\(", re.IGNORECASE),
        re.compile(r"execute_raw\s*\(", re.IGNORECASE),
        re.compile(r"raw_sql\s*\(", re.IGNORECASE),
        re.compile(r"\bconn\.execute\s*\(", re.IGNORECASE),
        re.compile(r"\.raw\s*\(\s*['\"]", re.IGNORECASE),
    ]

    # TypeScript `any` usage
    _TS_ANY_PATTERNS = [
        re.compile(r":\s*any\b"),
        re.compile(r"as\s+any\b"),
        re.compile(r"<any>"),
    ]

    # Security-sensitive patterns
    _SECURITY_PATTERNS = [
        re.compile(r"eval\s*\(", re.IGNORECASE),
        re.compile(r"exec\s*\(", re.IGNORECASE),
        re.compile(r"__import__\s*\("),
        re.compile(r"subprocess\.(?:call|run|Popen)\s*\(.*shell\s*=\s*True"),
        re.compile(r"os\.system\s*\("),
    ]

    # Dependency files
    _DEPENDENCY_FILES = {
        "package.json",
        "requirements.txt",
        "Pipfile",
        "Cargo.toml",
        "go.mod",
        "go.sum",
        "pom.xml",
        "build.gradle",
        "Gemfile",
    }

    def analyze_diff(
        self,
        file_path: str,
        added_lines: list[str],
        removed_lines: list[str],
        full_content: str | None = None,
    ) -> list[SemanticViolation]:
        """Analyze a diff for semantic violations.

        Args:
            file_path: Path to the file being modified.
            added_lines: Lines added in the diff.
            removed_lines: Lines removed in the diff.
            full_content: Optional full file content for deeper analysis.

        Returns:
            List of semantic violations found.
        """
        violations: list[SemanticViolation] = []

        violations.extend(self._check_test_deletions(file_path, removed_lines))
        violations.extend(self._check_raw_sql(file_path, added_lines))
        violations.extend(self._check_typescript_any(file_path, added_lines))
        violations.extend(self._check_security_sensitive(file_path, added_lines))
        violations.extend(self._check_dependency_changes(file_path, added_lines, removed_lines))

        if full_content and file_path.endswith(".py"):
            violations.extend(self._check_python_ast(file_path, full_content))

        return violations

    def _check_test_deletions(
        self, file_path: str, removed_lines: list[str]
    ) -> list[SemanticViolation]:
        """Detect deletion of test functions or classes."""
        violations = []
        patterns = (
            self._PYTHON_TEST_PATTERNS
            if file_path.endswith(".py")
            else self._JS_TEST_PATTERNS
        )

        for i, line in enumerate(removed_lines):
            for pattern in patterns:
                if pattern.search(line):
                    violations.append(
                        SemanticViolation(
                            violation_type=ViolationType.TEST_DELETION,
                            description=f"Test function/class deleted: {line.strip()}",
                            file_path=file_path,
                            line_number=i + 1,
                            severity="high",
                            suggestion="Consider deprecating or skipping the test instead of deleting it.",
                        )
                    )
                    break

        return violations

    def _check_raw_sql(
        self, file_path: str, added_lines: list[str]
    ) -> list[SemanticViolation]:
        """Detect raw SQL usage in added lines."""
        violations = []
        for i, line in enumerate(added_lines):
            for pattern in self._RAW_SQL_PATTERNS:
                if pattern.search(line):
                    violations.append(
                        SemanticViolation(
                            violation_type=ViolationType.RAW_SQL,
                            description=f"Raw SQL detected: {line.strip()}",
                            file_path=file_path,
                            line_number=i + 1,
                            severity="high",
                            suggestion="Use the project ORM instead of raw SQL queries.",
                        )
                    )
                    break
        return violations

    def _check_typescript_any(
        self, file_path: str, added_lines: list[str]
    ) -> list[SemanticViolation]:
        """Detect TypeScript ``any`` usage in added lines."""
        if not file_path.endswith((".ts", ".tsx")):
            return []

        violations = []
        for i, line in enumerate(added_lines):
            for pattern in self._TS_ANY_PATTERNS:
                if pattern.search(line):
                    violations.append(
                        SemanticViolation(
                            violation_type=ViolationType.TYPESCRIPT_ANY,
                            description=f"TypeScript 'any' usage: {line.strip()}",
                            file_path=file_path,
                            line_number=i + 1,
                            severity="medium",
                            suggestion="Use a specific type or 'unknown' instead of 'any'.",
                        )
                    )
                    break
        return violations

    def _check_security_sensitive(
        self, file_path: str, added_lines: list[str]
    ) -> list[SemanticViolation]:
        """Detect security-sensitive patterns in added lines."""
        violations = []
        for i, line in enumerate(added_lines):
            for pattern in self._SECURITY_PATTERNS:
                if pattern.search(line):
                    violations.append(
                        SemanticViolation(
                            violation_type=ViolationType.SECURITY_SENSITIVE,
                            description=f"Security-sensitive code: {line.strip()}",
                            file_path=file_path,
                            line_number=i + 1,
                            severity="critical",
                            suggestion="Review this code for security implications.",
                        )
                    )
                    break
        return violations

    def _check_dependency_changes(
        self,
        file_path: str,
        added_lines: list[str],
        removed_lines: list[str],
    ) -> list[SemanticViolation]:
        """Detect dependency changes in manifest files."""
        filename = file_path.rsplit("/", maxsplit=1)[-1] if "/" in file_path else file_path
        filename = filename.rsplit("\\", maxsplit=1)[-1] if "\\" in filename else filename

        if filename not in self._DEPENDENCY_FILES:
            return []

        violations = []
        added_deps = set()
        removed_deps = set()

        for line in added_lines:
            stripped = line.strip()
            if stripped and not stripped.startswith(("#", "//", "<!--")):
                added_deps.add(stripped)

        for line in removed_lines:
            stripped = line.strip()
            if stripped and not stripped.startswith(("#", "//", "<!--")):
                removed_deps.add(stripped)

        new_deps = added_deps - removed_deps
        if new_deps:
            violations.append(
                SemanticViolation(
                    violation_type=ViolationType.DEPENDENCY_CHANGE,
                    description=f"{len(new_deps)} new dependency(ies) added to {filename}",
                    file_path=file_path,
                    severity="medium",
                    suggestion="New dependencies should be reviewed by the tech lead.",
                )
            )

        return violations

    def _check_python_ast(
        self, file_path: str, content: str
    ) -> list[SemanticViolation]:
        """Use Python AST to detect deeper violations."""
        violations = []
        try:
            tree = ast.parse(content, filename=file_path)
        except SyntaxError:
            return violations

        for node in ast.walk(tree):
            # Detect eval() calls
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "eval":
                    violations.append(
                        SemanticViolation(
                            violation_type=ViolationType.SECURITY_SENSITIVE,
                            description="eval() call detected via AST analysis",
                            file_path=file_path,
                            line_number=node.lineno,
                            severity="critical",
                            suggestion="Avoid eval(). Use ast.literal_eval() or a safer alternative.",
                        )
                    )

        return violations
