"""
Git History Surgeon — Analyse and clean up Git history.

Detects large blobs, sensitive data leaks, messy commit messages,
and proposes cleanup plans (squash, BFG, filter-branch).
"""

from .history_analyzer import (
    HistoryAnalyzer,
    HistoryIssue,
    HistoryIssueType,
    SurgeryAction,
    SurgeryPlan,
)

__all__ = [
    "HistoryAnalyzer",
    "SurgeryPlan",
    "HistoryIssue",
    "HistoryIssueType",
    "SurgeryAction",
]
