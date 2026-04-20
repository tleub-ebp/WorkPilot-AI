"""Team Bot Runner — JSON stdout wrapper for Slack/Teams notifications.

Actions:
  - ``send``: post a notification payload to a webhook
  - ``test``: send a canned "hello from WorkPilot" payload (no LLM)

Payload shape (via --payload JSON):
  send:
    { "config": {...TeamBotConfig...}, "payload": {...NotificationPayload...} }
  test:
    { "config": {...TeamBotConfig...} }
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from integrations.team_bot import (
    NotificationPayload,
    TeamBotConfig,
    send_notification,
)


def _build_config(d: dict[str, Any]) -> TeamBotConfig:
    return TeamBotConfig(
        kind=d["kind"],
        webhook_url=d["webhook_url"],
        default_channel=d.get("default_channel"),
        enabled=bool(d.get("enabled", True)),
        tags=list(d.get("tags", [])),
    )


def _build_payload(d: dict[str, Any]) -> NotificationPayload:
    return NotificationPayload(
        event=d.get("event", "custom"),
        title=d["title"],
        summary=d.get("summary", ""),
        fields=dict(d.get("fields", {})),
        severity=d.get("severity", "info"),
    )


def main() -> int:
    parser = argparse.ArgumentParser(prog="team_bot_runner")
    parser.add_argument("--action", required=True, choices=["send", "test"])
    parser.add_argument("--payload", default="{}")
    args = parser.parse_args()

    try:
        data = json.loads(args.payload)
        config = _build_config(data["config"])
        if args.action == "send":
            payload = _build_payload(data["payload"])
        else:
            payload = NotificationPayload(
                event="custom",
                title="WorkPilot test notification",
                summary="If you can read this, your webhook is wired correctly.",
                severity="info",
                fields={"source": "team_bot_runner"},
            )
        ok = send_notification(config, payload)
        sys.stdout.write(json.dumps({"ok": bool(ok)}) + "\n")
        return 0 if ok else 2
    except Exception as exc:  # noqa: BLE001
        sys.stdout.write(json.dumps({"error": str(exc)}) + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
