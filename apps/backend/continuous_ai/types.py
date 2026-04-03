"""
Continuous AI Types
===================

Data models for the continuous AI daemon system.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ModuleState(str, Enum):
    """State of an individual daemon module."""

    DISABLED = "disabled"
    IDLE = "idle"
    POLLING = "polling"
    ACTING = "acting"
    ERROR = "error"
    COOLDOWN = "cooldown"


class ModuleName(str, Enum):
    """Available daemon modules."""

    CICD_WATCHER = "cicd_watcher"
    DEPENDENCY_SENTINEL = "dependency_sentinel"
    ISSUE_RESPONDER = "issue_responder"
    PR_REVIEWER = "pr_reviewer"


class ActionType(str, Enum):
    """Types of autonomous actions the daemon can take."""

    CICD_FIX = "cicd_fix"
    DEPENDENCY_PATCH = "dependency_patch"
    ISSUE_TRIAGE = "issue_triage"
    ISSUE_INVESTIGATION = "issue_investigation"
    PR_REVIEW = "pr_review"
    PR_AUTO_APPROVE = "pr_auto_approve"


class ActionStatus(str, Enum):
    """Status of a daemon action."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    NEEDS_APPROVAL = "needs_approval"


@dataclass
class DaemonModuleConfig:
    """Configuration for a single daemon module."""

    enabled: bool = False
    poll_interval_seconds: int = 300  # 5 minutes default
    auto_act: bool = False  # Whether to act automatically or request approval
    max_actions_per_hour: int = 5
    quiet_hours_start: str = ""  # e.g. "22:00" — empty means no quiet hours
    quiet_hours_end: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "poll_interval_seconds": self.poll_interval_seconds,
            "auto_act": self.auto_act,
            "max_actions_per_hour": self.max_actions_per_hour,
            "quiet_hours_start": self.quiet_hours_start,
            "quiet_hours_end": self.quiet_hours_end,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DaemonModuleConfig:
        return cls(
            enabled=data.get("enabled", False),
            poll_interval_seconds=data.get("poll_interval_seconds", 300),
            auto_act=data.get("auto_act", False),
            max_actions_per_hour=data.get("max_actions_per_hour", 5),
            quiet_hours_start=data.get("quiet_hours_start", ""),
            quiet_hours_end=data.get("quiet_hours_end", ""),
        )


@dataclass
class CICDWatcherConfig(DaemonModuleConfig):
    """Config specific to CI/CD watcher."""

    auto_fix: bool = False
    auto_create_pr: bool = False
    watched_workflows: list[str] = field(default_factory=list)  # Empty = all

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update(
            {
                "auto_fix": self.auto_fix,
                "auto_create_pr": self.auto_create_pr,
                "watched_workflows": self.watched_workflows,
            }
        )
        return base

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CICDWatcherConfig:
        return cls(
            enabled=data.get("enabled", False),
            poll_interval_seconds=data.get("poll_interval_seconds", 300),
            auto_act=data.get("auto_act", False),
            max_actions_per_hour=data.get("max_actions_per_hour", 5),
            quiet_hours_start=data.get("quiet_hours_start", ""),
            quiet_hours_end=data.get("quiet_hours_end", ""),
            auto_fix=data.get("auto_fix", False),
            auto_create_pr=data.get("auto_create_pr", False),
            watched_workflows=data.get("watched_workflows", []),
        )


@dataclass
class DependencySentinelConfig(DaemonModuleConfig):
    """Config specific to dependency sentinel."""

    auto_patch_minor: bool = True
    auto_patch_major: bool = False
    scan_interval_seconds: int = 86400  # Daily by default
    package_managers: list[str] = field(default_factory=lambda: ["npm", "pip"])

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update(
            {
                "auto_patch_minor": self.auto_patch_minor,
                "auto_patch_major": self.auto_patch_major,
                "scan_interval_seconds": self.scan_interval_seconds,
                "package_managers": self.package_managers,
            }
        )
        return base

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DependencySentinelConfig:
        return cls(
            enabled=data.get("enabled", False),
            poll_interval_seconds=data.get("poll_interval_seconds", 86400),
            auto_act=data.get("auto_act", False),
            max_actions_per_hour=data.get("max_actions_per_hour", 3),
            quiet_hours_start=data.get("quiet_hours_start", ""),
            quiet_hours_end=data.get("quiet_hours_end", ""),
            auto_patch_minor=data.get("auto_patch_minor", True),
            auto_patch_major=data.get("auto_patch_major", False),
            scan_interval_seconds=data.get("scan_interval_seconds", 86400),
            package_managers=data.get("package_managers", ["npm", "pip"]),
        )


@dataclass
class IssueResponderConfig(DaemonModuleConfig):
    """Config specific to issue auto-responder."""

    auto_triage: bool = True
    auto_investigate_bugs: bool = False
    auto_create_specs: bool = False
    labels_to_watch: list[str] = field(default_factory=list)  # Empty = all

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update(
            {
                "auto_triage": self.auto_triage,
                "auto_investigate_bugs": self.auto_investigate_bugs,
                "auto_create_specs": self.auto_create_specs,
                "labels_to_watch": self.labels_to_watch,
            }
        )
        return base

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IssueResponderConfig:
        return cls(
            enabled=data.get("enabled", False),
            poll_interval_seconds=data.get("poll_interval_seconds", 180),
            auto_act=data.get("auto_act", False),
            max_actions_per_hour=data.get("max_actions_per_hour", 10),
            quiet_hours_start=data.get("quiet_hours_start", ""),
            quiet_hours_end=data.get("quiet_hours_end", ""),
            auto_triage=data.get("auto_triage", True),
            auto_investigate_bugs=data.get("auto_investigate_bugs", False),
            auto_create_specs=data.get("auto_create_specs", False),
            labels_to_watch=data.get("labels_to_watch", []),
        )


@dataclass
class PRReviewerConfig(DaemonModuleConfig):
    """Config specific to PR auto-reviewer."""

    auto_approve_trivial: bool = False
    review_external_only: bool = True  # Only review PRs not created by WorkPilot
    post_review_comments: bool = True
    trivial_patterns: list[str] = field(
        default_factory=lambda: ["docs", "typo", "readme", "changelog"]
    )

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update(
            {
                "auto_approve_trivial": self.auto_approve_trivial,
                "review_external_only": self.review_external_only,
                "post_review_comments": self.post_review_comments,
                "trivial_patterns": self.trivial_patterns,
            }
        )
        return base

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PRReviewerConfig:
        return cls(
            enabled=data.get("enabled", False),
            poll_interval_seconds=data.get("poll_interval_seconds", 300),
            auto_act=data.get("auto_act", False),
            max_actions_per_hour=data.get("max_actions_per_hour", 5),
            quiet_hours_start=data.get("quiet_hours_start", ""),
            quiet_hours_end=data.get("quiet_hours_end", ""),
            auto_approve_trivial=data.get("auto_approve_trivial", False),
            review_external_only=data.get("review_external_only", True),
            post_review_comments=data.get("post_review_comments", True),
            trivial_patterns=data.get(
                "trivial_patterns", ["docs", "typo", "readme", "changelog"]
            ),
        )


@dataclass
class ContinuousAIConfig:
    """Master configuration for the continuous AI daemon."""

    enabled: bool = False
    daily_budget_usd: float = 5.0
    cicd_watcher: CICDWatcherConfig = field(default_factory=CICDWatcherConfig)
    dependency_sentinel: DependencySentinelConfig = field(
        default_factory=DependencySentinelConfig
    )
    issue_responder: IssueResponderConfig = field(default_factory=IssueResponderConfig)
    pr_reviewer: PRReviewerConfig = field(default_factory=PRReviewerConfig)

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "daily_budget_usd": self.daily_budget_usd,
            "cicd_watcher": self.cicd_watcher.to_dict(),
            "dependency_sentinel": self.dependency_sentinel.to_dict(),
            "issue_responder": self.issue_responder.to_dict(),
            "pr_reviewer": self.pr_reviewer.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContinuousAIConfig:
        return cls(
            enabled=data.get("enabled", False),
            daily_budget_usd=data.get("daily_budget_usd", 5.0),
            cicd_watcher=CICDWatcherConfig.from_dict(data.get("cicd_watcher", {})),
            dependency_sentinel=DependencySentinelConfig.from_dict(
                data.get("dependency_sentinel", {})
            ),
            issue_responder=IssueResponderConfig.from_dict(
                data.get("issue_responder", {})
            ),
            pr_reviewer=PRReviewerConfig.from_dict(data.get("pr_reviewer", {})),
        )


@dataclass
class DaemonAction:
    """A single action taken (or proposed) by the daemon."""

    id: str
    module: ModuleName
    action_type: ActionType
    status: ActionStatus = ActionStatus.PENDING
    title: str = ""
    description: str = ""
    target: str = ""  # PR URL, issue URL, workflow run URL, etc.
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    result: str | None = None
    error: str | None = None
    cost_usd: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float | None:
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "module": self.module.value,
            "action_type": self.action_type.value,
            "status": self.status.value,
            "title": self.title,
            "description": self.description,
            "target": self.target,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "error": self.error,
            "cost_usd": self.cost_usd,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata,
        }


@dataclass
class DaemonModule:
    """Runtime state of a daemon module."""

    name: ModuleName
    state: ModuleState = ModuleState.DISABLED
    last_poll_at: float | None = None
    last_action_at: float | None = None
    actions_this_hour: int = 0
    hour_reset_at: float = field(default_factory=lambda: time.time() + 3600)
    total_actions: int = 0
    total_cost_usd: float = 0.0
    error: str | None = None

    def can_act(self, config: DaemonModuleConfig) -> bool:
        """Check if this module can take another action."""
        if self.state in (ModuleState.DISABLED, ModuleState.ERROR):
            return False
        # Reset hourly counter if needed
        now = time.time()
        if now >= self.hour_reset_at:
            self.actions_this_hour = 0
            self.hour_reset_at = now + 3600
        return self.actions_this_hour < config.max_actions_per_hour

    def record_action(self, cost_usd: float = 0.0) -> None:
        """Record that an action was taken."""
        self.actions_this_hour += 1
        self.total_actions += 1
        self.total_cost_usd += cost_usd
        self.last_action_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name.value,
            "state": self.state.value,
            "last_poll_at": self.last_poll_at,
            "last_action_at": self.last_action_at,
            "actions_this_hour": self.actions_this_hour,
            "total_actions": self.total_actions,
            "total_cost_usd": self.total_cost_usd,
            "error": self.error,
        }


@dataclass
class ContinuousAIStatus:
    """Overall status of the daemon."""

    running: bool = False
    started_at: float | None = None
    modules: dict[str, DaemonModule] = field(default_factory=dict)
    recent_actions: list[DaemonAction] = field(default_factory=list)
    total_cost_today_usd: float = 0.0
    daily_budget_usd: float = 5.0

    @property
    def is_over_budget(self) -> bool:
        return self.total_cost_today_usd >= self.daily_budget_usd

    @property
    def enabled_modules_count(self) -> int:
        return sum(1 for m in self.modules.values() if m.state != ModuleState.DISABLED)

    def to_dict(self) -> dict[str, Any]:
        return {
            "running": self.running,
            "started_at": self.started_at,
            "modules": {k: v.to_dict() for k, v in self.modules.items()},
            "recent_actions": [a.to_dict() for a in self.recent_actions[-50:]],
            "total_cost_today_usd": self.total_cost_today_usd,
            "daily_budget_usd": self.daily_budget_usd,
            "enabled_modules_count": self.enabled_modules_count,
            "is_over_budget": self.is_over_budget,
        }
