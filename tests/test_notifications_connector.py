"""Tests for Feature 4.3 — Intégration Slack / Microsoft Teams.

Tests for NotificationsConnector, NotificationEvent, SlashCommand,
DailySummary, models and exceptions.

45 tests total:
- Exceptions: 4
- NotificationEvent: 5
- NotificationResult: 2
- SlashCommand: 5
- DailySummary: 4
- NotificationsConnector init: 3
- NotificationsConnector delivery: 8
- NotificationsConnector convenience: 7
- NotificationsConnector slash commands: 5
- NotificationsConnector stats: 2
"""

import json
import sys
import importlib.util
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

import pytest

# S'assurer que la racine du projet est dans le chemin
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import direct des modules pour éviter les problèmes d'import imbriqués
def import_module_from_file(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Import des modules notifications
connectors_dir = project_root / "src" / "connectors" / "notifications"
notifications_exceptions = import_module_from_file("src.connectors.notifications.exceptions", connectors_dir / "exceptions.py")
notifications_models = import_module_from_file("src.connectors.notifications.models", connectors_dir / "models.py")
notifications_connector = import_module_from_file("src.connectors.notifications.connector", connectors_dir / "connector.py")

# Import des classes et fonctions
NotificationError = notifications_exceptions.NotificationError
NotificationAuthenticationError = notifications_exceptions.NotificationAuthenticationError
NotificationConfigurationError = notifications_exceptions.NotificationConfigurationError
NotificationDeliveryError = notifications_exceptions.NotificationDeliveryError

DailySummary = notifications_models.DailySummary
EventType = notifications_models.EventType
NotificationChannel = notifications_models.NotificationChannel
NotificationEvent = notifications_models.NotificationEvent
NotificationPriority = notifications_models.NotificationPriority
NotificationResult = notifications_models.NotificationResult
SlashCommand = notifications_models.SlashCommand

NotificationsConnector = notifications_connector.NotificationsConnector


# -----------------------------------------------------------------------
# Exceptions
# -----------------------------------------------------------------------

class TestExceptions:
    def test_notification_error(self):
        err = NotificationError("test error")
        assert "test error" in str(err)
        assert err.message == "test error"

    def test_authentication_error_inherits(self):
        err = NotificationAuthenticationError("auth failed")
        assert isinstance(err, NotificationError)

    def test_configuration_error_inherits(self):
        err = NotificationConfigurationError("missing config")
        assert isinstance(err, NotificationError)

    def test_delivery_error_with_status_code(self):
        err = NotificationDeliveryError("timeout", status_code=408, channel="slack")
        assert err.status_code == 408
        assert err.channel == "slack"
        assert "408" in str(err)
        assert "slack" in str(err)


# -----------------------------------------------------------------------
# NotificationEvent
# -----------------------------------------------------------------------

class TestNotificationEvent:
    def test_create_event(self):
        event = NotificationEvent(
            event_type=EventType.TASK_COMPLETED,
            title="Task Done",
            message="Task X completed",
        )
        assert event.event_type == EventType.TASK_COMPLETED
        assert event.title == "Task Done"

    def test_event_to_dict(self):
        event = NotificationEvent(
            event_type=EventType.QA_FAILED,
            title="QA Failed",
            message="Score: 45/100",
            priority=NotificationPriority.HIGH,
            project_id="p1",
        )
        d = event.to_dict()
        assert d["event_type"] == "qa_failed"
        assert d["priority"] == "high"
        assert d["project_id"] == "p1"

    def test_event_to_slack_payload(self):
        event = NotificationEvent(
            event_type=EventType.TASK_COMPLETED,
            title="Task Done",
            message="All good",
            project_id="p1",
            task_id="t1",
        )
        payload = event.to_slack_payload()
        assert "blocks" in payload
        assert "text" in payload
        assert len(payload["blocks"]) >= 2

    def test_event_to_teams_payload(self):
        event = NotificationEvent(
            event_type=EventType.MERGE_SUCCESS,
            title="Merge OK",
            message="Branch merged",
        )
        payload = event.to_teams_payload()
        assert payload["type"] == "message"
        assert len(payload["attachments"]) == 1
        card = payload["attachments"][0]["content"]
        assert card["type"] == "AdaptiveCard"

    def test_event_default_channels_empty(self):
        event = NotificationEvent(
            event_type=EventType.CUSTOM, title="X", message="Y",
        )
        assert event.channels == []


# -----------------------------------------------------------------------
# NotificationResult
# -----------------------------------------------------------------------

class TestNotificationResult:
    def test_create_result(self):
        result = NotificationResult(
            success=True,
            channel=NotificationChannel.SLACK,
            event_type=EventType.TASK_COMPLETED,
            status_code=200,
        )
        assert result.success is True
        assert result.channel == NotificationChannel.SLACK

    def test_result_to_dict(self):
        result = NotificationResult(
            success=False,
            channel=NotificationChannel.TEAMS,
            event_type=EventType.QA_FAILED,
            error="timeout",
        )
        d = result.to_dict()
        assert d["success"] is False
        assert d["channel"] == "teams"
        assert d["error"] == "timeout"


# -----------------------------------------------------------------------
# SlashCommand
# -----------------------------------------------------------------------

class TestSlashCommand:
    def test_parse_simple_command(self):
        cmd = SlashCommand.parse("status")
        assert cmd.command == "status"
        assert cmd.args == ""
        assert cmd.is_valid is True

    def test_parse_command_with_args(self):
        cmd = SlashCommand.parse('create-task "Fix the login bug"')
        assert cmd.command == "create-task"
        assert cmd.args == '"Fix the login bug"'
        assert cmd.is_valid is True

    def test_parse_command_with_slash_prefix(self):
        cmd = SlashCommand.parse("/help")
        assert cmd.command == "help"
        assert cmd.is_valid is True

    def test_invalid_command(self):
        cmd = SlashCommand.parse("unknown-cmd")
        assert cmd.is_valid is False

    def test_slash_command_to_dict(self):
        cmd = SlashCommand.parse("budget my-project", user_id="U123")
        d = cmd.to_dict()
        assert d["command"] == "budget"
        assert d["args"] == "my-project"
        assert d["user_id"] == "U123"
        assert d["is_valid"] is True


# -----------------------------------------------------------------------
# DailySummary
# -----------------------------------------------------------------------

class TestDailySummary:
    def test_create_summary(self):
        summary = DailySummary(
            project_id="p1", date="2026-02-20",
            tasks_completed=5, tasks_failed=1,
            qa_pass_rate=83.3, merges_successful=4,
            total_cost=2.50,
        )
        assert summary.tasks_completed == 5
        assert abs(summary.total_cost - 2.50) < 1e-9

    def test_summary_to_notification_event(self):
        summary = DailySummary(
            project_id="p1", date="2026-02-20",
            tasks_completed=3, highlights=["Feature X deployed"],
        )
        event = summary.to_notification_event()
        assert event.event_type == EventType.DAILY_SUMMARY
        assert "3" in event.message
        assert "Feature X deployed" in event.message

    def test_summary_to_dict(self):
        summary = DailySummary(project_id="p1", date="2026-02-20")
        d = summary.to_dict()
        assert d["project_id"] == "p1"
        assert d["date"] == "2026-02-20"

    def test_summary_with_highlights(self):
        summary = DailySummary(
            project_id="p1", date="2026-02-20",
            highlights=["Deployed v2.0", "Fixed critical bug"],
        )
        event = summary.to_notification_event()
        assert "Deployed v2.0" in event.message


# -----------------------------------------------------------------------
# NotificationsConnector — Init
# -----------------------------------------------------------------------

class TestConnectorInit:
    def test_init_with_slack(self):
        conn = NotificationsConnector(slack_webhook_url="https://hooks.slack.com/test")
        assert NotificationChannel.SLACK in conn._enabled_channels

    def test_init_with_teams(self):
        conn = NotificationsConnector(teams_webhook_url="https://outlook.webhook.office.com/test")
        assert NotificationChannel.TEAMS in conn._enabled_channels

    def test_init_no_webhook_raises(self):
        with pytest.raises(NotificationConfigurationError):
            NotificationsConnector()


# -----------------------------------------------------------------------
# NotificationsConnector — Delivery (mocked HTTP)
# -----------------------------------------------------------------------

class TestConnectorDelivery:
    def _make_connector(self):
        return NotificationsConnector(
            slack_webhook_url="https://hooks.slack.com/test",
            teams_webhook_url="https://outlook.webhook.office.com/test",
        )

    @patch.object(NotificationsConnector, "_http_post", return_value=200)
    def test_send_to_slack(self, mock_post):
        conn = self._make_connector()
        event = NotificationEvent(
            event_type=EventType.TASK_COMPLETED, title="Done", message="OK",
            channels=[NotificationChannel.SLACK],
        )
        results = conn.send(event)
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].channel == NotificationChannel.SLACK

    @patch.object(NotificationsConnector, "_http_post", return_value=200)
    def test_send_to_teams(self, mock_post):
        conn = self._make_connector()
        event = NotificationEvent(
            event_type=EventType.TASK_COMPLETED, title="Done", message="OK",
            channels=[NotificationChannel.TEAMS],
        )
        results = conn.send(event)
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].channel == NotificationChannel.TEAMS

    @patch.object(NotificationsConnector, "_http_post", return_value=200)
    def test_send_to_all_channels(self, mock_post):
        conn = self._make_connector()
        event = NotificationEvent(
            event_type=EventType.TASK_COMPLETED, title="Done", message="OK",
        )
        results = conn.send(event)
        assert len(results) == 2

    @patch.object(NotificationsConnector, "_http_post", side_effect=NotificationDeliveryError("timeout"))
    def test_send_failure_logged(self, mock_post):
        conn = self._make_connector()
        event = NotificationEvent(
            event_type=EventType.TASK_FAILED, title="Fail", message="Error",
            channels=[NotificationChannel.SLACK],
        )
        results = conn.send(event)
        assert len(results) == 1
        assert results[0].success is False

    @patch.object(NotificationsConnector, "_http_post", return_value=200)
    def test_delivery_log_updated(self, mock_post):
        conn = self._make_connector()
        event = NotificationEvent(
            event_type=EventType.TASK_COMPLETED, title="Done", message="OK",
            channels=[NotificationChannel.SLACK],
        )
        conn.send(event)
        log = conn.get_delivery_log()
        assert len(log) == 1

    @patch.object(NotificationsConnector, "_http_post", return_value=200)
    def test_delivery_log_filter_by_channel(self, mock_post):
        conn = self._make_connector()
        event = NotificationEvent(
            event_type=EventType.TASK_COMPLETED, title="Done", message="OK",
        )
        conn.send(event)
        slack_log = conn.get_delivery_log(channel=NotificationChannel.SLACK)
        assert len(slack_log) == 1

    @patch.object(NotificationsConnector, "_http_post", return_value=200)
    def test_delivery_log_success_only(self, mock_post):
        conn = self._make_connector()
        event = NotificationEvent(
            event_type=EventType.TASK_COMPLETED, title="Done", message="OK",
            channels=[NotificationChannel.SLACK],
        )
        conn.send(event)
        success_log = conn.get_delivery_log(success_only=True)
        assert len(success_log) == 1

    def test_send_to_unconfigured_channel(self):
        conn = NotificationsConnector(slack_webhook_url="https://hooks.slack.com/test")
        event = NotificationEvent(
            event_type=EventType.TASK_COMPLETED, title="Done", message="OK",
            channels=[NotificationChannel.TEAMS],
        )
        results = conn.send(event)
        assert len(results) == 1
        assert results[0].success is False
        assert "not configured" in results[0].error


# -----------------------------------------------------------------------
# NotificationsConnector — Convenience methods
# -----------------------------------------------------------------------

class TestConnectorConvenience:
    @patch.object(NotificationsConnector, "_http_post", return_value=200)
    def test_notify_task_completed(self, mock_post):
        conn = NotificationsConnector(slack_webhook_url="https://hooks.slack.com/test")
        results = conn.notify_task_completed("p1", "t1", "Login Feature")
        assert len(results) == 1
        assert results[0].success is True

    @patch.object(NotificationsConnector, "_http_post", return_value=200)
    def test_notify_task_failed(self, mock_post):
        conn = NotificationsConnector(slack_webhook_url="https://hooks.slack.com/test")
        results = conn.notify_task_failed("p1", "t1", "Login Feature", error="Timeout")
        assert len(results) == 1

    @patch.object(NotificationsConnector, "_http_post", return_value=200)
    def test_notify_qa_passed(self, mock_post):
        conn = NotificationsConnector(slack_webhook_url="https://hooks.slack.com/test")
        results = conn.notify_qa_result("p1", "t1", passed=True, score=95.0)
        assert results[0].event_type == EventType.QA_PASSED

    @patch.object(NotificationsConnector, "_http_post", return_value=200)
    def test_notify_qa_failed(self, mock_post):
        conn = NotificationsConnector(slack_webhook_url="https://hooks.slack.com/test")
        results = conn.notify_qa_result("p1", "t1", passed=False, score=30.0)
        assert results[0].event_type == EventType.QA_FAILED

    @patch.object(NotificationsConnector, "_http_post", return_value=200)
    def test_notify_merge_success(self, mock_post):
        conn = NotificationsConnector(slack_webhook_url="https://hooks.slack.com/test")
        results = conn.notify_merge_success("p1", "t1", branch="feature/login")
        assert results[0].success is True

    @patch.object(NotificationsConnector, "_http_post", return_value=200)
    def test_notify_rate_limit(self, mock_post):
        conn = NotificationsConnector(slack_webhook_url="https://hooks.slack.com/test")
        results = conn.notify_rate_limit("anthropic", retry_after=60)
        assert results[0].success is True

    @patch.object(NotificationsConnector, "_http_post", return_value=200)
    def test_notify_security_alert(self, mock_post):
        conn = NotificationsConnector(slack_webhook_url="https://hooks.slack.com/test")
        results = conn.notify_security_alert("p1", "CVE-2026-1234 found", severity="critical")
        assert results[0].success is True


# -----------------------------------------------------------------------
# NotificationsConnector — Slash commands
# -----------------------------------------------------------------------

class TestConnectorSlashCommands:
    def _make_connector(self):
        return NotificationsConnector(slack_webhook_url="https://hooks.slack.com/test")

    def test_handle_help(self):
        conn = self._make_connector()
        cmd = SlashCommand.parse("help")
        response = conn.handle_slash_command(cmd)
        assert "Available Commands" in response["text"]

    def test_handle_status(self):
        conn = self._make_connector()
        cmd = SlashCommand.parse("status")
        response = conn.handle_slash_command(cmd)
        assert "Status" in response["text"]

    def test_handle_create_task(self):
        conn = self._make_connector()
        cmd = SlashCommand.parse('create-task "Fix login bug"')
        response = conn.handle_slash_command(cmd)
        assert "Fix login bug" in response["text"]

    def test_handle_invalid_command(self):
        conn = self._make_connector()
        cmd = SlashCommand.parse("foobar")
        response = conn.handle_slash_command(cmd)
        assert "Unknown command" in response["text"]

    def test_handle_budget(self):
        conn = self._make_connector()
        cmd = SlashCommand.parse("budget my-project")
        response = conn.handle_slash_command(cmd)
        assert "my-project" in response["text"]


# -----------------------------------------------------------------------
# NotificationsConnector — Stats
# -----------------------------------------------------------------------

class TestConnectorStats:
    @patch.object(NotificationsConnector, "_http_post", return_value=200)
    def test_get_stats(self, mock_post):
        conn = NotificationsConnector(slack_webhook_url="https://hooks.slack.com/test")
        conn.notify_task_completed("p1", "t1", "Test")
        stats = conn.get_stats()
        assert stats["total_sent"] == 1
        assert "slack" in stats["by_channel"]

    def test_success_rate_no_deliveries(self):
        conn = NotificationsConnector(slack_webhook_url="https://hooks.slack.com/test")
        stats = conn.get_stats()
        assert stats["success_rate"] == 100
