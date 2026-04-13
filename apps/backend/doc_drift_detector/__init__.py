"""
Documentation Drift Detector — Find stale docs that diverge from code.

Detects references to renamed/deleted functions, missing files,
outdated examples, and configuration mismatches.
"""

from .drift_scanner import (
    DriftIssue,
    DriftReport,
    DriftScanner,
    DriftSeverity,
    DriftType,
)

__all__ = ["DriftScanner", "DriftReport", "DriftIssue", "DriftType", "DriftSeverity"]
