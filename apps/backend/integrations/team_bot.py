"""
Team Bot — Slack / Microsoft Teams notification integration.
=============================================================

Sends structured notifications to Slack or Microsoft Teams via incoming
webhooks. Provider-agnostic: works with any AI backend because it only
reports events/metrics that originate from the WorkPilot runtime.

Notification types
------------------
- ``agent_started`` / ``agent_finished`` — lifecycle events
- ``cost_alert`` — when projected spend crosses a threshold
- ``guardrail_blocked`` — when a guardrail stops an agent action
- ``blast_radius_high`` — when a proposed change touches many files

All sends are best-effort: a failing webhook never blocks the caller.
"""

from __future__ import annotations

import json
import logging
import ssl
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

logger = logging.getLogger(__name__)

BotKind = Literal["slack", "teams"]
EventType = Literal[
    "agent_started",
    "agent_finished",
    "cost_alert",
    "guardrail_blocked",
    "blast_radius_high",
    "custom",
]


@dataclass
class TeamBotConfig:
    kind: BotKind
    webhook_url: str
    default_channel: str | None = None
    enabled: bool = True
    tags: list[str] = field(default_factory=list)


@dataclass
class NotificationPayload:
    event: EventType
    title: str
    summary: str
    fields: dict[str, Any] = field(default_factory=dict)
    severity: Literal["info", "warning", "critical"] = "info"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_SEVERITY_COLORS = {
    "info": "#4a90e2",
    "warning": "#f5a623",
    "critical": "#d0021b",
}


def _slack_body(payload: NotificationPayload) -> dict[str, Any]:
    fields = [
        {"title": k, "value": str(v), "short": True} for k, v in payload.fields.items()
    ]
    return {
        "text": payload.title,
        "attachments": [
            {
                "color": _SEVERITY_COLORS[payload.severity],
                "title": payload.title,
                "text": payload.summary,
                "fields": fields,
                "footer": f"WorkPilot AI · {payload.event}",
            },
        ],
    }


def _teams_body(payload: NotificationPayload) -> dict[str, Any]:
    facts = [{"name": k, "value": str(v)} for k, v in payload.fields.items()]
    return {
        "@type": "MessageCard",
        "@context": "https://schema.org/extensions",
        "themeColor": _SEVERITY_COLORS[payload.severity].lstrip("#"),
        "summary": payload.title,
        "title": payload.title,
        "text": payload.summary,
        "sections": [{"facts": facts}] if facts else [],
    }


def build_body(kind: BotKind, payload: NotificationPayload) -> dict[str, Any]:
    """Build provider-specific webhook JSON body."""
    if kind == "slack":
        return _slack_body(payload)
    if kind == "teams":
        return _teams_body(payload)
    raise ValueError(f"unknown bot kind: {kind}")


def send_notification(
    config: TeamBotConfig,
    payload: NotificationPayload,
    *,
    timeout: float = 5.0,
) -> bool:
    """POST a notification to the configured webhook.

    Returns ``True`` on success, ``False`` if the send failed or the bot is
    disabled. Never raises.
    """
    if not config.enabled:
        return False
    if not config.webhook_url:
        logger.warning("team_bot: empty webhook_url, skipping")
        return False

    body = build_body(config.kind, payload)
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(  # noqa: S310 — user-provided webhook, scheme validated below
        config.webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    if not config.webhook_url.startswith(("https://", "http://")):
        logger.warning("team_bot: invalid webhook scheme")
        return False

    try:
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:  # noqa: S310
            status = getattr(resp, "status", 200)
            return 200 <= int(status) < 300
    except (urllib.error.URLError, TimeoutError, ssl.SSLError) as exc:
        logger.warning("team_bot: delivery failed: %s", exc)
        return False
