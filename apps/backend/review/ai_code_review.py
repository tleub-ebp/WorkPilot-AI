"""AI-Assisted Code Review — Automated code review with scoring and suggestions.

Provides static + semantic analysis of code diffs, inline comments, quality
scoring, regression detection, and improvement suggestions with diff preview.
Extends the existing Quality Scorer with deeper review capabilities.

Feature 3.3 — Code review assisté par IA.

Example:
    >>> from apps.backend.review.ai_code_review import AICodeReviewer
    >>> reviewer = AICodeReviewer()
    >>> result = reviewer.review_diff(diff_text, language="python")
    >>> print(f"Score: {result.overall_score}/100")
    >>> for c in result.comments:
    ...     print(f"  L{c.line}: [{c.severity}] {c.message}")
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums and models
# ---------------------------------------------------------------------------


class ReviewSeverity(Enum):
    """Severity levels for review comments."""

    INFO = "info"
    SUGGESTION = "suggestion"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ReviewCategory(Enum):
    """Categories for review findings."""

    STYLE = "style"
    BUG_RISK = "bug_risk"
    PERFORMANCE = "performance"
    SECURITY = "security"
    COMPLEXITY = "complexity"
    NAMING = "naming"
    DOCUMENTATION = "documentation"
    ERROR_HANDLING = "error_handling"
    TESTING = "testing"
    DESIGN = "design"
    REGRESSION = "regression"
    BEST_PRACTICE = "best_practice"


@dataclass
class ReviewComment:
    """A single review comment on a code diff.

    Attributes:
        file_path: The file this comment applies to.
        line: The line number (in the new file), or 0 for file-level.
        severity: The severity of the finding.
        category: The category of the finding.
        message: The review comment text.
        suggestion: Optional code suggestion/fix.
        rule_id: Identifier of the rule that triggered this finding.
    """

    file_path: str
    line: int
    severity: ReviewSeverity
    category: ReviewCategory
    message: str
    suggestion: str = ""
    rule_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary."""
        return {
            "file_path": self.file_path,
            "line": self.line,
            "severity": self.severity.value,
            "category": self.category.value,
            "message": self.message,
            "suggestion": self.suggestion,
            "rule_id": self.rule_id,
        }


@dataclass
class DiffFile:
    """Parsed diff for a single file.

    Attributes:
        file_path: The file path.
        added_lines: Dict mapping line number → content for added lines.
        removed_lines: Dict mapping line number → content for removed lines.
        hunks: List of (start_line, end_line) tuples for changed regions.
        language: The detected programming language.
        is_new_file: Whether this file is newly created.
        is_deleted: Whether this file was deleted.
    """

    file_path: str
    added_lines: dict[int, str] = field(default_factory=dict)
    removed_lines: dict[int, str] = field(default_factory=dict)
    hunks: list[tuple[int, int]] = field(default_factory=list)
    language: str = ""
    is_new_file: bool = False
    is_deleted: bool = False

    @property
    def total_additions(self) -> int:
        """Number of added lines."""
        return len(self.added_lines)

    @property
    def total_deletions(self) -> int:
        """Number of removed lines."""
        return len(self.removed_lines)

    @property
    def total_changes(self) -> int:
        """Total changed lines."""
        return self.total_additions + self.total_deletions


@dataclass
class ReviewResult:
    """Complete result of an AI code review.

    Attributes:
        comments: List of review comments.
        overall_score: Quality score (0-100).
        category_scores: Scores per review category.
        files_reviewed: Number of files reviewed.
        total_additions: Total lines added.
        total_deletions: Total lines removed.
        summary: Human-readable summary of the review.
        potential_regressions: List of potential regression descriptions.
        timestamp: When the review was performed.
    """

    comments: list[ReviewComment] = field(default_factory=list)
    overall_score: int = 100
    category_scores: dict[str, int] = field(default_factory=dict)
    files_reviewed: int = 0
    total_additions: int = 0
    total_deletions: int = 0
    summary: str = ""
    potential_regressions: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def has_critical_issues(self) -> bool:
        """Check if there are critical issues that should block merge."""
        return any(
            c.severity in (ReviewSeverity.ERROR, ReviewSeverity.CRITICAL)
            for c in self.comments
        )

    @property
    def error_count(self) -> int:
        """Number of error-level or higher findings."""
        return sum(
            1
            for c in self.comments
            if c.severity in (ReviewSeverity.ERROR, ReviewSeverity.CRITICAL)
        )

    @property
    def warning_count(self) -> int:
        """Number of warning-level findings."""
        return sum(1 for c in self.comments if c.severity == ReviewSeverity.WARNING)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary."""
        return {
            "comments": [c.to_dict() for c in self.comments],
            "overall_score": self.overall_score,
            "category_scores": self.category_scores,
            "files_reviewed": self.files_reviewed,
            "total_additions": self.total_additions,
            "total_deletions": self.total_deletions,
            "summary": self.summary,
            "potential_regressions": self.potential_regressions,
            "has_critical_issues": self.has_critical_issues,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "timestamp": self.timestamp.isoformat(),
        }


# ---------------------------------------------------------------------------
# Static analysis rules
# ---------------------------------------------------------------------------


@dataclass
class ReviewRule:
    """A static analysis rule for code review.

    Attributes:
        rule_id: Unique rule identifier.
        pattern: Regex pattern to match in added lines.
        message: The message to display when the rule matches.
        severity: Severity of the finding.
        category: Category of the finding.
        suggestion: Optional fix suggestion.
        languages: Languages this rule applies to. Empty = all.
    """

    rule_id: str
    pattern: str
    message: str
    severity: ReviewSeverity
    category: ReviewCategory
    suggestion: str = ""
    languages: list[str] = field(default_factory=list)

    def applies_to(self, language: str) -> bool:
        """Check if this rule applies to the given language."""
        if not self.languages:
            return True
        return language.lower() in [lang.lower() for lang in self.languages]


# Built-in review rules (static pattern-based analysis)
BUILTIN_RULES: list[ReviewRule] = [
    # Security
    ReviewRule(
        rule_id="SEC001",
        pattern=r"eval\s*\(",
        message="Use of `eval()` detected — potential code injection risk.",
        severity=ReviewSeverity.CRITICAL,
        category=ReviewCategory.SECURITY,
        suggestion="Replace eval() with a safer alternative like ast.literal_eval() or a dedicated parser.",
        languages=["python", "javascript", "typescript"],
    ),
    ReviewRule(
        rule_id="SEC002",
        pattern=r"(password|secret|api_key|token)\s*=\s*['\"][^'\"]+['\"]",
        message="Hardcoded secret detected — use environment variables instead.",
        severity=ReviewSeverity.CRITICAL,
        category=ReviewCategory.SECURITY,
        suggestion="Move secrets to environment variables or a .env file.",
    ),
    ReviewRule(
        rule_id="SEC003",
        pattern=r"subprocess\.call\s*\(.*shell\s*=\s*True",
        message="Shell=True in subprocess — potential command injection.",
        severity=ReviewSeverity.ERROR,
        category=ReviewCategory.SECURITY,
        suggestion="Use subprocess.run() with shell=False and pass args as a list.",
        languages=["python"],
    ),
    ReviewRule(
        rule_id="SEC004",
        pattern=r"innerHTML\s*=",
        message="Direct innerHTML assignment — potential XSS vulnerability.",
        severity=ReviewSeverity.ERROR,
        category=ReviewCategory.SECURITY,
        suggestion="Use textContent or a sanitization library instead.",
        languages=["javascript", "typescript"],
    ),
    # Bug risk
    ReviewRule(
        rule_id="BUG001",
        pattern=r"except\s*:",
        message="Bare except clause — catches all exceptions including SystemExit.",
        severity=ReviewSeverity.WARNING,
        category=ReviewCategory.BUG_RISK,
        suggestion="Use `except Exception:` or catch a specific exception type.",
        languages=["python"],
    ),
    ReviewRule(
        rule_id="BUG002",
        pattern=r"==\s*None|None\s*==",
        message="Use `is None` instead of `== None` for None comparisons.",
        severity=ReviewSeverity.SUGGESTION,
        category=ReviewCategory.STYLE,
        suggestion="Replace `== None` with `is None`.",
        languages=["python"],
    ),
    ReviewRule(
        rule_id="BUG003",
        pattern=r"console\.log\(",
        message="console.log() found — remove debug logging before merge.",
        severity=ReviewSeverity.WARNING,
        category=ReviewCategory.BEST_PRACTICE,
        suggestion="Remove or replace with a proper logging framework.",
        languages=["javascript", "typescript"],
    ),
    ReviewRule(
        rule_id="BUG004",
        pattern=r"print\s*\(",
        message="print() found — consider using the logging module instead.",
        severity=ReviewSeverity.INFO,
        category=ReviewCategory.BEST_PRACTICE,
        suggestion="Replace with logger.info() or logger.debug().",
        languages=["python"],
    ),
    # Complexity
    ReviewRule(
        rule_id="CX001",
        pattern=r"if .+if .+if ",
        message="Deeply nested conditionals — consider simplifying.",
        severity=ReviewSeverity.WARNING,
        category=ReviewCategory.COMPLEXITY,
        suggestion="Use early returns, guard clauses, or extract helper functions.",
    ),
    # Error handling
    ReviewRule(
        rule_id="ERR001",
        pattern=r"except.*:\s*pass",
        message="Silent exception handler — errors will be silently ignored.",
        severity=ReviewSeverity.WARNING,
        category=ReviewCategory.ERROR_HANDLING,
        suggestion="Log the exception or handle it explicitly.",
        languages=["python"],
    ),
    ReviewRule(
        rule_id="ERR002",
        pattern=r"catch\s*\(\s*\w*\s*\)\s*\{\s*\}",
        message="Empty catch block — errors will be silently swallowed.",
        severity=ReviewSeverity.WARNING,
        category=ReviewCategory.ERROR_HANDLING,
        suggestion="Log the error or handle it explicitly.",
        languages=["javascript", "typescript"],
    ),
    # Performance
    ReviewRule(
        rule_id="PERF001",
        pattern=r"SELECT\s+\*\s+FROM",
        message="SELECT * query detected — specify explicit columns for better performance.",
        severity=ReviewSeverity.SUGGESTION,
        category=ReviewCategory.PERFORMANCE,
        suggestion="List only the columns you need.",
    ),
    ReviewRule(
        rule_id="PERF002",
        pattern=r"for\s+.+\s+in\s+range\(len\(",
        message="Use `enumerate()` instead of `range(len(...))` for Pythonic iteration.",
        severity=ReviewSeverity.SUGGESTION,
        category=ReviewCategory.STYLE,
        suggestion="Replace `for i in range(len(items)):` with `for i, item in enumerate(items):`.",
        languages=["python"],
    ),
    # Documentation
    ReviewRule(
        rule_id="DOC001",
        pattern=r"def\s+\w+\s*\([^)]*\)\s*(->\s*\w+)?\s*:\s*$",
        message="Function definition without docstring on next line.",
        severity=ReviewSeverity.INFO,
        category=ReviewCategory.DOCUMENTATION,
        suggestion="Add a docstring describing the function purpose, args, and return value.",
        languages=["python"],
    ),
    # Naming
    ReviewRule(
        rule_id="NAM001",
        pattern=r"def\s+[A-Z]\w*\s*\(",
        message="Function name starts with uppercase — Python convention is snake_case.",
        severity=ReviewSeverity.SUGGESTION,
        category=ReviewCategory.NAMING,
        suggestion="Rename to snake_case (e.g., `my_function` instead of `MyFunction`).",
        languages=["python"],
    ),
    # TODO/FIXME detection
    ReviewRule(
        rule_id="TODO001",
        pattern=r"(TODO|FIXME|HACK|XXX)\s*:",
        message="TODO/FIXME comment found — track as a separate task.",
        severity=ReviewSeverity.INFO,
        category=ReviewCategory.BEST_PRACTICE,
    ),
]


# ---------------------------------------------------------------------------
# Diff parser
# ---------------------------------------------------------------------------


def parse_unified_diff(diff_text: str) -> list[DiffFile]:
    """Parse a unified diff into structured DiffFile objects.

    Args:
        diff_text: The raw unified diff text.

    Returns:
        A list of DiffFile objects, one per file.
    """
    files: list[DiffFile] = []
    current_file: DiffFile | None = None
    current_new_line = 0

    for line in diff_text.splitlines():
        # New file header
        if line.startswith("diff --git"):
            if current_file:
                files.append(current_file)
            # Extract file path from "diff --git a/path b/path"
            parts = line.split()
            file_path = parts[-1].lstrip("b/") if len(parts) >= 4 else ""
            current_file = DiffFile(file_path=file_path)
            current_new_line = 0
            continue

        if current_file is None:
            continue

        # Detect new/deleted files
        if line.startswith("new file"):
            current_file.is_new_file = True
        elif line.startswith("deleted file"):
            current_file.is_deleted = True
        elif line.startswith("--- "):
            pass  # old file header
        elif line.startswith("+++ "):
            # Detect language from extension
            path = line[4:].strip().lstrip("b/")
            current_file.language = _detect_language(path)
        elif line.startswith("@@"):
            # Hunk header: @@ -old_start,old_count +new_start,new_count @@
            match = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", line)
            if match:
                start = int(match.group(1))
                count = int(match.group(2) or "1")
                current_new_line = start
                current_file.hunks.append((start, start + count - 1))
            else:
                current_new_line = 1
        elif line.startswith("+") and not line.startswith("+++"):
            current_file.added_lines[current_new_line] = line[1:]
            current_new_line += 1
        elif line.startswith("-") and not line.startswith("---"):
            current_file.removed_lines[current_new_line] = line[1:]
            # Don't increment new line for removed lines
        else:
            # Context line
            current_new_line += 1

    if current_file:
        files.append(current_file)

    return files


def _detect_language(file_path: str) -> str:
    """Detect programming language from file extension."""
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".jsx": "javascript",
        ".java": "java",
        ".rb": "ruby",
        ".go": "go",
        ".rs": "rust",
        ".cpp": "cpp",
        ".c": "c",
        ".cs": "csharp",
        ".php": "php",
        ".swift": "swift",
        ".kt": "kotlin",
        ".scala": "scala",
        ".sh": "shell",
        ".sql": "sql",
        ".html": "html",
        ".css": "css",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".json": "json",
        ".md": "markdown",
    }
    for ext, lang in ext_map.items():
        if file_path.endswith(ext):
            return lang
    return ""


# ---------------------------------------------------------------------------
# Main reviewer class
# ---------------------------------------------------------------------------


class AICodeReviewer:
    """AI-assisted code reviewer with static analysis and scoring.

    Performs rule-based static analysis on diffs, computes quality scores,
    detects potential regressions, and generates inline review comments.

    Optionally integrates with an LLM provider for deeper semantic analysis.

    Attributes:
        _rules: List of active review rules.
        _custom_rules: Custom rules added by the user.
        _review_history: History of past reviews.
        _llm_provider: Optional LLM provider for semantic analysis.
    """

    def __init__(self, llm_provider: Any = None) -> None:
        """Initialize the code reviewer.

        Args:
            llm_provider: Optional LLM provider instance for AI-powered analysis.
                Must have a ``generate(prompt: str) -> str`` method.
        """
        self._rules: list[ReviewRule] = list(BUILTIN_RULES)
        self._custom_rules: list[ReviewRule] = []
        self._review_history: list[ReviewResult] = []
        self._llm_provider = llm_provider

    # ------------------------------------------------------------------
    # Rule management
    # ------------------------------------------------------------------

    def add_rule(self, rule: ReviewRule) -> None:
        """Add a custom review rule.

        Args:
            rule: The review rule to add.
        """
        self._custom_rules.append(rule)
        self._rules.append(rule)

    def get_rules(self, language: str = "") -> list[ReviewRule]:
        """Get all active rules, optionally filtered by language.

        Args:
            language: Filter by language. Empty = return all.

        Returns:
            List of applicable ReviewRule objects.
        """
        if not language:
            return list(self._rules)
        return [r for r in self._rules if r.applies_to(language)]

    # ------------------------------------------------------------------
    # Core review
    # ------------------------------------------------------------------

    def review_diff(
        self,
        diff_text: str,
        language: str = "",
        file_path: str = "",
    ) -> ReviewResult:
        """Review a unified diff and return findings.

        Args:
            diff_text: The raw unified diff text.
            language: Override language detection.
            file_path: Override file path (for single-file diffs).

        Returns:
            A ReviewResult with comments, scores, and summary.
        """
        files = parse_unified_diff(diff_text)

        # If no valid diff structure, treat as raw code changes
        if not files and diff_text.strip():
            files = [
                DiffFile(
                    file_path=file_path or "unknown",
                    added_lines={
                        i + 1: line for i, line in enumerate(diff_text.splitlines())
                    },
                    language=language,
                )
            ]

        all_comments: list[ReviewComment] = []
        total_additions = 0
        total_deletions = 0

        for diff_file in files:
            file_lang = language or diff_file.language
            total_additions += diff_file.total_additions
            total_deletions += diff_file.total_deletions

            # Run static analysis rules on added lines
            comments = self._run_rules(diff_file, file_lang)
            all_comments.extend(comments)

            # Check for large file changes
            if diff_file.total_changes > 300:
                all_comments.append(
                    ReviewComment(
                        file_path=diff_file.file_path,
                        line=0,
                        severity=ReviewSeverity.WARNING,
                        category=ReviewCategory.COMPLEXITY,
                        message=f"Large change ({diff_file.total_changes} lines) — consider splitting into smaller commits.",
                        rule_id="META001",
                    )
                )

            # Check for potential regressions
            regression_comments = self._detect_regressions(diff_file)
            all_comments.extend(regression_comments)

        # Compute scores
        overall_score, category_scores = self._compute_scores(all_comments)

        # Generate summary
        summary = self._generate_summary(
            all_comments, len(files), total_additions, total_deletions, overall_score
        )

        # Extract potential regressions
        regressions = [
            c.message for c in all_comments if c.category == ReviewCategory.REGRESSION
        ]

        result = ReviewResult(
            comments=all_comments,
            overall_score=overall_score,
            category_scores=category_scores,
            files_reviewed=len(files),
            total_additions=total_additions,
            total_deletions=total_deletions,
            summary=summary,
            potential_regressions=regressions,
        )

        self._review_history.append(result)
        return result

    def review_file_content(
        self,
        content: str,
        file_path: str = "",
        language: str = "",
    ) -> ReviewResult:
        """Review a complete file content (not a diff).

        Args:
            content: The file content to review.
            file_path: The file path.
            language: The programming language.

        Returns:
            A ReviewResult.
        """
        lang = language or _detect_language(file_path)
        diff_file = DiffFile(
            file_path=file_path,
            added_lines={i + 1: line for i, line in enumerate(content.splitlines())},
            language=lang,
        )

        comments = self._run_rules(diff_file, lang)
        overall_score, category_scores = self._compute_scores(comments)
        summary = self._generate_summary(
            comments, 1, len(content.splitlines()), 0, overall_score
        )

        result = ReviewResult(
            comments=comments,
            overall_score=overall_score,
            category_scores=category_scores,
            files_reviewed=1,
            total_additions=len(content.splitlines()),
            summary=summary,
        )

        self._review_history.append(result)
        return result

    # ------------------------------------------------------------------
    # Internal analysis methods
    # ------------------------------------------------------------------

    def _run_rules(self, diff_file: DiffFile, language: str) -> list[ReviewComment]:
        """Run all applicable rules against a file's added lines.

        Args:
            diff_file: The parsed diff file.
            language: The detected language.

        Returns:
            A list of ReviewComment findings.
        """
        comments: list[ReviewComment] = []
        applicable_rules = [r for r in self._rules if r.applies_to(language)]

        for line_num, line_content in diff_file.added_lines.items():
            for rule in applicable_rules:
                try:
                    if re.search(rule.pattern, line_content):
                        comments.append(
                            ReviewComment(
                                file_path=diff_file.file_path,
                                line=line_num,
                                severity=rule.severity,
                                category=rule.category,
                                message=rule.message,
                                suggestion=rule.suggestion,
                                rule_id=rule.rule_id,
                            )
                        )
                except re.error:
                    pass  # Skip invalid regex patterns

        return comments

    def _detect_regressions(self, diff_file: DiffFile) -> list[ReviewComment]:
        """Detect potential regressions from removed code.

        Args:
            diff_file: The parsed diff file.

        Returns:
            A list of regression-related ReviewComment objects.
        """
        comments: list[ReviewComment] = []

        # Check if test files are being modified with deletions
        if "test" in diff_file.file_path.lower() and diff_file.total_deletions > 0:
            if diff_file.total_deletions > diff_file.total_additions:
                comments.append(
                    ReviewComment(
                        file_path=diff_file.file_path,
                        line=0,
                        severity=ReviewSeverity.WARNING,
                        category=ReviewCategory.REGRESSION,
                        message="Test file has net deletions — test coverage may decrease.",
                        rule_id="REG001",
                    )
                )

        # Check for removal of error handling patterns
        for line_num, content in diff_file.removed_lines.items():
            if any(kw in content for kw in ["try:", "except", "catch", "finally"]):
                comments.append(
                    ReviewComment(
                        file_path=diff_file.file_path,
                        line=line_num,
                        severity=ReviewSeverity.WARNING,
                        category=ReviewCategory.REGRESSION,
                        message="Error handling code was removed — verify this is intentional.",
                        rule_id="REG002",
                    )
                )
                break  # One regression warning per pattern type

        # Check for removal of validation patterns
        for line_num, content in diff_file.removed_lines.items():
            if any(kw in content for kw in ["validate", "assert", "check", "verify"]):
                comments.append(
                    ReviewComment(
                        file_path=diff_file.file_path,
                        line=line_num,
                        severity=ReviewSeverity.WARNING,
                        category=ReviewCategory.REGRESSION,
                        message="Validation code was removed — verify this is intentional.",
                        rule_id="REG003",
                    )
                )
                break

        return comments

    def _compute_scores(
        self, comments: list[ReviewComment]
    ) -> tuple[int, dict[str, int]]:
        """Compute quality scores from review comments.

        Args:
            comments: The list of review comments.

        Returns:
            A tuple of (overall_score, category_scores).
        """
        # Severity penalties
        penalties = {
            ReviewSeverity.CRITICAL: 20,
            ReviewSeverity.ERROR: 10,
            ReviewSeverity.WARNING: 3,
            ReviewSeverity.SUGGESTION: 1,
            ReviewSeverity.INFO: 0,
        }

        total_penalty = 0
        category_penalties: dict[str, int] = {}

        for comment in comments:
            penalty = penalties.get(comment.severity, 0)
            total_penalty += penalty
            cat = comment.category.value
            category_penalties[cat] = category_penalties.get(cat, 0) + penalty

        overall_score = max(0, 100 - total_penalty)

        # Category scores (100 - penalty per category, capped at 0)
        category_scores = {}
        for cat in ReviewCategory:
            cat_penalty = category_penalties.get(cat.value, 0)
            category_scores[cat.value] = max(0, 100 - cat_penalty * 5)

        return overall_score, category_scores

    def _generate_summary(
        self,
        comments: list[ReviewComment],
        files_count: int,
        additions: int,
        deletions: int,
        score: int,
    ) -> str:
        """Generate a human-readable review summary.

        Args:
            comments: The review comments.
            files_count: Number of files reviewed.
            additions: Total added lines.
            deletions: Total removed lines.
            score: The overall score.

        Returns:
            A Markdown-formatted summary string.
        """
        critical_count = sum(
            1 for c in comments if c.severity == ReviewSeverity.CRITICAL
        )
        error_count = sum(1 for c in comments if c.severity == ReviewSeverity.ERROR)
        warning_count = sum(1 for c in comments if c.severity == ReviewSeverity.WARNING)
        suggestion_count = sum(
            1 for c in comments if c.severity == ReviewSeverity.SUGGESTION
        )
        info_count = sum(1 for c in comments if c.severity == ReviewSeverity.INFO)

        if score >= 90:
            verdict = "Excellent"
        elif score >= 75:
            verdict = "Good"
        elif score >= 50:
            verdict = "Needs Improvement"
        else:
            verdict = "Significant Issues"

        lines = [
            f"**Code Review — {verdict}** (Score: {score}/100)",
            "",
            f"Reviewed {files_count} file(s): +{additions} / -{deletions} lines",
            "",
            "**Findings:**",
        ]

        if critical_count:
            lines.append(f"- Critical: {critical_count}")
        if error_count:
            lines.append(f"- Errors: {error_count}")
        if warning_count:
            lines.append(f"- Warnings: {warning_count}")
        if suggestion_count:
            lines.append(f"- Suggestions: {suggestion_count}")
        if info_count:
            lines.append(f"- Info: {info_count}")
        if not comments:
            lines.append("- No issues found!")

        if critical_count or error_count:
            lines.append("")
            lines.append(
                "**Action required:** Please address critical/error findings before merge."
            )

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # LLM-powered semantic review (optional)
    # ------------------------------------------------------------------

    def review_with_llm(
        self,
        diff_text: str,
        context: str = "",
        language: str = "",
    ) -> ReviewResult:
        """Perform a combined static + LLM-powered semantic review.

        First runs the static analysis rules, then sends the diff to the
        LLM for deeper semantic analysis if a provider is configured.

        Args:
            diff_text: The raw diff text.
            context: Optional context about the change (PR description, etc.).
            language: Override language detection.

        Returns:
            A ReviewResult combining static and LLM findings.
        """
        # Start with static analysis
        result = self.review_diff(diff_text, language=language)

        if not self._llm_provider:
            return result

        # Generate LLM prompt
        prompt = self._build_llm_review_prompt(diff_text, context, language)

        try:
            llm_response = self._llm_provider.generate(prompt)
            llm_comments = self._parse_llm_response(llm_response)
            result.comments.extend(llm_comments)

            # Recalculate scores with LLM findings
            result.overall_score, result.category_scores = self._compute_scores(
                result.comments
            )
            result.summary = self._generate_summary(
                result.comments,
                result.files_reviewed,
                result.total_additions,
                result.total_deletions,
                result.overall_score,
            )
        except Exception as exc:
            logger.warning(f"LLM review failed: {exc}")

        return result

    def _build_llm_review_prompt(
        self, diff_text: str, context: str, language: str
    ) -> str:
        """Build the prompt for LLM code review."""
        return (
            "You are an expert code reviewer. Analyze the following diff and provide "
            "a code review with specific, actionable comments.\n\n"
            f"Language: {language or 'auto-detect'}\n"
            f"Context: {context or 'None provided'}\n\n"
            f"```diff\n{diff_text[:8000]}\n```\n\n"
            "For each finding, provide:\n"
            "- LINE: <line number>\n"
            "- SEVERITY: info|suggestion|warning|error|critical\n"
            "- CATEGORY: bug_risk|security|performance|style|complexity|error_handling|design\n"
            "- MESSAGE: <description>\n"
            "- SUGGESTION: <fix>\n\n"
            "Focus on bugs, security issues, and design problems. "
            "Be specific and constructive."
        )

    def _parse_llm_response(self, response: str) -> list[ReviewComment]:
        """Parse LLM response into ReviewComment objects."""
        comments: list[ReviewComment] = []

        # Simple pattern matching on structured LLM output
        current: dict[str, str] = {}
        for line in response.splitlines():
            line = line.strip()
            if line.startswith("- LINE:"):
                if current:
                    comments.append(self._build_comment_from_dict(current))
                current = {"line": line.split(":", 1)[1].strip()}
            elif line.startswith("- SEVERITY:"):
                current["severity"] = line.split(":", 1)[1].strip().lower()
            elif line.startswith("- CATEGORY:"):
                current["category"] = line.split(":", 1)[1].strip().lower()
            elif line.startswith("- MESSAGE:"):
                current["message"] = line.split(":", 1)[1].strip()
            elif line.startswith("- SUGGESTION:"):
                current["suggestion"] = line.split(":", 1)[1].strip()

        if current and "message" in current:
            comments.append(self._build_comment_from_dict(current))

        return comments

    def _build_comment_from_dict(self, data: dict[str, str]) -> ReviewComment:
        """Build a ReviewComment from a parsed dict."""
        try:
            severity = ReviewSeverity(data.get("severity", "info"))
        except ValueError:
            severity = ReviewSeverity.INFO

        try:
            category = ReviewCategory(data.get("category", "best_practice"))
        except ValueError:
            category = ReviewCategory.BEST_PRACTICE

        try:
            line = int(data.get("line", "0"))
        except ValueError:
            line = 0

        return ReviewComment(
            file_path="",
            line=line,
            severity=severity,
            category=category,
            message=data.get("message", ""),
            suggestion=data.get("suggestion", ""),
            rule_id="LLM",
        )

    # ------------------------------------------------------------------
    # History and stats
    # ------------------------------------------------------------------

    def get_review_history(self) -> list[ReviewResult]:
        """Get the history of all reviews performed."""
        return list(self._review_history)

    def get_stats(self) -> dict[str, Any]:
        """Get reviewer statistics.

        Returns:
            Dict with ``'total_reviews'``, ``'avg_score'``,
            ``'total_rules'``, ``'custom_rules'``, ``'total_findings'``.
        """
        total_findings = sum(len(r.comments) for r in self._review_history)
        avg_score = (
            sum(r.overall_score for r in self._review_history)
            / len(self._review_history)
            if self._review_history
            else 0
        )
        return {
            "total_reviews": len(self._review_history),
            "avg_score": round(avg_score, 1),
            "total_rules": len(self._rules),
            "custom_rules": len(self._custom_rules),
            "total_findings": total_findings,
        }
