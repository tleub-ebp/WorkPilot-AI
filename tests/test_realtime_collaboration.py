"""Tests for Feature 3.1 — Mode multi-utilisateurs en temps réel.

Tests: ConnectedUser (3), TaskLock (3), RealtimeEvent (3), ChatMessage (2),
       ConflictRecord (2), CollaborationServer — users (7), locks (8),
       task updates (4), chat (4), conflicts (3), events (4),
       agent integration (3), sync (2), stats (2) = 50 tests.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

# Load the module directly from file to avoid teams/__init__.py
# which pulls heavy dependencies (claude_agent_sdk)
_spec = importlib.util.spec_from_file_location(
    "realtime_collaboration",
    Path(__file__).resolve().parent.parent / "apps" / "backend" / "teams" / "realtime_collaboration.py",
)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["realtime_collaboration"] = _mod
_spec.loader.exec_module(_mod)

ChatMessage = _mod.ChatMessage
CollaborationServer = _mod.CollaborationServer
ConflictRecord = _mod.ConflictRecord
ConflictResolution = _mod.ConflictResolution
ConnectedUser = _mod.ConnectedUser
EventType = _mod.EventType
LockType = _mod.LockType
RealtimeEvent = _mod.RealtimeEvent
TaskLock = _mod.TaskLock
UserStatus = _mod.UserStatus


# ---------------------------------------------------------------------------
# Data model tests
# ---------------------------------------------------------------------------

class TestConnectedUser:
    def test_create_user(self):
        user = ConnectedUser(user_id="u-1", display_name="Alice")
        assert user.status == UserStatus.ONLINE
        assert user.connected_at != ""
        assert user.role == "developer"

    def test_to_dict(self):
        user = ConnectedUser(user_id="u-1", display_name="Alice", role="lead")
        d = user.to_dict()
        assert d["user_id"] == "u-1"
        assert d["status"] == "online"

    def test_status_from_string(self):
        user = ConnectedUser(user_id="u-1", display_name="Alice", status="busy")
        assert user.status == UserStatus.BUSY


class TestTaskLock:
    def test_create_lock(self):
        lock = TaskLock(task_id="t-1", locked_by="u-1", lock_type="user")
        assert lock.lock_type == LockType.USER
        assert not lock.is_agent_lock
        assert lock.locked_at != ""

    def test_agent_lock(self):
        lock = TaskLock(task_id="t-1", locked_by="agent:coder", lock_type="agent")
        assert lock.is_agent_lock

    def test_to_dict(self):
        lock = TaskLock(task_id="t-1", locked_by="u-1", lock_type="user", reason="editing")
        d = lock.to_dict()
        assert d["lock_type"] == "user"
        assert d["reason"] == "editing"


class TestRealtimeEvent:
    def test_create_event(self):
        event = RealtimeEvent(
            event_id="evt-1", event_type=EventType.USER_JOINED,
            sender_id="u-1", data={"user_id": "u-1"},
        )
        assert event.is_broadcast
        assert event.timestamp != ""

    def test_targeted_event(self):
        event = RealtimeEvent(
            event_id="evt-1", event_type=EventType.NOTIFICATION,
            sender_id="system", target_users=["u-1"],
        )
        assert not event.is_broadcast

    def test_to_dict(self):
        event = RealtimeEvent(
            event_id="evt-1", event_type="task_updated",
            sender_id="u-1", data={"task_id": "t-1"},
        )
        d = event.to_dict()
        assert d["event_type"] == "task_updated"


class TestChatMessage:
    def test_create_message(self):
        msg = ChatMessage(
            message_id="msg-1", sender_id="u-1",
            sender_name="Alice", content="Hello!",
        )
        assert msg.timestamp != ""
        assert msg.reply_to == ""

    def test_to_dict(self):
        msg = ChatMessage(
            message_id="msg-1", sender_id="u-1",
            sender_name="Alice", content="Hello!", mentions=["u-2"],
        )
        d = msg.to_dict()
        assert d["mentions"] == ["u-2"]


class TestConflictRecord:
    def test_create_conflict(self):
        conflict = ConflictRecord(
            conflict_id="cfl-1", task_id="t-1",
            user_a="u-1", user_b="u-2",
            field_name="status", value_a="done", value_b="in_progress",
        )
        assert conflict.resolution == ConflictResolution.MANUAL
        assert not conflict.resolved

    def test_to_dict(self):
        conflict = ConflictRecord(
            conflict_id="cfl-1", task_id="t-1",
            user_a="u-1", user_b="u-2",
            field_name="title", value_a="A", value_b="B",
            resolution="last_write_wins",
        )
        d = conflict.to_dict()
        assert d["resolution"] == "last_write_wins"


# ---------------------------------------------------------------------------
# CollaborationServer — User management
# ---------------------------------------------------------------------------

class TestServerUserManagement:
    def test_connect_user(self):
        server = CollaborationServer(project_id="proj-1")
        user = server.connect_user("u-1", "Alice")
        assert user.user_id == "u-1"
        assert user.status == UserStatus.ONLINE
        assert len(server.get_connected_users()) == 1

    def test_connect_user_twice_reconnects(self):
        server = CollaborationServer()
        server.connect_user("u-1", "Alice")
        server.disconnect_user("u-1")
        user = server.connect_user("u-1", "Alice")
        assert user.status == UserStatus.ONLINE

    def test_disconnect_user(self):
        server = CollaborationServer()
        server.connect_user("u-1", "Alice")
        assert server.disconnect_user("u-1")
        online = server.get_connected_users()
        assert len(online) == 0

    def test_disconnect_nonexistent_user(self):
        server = CollaborationServer()
        assert not server.disconnect_user("u-99")

    def test_get_all_users_includes_offline(self):
        server = CollaborationServer()
        server.connect_user("u-1", "Alice")
        server.connect_user("u-2", "Bob")
        server.disconnect_user("u-1")
        assert len(server.get_all_users()) == 2
        assert len(server.get_connected_users()) == 1

    def test_update_user_status(self):
        server = CollaborationServer()
        server.connect_user("u-1", "Alice")
        assert server.update_user_status("u-1", "busy")
        user = server._users["u-1"]
        assert user.status == UserStatus.BUSY

    def test_set_user_current_task(self):
        server = CollaborationServer()
        server.connect_user("u-1", "Alice")
        assert server.set_user_current_task("u-1", "t-42")
        assert server._users["u-1"].current_task == "t-42"


# ---------------------------------------------------------------------------
# CollaborationServer — Task locking
# ---------------------------------------------------------------------------

class TestServerTaskLocking:
    def test_lock_task(self):
        server = CollaborationServer()
        server.connect_user("u-1", "Alice")
        lock = server.lock_task("t-1", "u-1")
        assert lock is not None
        assert lock.task_id == "t-1"
        assert lock.locked_by == "u-1"

    def test_lock_task_already_locked_by_other(self):
        server = CollaborationServer()
        server.lock_task("t-1", "u-1")
        lock = server.lock_task("t-1", "u-2")
        assert lock is None

    def test_lock_task_same_user_returns_existing(self):
        server = CollaborationServer()
        lock1 = server.lock_task("t-1", "u-1")
        lock2 = server.lock_task("t-1", "u-1")
        assert lock2 is lock1

    def test_unlock_task(self):
        server = CollaborationServer()
        server.lock_task("t-1", "u-1")
        assert server.unlock_task("t-1", "u-1")
        assert not server.is_task_locked("t-1")

    def test_unlock_by_wrong_user_fails(self):
        server = CollaborationServer()
        server.lock_task("t-1", "u-1")
        assert not server.unlock_task("t-1", "u-2")
        assert server.is_task_locked("t-1")

    def test_force_unlock_task(self):
        server = CollaborationServer()
        server.lock_task("t-1", "u-1")
        assert server.force_unlock_task("t-1", "admin")
        assert not server.is_task_locked("t-1")

    def test_disconnect_releases_locks(self):
        server = CollaborationServer()
        server.connect_user("u-1", "Alice")
        server.lock_task("t-1", "u-1")
        server.lock_task("t-2", "u-1")
        server.disconnect_user("u-1")
        assert not server.is_task_locked("t-1")
        assert not server.is_task_locked("t-2")

    def test_get_all_locks(self):
        server = CollaborationServer()
        server.lock_task("t-1", "u-1")
        server.lock_task("t-2", "u-2")
        locks = server.get_all_locks()
        assert len(locks) == 2


# ---------------------------------------------------------------------------
# CollaborationServer — Task updates
# ---------------------------------------------------------------------------

class TestServerTaskUpdates:
    def test_broadcast_task_update(self):
        server = CollaborationServer()
        event = server.broadcast_task_update("t-1", {"status": "done"}, "u-1")
        assert event.event_type == EventType.TASK_UPDATED
        assert event.data["task_id"] == "t-1"
        assert event.data["version"] == 1

    def test_task_version_increments(self):
        server = CollaborationServer()
        server.broadcast_task_update("t-1", {"status": "pending"})
        server.broadcast_task_update("t-1", {"status": "done"})
        events = server.get_events(event_type="task_updated")
        assert events[-1].data["version"] == 2

    def test_broadcast_task_move(self):
        server = CollaborationServer()
        event = server.broadcast_task_move("t-1", "todo", "in_progress", "u-1")
        assert event.event_type == EventType.TASK_MOVED
        assert event.data["from_column"] == "todo"

    def test_multiple_tasks_independent_versions(self):
        server = CollaborationServer()
        server.broadcast_task_update("t-1", {"x": 1})
        server.broadcast_task_update("t-2", {"x": 1})
        server.broadcast_task_update("t-1", {"x": 2})
        assert server._task_versions["t-1"] == 2
        assert server._task_versions["t-2"] == 1


# ---------------------------------------------------------------------------
# CollaborationServer — Chat
# ---------------------------------------------------------------------------

class TestServerChat:
    def test_send_chat_message(self):
        server = CollaborationServer()
        server.connect_user("u-1", "Alice")
        msg = server.send_chat_message("u-1", "Hello!")
        assert msg is not None
        assert msg.sender_name == "Alice"
        assert msg.content == "Hello!"

    def test_send_chat_disconnected_user(self):
        server = CollaborationServer()
        msg = server.send_chat_message("u-99", "Hello!")
        assert msg is None

    def test_get_chat_history(self):
        server = CollaborationServer()
        server.connect_user("u-1", "Alice")
        for i in range(5):
            server.send_chat_message("u-1", f"Message {i}")
        history = server.get_chat_history(limit=3)
        assert len(history) == 3
        assert history[-1].content == "Message 4"

    def test_search_chat(self):
        server = CollaborationServer()
        server.connect_user("u-1", "Alice")
        server.send_chat_message("u-1", "Working on login feature")
        server.send_chat_message("u-1", "Bug fix ready")
        server.send_chat_message("u-1", "Login tests passing")
        results = server.search_chat("login")
        assert len(results) == 2


# ---------------------------------------------------------------------------
# CollaborationServer — Conflicts
# ---------------------------------------------------------------------------

class TestServerConflicts:
    def test_detect_conflict(self):
        server = CollaborationServer()
        server.broadcast_task_update("t-1", {"status": "pending"})
        server.broadcast_task_update("t-1", {"status": "done"})
        conflict = server.detect_conflict("t-1", "u-1", "status", "in_progress",
                                           expected_version=1)
        assert conflict is not None
        assert conflict.task_id == "t-1"

    def test_no_conflict_when_version_matches(self):
        server = CollaborationServer()
        server.broadcast_task_update("t-1", {"status": "pending"})
        conflict = server.detect_conflict("t-1", "u-1", "status", "done",
                                           expected_version=1)
        assert conflict is None

    def test_resolve_conflict(self):
        server = CollaborationServer()
        server.broadcast_task_update("t-1", {"s": "a"})
        server.broadcast_task_update("t-1", {"s": "b"})
        conflict = server.detect_conflict("t-1", "u-1", "s", "c", expected_version=1)
        assert server.resolve_conflict(conflict.conflict_id, "merged_value")
        resolved = server.get_conflicts(resolved=True)
        assert len(resolved) == 1
        assert resolved[0].resolved_value == "merged_value"


# ---------------------------------------------------------------------------
# CollaborationServer — Events
# ---------------------------------------------------------------------------

class TestServerEvents:
    def test_event_listener(self):
        server = CollaborationServer()
        received = []
        server.on_event("user_joined", lambda e: received.append(e))
        server.connect_user("u-1", "Alice")
        assert len(received) == 1
        assert received[0].event_type == EventType.USER_JOINED

    def test_wildcard_listener(self):
        server = CollaborationServer()
        received = []
        server.on_event("*", lambda e: received.append(e))
        server.connect_user("u-1", "Alice")
        server.lock_task("t-1", "u-1")
        assert len(received) >= 2

    def test_get_events_filtered(self):
        server = CollaborationServer()
        server.connect_user("u-1", "Alice")
        server.broadcast_task_update("t-1", {"x": 1}, "u-1")
        events = server.get_events(event_type="task_updated")
        assert len(events) == 1

    def test_get_events_by_sender(self):
        server = CollaborationServer()
        server.connect_user("u-1", "Alice")
        server.broadcast_task_update("t-1", {"x": 1}, "u-1")
        server.broadcast_task_update("t-2", {"x": 1}, "u-2")
        events = server.get_events(sender_id="u-1")
        assert all(e.sender_id == "u-1" for e in events)


# ---------------------------------------------------------------------------
# CollaborationServer — Agent integration
# ---------------------------------------------------------------------------

class TestServerAgentIntegration:
    def test_notify_agent_started_locks_task(self):
        server = CollaborationServer()
        server.notify_agent_started("t-1", "coder")
        assert server.is_task_locked("t-1")
        lock = server.get_lock("t-1")
        assert lock.is_agent_lock

    def test_notify_agent_completed_unlocks_task(self):
        server = CollaborationServer()
        server.notify_agent_started("t-1", "coder")
        server.notify_agent_completed("t-1", "coder", success=True)
        assert not server.is_task_locked("t-1")

    def test_agent_events_emitted(self):
        server = CollaborationServer()
        server.notify_agent_started("t-1", "qa")
        server.notify_agent_completed("t-1", "qa")
        started = server.get_events(event_type="agent_started")
        completed = server.get_events(event_type="agent_completed")
        assert len(started) == 1
        assert len(completed) == 1


# ---------------------------------------------------------------------------
# CollaborationServer — Sync & Notifications
# ---------------------------------------------------------------------------

class TestServerSync:
    def test_request_sync(self):
        server = CollaborationServer(project_id="proj-1")
        server.connect_user("u-1", "Alice")
        server.lock_task("t-1", "u-1")
        server.send_chat_message("u-1", "Hello")
        sync = server.request_sync("u-1")
        assert sync["project_id"] == "proj-1"
        assert len(sync["users"]) == 1
        assert len(sync["locks"]) == 1
        assert len(sync["chat_history"]) >= 1

    def test_notify_user(self):
        server = CollaborationServer()
        event = server.notify_user("u-1", "Task completed!")
        assert event.event_type == EventType.NOTIFICATION
        assert event.target_users == ["u-1"]


# ---------------------------------------------------------------------------
# CollaborationServer — Stats
# ---------------------------------------------------------------------------

class TestServerStats:
    def test_get_stats_empty(self):
        server = CollaborationServer(project_id="proj-1")
        stats = server.get_stats()
        assert stats["project_id"] == "proj-1"
        assert stats["total_users"] == 0
        assert stats["online_users"] == 0

    def test_get_stats_with_data(self):
        server = CollaborationServer(project_id="proj-1")
        server.connect_user("u-1", "Alice")
        server.connect_user("u-2", "Bob")
        server.lock_task("t-1", "u-1")
        server.notify_agent_started("t-2", "coder")
        server.send_chat_message("u-1", "Hello")
        stats = server.get_stats()
        assert stats["total_users"] == 2
        assert stats["online_users"] == 2
        assert stats["active_locks"] == 2
        assert stats["agent_locks"] == 1
        assert stats["chat_messages"] == 1
