"""Data models for the Notifications connector (Slack / Microsoft Teams).

Defines dataclass representations for notification events, results,
slash commands, and daily summaries.

Feature 4.3 — Intégration Slack / Microsoft Teams.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class NotificationChannel(Enum):
    """Supported notification channels."""
    SLACK = "slack"
    TEAMS = "teams"


class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class EventType(Enum):
    """Types of events that can trigger notifications."""
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    QA_PASSED = "qa_passed"
    QA_FAILED = "qa_failed"
    MERGE_SUCCESS = "merge_success"
    MERGE_CONFLICT = "merge_conflict"
    RATE_LIMIT = "rate_limit"
    BUDGET_ALERT = "budget_alert"
    SECURITY_ALERT = "security_alert"
    DAILY_SUMMARY = "daily_summary"
    CUSTOM = "custom"


@dataclass
class NotificationEvent:
    """A notification event to be delivered.

    Attributes:
        event_type: The type of event that triggered this notification.
        title: Short title of the notification.
        message: The notification body text.
        priority: The notification priority level.
        project_id: The project this event relates to.
        task_id: Optional task identifier.
        metadata: Additional structured data for the notification.
        channels: Target channels to deliver to. If empty, delivers to all configured.
        timestamp: When the event occurred.
    """
    event_type: EventType
    title: str
    message: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    project_id: str = ""
    task_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    channels: list[NotificationChannel] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary."""
        return {
            "event_type": self.event_type.value,
            "title": self.title,
            "message": self.message,
            "priority": self.priority.value,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "metadata": self.metadata,
            "channels": [c.value for c in self.channels],
            "timestamp": self.timestamp.isoformat(),
        }

    def to_slack_payload(self) -> dict[str, Any]:
        """Convert to Slack webhook payload (Block Kit format).

        Returns:
            A Slack-compatible JSON payload with blocks.
        """
        color = _priority_to_color(self.priority)
        emoji = _event_type_to_emoji(self.event_type)

        blocks: list[dict[str, Any]] = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} {self.title}",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": self.message,
                },
            },
        ]

        context_elements = []
        if self.project_id:
            context_elements.append(
                {"type": "mrkdwn", "text": f"*Project:* {self.project_id}"}
            )
        if self.task_id:
            context_elements.append(
                {"type": "mrkdwn", "text": f"*Task:* {self.task_id}"}
            )
        context_elements.append(
            {"type": "mrkdwn", "text": f"*Priority:* {self.priority.value}"}
        )

        if context_elements:
            blocks.append({"type": "context", "elements": context_elements})

        return {
            "text": f"{emoji} {self.title}: {self.message}",
            "blocks": blocks,
            "attachments": [{"color": color, "blocks": []}] if color else [],
        }

    def to_teams_payload(self) -> dict[str, Any]:
        """Convert to Microsoft Teams webhook payload (Adaptive Card).

        Returns:
            A Teams-compatible Adaptive Card JSON payload.
        """
        emoji = _event_type_to_emoji(self.event_type)
        color = _priority_to_teams_color(self.priority)

        facts = []
        if self.project_id:
            facts.append({"title": "Project", "value": self.project_id})
        if self.task_id:
            facts.append({"title": "Task", "value": self.task_id})
        facts.append({"title": "Priority", "value": self.priority.value.capitalize()})
        facts.append({"title": "Type", "value": self.event_type.value.replace("_", " ").title()})

        body: list[dict[str, Any]] = [
            {
                "type": "TextBlock",
                "size": "Large",
                "weight": "Bolder",
                "text": f"{emoji} {self.title}",
                "wrap": True,
            },
            {
                "type": "TextBlock",
                "text": self.message,
                "wrap": True,
            },
            {
                "type": "FactSet",
                "facts": facts,
            },
        ]

        return {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "msteams": {"width": "Full"},
                        "body": body,
                    },
                }
            ],
        }


@dataclass
class NotificationResult:
    """Result of a notification delivery attempt.

    Attributes:
        success: Whether the delivery succeeded.
        channel: The target channel.
        event_type: The event type that was delivered.
        status_code: HTTP status code from the webhook, or 0.
        error: Error message if delivery failed, or None.
        timestamp: When the delivery was attempted.
    """
    success: bool
    channel: NotificationChannel
    event_type: EventType
    status_code: int = 0
    error: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary."""
        return {
            "success": self.success,
            "channel": self.channel.value,
            "event_type": self.event_type.value,
            "status_code": self.status_code,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class SlashCommand:
    """Represents a parsed slash command from Slack or Teams.

    Attributes:
        command: The command name (e.g., ``'create-task'``, ``'status'``).
        args: The command arguments as a string.
        channel: The originating channel.
        user_id: The user who invoked the command.
        channel_id: The channel where the command was invoked.
        response_url: URL to send the response to.
    """
    command: str
    args: str = ""
    channel: NotificationChannel = NotificationChannel.SLACK
    user_id: str = ""
    channel_id: str = ""
    response_url: str = ""

    SUPPORTED_COMMANDS = [
        "create-task",
        "status",
        "list-tasks",
        "budget",
        "help",
    ]

    @classmethod
    def parse(cls, text: str, channel: NotificationChannel = NotificationChannel.SLACK, **kwargs: Any) -> "SlashCommand":
        """Parse a slash command string.

        Args:
            text: The raw command text (e.g., ``'create-task "Fix the login bug"'``).
            channel: The originating channel.
            **kwargs: Additional fields (user_id, channel_id, response_url).

        Returns:
            A SlashCommand instance.
        """
        text = text.strip()
        parts = text.split(maxsplit=1)
        command = parts[0].lstrip("/").lower() if parts else ""
        args = parts[1] if len(parts) > 1 else ""
        return cls(
            command=command,
            args=args,
            channel=channel,
            user_id=kwargs.get("user_id", ""),
            channel_id=kwargs.get("channel_id", ""),
            response_url=kwargs.get("response_url", ""),
        )

    @property
    def is_valid(self) -> bool:
        """Check if this is a recognized command."""
        return self.command in self.SUPPORTED_COMMANDS

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary."""
        return {
            "command": self.command,
            "args": self.args,
            "channel": self.channel.value,
            "user_id": self.user_id,
            "is_valid": self.is_valid,
        }


@dataclass
class DailySummary:
    """Daily activity summary for notification delivery.

    Attributes:
        project_id: The project this summary covers.
        date: The date covered.
        tasks_completed: Number of tasks completed.
        tasks_failed: Number of tasks that failed.
        qa_pass_rate: QA pass rate as a percentage (0-100).
        merges_successful: Number of successful merges.
        total_cost: Total LLM cost for the day in USD.
        highlights: List of notable events.
    """
    project_id: str
    date: str
    tasks_completed: int = 0
    tasks_failed: int = 0
    qa_pass_rate: float = 0.0
    merges_successful: int = 0
    total_cost: float = 0.0
    highlights: list[str] = field(default_factory=list)

    def to_notification_event(self) -> NotificationEvent:
        """Convert to a NotificationEvent for delivery.

        Returns:
            A NotificationEvent containing the summary as message.
        """
        lines = [
            f"*Tasks completed:* {self.tasks_completed}",
            f"*Tasks failed:* {self.tasks_failed}",
            f"*QA pass rate:* {self.qa_pass_rate:.0f}%",
            f"*Merges:* {self.merges_successful}",
            f"*Total cost:* ${self.total_cost:.2f}",
        ]
        if self.highlights:
            lines.append("\n*Highlights:*")
            for h in self.highlights:
                lines.append(f"  - {h}")

        return NotificationEvent(
            event_type=EventType.DAILY_SUMMARY,
            title=f"Daily Summary — {self.date}",
            message="\n".join(lines),
            priority=NotificationPriority.LOW,
            project_id=self.project_id,
            metadata={
                "tasks_completed": self.tasks_completed,
                "tasks_failed": self.tasks_failed,
                "qa_pass_rate": self.qa_pass_rate,
                "merges_successful": self.merges_successful,
                "total_cost": self.total_cost,
            },
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary."""
        return {
            "project_id": self.project_id,
            "date": self.date,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "qa_pass_rate": self.qa_pass_rate,
            "merges_successful": self.merges_successful,
            "total_cost": self.total_cost,
            "highlights": self.highlights,
        }


# ---- Helpers ----

def _priority_to_color(priority: NotificationPriority) -> str:
    """Map priority to Slack attachment color."""
    return {
        NotificationPriority.LOW: "#36a64f",
        NotificationPriority.NORMAL: "#2196F3",
        NotificationPriority.HIGH: "#ff9800",
        NotificationPriority.URGENT: "#f44336",
    }.get(priority, "#2196F3")


def _priority_to_teams_color(priority: NotificationPriority) -> str:
    """Map priority to Teams theme color."""
    return {
        NotificationPriority.LOW: "good",
        NotificationPriority.NORMAL: "default",
        NotificationPriority.HIGH: "warning",
        NotificationPriority.URGENT: "attention",
    }.get(priority, "default")


def _event_type_to_emoji(event_type: EventType) -> str:
    """Map event type to an emoji for display."""
    return {
        EventType.TASK_COMPLETED: "\u2705",
        EventType.TASK_FAILED: "\u274c",
        EventType.QA_PASSED: "\u2705",
        EventType.QA_FAILED: "\u26a0\ufe0f",
        EventType.MERGE_SUCCESS: "\ud83d\udd00",
        EventType.MERGE_CONFLICT: "\u26a0\ufe0f",
        EventType.RATE_LIMIT: "\u23f3",
        EventType.BUDGET_ALERT: "\ud83d\udcb0",
        EventType.SECURITY_ALERT: "\ud83d\udee1\ufe0f",
        EventType.DAILY_SUMMARY: "\ud83d\udcca",
        EventType.CUSTOM: "\ud83d\udce3",
    }.get(event_type, "\ud83d\udce3")
