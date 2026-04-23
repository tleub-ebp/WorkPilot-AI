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

from agents.scanner_base import BaseScanReport

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
    """A detected issue in Git history.

    Implements the :class:`agents.scanner_base.HasSeverity` duck-typed
    contract (``severity`` + ``file``) so :class:`SurgeryPlan` can ride
    on :class:`BaseScanReport`. ``file`` is a read-only alias of
    ``file_path`` — we don't rename the field because the frontend view
    and the runner serializer read ``file_path``.
    """

    issue_type: HistoryIssueType
    severity: str = "medium"
    description: str = ""
    commit_sha: str = ""
    file_path: str = ""
    size_bytes: int = 0
    suggested_action: SurgeryAction = SurgeryAction.SQUASH

    @property
    def file(self) -> str:
        """Alias required by :class:`HasSeverity`; exposes ``file_path``."""
        return self.file_path


@dataclass
class SurgeryPlan(BaseScanReport[HistoryIssue]):
    """A proposed plan to clean up Git history.

    Backed by :class:`BaseScanReport[HistoryIssue]` for the per-severity
    counters and ``passed`` / ``blocking_count`` semantics. The
    historical ``issues`` attribute is kept as an alias for ``findings``
    so the runner (which reads ``plan.issues``) and frontend view stay
    compatible.

    ``summary`` is overridden to group by ``issue_type`` (large_blob /
    sensitive_data / messy_commits / …) because that's what the UI
    renders — not the severity bucket.
    """

    actions: list[tuple[SurgeryAction, str]] = field(default_factory=list)
    estimated_size_savings_mb: float = 0.0
    requires_force_push: bool = False

    @property
    def issues(self) -> list[HistoryIssue]:
        """Back-compat alias — same list object as ``findings``."""
        return self.findings

    @issues.setter
    def issues(self, value: list[HistoryIssue]) -> None:
        self.findings = value

    @property
    def summary(self) -> str:
        """Per-issue-type summary — what the UI has always displayed."""
        if not self.findings:
            return "Clean history"
        by_type: dict[str, int] = {}
        for issue in self.findings:
            by_type[issue.issue_type.value] = (
                by_type.get(issue.issue_type.value, 0) + 1
            )
        # Stable ordering so test snapshots don't flap.
        ordered = sorted(by_type.items(), key=lambda kv: kv[0])
        return ", ".join(f"{count} {t}" for t, count in ordered)


_SENSITIVE_PATTERNS = [
    re.compile(
        r"(?i)(password|secret|api_key|apikey|token)\s*[:=]\s*['\"][^'\"]{8,}['\"]"
    ),
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
            i.size_bytes
            for i in plan.issues
            if i.issue_type == HistoryIssueType.LARGE_BLOB
        ) / (1024 * 1024)

        plan.requires_force_push = any(
            i.suggested_action
            in (SurgeryAction.BFG_REMOVE, SurgeryAction.FILTER_BRANCH)
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
                capture_output=True,
                text=True,
                timeout=60,
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
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    size = (
                        int(size_result.stdout.strip())
                        if size_result.returncode == 0
                        else 0
                    )
                except (ValueError, subprocess.SubprocessError):
                    size = 0

                if size > threshold_mb * 1024 * 1024:
                    issues.append(
                        HistoryIssue(
                            issue_type=HistoryIssueType.LARGE_BLOB,
                            severity="high",
                            description=f"Large file: {path} ({size / 1024 / 1024:.1f} MB)",
                            commit_sha=sha,
                            file_path=path,
                            size_bytes=size,
                            suggested_action=SurgeryAction.BFG_REMOVE,
                        )
                    )
        except (subprocess.SubprocessError, OSError):
            pass
        return issues

    def _find_sensitive_data(self, max_commits: int) -> list[HistoryIssue]:
        """Scan commit diffs for sensitive data patterns."""
        issues: list[HistoryIssue] = []
        try:
            result = subprocess.run(
                [
                    "git",
                    "log",
                    f"-{max_commits}",
                    "--pretty=format:%H",
                    "--diff-filter=A",
                    "-p",
                ],
                cwd=str(self._repo_root),
                capture_output=True,
                text=True,
                timeout=120,
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
                        issues.append(
                            HistoryIssue(
                                issue_type=HistoryIssueType.SENSITIVE_DATA,
                                severity="critical",
                                description=f"Potential secret in commit {current_sha[:8]}",
                                commit_sha=current_sha,
                                suggested_action=SurgeryAction.BFG_REMOVE,
                            )
                        )
                        break
        except (subprocess.SubprocessError, OSError):
            pass
        return issues

    def _find_messy_commits(self, max_commits: int) -> list[HistoryIssue]:
        """Find commits with poor messages (WIP, fixup, etc.)."""
        issues: list[HistoryIssue] = []
        messy_patterns = re.compile(
            r"^(wip|fixup|tmp|test|asdf|xxx|todo|hack)", re.IGNORECASE
        )

        try:
            result = subprocess.run(
                ["git", "log", f"-{max_commits}", "--pretty=format:%H %s"],
                cwd=str(self._repo_root),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return issues

            for line in result.stdout.splitlines():
                parts = line.split(None, 1)
                if len(parts) < 2:
                    continue
                sha, message = parts
                if messy_patterns.match(message):
                    issues.append(
                        HistoryIssue(
                            issue_type=HistoryIssueType.MESSY_COMMITS,
                            severity="low",
                            description=f"Messy commit message: '{message[:60]}'",
                            commit_sha=sha,
                            suggested_action=SurgeryAction.SQUASH,
                        )
                    )
        except (subprocess.SubprocessError, OSError):
            pass
        return issues
