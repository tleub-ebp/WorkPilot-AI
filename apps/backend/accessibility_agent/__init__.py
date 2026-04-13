"""
Accessibility Agent — WCAG 2.1 compliance scanner.

Scans HTML/JSX/TSX/Vue templates for WCAG A/AA/AAA violations
and generates fix suggestions with ARIA patterns.

Modules:
    - accessibility_scanner: rule-based WCAG violation detection
"""

from .accessibility_scanner import (
    A11yReport,
    A11ySeverity,
    A11yViolation,
    AccessibilityScanner,
    WcagLevel,
)

__all__ = [
    "AccessibilityScanner",
    "A11yReport",
    "A11yViolation",
    "A11ySeverity",
    "WcagLevel",
]
