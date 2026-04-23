"""Tests for the Self-Healing AlertManager delivery channels.

The Slack, email and GitHub channels were stubs until now. These tests
verify:

- Each channel is a no-op when its env vars aren't set (no exception,
  no network call).
- Slack: the webhook is called with a Slack-shaped payload including
  the right severity color.
- Email: SMTP.send_message is called with the expected headers.
- GitHub: ``gh issue create`` is invoked with the right arguments and
  a missing ``gh`` binary degrades gracefully.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_BACKEND = Path(__file__).resolve().parents[2] / "apps" / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from self_healing.alert_manager import (  # noqa: E402
    Alert,
    AlertLevel,
    AlertManager,
)


@pytest.fixture
def sample_alert() -> Alert:
    return Alert(
        level=AlertLevel.CRITICAL,
        title="Database latency",
        message="p95 latency exceeded 5s for 10 minutes.",
        health_score=42.0,
        score_change=-20.0,
        issue_count=3,
        actions_suggested=["Check DB pool", "Review recent migrations"],
    )


@pytest.fixture
def manager(tmp_path: Path) -> AlertManager:
    return AlertManager(tmp_path)


# ---------------------------------------------------------------------------
# Skip-when-unconfigured: every channel must no-op silently (no raise, no
# network) when its env vars are missing.
# ---------------------------------------------------------------------------


async def _run(coro):
    return await coro


def test_slack_skip_when_no_webhook(
    monkeypatch, manager: AlertManager, sample_alert: Alert
) -> None:
    monkeypatch.delenv("SELF_HEALING_SLACK_WEBHOOK", raising=False)
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    with patch("httpx.AsyncClient") as http:
        asyncio.run(manager._send_slack(sample_alert))
        http.assert_not_called()


def test_email_skip_when_no_smtp(
    monkeypatch, manager: AlertManager, sample_alert: Alert
) -> None:
    monkeypatch.delenv("SELF_HEALING_SMTP_HOST", raising=False)
    monkeypatch.delenv("SELF_HEALING_ALERT_TO", raising=False)
    with patch("smtplib.SMTP") as smtp:
        asyncio.run(manager._send_email(sample_alert))
        smtp.assert_not_called()


def test_github_skip_when_no_repo(
    monkeypatch, manager: AlertManager, sample_alert: Alert
) -> None:
    monkeypatch.delenv("SELF_HEALING_GITHUB_REPO", raising=False)
    with patch("subprocess.run") as run:
        asyncio.run(manager._send_github_issue(sample_alert))
        run.assert_not_called()


# ---------------------------------------------------------------------------
# Slack channel.
# ---------------------------------------------------------------------------


def test_slack_posts_to_webhook(
    monkeypatch, manager: AlertManager, sample_alert: Alert
) -> None:
    monkeypatch.setenv(
        "SELF_HEALING_SLACK_WEBHOOK", "https://hooks.slack.example/T/B/X"
    )

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        asyncio.run(manager._send_slack(sample_alert))

    mock_client.post.assert_awaited_once()
    call = mock_client.post.await_args
    assert call.args[0] == "https://hooks.slack.example/T/B/X"
    payload = call.kwargs["json"]
    assert payload["attachments"][0]["color"] == "#e63946"  # critical
    assert "Database latency" in payload["attachments"][0]["title"]
    # Structured fields surface the alert context.
    field_titles = {f["title"] for f in payload["attachments"][0]["fields"]}
    assert {"Health score", "Issues", "Suggested actions"}.issubset(field_titles)


def test_slack_network_error_does_not_raise(
    monkeypatch, manager: AlertManager, sample_alert: Alert
) -> None:
    monkeypatch.setenv(
        "SELF_HEALING_SLACK_WEBHOOK", "https://hooks.slack.example/T/B/X"
    )

    async def _raise(*a, **kw):
        raise RuntimeError("boom")

    mock_client = MagicMock()
    mock_client.post = AsyncMock(side_effect=RuntimeError("boom"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        # Must not raise — an alert failing to post should never break the
        # coroutine that triggered it.
        asyncio.run(manager._send_slack(sample_alert))


# ---------------------------------------------------------------------------
# Email channel.
# ---------------------------------------------------------------------------


def test_email_sends_via_smtp(
    monkeypatch, manager: AlertManager, sample_alert: Alert
) -> None:
    monkeypatch.setenv("SELF_HEALING_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SELF_HEALING_SMTP_PORT", "587")
    monkeypatch.setenv("SELF_HEALING_SMTP_USER", "alerts@example.com")
    monkeypatch.setenv("SELF_HEALING_SMTP_PASSWORD", "secret")
    monkeypatch.setenv("SELF_HEALING_ALERT_FROM", "alerts@example.com")
    monkeypatch.setenv("SELF_HEALING_ALERT_TO", "oncall@example.com")

    mock_smtp_instance = MagicMock()
    mock_smtp_instance.__enter__ = MagicMock(return_value=mock_smtp_instance)
    mock_smtp_instance.__exit__ = MagicMock(return_value=None)

    with patch("smtplib.SMTP", return_value=mock_smtp_instance) as smtp_ctor:
        asyncio.run(manager._send_email(sample_alert))

    smtp_ctor.assert_called_once_with("smtp.example.com", 587, timeout=10)
    mock_smtp_instance.login.assert_called_once_with(
        "alerts@example.com", "secret"
    )
    mock_smtp_instance.send_message.assert_called_once()
    msg = mock_smtp_instance.send_message.call_args.args[0]
    assert msg["To"] == "oncall@example.com"
    assert msg["From"] == "alerts@example.com"
    assert "[CRITICAL]" in msg["Subject"]
    assert "Database latency" in msg["Subject"]


# ---------------------------------------------------------------------------
# GitHub channel.
# ---------------------------------------------------------------------------


def test_github_invokes_gh_cli(
    monkeypatch, manager: AlertManager, sample_alert: Alert
) -> None:
    monkeypatch.setenv("SELF_HEALING_GITHUB_REPO", "acme/demo")

    completed = MagicMock(returncode=0, stdout="https://github.com/…", stderr="")
    with patch("subprocess.run", return_value=completed) as run:
        asyncio.run(manager._send_github_issue(sample_alert))

    assert run.call_count == 1
    args = run.call_args.args[0]
    assert args[:4] == ["gh", "issue", "create", "--repo"]
    assert "acme/demo" in args
    assert "--title" in args
    title_idx = args.index("--title")
    assert "Database latency" in args[title_idx + 1]
    assert "--label" in args
    label_idx = args.index("--label")
    assert args[label_idx + 1] == "self-healing:critical"


def test_github_missing_gh_cli_is_tolerated(
    monkeypatch, manager: AlertManager, sample_alert: Alert
) -> None:
    monkeypatch.setenv("SELF_HEALING_GITHUB_REPO", "acme/demo")
    with patch("subprocess.run", side_effect=FileNotFoundError()):
        # No raise, no crash — just a logged warning.
        asyncio.run(manager._send_github_issue(sample_alert))


def test_github_gh_failure_is_tolerated(
    monkeypatch, manager: AlertManager, sample_alert: Alert
) -> None:
    monkeypatch.setenv("SELF_HEALING_GITHUB_REPO", "acme/demo")
    completed = MagicMock(
        returncode=1, stdout="", stderr="not authenticated"
    )
    with patch("subprocess.run", return_value=completed):
        asyncio.run(manager._send_github_issue(sample_alert))
