"""
Alert Manager
=============

Manages alerts for health degradation and critical issues.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

try:
    from debug import debug, debug_section, debug_warning
except ImportError:

    def debug(module: str, message: str, **kwargs):
        pass

    def debug_section(module: str, message: str):
        pass

    def debug_warning(module: str, message: str, **kwargs):
        pass


class AlertLevel(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Represents an alert."""

    level: AlertLevel
    title: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)

    # Context
    health_score: float | None = None
    score_change: float | None = None
    issue_count: int = 0

    # Actions
    actions_suggested: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "level": self.level.value,
            "title": self.title,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "health_score": self.health_score,
            "score_change": self.score_change,
            "issue_count": self.issue_count,
            "actions_suggested": self.actions_suggested,
        }

    def format_console(self) -> str:
        """Format for console output."""
        emoji = {
            AlertLevel.INFO: "ℹ️",
            AlertLevel.WARNING: "⚠️",
            AlertLevel.CRITICAL: "🚨",
        }

        lines = [
            f"\n{emoji[self.level]} {self.level.value.upper()}: {self.title}",
            f"Time: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"\n{self.message}",
        ]

        if self.health_score is not None:
            lines.append(f"\nHealth Score: {self.health_score:.1f}/100")

        if self.score_change is not None:
            change_sign = "+" if self.score_change >= 0 else ""
            lines.append(f"Change: {change_sign}{self.score_change:.1f}")

        if self.issue_count:
            lines.append(f"Issues Found: {self.issue_count}")

        if self.actions_suggested:
            lines.append("\nSuggested Actions:")
            for action in self.actions_suggested:
                lines.append(f"  - {action}")

        return "\n".join(lines)


class AlertManager:
    """Manages and sends alerts."""

    def __init__(self, project_dir: str | Path):
        self.project_dir = Path(project_dir)
        self.alert_history: list[Alert] = []

    async def send_alert(
        self,
        alert: Alert,
        channels: list[str] | None = None,
    ) -> None:
        """Send an alert through configured channels."""
        debug_section("alerts", f"🔔 Sending {alert.level.value.upper()} Alert")

        # Store in history
        self.alert_history.append(alert)

        # Default to console
        if not channels:
            channels = ["console"]

        # Send to each channel
        for channel in channels:
            await self._send_to_channel(alert, channel)

    async def _send_to_channel(self, alert: Alert, channel: str) -> None:
        """Send alert to a specific channel."""
        try:
            if channel == "console":
                print(alert.format_console())

            elif channel == "email":
                await self._send_email(alert)

            elif channel == "slack":
                await self._send_slack(alert)

            elif channel == "github":
                await self._send_github_issue(alert)

            else:
                debug_warning("self_healing", f"Unknown alert channel: {channel}")

        except Exception as e:
            debug_warning("self_healing", f"Failed to send alert to {channel}: {e}")

    async def _send_email(self, alert: Alert) -> None:
        """Send alert via email."""
        # TODO: Implement email sending
        # Would use SMTP configuration from environment
        debug("self_healing", "Email alerts not yet configured")

    async def _send_slack(self, alert: Alert) -> None:
        """Send alert to Slack."""
        # TODO: Implement Slack webhook
        debug("self_healing", "Slack alerts not yet configured")

    async def _send_github_issue(self, alert: Alert) -> None:
        """Create a GitHub issue for the alert."""
        # TODO: Implement GitHub API integration
        debug("self_healing", "GitHub issue creation not yet configured")

    def get_recent_alerts(self, count: int = 10) -> list[Alert]:
        """Get recent alerts."""
        return self.alert_history[-count:]

    def get_critical_alerts(self) -> list[Alert]:
        """Get all critical alerts."""
        return [
            alert for alert in self.alert_history if alert.level == AlertLevel.CRITICAL
        ]

    def clear_history(self) -> None:
        """Clear alert history."""
        self.alert_history.clear()
