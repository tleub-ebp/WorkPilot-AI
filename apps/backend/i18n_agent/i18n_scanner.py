"""
i18n Scanner — Detect internationalisation issues in codebases.

Finds hardcoded strings, missing translation keys, inconsistent
locale files, and format/pluralisation problems.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from agents.scanner_base import BaseScanner, BaseScanReport

logger = logging.getLogger(__name__)


class I18nIssueType(str, Enum):
    HARDCODED_STRING = "hardcoded_string"
    MISSING_KEY = "missing_key"
    UNUSED_KEY = "unused_key"
    INCONSISTENT_PARAMS = "inconsistent_params"
    MISSING_PLURAL = "missing_plural"
    LOCALE_FILE_MISMATCH = "locale_file_mismatch"


class I18nSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class I18nIssue:
    """A single internationalisation issue."""

    issue_type: I18nIssueType
    severity: I18nSeverity
    file: str
    line: int = 0
    message: str = ""
    key: str = ""
    locale: str = ""
    suggestion: str = ""


# In i18n, only ``error`` blocks (warnings are advisory, info is noise).
_I18N_BLOCKING = frozenset({I18nSeverity.ERROR.value})


@dataclass
class I18nReport(BaseScanReport[I18nIssue]):
    """Report of all i18n issues found.

    Backed by :class:`agents.scanner_base.BaseScanReport`. The historical
    ``issues`` attribute is kept as an alias for ``findings`` so existing
    callers (runners, tests, frontend views) stay compatible.

    The ``summary`` property is overridden to group by issue *type*
    (hardcoded_string, missing_key, …) rather than severity, because
    that's what the frontend report view has always rendered.
    """

    locales_found: list[str] = field(default_factory=list)
    total_keys: int = 0
    coverage: dict[str, float] = field(default_factory=dict)
    blocking_severities: frozenset[str] = field(default_factory=lambda: _I18N_BLOCKING)

    @property
    def issues(self) -> list[I18nIssue]:
        """Back-compat alias — same list object as ``findings``."""
        return self.findings

    @issues.setter
    def issues(self, value: list[I18nIssue]) -> None:
        self.findings = value

    @property
    def error_count(self) -> int:
        """Back-compat: i18n only considers ERROR findings blocking."""
        return self.blocking_count

    @property
    def summary(self) -> str:
        """Per-type summary (overrides the base's per-severity one)."""
        if not self.findings:
            return "No issues"
        by_type: dict[str, int] = {}
        for issue in self.findings:
            by_type[issue.issue_type.value] = by_type.get(issue.issue_type.value, 0) + 1
        # Stable ordering so test snapshots don't flap.
        ordered = sorted(by_type.items(), key=lambda kv: kv[0])
        return ", ".join(f"{count} {t}" for t, count in ordered)


# Patterns for detecting hardcoded user-facing strings
_HARDCODED_PATTERNS = [
    # JSX/TSX: <Tag>Hardcoded text</Tag>
    re.compile(r">\s*([A-Z][a-z][^<>{}\n]{3,50})\s*<", re.MULTILINE),
    # Python: displayed strings in common functions
    re.compile(
        r'(?:flash|message|title|label|placeholder|error)\s*[=(]\s*["\']([A-Z][^"\']{3,60})["\']'
    ),
]


class I18nScanner(BaseScanner[I18nIssue, I18nReport]):
    """Scan a codebase for internationalisation issues.

    Per-file detection (``scan_file`` / ``scan_file_for_hardcoded``) is
    powered by ``BaseScanner``, so ``scan_files({path: content})`` works
    out of the box and swallows per-file exceptions. Locale-file
    comparison (``compare_locale_files``) and coverage computation
    (``compute_coverage``) are orthogonal to the per-file pattern and
    stay as standalone methods.

    Usage::

        scanner = I18nScanner()
        report = scanner.scan_file("src/App.tsx", tsx_content)
    """

    report_cls = I18nReport

    def __init__(self, reference_locale: str = "en") -> None:
        self._reference_locale = reference_locale

    def scan_file(self, file_path: str, content: str) -> I18nReport:
        """Scan one file and return an :class:`I18nReport`.

        Thin adapter around :meth:`scan_file_for_hardcoded` so we stay
        compatible with the ``BaseScanner`` contract while keeping the
        original method name for existing callers.
        """
        report = I18nReport(files_scanned=1)
        report.findings.extend(self.scan_file_for_hardcoded(file_path, content))
        return report

    def scan_file_for_hardcoded(self, file_path: str, content: str) -> list[I18nIssue]:
        """Detect hardcoded user-facing strings in a source file."""
        issues: list[I18nIssue] = []
        lines = content.splitlines()

        for i, line in enumerate(lines, 1):
            for pattern in _HARDCODED_PATTERNS:
                for match in pattern.finditer(line):
                    text = match.group(1).strip()
                    if len(text) > 3 and not _is_likely_code(text):
                        issues.append(
                            I18nIssue(
                                issue_type=I18nIssueType.HARDCODED_STRING,
                                severity=I18nSeverity.WARNING,
                                file=file_path,
                                line=i,
                                message=f'Hardcoded string: "{text[:50]}"',
                                suggestion="Extract to translation key",
                            )
                        )
        return issues

    def compare_locale_files(
        self, reference: dict[str, Any], target: dict[str, Any], target_locale: str
    ) -> list[I18nIssue]:
        """Compare a target locale file against the reference."""
        issues: list[I18nIssue] = []
        ref_keys = _flatten_keys(reference)
        target_keys = _flatten_keys(target)

        for key in ref_keys:
            if key not in target_keys:
                issues.append(
                    I18nIssue(
                        issue_type=I18nIssueType.MISSING_KEY,
                        severity=I18nSeverity.ERROR,
                        file=f"locale/{target_locale}.json",
                        key=key,
                        locale=target_locale,
                        message=f"Key '{key}' missing in {target_locale}",
                        suggestion=f"Add translation for '{key}' in {target_locale}",
                    )
                )

        for key in target_keys:
            if key not in ref_keys:
                issues.append(
                    I18nIssue(
                        issue_type=I18nIssueType.UNUSED_KEY,
                        severity=I18nSeverity.INFO,
                        file=f"locale/{target_locale}.json",
                        key=key,
                        locale=target_locale,
                        message=f"Key '{key}' in {target_locale} not in reference locale",
                    )
                )

        return issues

    def compute_coverage(
        self, reference: dict[str, Any], locales: dict[str, dict[str, Any]]
    ) -> dict[str, float]:
        """Compute translation coverage per locale."""
        ref_keys = _flatten_keys(reference)
        if not ref_keys:
            return {}

        coverage: dict[str, float] = {}
        for locale_name, locale_data in locales.items():
            target_keys = _flatten_keys(locale_data)
            matched = sum(1 for k in ref_keys if k in target_keys)
            coverage[locale_name] = matched / len(ref_keys)
        return coverage


def _flatten_keys(data: dict[str, Any], prefix: str = "") -> set[str]:
    """Flatten a nested dict into dot-separated keys."""
    keys: set[str] = set()
    for k, v in data.items():
        full_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            keys.update(_flatten_keys(v, full_key))
        else:
            keys.add(full_key)
    return keys


def _is_likely_code(text: str) -> bool:
    """Heuristic: is this string likely code rather than user-facing text?"""
    code_indicators = [
        "()",
        "=>",
        "->",
        "==",
        "!=",
        "{}",
        "[]",
        "//",
        "/*",
        "import ",
        "from ",
    ]
    return any(ind in text for ind in code_indicators)
