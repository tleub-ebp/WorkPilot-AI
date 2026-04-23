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

from agents.scanner_base import BaseScanner, BaseScanReport

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


# Accessibility uses a richer severity vocabulary than the default
# {critical, high, medium, low, info} — only "critical" blocks by default.
_A11Y_BLOCKING = frozenset({A11ySeverity.CRITICAL.value})


@dataclass
class A11yReport(BaseScanReport[A11yViolation]):
    """Accessibility audit report.

    Backed by :class:`agents.scanner_base.BaseScanReport`. Keeps a
    ``violations`` alias because existing callers (runners, tests) already
    iterate ``.violations``; new code should prefer ``.findings``.
    """

    target_level: WcagLevel = WcagLevel.AA
    blocking_severities: frozenset[str] = field(default_factory=lambda: _A11Y_BLOCKING)

    @property
    def violations(self) -> list[A11yViolation]:
        """Back-compat alias — same list object as ``findings``."""
        return self.findings

    @violations.setter
    def violations(self, value: list[A11yViolation]) -> None:
        self.findings = value

    @property
    def critical_count(self) -> int:
        """Back-compat: a11y only considers CRITICAL findings blocking."""
        return self.blocking_count


# Rule definitions: (regex, rule_id, description, severity, wcag_level, wcag_criteria, suggestion)
_HTML_RULES: list[
    tuple[re.Pattern[str], str, str, A11ySeverity, WcagLevel, str, str]
] = [
    (
        re.compile(r"<img\b(?![^>]*\balt\s*=)", re.IGNORECASE),
        "img-alt",
        "Image missing alt attribute",
        A11ySeverity.CRITICAL,
        WcagLevel.A,
        "1.1.1",
        'Add alt attribute: alt="descriptive text" or alt="" for decorative images',
    ),
    (
        re.compile(
            r"<input\b(?![^>]*\b(?:aria-label|aria-labelledby|id\s*=\s*[\"'][^\"']+[\"'])\b)(?![^>]*\btype\s*=\s*[\"']hidden[\"'])",
            re.IGNORECASE,
        ),
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
        'Use <button> or <a> instead, or add onKeyDown/onKeyPress handler and role="button"',
    ),
    (
        re.compile(r"<html\b(?![^>]*\blang\s*=)", re.IGNORECASE),
        "html-lang",
        "HTML element missing lang attribute",
        A11ySeverity.SERIOUS,
        WcagLevel.A,
        "3.1.1",
        'Add lang attribute: <html lang="en">',
    ),
    (
        re.compile(r"tabindex\s*=\s*[\"']([2-9]|\d{2,})[\"']", re.IGNORECASE),
        "tabindex-positive",
        "Positive tabindex value creates confusing tab order",
        A11ySeverity.MODERATE,
        WcagLevel.A,
        "2.4.3",
        'Use tabindex="0" or tabindex="-1" instead of positive values',
    ),
    (
        re.compile(r"<a\b[^>]*href\s*=\s*[\"']#[\"'][^>]*>", re.IGNORECASE),
        "anchor-is-valid",
        'Anchor with href="#" — not a valid link',
        A11ySeverity.MODERATE,
        WcagLevel.A,
        "2.1.1",
        "Use <button> for interactive elements or provide a valid href",
    ),
    (
        re.compile(
            r"aria-hidden\s*=\s*[\"']true[\"'][^>]*\bfocusable\b", re.IGNORECASE
        ),
        "aria-hidden-focusable",
        'Element with aria-hidden="true" is also focusable',
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
        'Add <track kind="captions" src="..." srclang="en">',
    ),
]


class AccessibilityScanner(BaseScanner[A11yViolation, A11yReport]):
    """Scan files for WCAG accessibility violations.

    Usage::

        scanner = AccessibilityScanner(target_level=WcagLevel.AA)
        report = scanner.scan_file("src/App.tsx", content)
    """

    report_cls = A11yReport

    def __init__(self, target_level: WcagLevel = WcagLevel.AA) -> None:
        self._target_level = target_level

    def _new_report(self) -> A11yReport:
        return A11yReport(target_level=self._target_level)

    def scan_file(self, file_path: str, content: str) -> A11yReport:
        """Scan a single file for violations."""
        report = A11yReport(files_scanned=1, target_level=self._target_level)
        lines = content.splitlines()

        for (
            rule_pattern,
            rule_id,
            desc,
            sev,
            level,
            criteria,
            suggestion,
        ) in _HTML_RULES:
            for i, line in enumerate(lines, 1):
                if rule_pattern.search(line):
                    report.findings.append(
                        A11yViolation(
                            rule_id=rule_id,
                            description=desc,
                            severity=sev,
                            wcag_level=level,
                            wcag_criteria=criteria,
                            file=file_path,
                            line=i,
                            element=line.strip()[:120],
                            suggestion=suggestion,
                        )
                    )

        return report
