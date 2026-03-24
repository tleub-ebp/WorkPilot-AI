"""Enriched Native Desktop Notifications — Rich system notifications with actions.

Provides a notification manager that creates rich desktop notifications using
Electron's native notification API. Supports task completion/failure alerts,
QA results with scores, rate limit warnings, periodic summaries, and quick
actions directly from the notification (approve merge, rerun QA, switch profile).

Feature 9.3 — Notifications desktop natives enrichies.

Example:
    >>> from apps.backend.ui.desktop_notifications import DesktopNotificationManager
    >>> manager = DesktopNotificationManager(project_id="my-project")
    >>> manager.notify_task_completed("task-42", "Login page", agent_type="coder")
    >>> manager.notify_qa_result("task-42", passed=True, score=92.5)
    >>> summary = manager.create_periodic_summary()
"""

import logging
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class NotificationType(str, Enum):
    """Types of desktop notifications."""

    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    QA_PASSED = "qa_passed"
    QA_FAILED = "qa_failed"
    RATE_LIMIT = "rate_limit"
    MERGE_READY = "merge_ready"
    MERGE_CONFLICT = "merge_conflict"
    SECURITY_ALERT = "security_alert"
    PERIODIC_SUMMARY = "periodic_summary"
    AGENT_STARTED = "agent_started"
    AGENT_PAUSED = "agent_paused"
    BUDGET_ALERT = "budget_alert"
    CUSTOM = "custom"


class NotificationPriority(str, Enum):
    """Priority levels for notifications."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationActionType(str, Enum):
    """Types of quick actions available from notifications."""

    APPROVE_MERGE = "approve_merge"
    RERUN_QA = "rerun_qa"
    VIEW_DETAILS = "view_details"
    SWITCH_PROVIDER = "switch_provider"
    DISMISS = "dismiss"
    OPEN_TASK = "open_task"
    RETRY_TASK = "retry_task"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class NotificationAction:
    """A quick action button attached to a notification."""

    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action_type: str = "view_details"
    label: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DesktopNotification:
    """A rich desktop notification with optional actions."""

    notification_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    notification_type: str = "custom"
    title: str = ""
    body: str = ""
    icon: str = ""
    priority: str = "normal"
    actions: list[NotificationAction] = field(default_factory=list)
    task_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    read: bool = False
    clicked: bool = False

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        return result

    def to_electron_payload(self) -> dict[str, Any]:
        """Convert to Electron Notification API payload."""
        payload: dict[str, Any] = {
            "title": self.title,
            "body": self.body,
            "silent": self.priority == "low",
            "urgency": "critical" if self.priority == "urgent" else "normal",
            "metadata": {
                "notification_id": self.notification_id,
                "notification_type": self.notification_type,
                "task_id": self.task_id,
            },
        }
        if self.icon:
            payload["icon"] = self.icon
        if self.actions:
            payload["actions"] = [
                {"type": "button", "text": a.label} for a in self.actions[:3]
            ]
        return payload


@dataclass
class PeriodicSummary:
    """A periodic summary notification with aggregated stats."""

    summary_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    period: str = "hourly"
    tasks_completed: int = 0
    tasks_failed: int = 0
    qa_pass_rate: float = 0.0
    total_tokens: int = 0
    total_cost: float = 0.0
    highlights: list[str] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_notification_body(self) -> str:
        parts = []
        total = self.tasks_completed + self.tasks_failed
        if total > 0:
            parts.append(
                f"{self.tasks_completed} completed, {self.tasks_failed} failed"
            )
        if self.qa_pass_rate > 0:
            parts.append(f"QA pass rate: {self.qa_pass_rate:.0f}%")
        if self.total_cost > 0:
            parts.append(f"Cost: ${self.total_cost:.2f}")
        if self.highlights:
            parts.append(self.highlights[0])
        return " | ".join(parts) if parts else "No activity this period"


@dataclass
class NotificationPreferences:
    """User preferences for desktop notifications."""

    enabled: bool = True
    task_completed: bool = True
    task_failed: bool = True
    qa_results: bool = True
    rate_limit: bool = True
    merge_ready: bool = True
    security_alerts: bool = True
    periodic_summary: bool = True
    summary_interval_minutes: int = 60
    quiet_hours_start: int | None = None
    quiet_hours_end: int | None = None
    min_priority: str = "low"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def is_quiet_hours(self) -> bool:
        if self.quiet_hours_start is None or self.quiet_hours_end is None:
            return False
        now_hour = datetime.now().hour
        if self.quiet_hours_start <= self.quiet_hours_end:
            return self.quiet_hours_start <= now_hour < self.quiet_hours_end
        return now_hour >= self.quiet_hours_start or now_hour < self.quiet_hours_end


# ---------------------------------------------------------------------------
# Icons mapping
# ---------------------------------------------------------------------------

NOTIFICATION_ICONS = {
    NotificationType.TASK_COMPLETED.value: "check-circle",
    NotificationType.TASK_FAILED.value: "x-circle",
    NotificationType.QA_PASSED.value: "shield-check",
    NotificationType.QA_FAILED.value: "shield-x",
    NotificationType.RATE_LIMIT.value: "clock",
    NotificationType.MERGE_READY.value: "git-merge",
    NotificationType.MERGE_CONFLICT.value: "git-pull-request",
    NotificationType.SECURITY_ALERT.value: "shield-alert",
    NotificationType.PERIODIC_SUMMARY.value: "bar-chart",
    NotificationType.AGENT_STARTED.value: "play-circle",
    NotificationType.AGENT_PAUSED.value: "pause-circle",
    NotificationType.BUDGET_ALERT.value: "dollar-sign",
}

PRIORITY_MAP = {
    NotificationType.TASK_COMPLETED.value: "normal",
    NotificationType.TASK_FAILED.value: "high",
    NotificationType.QA_PASSED.value: "normal",
    NotificationType.QA_FAILED.value: "high",
    NotificationType.RATE_LIMIT.value: "high",
    NotificationType.MERGE_READY.value: "normal",
    NotificationType.MERGE_CONFLICT.value: "high",
    NotificationType.SECURITY_ALERT.value: "urgent",
    NotificationType.PERIODIC_SUMMARY.value: "low",
    NotificationType.AGENT_STARTED.value: "low",
    NotificationType.AGENT_PAUSED.value: "high",
    NotificationType.BUDGET_ALERT.value: "high",
}


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class DesktopNotificationManager:
    """Manages rich native desktop notifications for the application.

    Creates, dispatches, and tracks desktop notifications with support for
    quick actions, periodic summaries, user preferences, and quiet hours.

    Args:
        project_id: The project identifier.
        preferences: User notification preferences.
    """

    def __init__(
        self,
        project_id: str = "",
        preferences: NotificationPreferences | None = None,
    ) -> None:
        self._project_id = project_id
        self._preferences = preferences or NotificationPreferences()
        self._notifications: list[DesktopNotification] = []
        self._summaries: list[PeriodicSummary] = []
        self._action_handlers: dict[str, Callable] = {}
        self._dispatch_callback: Callable | None = None

        # Counters for periodic summaries
        self._period_tasks_completed: int = 0
        self._period_tasks_failed: int = 0
        self._period_qa_results: list[float] = []
        self._period_tokens: int = 0
        self._period_cost: float = 0.0
        self._period_highlights: list[str] = []

    # -- Configuration -------------------------------------------------------

    def set_preferences(self, preferences: NotificationPreferences) -> None:
        """Update notification preferences."""
        self._preferences = preferences

    def get_preferences(self) -> NotificationPreferences:
        """Get current preferences."""
        return self._preferences

    def set_dispatch_callback(self, callback: Callable) -> None:
        """Set the callback used to actually display the notification (Electron IPC)."""
        self._dispatch_callback = callback

    def register_action_handler(self, action_type: str, handler: Callable) -> None:
        """Register a handler for a notification action button."""
        self._action_handlers[action_type] = handler

    # -- Notification creation -----------------------------------------------

    def notify_task_completed(
        self,
        task_id: str,
        task_title: str,
        agent_type: str = "coder",
        duration_s: float | None = None,
    ) -> DesktopNotification | None:
        """Notify that a task has been completed successfully."""
        if not self._preferences.task_completed:
            return None

        body = f"Agent {agent_type} finished '{task_title}'"
        if duration_s is not None:
            minutes = int(duration_s / 60)
            body += f" in {minutes}min"

        notif = self._create_notification(
            notification_type=NotificationType.TASK_COMPLETED.value,
            title="Task Completed",
            body=body,
            task_id=task_id,
            actions=[
                NotificationAction(action_type="view_details", label="View Details"),
                NotificationAction(action_type="open_task", label="Open Task"),
            ],
        )
        self._period_tasks_completed += 1
        self._period_highlights.append(f"Completed: {task_title}")
        return notif

    def notify_task_failed(
        self,
        task_id: str,
        task_title: str,
        error: str = "",
        agent_type: str = "coder",
    ) -> DesktopNotification | None:
        """Notify that a task has failed."""
        if not self._preferences.task_failed:
            return None

        body = f"Agent {agent_type} failed on '{task_title}'"
        if error:
            body += f": {error[:100]}"

        notif = self._create_notification(
            notification_type=NotificationType.TASK_FAILED.value,
            title="Task Failed",
            body=body,
            task_id=task_id,
            actions=[
                NotificationAction(action_type="retry_task", label="Retry"),
                NotificationAction(action_type="view_details", label="View Logs"),
            ],
        )
        self._period_tasks_failed += 1
        return notif

    def notify_qa_result(
        self,
        task_id: str,
        passed: bool,
        score: float = 0.0,
        task_title: str = "",
    ) -> DesktopNotification | None:
        """Notify of a QA result with score."""
        if not self._preferences.qa_results:
            return None

        ntype = (
            NotificationType.QA_PASSED.value
            if passed
            else NotificationType.QA_FAILED.value
        )
        status = "passed" if passed else "failed"
        title = f"QA {status.capitalize()}"
        body = f"Score: {score:.1f}/100"
        if task_title:
            body = f"'{task_title}' — {body}"

        actions = [NotificationAction(action_type="view_details", label="View Report")]
        if not passed:
            actions.append(NotificationAction(action_type="rerun_qa", label="Rerun QA"))

        notif = self._create_notification(
            notification_type=ntype,
            title=title,
            body=body,
            task_id=task_id,
            actions=actions,
            metadata={"score": score, "passed": passed},
        )
        self._period_qa_results.append(score)
        return notif

    def notify_rate_limit(
        self,
        provider: str,
        model: str,
        retry_after_s: int = 60,
    ) -> DesktopNotification | None:
        """Notify of a rate limit hit."""
        if not self._preferences.rate_limit:
            return None

        return self._create_notification(
            notification_type=NotificationType.RATE_LIMIT.value,
            title="Rate Limit Reached",
            body=f"{provider}/{model} — retry in {retry_after_s}s",
            actions=[
                NotificationAction(
                    action_type="switch_provider", label="Switch Provider"
                ),
                NotificationAction(action_type="dismiss", label="Wait"),
            ],
            metadata={
                "provider": provider,
                "model": model,
                "retry_after_s": retry_after_s,
            },
        )

    def notify_merge_ready(
        self,
        task_id: str,
        task_title: str,
        branch: str = "",
    ) -> DesktopNotification | None:
        """Notify that a merge is ready for approval."""
        if not self._preferences.merge_ready:
            return None

        body = f"'{task_title}' is ready to merge"
        if branch:
            body += f" (branch: {branch})"

        return self._create_notification(
            notification_type=NotificationType.MERGE_READY.value,
            title="Merge Ready",
            body=body,
            task_id=task_id,
            actions=[
                NotificationAction(action_type="approve_merge", label="Approve Merge"),
                NotificationAction(action_type="view_details", label="Review"),
            ],
        )

    def notify_security_alert(
        self,
        title: str,
        description: str,
        severity: str = "high",
    ) -> DesktopNotification | None:
        """Notify of a security alert."""
        if not self._preferences.security_alerts:
            return None

        return self._create_notification(
            notification_type=NotificationType.SECURITY_ALERT.value,
            title=f"Security Alert: {title}",
            body=description,
            actions=[
                NotificationAction(action_type="view_details", label="View Details"),
            ],
            metadata={"severity": severity},
        )

    def notify_budget_alert(
        self,
        current_cost: float,
        budget_limit: float,
        percentage: float,
    ) -> DesktopNotification | None:
        """Notify of a budget threshold being reached."""
        return self._create_notification(
            notification_type=NotificationType.BUDGET_ALERT.value,
            title="Budget Alert",
            body=f"${current_cost:.2f} / ${budget_limit:.2f} ({percentage:.0f}% used)",
            actions=[
                NotificationAction(action_type="view_details", label="View Costs"),
            ],
            metadata={
                "current_cost": current_cost,
                "budget_limit": budget_limit,
                "percentage": percentage,
            },
        )

    def notify_custom(
        self,
        title: str,
        body: str,
        priority: str = "normal",
        task_id: str | None = None,
        actions: list[NotificationAction] | None = None,
    ) -> DesktopNotification | None:
        """Send a custom notification."""
        return self._create_notification(
            notification_type=NotificationType.CUSTOM.value,
            title=title,
            body=body,
            task_id=task_id,
            actions=actions or [],
            priority_override=priority,
        )

    # -- Periodic summaries --------------------------------------------------

    def create_periodic_summary(self, period: str = "hourly") -> PeriodicSummary:
        """Create and dispatch a periodic summary notification."""
        qa_pass_rate = 0.0
        if self._period_qa_results:
            passing = sum(1 for s in self._period_qa_results if s >= 70)
            qa_pass_rate = (passing / len(self._period_qa_results)) * 100

        summary = PeriodicSummary(
            period=period,
            tasks_completed=self._period_tasks_completed,
            tasks_failed=self._period_tasks_failed,
            qa_pass_rate=qa_pass_rate,
            total_tokens=self._period_tokens,
            total_cost=self._period_cost,
            highlights=self._period_highlights[:5],
        )
        self._summaries.append(summary)

        if self._preferences.periodic_summary:
            total = summary.tasks_completed + summary.tasks_failed
            title = f"{period.capitalize()} Summary — {total} tasks"
            self._create_notification(
                notification_type=NotificationType.PERIODIC_SUMMARY.value,
                title=title,
                body=summary.to_notification_body(),
                metadata=summary.to_dict(),
            )

        self._reset_period_counters()
        return summary

    def record_token_usage(self, tokens: int, cost: float) -> None:
        """Record token usage for the current period summary."""
        self._period_tokens += tokens
        self._period_cost += cost

    # -- Action handling -----------------------------------------------------

    def handle_action(self, notification_id: str, action_type: str) -> dict[str, Any]:
        """Handle a quick action clicked from a notification."""
        notif = self._get_notification(notification_id)
        notif.clicked = True

        handler = self._action_handlers.get(action_type)
        if handler:
            try:
                result = handler(notif)
                return {"success": True, "action": action_type, "result": result}
            except Exception as exc:
                return {"success": False, "action": action_type, "error": str(exc)}
        return {"success": True, "action": action_type, "result": "no_handler"}

    def mark_read(self, notification_id: str) -> None:
        """Mark a notification as read."""
        notif = self._get_notification(notification_id)
        notif.read = True

    def mark_all_read(self) -> int:
        """Mark all notifications as read. Returns count of newly marked."""
        count = 0
        for n in self._notifications:
            if not n.read:
                n.read = True
                count += 1
        return count

    # -- Queries -------------------------------------------------------------

    def get_notifications(
        self,
        notification_type: str | None = None,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[DesktopNotification]:
        """Get notifications, optionally filtered."""
        result = list(self._notifications)
        if notification_type:
            result = [n for n in result if n.notification_type == notification_type]
        if unread_only:
            result = [n for n in result if not n.read]
        result.sort(key=lambda n: n.timestamp, reverse=True)
        return result[:limit]

    def get_unread_count(self) -> int:
        """Get the count of unread notifications."""
        return sum(1 for n in self._notifications if not n.read)

    def get_summaries(self) -> list[PeriodicSummary]:
        """Get all periodic summaries."""
        return list(self._summaries)

    def get_stats(self) -> dict[str, Any]:
        """Get notification statistics."""
        type_counts: dict[str, int] = {}
        for n in self._notifications:
            type_counts[n.notification_type] = (
                type_counts.get(n.notification_type, 0) + 1
            )

        return {
            "total_notifications": len(self._notifications),
            "unread_count": self.get_unread_count(),
            "type_counts": type_counts,
            "total_summaries": len(self._summaries),
            "period_tasks_completed": self._period_tasks_completed,
            "period_tasks_failed": self._period_tasks_failed,
            "preferences_enabled": self._preferences.enabled,
        }

    # -- Internal helpers ----------------------------------------------------

    def _create_notification(
        self,
        notification_type: str,
        title: str,
        body: str,
        task_id: str | None = None,
        actions: list[NotificationAction] | None = None,
        metadata: dict[str, Any] | None = None,
        priority_override: str | None = None,
    ) -> DesktopNotification | None:
        if not self._preferences.enabled:
            return None
        if self._preferences.is_quiet_hours():
            priority = priority_override or PRIORITY_MAP.get(
                notification_type, "normal"
            )
            if priority != "urgent":
                return None

        priority = priority_override or PRIORITY_MAP.get(notification_type, "normal")
        priority_order = {"low": 0, "normal": 1, "high": 2, "urgent": 3}
        min_priority_level = priority_order.get(self._preferences.min_priority, 0)
        if priority_order.get(priority, 1) < min_priority_level:
            return None

        notif = DesktopNotification(
            notification_type=notification_type,
            title=title,
            body=body,
            icon=NOTIFICATION_ICONS.get(notification_type, "bell"),
            priority=priority,
            actions=actions or [],
            task_id=task_id,
            metadata=metadata or {},
        )
        self._notifications.append(notif)

        if self._dispatch_callback:
            try:
                self._dispatch_callback(notif.to_electron_payload())
            except Exception as exc:
                logger.error("Failed to dispatch notification: %s", exc)

        return notif

    def _get_notification(self, notification_id: str) -> DesktopNotification:
        for n in self._notifications:
            if n.notification_id == notification_id:
                return n
        raise KeyError(f"Notification '{notification_id}' not found")

    def _reset_period_counters(self) -> None:
        self._period_tasks_completed = 0
        self._period_tasks_failed = 0
        self._period_qa_results = []
        self._period_tokens = 0
        self._period_cost = 0.0
        self._period_highlights = []
