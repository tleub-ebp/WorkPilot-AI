"""
i18n Agent — Internationalisation quality scanner.

Detects hardcoded strings, missing translation keys, locale file
mismatches, and pluralisation issues.
"""

from .i18n_scanner import (
    I18nIssue,
    I18nIssueType,
    I18nReport,
    I18nScanner,
    I18nSeverity,
)

__all__ = ["I18nScanner", "I18nReport", "I18nIssue", "I18nIssueType", "I18nSeverity"]
