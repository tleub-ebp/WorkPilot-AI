"""
Git History Surgeon — Analyse and clean up Git history.

Detects large blobs, sensitive data in history, messy commit messages,
and proposes interactive rebase plans, BFG operations, and squash
strategies.
"""

from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class HistoryIssueType(str, Enum):
    LARGE_BLOB = "large_blob"
    SENSITIVE_DATA = "sensitive_data"
    MESSY_COMMITS = "messy_commits"
    FORCE_PUSH_RISK = "force_push_risk"
    DUPLICATE_COMMITS = "duplicate_commits"


class SurgeryAction(str, Enum):
    SQUASH = "squash"
    REWORD = "reword"
    DROP = "drop"
    BFG_REMOVE = "bfg_remove"
    FILTER_BRANCH = "filter_branch"


@dataclass
class HistoryIssue:
    """A detected issue in Git history."""

    issue_type: HistoryIssueType
    severity: str = "medium"
    description: str = ""
    commit_sha: str = ""
    file_path: str = ""
    size_bytes: int = 0
    suggested_action: SurgeryAction = SurgeryAction.SQUASH


@dataclass
class SurgeryPlan:
    """A proposed plan to clean up Git history."""

    issues: list[HistoryIssue] = field(default_factory=list)
    actions: list[tuple[SurgeryAction, str]] = field(default_factory=list)
    estimated_size_savings_mb: float = 0.0
    requires_force_push: bool = False

    @property
    def summary(self) -> str:
        by_type = {}
        for issue in self.issues:
            by_type[issue.issue_type.value] = by_type.get(issue.issue_type.value, 0) + 1
        parts = [f"{count} {t}" for t, count in by_type.items()]
        return ", ".join(parts) or "Clean history"


_SENSITIVE_PATTERNS = [
    re.compile(r"(?i)(password|secret|api_key|apikey|token)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
    re.compile(r"(?i)AKIA[0-9A-Z]{16}"),  # AWS access key
    re.compile(r"ghp_[a-zA-Z0-9]{36}"),  # GitHub PAT
    re.compile(r"sk-[a-zA-Z0-9]{32,}"),  # OpenAI key pattern
]


class HistoryAnalyzer:
    """Analyse Git history for issues and propose cleanup plans.

    Usage::

        analyzer = HistoryAnalyzer(repo_root=Path("/my/repo"))
        plan = analyzer.analyze()
    """

    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root

    def analyze(self, max_commits: int = 500) -> SurgeryPlan:
        """Analyse recent history and produce a surgery plan."""
        plan = SurgeryPlan()

        plan.issues.extend(self._find_large_blobs())
        plan.issues.extend(self._find_sensitive_data(max_commits))
        plan.issues.extend(self._find_messy_commits(max_commits))

        # Generate actions
        for issue in plan.issues:
            plan.actions.append((issue.suggested_action, issue.description))

        plan.estimated_size_savings_mb = sum(
            i.size_bytes for i in plan.issues if i.issue_type == HistoryIssueType.LARGE_BLOB
        ) / (1024 * 1024)

        plan.requires_force_push = any(
            i.suggested_action in (SurgeryAction.BFG_REMOVE, SurgeryAction.FILTER_BRANCH)
            for i in plan.issues
        )

        return plan

    def _find_large_blobs(self, threshold_mb: float = 10.0) -> list[HistoryIssue]:
        """Find files larger than threshold in history."""
        issues: list[HistoryIssue] = []
        try:
            result = subprocess.run(
                ["git", "rev-list", "--objects", "--all"],
                cwd=str(self._repo_root),
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode != 0:
                return issues

            # Get sizes via git cat-file
            objects = result.stdout.strip().split("\n")[:1000]
            for line in objects:
                parts = line.split(None, 1)
                if len(parts) < 2:
                    continue
                sha, path = parts[0], parts[1]
                try:
                    size_result = subprocess.run(
                        ["git", "cat-file", "-s", sha],
                        cwd=str(self._repo_root),
                        capture_output=True, text=True, timeout=5,
                    )
                    size = int(size_result.stdout.strip()) if size_result.returncode == 0 else 0
                except (ValueError, subprocess.SubprocessError):
                    size = 0

                if size > threshold_mb * 1024 * 1024:
                    issues.append(HistoryIssue(
                        issue_type=HistoryIssueType.LARGE_BLOB,
                        severity="high",
                        description=f"Large file: {path} ({size / 1024 / 1024:.1f} MB)",
                        commit_sha=sha,
                        file_path=path,
                        size_bytes=size,
                        suggested_action=SurgeryAction.BFG_REMOVE,
                    ))
        except (subprocess.SubprocessError, OSError):
            pass
        return issues

    def _find_sensitive_data(self, max_commits: int) -> list[HistoryIssue]:
        """Scan commit diffs for sensitive data patterns."""
        issues: list[HistoryIssue] = []
        try:
            result = subprocess.run(
                ["git", "log", f"-{max_commits}", "--pretty=format:%H", "--diff-filter=A", "-p"],
                cwd=str(self._repo_root),
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                return issues

            current_sha = ""
            for line in result.stdout.splitlines():
                if re.match(r"^[0-9a-f]{40}$", line):
                    current_sha = line
                    continue
                for pattern in _SENSITIVE_PATTERNS:
                    if pattern.search(line):
                        issues.append(HistoryIssue(
                            issue_type=HistoryIssueType.SENSITIVE_DATA,
                            severity="critical",
                            description=f"Potential secret in commit {current_sha[:8]}",
                            commit_sha=current_sha,
                            suggested_action=SurgeryAction.BFG_REMOVE,
                        ))
                        break
        except (subprocess.SubprocessError, OSError):
            pass
        return issues

    def _find_messy_commits(self, max_commits: int) -> list[HistoryIssue]:
        """Find commits with poor messages (WIP, fixup, etc.)."""
        issues: list[HistoryIssue] = []
        messy_patterns = re.compile(r"^(wip|fixup|tmp|test|asdf|xxx|todo|hack)", re.IGNORECASE)

        try:
            result = subprocess.run(
                ["git", "log", f"-{max_commits}", "--pretty=format:%H %s"],
                cwd=str(self._repo_root),
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                return issues

            for line in result.stdout.splitlines():
                parts = line.split(None, 1)
                if len(parts) < 2:
                    continue
                sha, message = parts
                if messy_patterns.match(message):
                    issues.append(HistoryIssue(
                        issue_type=HistoryIssueType.MESSY_COMMITS,
                        severity="low",
                        description=f"Messy commit message: '{message[:60]}'",
                        commit_sha=sha,
                        suggested_action=SurgeryAction.SQUASH,
                    ))
        except (subprocess.SubprocessError, OSError):
            pass
        return issues
