"""Notifications connector — Slack & Microsoft Teams integration.

Provides unified notification delivery to Slack (via Incoming Webhooks)
and Microsoft Teams (via Incoming Webhooks / Adaptive Cards), with
support for slash commands, daily summaries, and security alerts.

Feature 4.3 — Intégration Slack / Microsoft Teams.

Example:
    >>> from src.connectors.notifications import NotificationsConnector
    >>> connector = NotificationsConnector.from_env()
    >>> connector.notify_task_completed("my-project", "task-42", "Implement login page")
"""

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

from src.connectors.notifications.exceptions import (
    NotificationConfigurationError,
    NotificationDeliveryError,
    NotificationError,
)
from src.connectors.notifications.models import (
    DailySummary,
    EventType,
    NotificationChannel,
    NotificationEvent,
    NotificationPriority,
    NotificationResult,
    SlashCommand,
)

logger = logging.getLogger(__name__)


class NotificationsConnector:
    """Unified connector for Slack and Microsoft Teams notifications.

    Sends notifications via webhook URLs to one or both platforms.
    Provides convenience methods for common WorkPilot events (task
    completion, QA results, merge status, security alerts, budget alerts).

    Attributes:
        _slack_webhook_url: Slack Incoming Webhook URL, or None.
        _teams_webhook_url: Microsoft Teams Incoming Webhook URL, or None.
        _slack_channel: Default Slack channel override, or None.
        _delivery_log: History of delivery attempts.
        _enabled_channels: Set of enabled notification channels.
    """

    def __init__(
        self,
        slack_webhook_url: str | None = None,
        teams_webhook_url: str | None = None,
        slack_channel: str | None = None,
    ) -> None:
        """Initialize the notifications connector.

        Args:
            slack_webhook_url: Slack Incoming Webhook URL.
            teams_webhook_url: Microsoft Teams Incoming Webhook URL.
            slack_channel: Optional Slack channel override.

        Raises:
            NotificationConfigurationError: If no webhook URL is provided.
        """
        self._slack_webhook_url = slack_webhook_url
        self._teams_webhook_url = teams_webhook_url
        self._slack_channel = slack_channel
        self._delivery_log: list[NotificationResult] = []
        self._enabled_channels: set[NotificationChannel] = set()

        if slack_webhook_url:
            self._enabled_channels.add(NotificationChannel.SLACK)
        if teams_webhook_url:
            self._enabled_channels.add(NotificationChannel.TEAMS)

        if not self._enabled_channels:
            raise NotificationConfigurationError(
                "At least one webhook URL must be provided "
                "(SLACK_WEBHOOK_URL or TEAMS_WEBHOOK_URL)."
            )

    @classmethod
    def from_env(cls) -> "NotificationsConnector":
        """Create a connector from environment variables.

        Reads ``SLACK_WEBHOOK_URL``, ``TEAMS_WEBHOOK_URL``, and
        optionally ``SLACK_CHANNEL`` from the environment.

        Returns:
            A configured NotificationsConnector instance.

        Raises:
            NotificationConfigurationError: If no webhook URLs are set.
        """
        slack_url = os.environ.get("SLACK_WEBHOOK_URL")
        teams_url = os.environ.get("TEAMS_WEBHOOK_URL")
        slack_channel = os.environ.get("SLACK_CHANNEL")

        if not slack_url and not teams_url:
            raise NotificationConfigurationError(
                "No webhook URL configured. Set SLACK_WEBHOOK_URL "
                "and/or TEAMS_WEBHOOK_URL environment variables."
            )

        return cls(
            slack_webhook_url=slack_url,
            teams_webhook_url=teams_url,
            slack_channel=slack_channel,
        )

    # ------------------------------------------------------------------
    # Core delivery
    # ------------------------------------------------------------------

    def send(self, event: NotificationEvent) -> list[NotificationResult]:
        """Send a notification event to all configured (or specified) channels.

        Args:
            event: The notification event to deliver.

        Returns:
            A list of NotificationResult (one per target channel).
        """
        target_channels = (
            set(event.channels) if event.channels else self._enabled_channels
        )
        results: list[NotificationResult] = []

        for channel in target_channels:
            if channel not in self._enabled_channels:
                result = NotificationResult(
                    success=False,
                    channel=channel,
                    event_type=event.event_type,
                    error=f"Channel {channel.value} is not configured.",
                )
                results.append(result)
                self._delivery_log.append(result)
                continue

            try:
                if channel == NotificationChannel.SLACK:
                    result = self._send_slack(event)
                elif channel == NotificationChannel.TEAMS:
                    result = self._send_teams(event)
                else:
                    result = NotificationResult(
                        success=False,
                        channel=channel,
                        event_type=event.event_type,
                        error=f"Unknown channel: {channel.value}",
                    )
            except NotificationError as exc:
                result = NotificationResult(
                    success=False,
                    channel=channel,
                    event_type=event.event_type,
                    error=str(exc),
                )

            results.append(result)
            self._delivery_log.append(result)

        return results

    def _send_slack(self, event: NotificationEvent) -> NotificationResult:
        """Deliver a notification to Slack via Incoming Webhook.

        Args:
            event: The notification event.

        Returns:
            A NotificationResult.
        """
        if not self._slack_webhook_url:
            raise NotificationConfigurationError("Slack webhook URL not configured.")

        payload = event.to_slack_payload()
        if self._slack_channel:
            payload["channel"] = self._slack_channel

        status_code = self._http_post(self._slack_webhook_url, payload)

        return NotificationResult(
            success=200 <= status_code < 300,
            channel=NotificationChannel.SLACK,
            event_type=event.event_type,
            status_code=status_code,
        )

    def _send_teams(self, event: NotificationEvent) -> NotificationResult:
        """Deliver a notification to Microsoft Teams via Incoming Webhook.

        Args:
            event: The notification event.

        Returns:
            A NotificationResult.
        """
        if not self._teams_webhook_url:
            raise NotificationConfigurationError("Teams webhook URL not configured.")

        payload = event.to_teams_payload()
        status_code = self._http_post(self._teams_webhook_url, payload)

        return NotificationResult(
            success=200 <= status_code < 300,
            channel=NotificationChannel.TEAMS,
            event_type=event.event_type,
            status_code=status_code,
        )

    def _http_post(self, url: str, payload: dict[str, Any]) -> int:
        """Send an HTTP POST request with a JSON payload.

        Args:
            url: The webhook URL.
            payload: The JSON-serializable payload.

        Returns:
            The HTTP status code.

        Raises:
            NotificationDeliveryError: If the request fails.
        """
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status
        except urllib.error.HTTPError as exc:
            raise NotificationDeliveryError(
                message=f"HTTP error: {exc.reason}",
                status_code=exc.code,
            )
        except urllib.error.URLError as exc:
            raise NotificationDeliveryError(
                message=f"URL error: {exc.reason}",
            )
        except Exception as exc:
            raise NotificationDeliveryError(message=str(exc))

    # ------------------------------------------------------------------
    # Convenience methods for common WorkPilot events
    # ------------------------------------------------------------------

    def notify_task_completed(
        self, project_id: str, task_id: str, task_name: str
    ) -> list[NotificationResult]:
        """Send a 'task completed' notification.

        Args:
            project_id: The project identifier.
            task_id: The task identifier.
            task_name: The task name/title.

        Returns:
            Delivery results.
        """
        event = NotificationEvent(
            event_type=EventType.TASK_COMPLETED,
            title="Task Completed",
            message=f"Task *{task_name}* has been completed successfully.",
            priority=NotificationPriority.NORMAL,
            project_id=project_id,
            task_id=task_id,
        )
        return self.send(event)

    def notify_task_failed(
        self, project_id: str, task_id: str, task_name: str, error: str = ""
    ) -> list[NotificationResult]:
        """Send a 'task failed' notification.

        Args:
            project_id: The project identifier.
            task_id: The task identifier.
            task_name: The task name/title.
            error: Optional error message.

        Returns:
            Delivery results.
        """
        msg = f"Task *{task_name}* has failed."
        if error:
            msg += f"\n> {error}"
        event = NotificationEvent(
            event_type=EventType.TASK_FAILED,
            title="Task Failed",
            message=msg,
            priority=NotificationPriority.HIGH,
            project_id=project_id,
            task_id=task_id,
        )
        return self.send(event)

    def notify_qa_result(
        self, project_id: str, task_id: str, passed: bool, score: float = 0.0
    ) -> list[NotificationResult]:
        """Send a QA result notification.

        Args:
            project_id: The project identifier.
            task_id: The task identifier.
            passed: Whether QA passed.
            score: The quality score (0-100).

        Returns:
            Delivery results.
        """
        event_type = EventType.QA_PASSED if passed else EventType.QA_FAILED
        status = "passed" if passed else "failed"
        event = NotificationEvent(
            event_type=event_type,
            title=f"QA {status.capitalize()}",
            message=f"QA {status} for task `{task_id}` with score *{score:.0f}/100*.",
            priority=NotificationPriority.NORMAL if passed else NotificationPriority.HIGH,
            project_id=project_id,
            task_id=task_id,
            metadata={"score": score, "passed": passed},
        )
        return self.send(event)

    def notify_merge_success(
        self, project_id: str, task_id: str, branch: str = ""
    ) -> list[NotificationResult]:
        """Send a 'merge success' notification.

        Args:
            project_id: The project identifier.
            task_id: The task identifier.
            branch: The branch that was merged.

        Returns:
            Delivery results.
        """
        msg = f"Task `{task_id}` has been merged successfully."
        if branch:
            msg += f" (branch: `{branch}`)"
        event = NotificationEvent(
            event_type=EventType.MERGE_SUCCESS,
            title="Merge Successful",
            message=msg,
            priority=NotificationPriority.NORMAL,
            project_id=project_id,
            task_id=task_id,
        )
        return self.send(event)

    def notify_rate_limit(
        self, provider: str, retry_after: int = 0
    ) -> list[NotificationResult]:
        """Send a rate limit notification.

        Args:
            provider: The LLM provider that is rate-limited.
            retry_after: Seconds before retry, if known.

        Returns:
            Delivery results.
        """
        msg = f"Provider *{provider}* has hit its rate limit."
        if retry_after:
            msg += f" Retry in {retry_after}s."
        event = NotificationEvent(
            event_type=EventType.RATE_LIMIT,
            title="Rate Limit Reached",
            message=msg,
            priority=NotificationPriority.HIGH,
            metadata={"provider": provider, "retry_after": retry_after},
        )
        return self.send(event)

    def notify_security_alert(
        self, project_id: str, alert_message: str, severity: str = "high"
    ) -> list[NotificationResult]:
        """Send a security alert notification.

        Args:
            project_id: The project identifier.
            alert_message: Description of the security issue.
            severity: Alert severity ('low', 'medium', 'high', 'critical').

        Returns:
            Delivery results.
        """
        priority = NotificationPriority.URGENT if severity in ("high", "critical") else NotificationPriority.HIGH
        event = NotificationEvent(
            event_type=EventType.SECURITY_ALERT,
            title="Security Alert",
            message=alert_message,
            priority=priority,
            project_id=project_id,
            metadata={"severity": severity},
        )
        return self.send(event)

    def notify_budget_alert(
        self, project_id: str, message: str, level: str = "warning"
    ) -> list[NotificationResult]:
        """Send a budget alert notification.

        Args:
            project_id: The project identifier.
            message: The budget alert message.
            level: Alert level ('warning', 'critical', 'exceeded').

        Returns:
            Delivery results.
        """
        priority_map = {
            "warning": NotificationPriority.HIGH,
            "critical": NotificationPriority.URGENT,
            "exceeded": NotificationPriority.URGENT,
        }
        event = NotificationEvent(
            event_type=EventType.BUDGET_ALERT,
            title="Budget Alert",
            message=message,
            priority=priority_map.get(level, NotificationPriority.HIGH),
            project_id=project_id,
            metadata={"level": level},
        )
        return self.send(event)

    def send_daily_summary(self, summary: DailySummary) -> list[NotificationResult]:
        """Send a daily activity summary.

        Args:
            summary: The daily summary to deliver.

        Returns:
            Delivery results.
        """
        event = summary.to_notification_event()
        return self.send(event)

    # ------------------------------------------------------------------
    # Slash command handling
    # ------------------------------------------------------------------

    def handle_slash_command(self, command: SlashCommand) -> dict[str, Any]:
        """Process a slash command and return a response.

        Args:
            command: The parsed SlashCommand.

        Returns:
            A response dict suitable for sending back to Slack/Teams.
        """
        if not command.is_valid:
            return {
                "text": f"Unknown command: `{command.command}`. "
                f"Available commands: {', '.join(SlashCommand.SUPPORTED_COMMANDS)}",
            }

        if command.command == "help":
            return self._cmd_help()
        elif command.command == "status":
            return self._cmd_status()
        elif command.command == "create-task":
            return self._cmd_create_task(command.args)
        elif command.command == "list-tasks":
            return self._cmd_list_tasks()
        elif command.command == "budget":
            return self._cmd_budget(command.args)
        else:
            return {"text": f"Command `{command.command}` is recognized but not yet implemented."}

    def _cmd_help(self) -> dict[str, Any]:
        """Return help text for available commands."""
        return {
            "text": (
                "*WorkPilot AI — Available Commands:*\n"
                "• `/workpilot create-task \"description\"` — Create a new task\n"
                "• `/workpilot status` — Show project status\n"
                "• `/workpilot list-tasks` — List current tasks\n"
                "• `/workpilot budget [project_id]` — Show budget status\n"
                "• `/workpilot help` — Show this help message"
            ),
        }

    def _cmd_status(self) -> dict[str, Any]:
        """Return project status summary."""
        return {
            "text": (
                "*WorkPilot AI Status:*\n"
                f"• Configured channels: {', '.join(c.value for c in self._enabled_channels)}\n"
                f"• Notifications sent: {len(self._delivery_log)}\n"
                f"• Success rate: {self._success_rate():.0f}%"
            ),
        }

    def _cmd_create_task(self, args: str) -> dict[str, Any]:
        """Handle the create-task command."""
        task_desc = args.strip().strip('"').strip("'")
        if not task_desc:
            return {"text": "Usage: `/workpilot create-task \"task description\"`"}
        return {
            "text": f"Task creation requested: *{task_desc}*\n_Task will be created in WorkPilot AI._",
            "task_description": task_desc,
        }

    def _cmd_list_tasks(self) -> dict[str, Any]:
        """Handle the list-tasks command."""
        return {
            "text": "_Fetching tasks from WorkPilot AI..._\n"
            "Use the WorkPilot AI dashboard for full task management.",
        }

    def _cmd_budget(self, args: str) -> dict[str, Any]:
        """Handle the budget command."""
        project_id = args.strip() or "(default)"
        return {
            "text": f"_Fetching budget for project `{project_id}`..._\n"
            "Use the WorkPilot AI Cost Management page for detailed reports.",
        }

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def get_delivery_log(
        self,
        channel: NotificationChannel | None = None,
        success_only: bool = False,
    ) -> list[NotificationResult]:
        """Get the delivery log.

        Args:
            channel: Filter by channel.
            success_only: If True, only return successful deliveries.

        Returns:
            A list of NotificationResult objects.
        """
        results = self._delivery_log
        if channel:
            results = [r for r in results if r.channel == channel]
        if success_only:
            results = [r for r in results if r.success]
        return results

    def _success_rate(self) -> float:
        """Calculate the delivery success rate."""
        if not self._delivery_log:
            return 100.0
        successes = sum(1 for r in self._delivery_log if r.success)
        return (successes / len(self._delivery_log)) * 100

    def get_stats(self) -> dict[str, Any]:
        """Get connector statistics.

        Returns:
            Dict with ``'enabled_channels'``, ``'total_sent'``,
            ``'success_rate'``, ``'by_channel'``, ``'by_event_type'``.
        """
        by_channel: dict[str, int] = {}
        by_event_type: dict[str, int] = {}
        for r in self._delivery_log:
            by_channel[r.channel.value] = by_channel.get(r.channel.value, 0) + 1
            by_event_type[r.event_type.value] = by_event_type.get(r.event_type.value, 0) + 1

        return {
            "enabled_channels": [c.value for c in self._enabled_channels],
            "total_sent": len(self._delivery_log),
            "success_rate": self._success_rate(),
            "by_channel": by_channel,
            "by_event_type": by_event_type,
        }
