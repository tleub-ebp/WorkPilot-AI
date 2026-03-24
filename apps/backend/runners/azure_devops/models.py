"""
Azure DevOps PR Review Data Models
===================================

Data structures for Azure DevOps PR review features.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path


class ReviewSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ReviewCategory(str, Enum):
    SECURITY = "security"
    QUALITY = "quality"
    STYLE = "style"
    TEST = "test"
    DOCS = "docs"
    PATTERN = "pattern"
    PERFORMANCE = "performance"


class MergeVerdict(str, Enum):
    READY_TO_MERGE = "ready_to_merge"
    MERGE_WITH_CHANGES = "merge_with_changes"
    NEEDS_REVISION = "needs_revision"
    BLOCKED = "blocked"


@dataclass
class PRReviewFinding:
    """A single finding from a PR review."""

    id: str
    severity: ReviewSeverity
    category: ReviewCategory
    title: str
    description: str
    file: str
    line: int
    end_line: int | None = None
    suggested_fix: str | None = None
    fixable: bool = False
    evidence: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "severity": self.severity.value,
            "category": self.category.value,
            "title": self.title,
            "description": self.description,
            "file": self.file,
            "line": self.line,
            "end_line": self.end_line,
            "suggested_fix": self.suggested_fix,
            "fixable": self.fixable,
            "evidence": self.evidence,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PRReviewFinding:
        return cls(
            id=data["id"],
            severity=ReviewSeverity(data["severity"]),
            category=ReviewCategory(data["category"]),
            title=data["title"],
            description=data["description"],
            file=data["file"],
            line=data["line"],
            end_line=data.get("end_line"),
            suggested_fix=data.get("suggested_fix"),
            fixable=data.get("fixable", False),
            evidence=data.get("evidence"),
        )


@dataclass
class PRReviewResult:
    """Complete result of an Azure DevOps PR review."""

    pr_id: int
    project: str
    repository_id: str
    success: bool
    findings: list[PRReviewFinding] = field(default_factory=list)
    summary: str = ""
    overall_status: str = "comment"  # approve, request_changes, comment
    reviewed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    error: str | None = None

    # Verdict system
    verdict: MergeVerdict = MergeVerdict.READY_TO_MERGE
    verdict_reasoning: str = ""
    blockers: list[str] = field(default_factory=list)

    # Follow-up review tracking
    reviewed_commit_sha: str | None = None
    is_followup_review: bool = False
    resolved_findings: list[str] = field(default_factory=list)
    unresolved_findings: list[str] = field(default_factory=list)
    new_findings_since_last_review: list[str] = field(default_factory=list)

    # Posting tracking
    has_posted_findings: bool = False
    posted_finding_ids: list[str] = field(default_factory=list)

    # Deep codebase context metadata
    deep_context: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "pr_id": self.pr_id,
            "project": self.project,
            "repository_id": self.repository_id,
            "success": self.success,
            "findings": [f.to_dict() for f in self.findings],
            "summary": self.summary,
            "overall_status": self.overall_status,
            "reviewed_at": self.reviewed_at,
            "error": self.error,
            "verdict": self.verdict.value,
            "verdict_reasoning": self.verdict_reasoning,
            "blockers": self.blockers,
            "reviewed_commit_sha": self.reviewed_commit_sha,
            "is_followup_review": self.is_followup_review,
            "resolved_findings": self.resolved_findings,
            "unresolved_findings": self.unresolved_findings,
            "new_findings_since_last_review": self.new_findings_since_last_review,
            "has_posted_findings": self.has_posted_findings,
            "posted_finding_ids": self.posted_finding_ids,
            "deep_context": self.deep_context,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PRReviewResult:
        return cls(
            pr_id=data["pr_id"],
            project=data["project"],
            repository_id=data.get("repository_id", ""),
            success=data["success"],
            findings=[PRReviewFinding.from_dict(f) for f in data.get("findings", [])],
            summary=data.get("summary", ""),
            overall_status=data.get("overall_status", "comment"),
            reviewed_at=data.get("reviewed_at", datetime.now().isoformat()),
            error=data.get("error"),
            verdict=MergeVerdict(data.get("verdict", "ready_to_merge")),
            verdict_reasoning=data.get("verdict_reasoning", ""),
            blockers=data.get("blockers", []),
            reviewed_commit_sha=data.get("reviewed_commit_sha"),
            is_followup_review=data.get("is_followup_review", False),
            resolved_findings=data.get("resolved_findings", []),
            unresolved_findings=data.get("unresolved_findings", []),
            new_findings_since_last_review=data.get(
                "new_findings_since_last_review", []
            ),
            has_posted_findings=data.get("has_posted_findings", False),
            posted_finding_ids=data.get("posted_finding_ids", []),
            deep_context=data.get("deep_context", {}),
        )

    def save(self, azdo_dir: Path) -> None:
        """Save review result to .auto-claude/azure-devops/pr/"""
        pr_dir = azdo_dir / "pr"
        pr_dir.mkdir(parents=True, exist_ok=True)

        review_file = pr_dir / f"review_{self.pr_id}.json"
        with open(review_file, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, azdo_dir: Path, pr_id: int) -> PRReviewResult | None:
        """Load a review result from disk."""
        review_file = azdo_dir / "pr" / f"review_{pr_id}.json"
        if not review_file.exists():
            return None

        with open(review_file, encoding="utf-8") as f:
            return cls.from_dict(json.load(f))


@dataclass
class AzureDevOpsRunnerConfig:
    """Configuration for Azure DevOps PR review runner."""

    pat: str
    organization_url: str
    project: str
    repository_id: str = ""

    # Model settings
    model: str = "sonnet"
    thinking_level: str = "medium"

    def to_dict(self) -> dict:
        return {
            "pat": "***",
            "organization_url": self.organization_url,
            "project": self.project,
            "repository_id": self.repository_id,
            "model": self.model,
            "thinking_level": self.thinking_level,
        }


@dataclass
class AzDOPRContext:
    """Context for an Azure DevOps PR review."""

    pr_id: int
    title: str
    description: str
    author: str
    source_branch: str
    target_branch: str
    status: str
    changed_files: list[dict] = field(default_factory=list)
    diff: str = ""
    total_additions: int = 0
    total_deletions: int = 0
    head_sha: str | None = None

    # Deep codebase context (architecture, patterns, memory)
    deep_context: dict = field(default_factory=dict)
