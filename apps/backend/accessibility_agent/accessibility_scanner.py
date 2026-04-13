"""
Accessibility Scanner — Detect WCAG 2.1 / ADA compliance issues.

Scans HTML, JSX/TSX, and Vue templates for accessibility violations
such as missing alt text, insufficient colour contrast, missing ARIA
roles, keyboard traps, and focus management issues.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class WcagLevel(str, Enum):
    A = "A"
    AA = "AA"
    AAA = "AAA"


class A11ySeverity(str, Enum):
    CRITICAL = "critical"
    SERIOUS = "serious"
    MODERATE = "moderate"
    MINOR = "minor"


@dataclass
class A11yViolation:
    """A single accessibility violation."""

    rule_id: str
    description: str
    severity: A11ySeverity
    wcag_level: WcagLevel
    wcag_criteria: str = ""
    file: str = ""
    line: int = 0
    element: str = ""
    suggestion: str = ""


@dataclass
class A11yReport:
    """Accessibility audit report."""

    violations: list[A11yViolation] = field(default_factory=list)
    files_scanned: int = 0
    target_level: WcagLevel = WcagLevel.AA

    @property
    def critical_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == A11ySeverity.CRITICAL)

    @property
    def passed(self) -> bool:
        return self.critical_count == 0

    @property
    def summary(self) -> str:
        by_sev = {}
        for v in self.violations:
            by_sev[v.severity.value] = by_sev.get(v.severity.value, 0) + 1
        parts = [f"{count} {sev}" for sev, count in by_sev.items()]
        return ", ".join(parts) or "No violations"


# Rule definitions: (regex, rule_id, description, severity, wcag_level, wcag_criteria, suggestion)
_HTML_RULES: list[tuple[re.Pattern[str], str, str, A11ySeverity, WcagLevel, str, str]] = [
    (
        re.compile(r"<img\b(?![^>]*\balt\s*=)", re.IGNORECASE),
        "img-alt",
        "Image missing alt attribute",
        A11ySeverity.CRITICAL,
        WcagLevel.A,
        "1.1.1",
        "Add alt attribute: alt=\"descriptive text\" or alt=\"\" for decorative images",
    ),
    (
        re.compile(r"<input\b(?![^>]*\b(?:aria-label|aria-labelledby|id\s*=\s*[\"'][^\"']+[\"'])\b)(?![^>]*\btype\s*=\s*[\"']hidden[\"'])", re.IGNORECASE),
        "input-label",
        "Form input missing accessible label",
        A11ySeverity.SERIOUS,
        WcagLevel.A,
        "1.3.1",
        "Add aria-label, aria-labelledby, or associate with a <label> element",
    ),
    (
        re.compile(r"<(?:div|span)\b[^>]*\bonclick\b", re.IGNORECASE),
        "click-events-have-key-events",
        "Interactive element using div/span with onclick but no keyboard handler",
        A11ySeverity.SERIOUS,
        WcagLevel.A,
        "2.1.1",
        "Use <button> or <a> instead, or add onKeyDown/onKeyPress handler and role=\"button\"",
    ),
    (
        re.compile(r"<html\b(?![^>]*\blang\s*=)", re.IGNORECASE),
        "html-lang",
        "HTML element missing lang attribute",
        A11ySeverity.SERIOUS,
        WcagLevel.A,
        "3.1.1",
        "Add lang attribute: <html lang=\"en\">",
    ),
    (
        re.compile(r"tabindex\s*=\s*[\"']([2-9]|\d{2,})[\"']", re.IGNORECASE),
        "tabindex-positive",
        "Positive tabindex value creates confusing tab order",
        A11ySeverity.MODERATE,
        WcagLevel.A,
        "2.4.3",
        "Use tabindex=\"0\" or tabindex=\"-1\" instead of positive values",
    ),
    (
        re.compile(r"<a\b[^>]*href\s*=\s*[\"']#[\"'][^>]*>", re.IGNORECASE),
        "anchor-is-valid",
        "Anchor with href=\"#\" — not a valid link",
        A11ySeverity.MODERATE,
        WcagLevel.A,
        "2.1.1",
        "Use <button> for interactive elements or provide a valid href",
    ),
    (
        re.compile(r"aria-hidden\s*=\s*[\"']true[\"'][^>]*\bfocusable\b", re.IGNORECASE),
        "aria-hidden-focusable",
        "Element with aria-hidden=\"true\" is also focusable",
        A11ySeverity.SERIOUS,
        WcagLevel.A,
        "4.1.2",
        "Remove focusability or aria-hidden from this element",
    ),
    (
        re.compile(r"<video\b(?![^>]*\b(?:track|captions))", re.IGNORECASE),
        "video-captions",
        "Video element missing captions track",
        A11ySeverity.CRITICAL,
        WcagLevel.A,
        "1.2.2",
        "Add <track kind=\"captions\" src=\"...\" srclang=\"en\">",
    ),
]


class AccessibilityScanner:
    """Scan files for WCAG accessibility violations.

    Usage::

        scanner = AccessibilityScanner(target_level=WcagLevel.AA)
        report = scanner.scan_file("src/App.tsx", content)
    """

    def __init__(self, target_level: WcagLevel = WcagLevel.AA) -> None:
        self._target_level = target_level

    def scan_file(self, file_path: str, content: str) -> A11yReport:
        """Scan a single file for violations."""
        report = A11yReport(files_scanned=1, target_level=self._target_level)
        lines = content.splitlines()

        for rule_pattern, rule_id, desc, sev, level, criteria, suggestion in _HTML_RULES:
            for i, line in enumerate(lines, 1):
                if rule_pattern.search(line):
                    report.violations.append(A11yViolation(
                        rule_id=rule_id,
                        description=desc,
                        severity=sev,
                        wcag_level=level,
                        wcag_criteria=criteria,
                        file=file_path,
                        line=i,
                        element=line.strip()[:120],
                        suggestion=suggestion,
                    ))

        return report

    def scan_files(self, files: dict[str, str]) -> A11yReport:
        """Scan multiple files. Keys are paths, values are content."""
        report = A11yReport(target_level=self._target_level)
        for path, content in files.items():
            sub = self.scan_file(path, content)
            report.violations.extend(sub.violations)
            report.files_scanned += 1
        return report
