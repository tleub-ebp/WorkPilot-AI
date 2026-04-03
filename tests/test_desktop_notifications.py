"""Tests for Feature 9.3 — Enriched Native Desktop Notifications.

40 tests covering:
- NotificationAction: 2
- DesktopNotification: 3
- PeriodicSummary: 3
- NotificationPreferences: 3
- Task completed notifications: 3
- Task failed notifications: 2
- QA result notifications: 3
- Rate limit notifications: 2
- Merge ready notifications: 2
- Security alert notifications: 1
- Budget alert notifications: 1
- Custom notifications: 2
- Periodic summaries: 3
- Action handling: 2
- Mark read: 2
- Queries & filters: 3
- Dispatch callback: 1
- Stats: 2
"""

import pytest

from apps.backend.ui.desktop_notifications import (
    DesktopNotification,
    DesktopNotificationManager,
    NotificationAction,
    NotificationPreferences,
    NotificationType,
    PeriodicSummary,
)

# ---------------------------------------------------------------------------
# NotificationAction tests (2)
# ---------------------------------------------------------------------------

class TestNotificationAction:
    def test_creation(self):
        a = NotificationAction(action_type="approve_merge", label="Approve")
        assert a.action_type == "approve_merge"
        assert a.label == "Approve"

    def test_to_dict(self):
        a = NotificationAction(action_type="retry_task", label="Retry")
        d = a.to_dict()
        assert d["action_type"] == "retry_task"


# ---------------------------------------------------------------------------
# DesktopNotification tests (3)
# ---------------------------------------------------------------------------

class TestDesktopNotification:
    def test_creation_defaults(self):
        n = DesktopNotification(title="Test", body="Body")
        assert n.read is False
        assert n.clicked is False
        assert n.notification_id

    def test_to_dict(self):
        n = DesktopNotification(title="T", body="B", notification_type="task_completed")
        d = n.to_dict()
        assert d["title"] == "T"
        assert d["notification_type"] == "task_completed"

    def test_to_electron_payload(self):
        n = DesktopNotification(
            title="Test",
            body="Body",
            icon="check-circle",
            priority="urgent",
            actions=[NotificationAction(action_type="view_details", label="View")],
        )
        payload = n.to_electron_payload()
        assert payload["title"] == "Test"
        assert payload["urgency"] == "critical"
        assert len(payload["actions"]) == 1


# ---------------------------------------------------------------------------
# PeriodicSummary tests (3)
# ---------------------------------------------------------------------------

class TestPeriodicSummary:
    def test_creation(self):
        s = PeriodicSummary(tasks_completed=5, tasks_failed=1)
        assert s.tasks_completed == 5
        assert s.period == "hourly"

    def test_to_dict(self):
        s = PeriodicSummary(qa_pass_rate=88.0)
        d = s.to_dict()
        assert d["qa_pass_rate"] == 88.0

    def test_to_notification_body(self):
        s = PeriodicSummary(tasks_completed=3, tasks_failed=1, qa_pass_rate=75.0, total_cost=1.5)
        body = s.to_notification_body()
        assert "3 completed" in body
        assert "1 failed" in body
        assert "$1.50" in body


# ---------------------------------------------------------------------------
# NotificationPreferences tests (3)
# ---------------------------------------------------------------------------

class TestNotificationPreferences:
    def test_defaults(self):
        p = NotificationPreferences()
        assert p.enabled is True
        assert p.task_completed is True

    def test_to_dict(self):
        p = NotificationPreferences(enabled=False)
        d = p.to_dict()
        assert d["enabled"] is False

    def test_quiet_hours(self):
        p = NotificationPreferences(quiet_hours_start=22, quiet_hours_end=8)
        # is_quiet_hours depends on current time, just verify it's callable
        result = p.is_quiet_hours()
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# Task completed notifications (3)
# ---------------------------------------------------------------------------

class TestTaskCompleted:
    def test_basic_notification(self):
        mgr = DesktopNotificationManager(project_id="proj")
        notif = mgr.notify_task_completed("t1", "Login page")
        assert notif is not None
        assert notif.notification_type == "task_completed"
        assert "Login page" in notif.body

    def test_with_duration(self):
        mgr = DesktopNotificationManager()
        notif = mgr.notify_task_completed("t1", "API", duration_s=300)
        assert "5min" in notif.body

    def test_disabled_preference(self):
        prefs = NotificationPreferences(task_completed=False)
        mgr = DesktopNotificationManager(preferences=prefs)
        notif = mgr.notify_task_completed("t1", "API")
        assert notif is None


# ---------------------------------------------------------------------------
# Task failed notifications (2)
# ---------------------------------------------------------------------------

class TestTaskFailed:
    def test_basic_notification(self):
        mgr = DesktopNotificationManager()
        notif = mgr.notify_task_failed("t1", "Login", error="Timeout")
        assert notif.notification_type == "task_failed"
        assert "Timeout" in notif.body

    def test_has_retry_action(self):
        mgr = DesktopNotificationManager()
        notif = mgr.notify_task_failed("t1", "Login")
        action_types = [a.action_type for a in notif.actions]
        assert "retry_task" in action_types


# ---------------------------------------------------------------------------
# QA result notifications (3)
# ---------------------------------------------------------------------------

class TestQAResult:
    def test_qa_passed(self):
        mgr = DesktopNotificationManager()
        notif = mgr.notify_qa_result("t1", passed=True, score=92.5)
        assert notif.notification_type == "qa_passed"
        assert "92.5" in notif.body

    def test_qa_failed(self):
        mgr = DesktopNotificationManager()
        notif = mgr.notify_qa_result("t1", passed=False, score=45.0)
        assert notif.notification_type == "qa_failed"
        action_types = [a.action_type for a in notif.actions]
        assert "rerun_qa" in action_types

    def test_qa_with_task_title(self):
        mgr = DesktopNotificationManager()
        notif = mgr.notify_qa_result("t1", passed=True, score=80, task_title="Login")
        assert "Login" in notif.body


# ---------------------------------------------------------------------------
# Rate limit notifications (2)
# ---------------------------------------------------------------------------

class TestRateLimit:
    def test_basic(self):
        mgr = DesktopNotificationManager()
        notif = mgr.notify_rate_limit("anthropic", "claude-sonnet", retry_after_s=120)
        assert notif.notification_type == "rate_limit"
        assert "120s" in notif.body

    def test_has_switch_action(self):
        mgr = DesktopNotificationManager()
        notif = mgr.notify_rate_limit("openai", "gpt-4o")
        action_types = [a.action_type for a in notif.actions]
        assert "switch_provider" in action_types


# ---------------------------------------------------------------------------
# Merge ready notifications (2)
# ---------------------------------------------------------------------------

class TestMergeReady:
    def test_basic(self):
        mgr = DesktopNotificationManager()
        notif = mgr.notify_merge_ready("t1", "Login page")
        assert notif.notification_type == "merge_ready"
        assert "Login page" in notif.body

    def test_with_branch(self):
        mgr = DesktopNotificationManager()
        notif = mgr.notify_merge_ready("t1", "API", branch="feature/api")
        assert "feature/api" in notif.body


# ---------------------------------------------------------------------------
# Security alert (1)
# ---------------------------------------------------------------------------

class TestSecurityAlert:
    def test_basic(self):
        mgr = DesktopNotificationManager()
        notif = mgr.notify_security_alert("XSS Found", "Input not sanitized")
        assert notif.notification_type == "security_alert"
        assert "XSS Found" in notif.title


# ---------------------------------------------------------------------------
# Budget alert (1)
# ---------------------------------------------------------------------------

class TestBudgetAlert:
    def test_basic(self):
        mgr = DesktopNotificationManager()
        notif = mgr.notify_budget_alert(37.50, 50.0, 75.0)
        assert "75%" in notif.body
        assert "$37.50" in notif.body


# ---------------------------------------------------------------------------
# Custom notifications (2)
# ---------------------------------------------------------------------------

class TestCustomNotification:
    def test_basic(self):
        mgr = DesktopNotificationManager()
        notif = mgr.notify_custom("Hello", "World")
        assert notif.notification_type == "custom"
        assert notif.title == "Hello"

    def test_with_priority(self):
        mgr = DesktopNotificationManager()
        notif = mgr.notify_custom("Alert", "Important", priority="urgent")
        assert notif.priority == "urgent"


# ---------------------------------------------------------------------------
# Periodic summaries (3)
# ---------------------------------------------------------------------------

class TestPeriodicSummaryCreation:
    def test_create_summary(self):
        mgr = DesktopNotificationManager()
        mgr.notify_task_completed("t1", "A")
        mgr.notify_task_completed("t2", "B")
        mgr.notify_task_failed("t3", "C")
        summary = mgr.create_periodic_summary()
        assert summary.tasks_completed == 2
        assert summary.tasks_failed == 1

    def test_summary_resets_counters(self):
        mgr = DesktopNotificationManager()
        mgr.notify_task_completed("t1", "A")
        mgr.create_periodic_summary()
        summary2 = mgr.create_periodic_summary()
        assert summary2.tasks_completed == 0

    def test_record_token_usage(self):
        mgr = DesktopNotificationManager()
        mgr.record_token_usage(5000, 0.05)
        mgr.record_token_usage(3000, 0.03)
        summary = mgr.create_periodic_summary()
        assert summary.total_tokens == 8000
        assert summary.total_cost == pytest.approx(0.08)


# ---------------------------------------------------------------------------
# Action handling (2)
# ---------------------------------------------------------------------------

class TestActionHandling:
    def test_handle_action_with_handler(self):
        mgr = DesktopNotificationManager()
        mgr.register_action_handler("view_details", lambda n: "opened")
        notif = mgr.notify_task_completed("t1", "Test")
        result = mgr.handle_action(notif.notification_id, "view_details")
        assert result["success"] is True

    def test_handle_action_no_handler(self):
        mgr = DesktopNotificationManager()
        notif = mgr.notify_task_completed("t1", "Test")
        result = mgr.handle_action(notif.notification_id, "view_details")
        assert result["result"] == "no_handler"


# ---------------------------------------------------------------------------
# Mark read (2)
# ---------------------------------------------------------------------------

class TestMarkRead:
    def test_mark_single_read(self):
        mgr = DesktopNotificationManager()
        notif = mgr.notify_task_completed("t1", "A")
        assert mgr.get_unread_count() == 1
        mgr.mark_read(notif.notification_id)
        assert mgr.get_unread_count() == 0

    def test_mark_all_read(self):
        mgr = DesktopNotificationManager()
        mgr.notify_task_completed("t1", "A")
        mgr.notify_task_completed("t2", "B")
        count = mgr.mark_all_read()
        assert count == 2
        assert mgr.get_unread_count() == 0


# ---------------------------------------------------------------------------
# Queries & filters (3)
# ---------------------------------------------------------------------------

class TestQueries:
    def test_get_notifications_filtered(self):
        mgr = DesktopNotificationManager()
        mgr.notify_task_completed("t1", "A")
        mgr.notify_task_failed("t2", "B")
        completed = mgr.get_notifications(notification_type="task_completed")
        assert len(completed) == 1

    def test_unread_only(self):
        mgr = DesktopNotificationManager()
        n1 = mgr.notify_task_completed("t1", "A")
        mgr.notify_task_completed("t2", "B")
        mgr.mark_read(n1.notification_id)
        unread = mgr.get_notifications(unread_only=True)
        assert len(unread) == 1

    def test_get_summaries(self):
        mgr = DesktopNotificationManager()
        mgr.create_periodic_summary()
        mgr.create_periodic_summary()
        assert len(mgr.get_summaries()) == 2


# ---------------------------------------------------------------------------
# Dispatch callback (1)
# ---------------------------------------------------------------------------

class TestDispatchCallback:
    def test_callback_called(self):
        dispatched = []
        mgr = DesktopNotificationManager()
        mgr.set_dispatch_callback(lambda payload: dispatched.append(payload))
        mgr.notify_task_completed("t1", "Test")
        assert len(dispatched) == 1
        assert dispatched[0]["title"] == "Task Completed"


# ---------------------------------------------------------------------------
# Stats (2)
# ---------------------------------------------------------------------------

class TestStats:
    def test_basic_stats(self):
        mgr = DesktopNotificationManager()
        mgr.notify_task_completed("t1", "A")
        mgr.notify_task_failed("t2", "B")
        stats = mgr.get_stats()
        assert stats["total_notifications"] == 2
        assert stats["unread_count"] == 2

    def test_type_counts(self):
        mgr = DesktopNotificationManager()
        mgr.notify_task_completed("t1", "A")
        mgr.notify_task_completed("t2", "B")
        mgr.notify_task_failed("t3", "C")
        stats = mgr.get_stats()
        assert stats["type_counts"]["task_completed"] == 2
        assert stats["type_counts"]["task_failed"] == 1
