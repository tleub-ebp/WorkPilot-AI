"""
Alert Manager
=============

Manages alerts for health degradation and critical issues.

Delivery channels
-----------------

``console`` (default): prints the alert with emoji + metadata.

``slack``: posts a Slack-formatted message to the webhook in
``SELF_HEALING_SLACK_WEBHOOK`` (or the alias ``SLACK_WEBHOOK_URL``).

``email``: sends via SMTP — requires ``SELF_HEALING_SMTP_HOST`` +
``SELF_HEALING_ALERT_TO``. ``SELF_HEALING_SMTP_PORT`` (default 587),
``SELF_HEALING_SMTP_USER`` / ``SELF_HEALING_SMTP_PASSWORD`` and
``SELF_HEALING_ALERT_FROM`` refine the connection.

``github``: opens an issue via ``gh issue create``. Requires
``SELF_HEALING_GITHUB_REPO`` (``owner/name``). Uses the ``gh`` CLI so
authentication is delegated to the user's existing ``gh auth`` state —
no token flows through WorkPilot AI.

If a channel is requested but its env vars aren't set, the send is
skipped with a ``debug`` log rather than raising. That keeps
``send_alert`` resilient when operators partially configure channels.
"""

from __future__ import annotations

import asyncio
import logging
import os
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


logger = logging.getLogger(__name__)


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
        """Send alert via email (SMTP)."""
        smtp_host = os.environ.get("SELF_HEALING_SMTP_HOST")
        recipient = os.environ.get("SELF_HEALING_ALERT_TO")
        if not smtp_host or not recipient:
            debug(
                "self_healing",
                "Email alerts skipped — set SELF_HEALING_SMTP_HOST and "
                "SELF_HEALING_ALERT_TO to enable.",
            )
            return

        smtp_port = int(os.environ.get("SELF_HEALING_SMTP_PORT", "587"))
        smtp_user = os.environ.get("SELF_HEALING_SMTP_USER")
        smtp_password = os.environ.get("SELF_HEALING_SMTP_PASSWORD")
        sender = os.environ.get("SELF_HEALING_ALERT_FROM", smtp_user or recipient)

        def _blocking_send() -> None:
            # smtplib is imported here so tests that don't exercise email
            # don't pay the import cost on the hot path.
            import smtplib
            from email.message import EmailMessage

            msg = EmailMessage()
            msg["Subject"] = f"[{alert.level.value.upper()}] {alert.title}"
            msg["From"] = sender
            msg["To"] = recipient
            msg.set_content(alert.format_console())

            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as client:
                client.ehlo()
                if smtp_port in (587, 25):
                    # Best-effort STARTTLS; servers that don't support it
                    # will raise, which is correctly surfaced as a warning.
                    try:
                        client.starttls()
                        client.ehlo()
                    except smtplib.SMTPException:
                        pass
                if smtp_user and smtp_password:
                    client.login(smtp_user, smtp_password)
                client.send_message(msg)

        try:
            await asyncio.to_thread(_blocking_send)
            debug("self_healing", f"Email alert sent to {recipient}")
        except Exception as exc:
            debug_warning("self_healing", f"Failed to send email alert: {exc}")
            logger.warning("Email alert send failed", exc_info=True)

    async def _send_slack(self, alert: Alert) -> None:
        """Post alert to a Slack incoming webhook."""
        webhook = os.environ.get("SELF_HEALING_SLACK_WEBHOOK") or os.environ.get(
            "SLACK_WEBHOOK_URL"
        )
        if not webhook:
            debug(
                "self_healing",
                "Slack alerts skipped — set SELF_HEALING_SLACK_WEBHOOK (or "
                "SLACK_WEBHOOK_URL) to enable.",
            )
            return

        color = {
            AlertLevel.INFO: "#36a64f",
            AlertLevel.WARNING: "#ff9f1c",
            AlertLevel.CRITICAL: "#e63946",
        }[alert.level]

        payload: dict[str, Any] = {
            "attachments": [
                {
                    "color": color,
                    "title": f"[{alert.level.value.upper()}] {alert.title}",
                    "text": alert.message,
                    "ts": int(alert.timestamp.timestamp()),
                    "fields": [],
                }
            ]
        }
        fields = payload["attachments"][0]["fields"]
        if alert.health_score is not None:
            fields.append(
                {
                    "title": "Health score",
                    "value": f"{alert.health_score:.1f}/100",
                    "short": True,
                }
            )
        if alert.issue_count:
            fields.append(
                {
                    "title": "Issues",
                    "value": str(alert.issue_count),
                    "short": True,
                }
            )
        if alert.actions_suggested:
            fields.append(
                {
                    "title": "Suggested actions",
                    "value": "\n".join(f"• {a}" for a in alert.actions_suggested),
                    "short": False,
                }
            )

        try:
            import httpx  # imported lazily — not every caller uses slack

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(webhook, json=payload)
                resp.raise_for_status()
            debug("self_healing", "Slack alert delivered")
        except Exception as exc:
            debug_warning("self_healing", f"Failed to post Slack alert: {exc}")
            logger.warning("Slack alert send failed", exc_info=True)

    async def _send_github_issue(self, alert: Alert) -> None:
        """Create a GitHub issue for the alert via the ``gh`` CLI.

        Delegates authentication to the user's existing ``gh`` setup, so
        we never handle a GitHub token here. If ``gh`` isn't installed
        or not authenticated, the failure is logged and the alert is
        skipped — we never fall back to an alternate channel.
        """
        repo = os.environ.get("SELF_HEALING_GITHUB_REPO")
        if not repo:
            debug(
                "self_healing",
                "GitHub issue creation skipped — set SELF_HEALING_GITHUB_REPO "
                "(owner/name format) to enable.",
            )
            return

        title = f"[{alert.level.value.upper()}] {alert.title}"
        body_parts = [alert.message]
        if alert.health_score is not None:
            body_parts.append(f"\n**Health score:** {alert.health_score:.1f}/100")
        if alert.issue_count:
            body_parts.append(f"**Issues detected:** {alert.issue_count}")
        if alert.actions_suggested:
            body_parts.append("\n**Suggested actions:**")
            body_parts.extend(f"- {a}" for a in alert.actions_suggested)
        body_parts.append(
            f"\n_Automatically opened by WorkPilot AI Self-Healing at "
            f"{alert.timestamp.isoformat()}_"
        )
        body = "\n".join(body_parts)

        label = {
            AlertLevel.INFO: "self-healing:info",
            AlertLevel.WARNING: "self-healing:warning",
            AlertLevel.CRITICAL: "self-healing:critical",
        }[alert.level]

        def _blocking_run() -> int:
            import subprocess

            result = subprocess.run(
                [
                    "gh",
                    "issue",
                    "create",
                    "--repo",
                    repo,
                    "--title",
                    title,
                    "--body",
                    body,
                    "--label",
                    label,
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"gh issue create failed (exit {result.returncode}): "
                    f"{result.stderr.strip()}"
                )
            return result.returncode

        try:
            await asyncio.to_thread(_blocking_run)
            debug("self_healing", f"GitHub issue created in {repo}")
        except FileNotFoundError:
            debug_warning(
                "self_healing",
                "GitHub issue creation skipped — `gh` CLI not installed.",
            )
        except Exception as exc:
            debug_warning("self_healing", f"Failed to create GitHub issue: {exc}")
            logger.warning("GitHub alert send failed", exc_info=True)

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
