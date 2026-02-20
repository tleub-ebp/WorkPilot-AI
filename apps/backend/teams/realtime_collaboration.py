"""Real-time Multi-User Collaboration — Enable multiple developers to work simultaneously.

Provides WebSocket-based real-time synchronization of Kanban board state, user presence
tracking, automatic task locking when agents are working, real-time notifications,
and integrated team chat.

Feature 3.1 — Mode multi-utilisateurs en temps réel.

Example:
    >>> from apps.backend.teams.realtime_collaboration import CollaborationServer
    >>> server = CollaborationServer(project_id="proj-1")
    >>> server.connect_user("user-1", "Alice", role="developer")
    >>> server.connect_user("user-2", "Bob", role="developer")
    >>> server.lock_task("task-42", "user-1")
    >>> server.broadcast_task_update("task-42", {"status": "in_progress"})
    >>> server.send_chat_message("user-1", "Starting work on login feature")
"""

import json
import logging
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class UserStatus(str, Enum):
    """Online status of a connected user."""
    ONLINE = "online"
    AWAY = "away"
    BUSY = "busy"
    OFFLINE = "offline"


class EventType(str, Enum):
    """Types of real-time events."""
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    USER_STATUS_CHANGED = "user_status_changed"
    TASK_UPDATED = "task_updated"
    TASK_LOCKED = "task_locked"
    TASK_UNLOCKED = "task_unlocked"
    TASK_CREATED = "task_created"
    TASK_DELETED = "task_deleted"
    TASK_MOVED = "task_moved"
    CHAT_MESSAGE = "chat_message"
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    NOTIFICATION = "notification"
    CONFLICT_DETECTED = "conflict_detected"
    SYNC_REQUEST = "sync_request"
    SYNC_RESPONSE = "sync_response"


class LockType(str, Enum):
    """Type of lock on a task."""
    USER = "user"
    AGENT = "agent"


class ConflictResolution(str, Enum):
    """Strategy for resolving concurrent modification conflicts."""
    LAST_WRITE_WINS = "last_write_wins"
    FIRST_WRITE_WINS = "first_write_wins"
    MANUAL = "manual"
    MERGE = "merge"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class ConnectedUser:
    """A user currently connected to the collaboration session."""
    user_id: str
    display_name: str
    role: str = "developer"
    status: UserStatus = UserStatus.ONLINE
    current_task: str = ""
    connected_at: str = ""
    last_activity: str = ""
    cursor_position: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        now = datetime.now(timezone.utc).isoformat()
        if not self.connected_at:
            self.connected_at = now
        if not self.last_activity:
            self.last_activity = now
        if isinstance(self.status, str):
            self.status = UserStatus(self.status)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class TaskLock:
    """A lock on a task preventing concurrent modification."""
    task_id: str
    locked_by: str
    lock_type: LockType
    locked_at: str = ""
    reason: str = ""
    expires_at: str = ""

    def __post_init__(self):
        if not self.locked_at:
            self.locked_at = datetime.now(timezone.utc).isoformat()
        if isinstance(self.lock_type, str):
            self.lock_type = LockType(self.lock_type)

    @property
    def is_agent_lock(self) -> bool:
        return self.lock_type == LockType.AGENT

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["lock_type"] = self.lock_type.value
        return d


@dataclass
class RealtimeEvent:
    """An event in the real-time event stream."""
    event_id: str
    event_type: EventType
    sender_id: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    target_users: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if isinstance(self.event_type, str):
            self.event_type = EventType(self.event_type)

    @property
    def is_broadcast(self) -> bool:
        """If no target_users, event is broadcast to all."""
        return len(self.target_users) == 0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["event_type"] = self.event_type.value
        return d


@dataclass
class ChatMessage:
    """A chat message in the team chat."""
    message_id: str
    sender_id: str
    sender_name: str
    content: str
    timestamp: str = ""
    reply_to: str = ""
    mentions: list[str] = field(default_factory=list)
    attachments: list[dict[str, str]] = field(default_factory=list)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ConflictRecord:
    """Record of a concurrent modification conflict."""
    conflict_id: str
    task_id: str
    user_a: str
    user_b: str
    field_name: str
    value_a: Any
    value_b: Any
    resolution: ConflictResolution = ConflictResolution.MANUAL
    resolved: bool = False
    resolved_value: Any = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if isinstance(self.resolution, str):
            self.resolution = ConflictResolution(self.resolution)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["resolution"] = self.resolution.value
        return d


# ---------------------------------------------------------------------------
# CollaborationServer
# ---------------------------------------------------------------------------

class CollaborationServer:
    """Real-time collaboration server managing users, events, locks, and chat.

    Args:
        project_id: The project identifier.
        conflict_strategy: Default conflict resolution strategy.
        max_chat_history: Maximum chat messages to retain in memory.
    """

    def __init__(
        self,
        project_id: str = "",
        conflict_strategy: str = "last_write_wins",
        max_chat_history: int = 500,
    ):
        self.project_id = project_id
        self.conflict_strategy = ConflictResolution(conflict_strategy)
        self.max_chat_history = max_chat_history

        self._users: dict[str, ConnectedUser] = {}
        self._locks: dict[str, TaskLock] = {}
        self._events: list[RealtimeEvent] = []
        self._chat_messages: deque[ChatMessage] = deque(maxlen=max_chat_history)
        self._conflicts: list[ConflictRecord] = []
        self._task_versions: dict[str, int] = {}
        self._event_listeners: dict[str, list[Callable]] = {}
        self._event_counter = 0
        self._msg_counter = 0
        self._conflict_counter = 0

    def _next_event_id(self) -> str:
        self._event_counter += 1
        return f"evt-{self._event_counter:06d}"

    def _next_msg_id(self) -> str:
        self._msg_counter += 1
        return f"msg-{self._msg_counter:06d}"

    def _next_conflict_id(self) -> str:
        self._conflict_counter += 1
        return f"cfl-{self._conflict_counter:04d}"

    # -- User management ----------------------------------------------------

    def connect_user(
        self,
        user_id: str,
        display_name: str,
        role: str = "developer",
    ) -> ConnectedUser:
        """Connect a user to the collaboration session.

        Args:
            user_id: Unique user identifier.
            display_name: Display name of the user.
            role: User's role (developer, lead, viewer, etc.).

        Returns:
            ConnectedUser object.
        """
        if user_id in self._users:
            user = self._users[user_id]
            user.status = UserStatus.ONLINE
            user.last_activity = datetime.now(timezone.utc).isoformat()
            return user

        user = ConnectedUser(
            user_id=user_id,
            display_name=display_name,
            role=role,
        )
        self._users[user_id] = user

        self._emit_event(EventType.USER_JOINED, user_id, {
            "user_id": user_id,
            "display_name": display_name,
            "role": role,
        })
        logger.info("User %s (%s) connected to project %s", display_name, user_id, self.project_id)
        return user

    def disconnect_user(self, user_id: str) -> bool:
        """Disconnect a user and release their locks.

        Args:
            user_id: The user to disconnect.

        Returns:
            True if user was connected.
        """
        if user_id not in self._users:
            return False

        # Release all locks held by this user
        locks_to_release = [tid for tid, lock in self._locks.items()
                            if lock.locked_by == user_id]
        for task_id in locks_to_release:
            self.unlock_task(task_id, user_id)

        user = self._users[user_id]
        user.status = UserStatus.OFFLINE
        user.current_task = ""

        self._emit_event(EventType.USER_LEFT, user_id, {
            "user_id": user_id,
            "display_name": user.display_name,
        })
        logger.info("User %s disconnected from project %s", user_id, self.project_id)
        return True

    def get_connected_users(self) -> list[ConnectedUser]:
        """Get all currently online users."""
        return [u for u in self._users.values() if u.status != UserStatus.OFFLINE]

    def get_all_users(self) -> list[ConnectedUser]:
        """Get all users (including offline)."""
        return list(self._users.values())

    def update_user_status(self, user_id: str, status: str) -> bool:
        """Update a user's online status."""
        if user_id not in self._users:
            return False
        self._users[user_id].status = UserStatus(status)
        self._users[user_id].last_activity = datetime.now(timezone.utc).isoformat()
        self._emit_event(EventType.USER_STATUS_CHANGED, user_id, {
            "user_id": user_id,
            "status": status,
        })
        return True

    def set_user_current_task(self, user_id: str, task_id: str) -> bool:
        """Set which task a user is currently working on (presence indicator)."""
        if user_id not in self._users:
            return False
        self._users[user_id].current_task = task_id
        self._users[user_id].last_activity = datetime.now(timezone.utc).isoformat()
        return True

    # -- Task locking -------------------------------------------------------

    def lock_task(
        self,
        task_id: str,
        locked_by: str,
        lock_type: str = "user",
        reason: str = "",
    ) -> TaskLock | None:
        """Lock a task to prevent concurrent modification.

        Args:
            task_id: The task to lock.
            locked_by: The user or agent ID requesting the lock.
            lock_type: 'user' or 'agent'.
            reason: Optional reason for the lock.

        Returns:
            TaskLock if successful, None if already locked by someone else.
        """
        if task_id in self._locks:
            existing = self._locks[task_id]
            if existing.locked_by != locked_by:
                logger.warning("Task %s already locked by %s", task_id, existing.locked_by)
                return None
            return existing  # Already locked by same user

        lock = TaskLock(
            task_id=task_id,
            locked_by=locked_by,
            lock_type=lock_type,
            reason=reason,
        )
        self._locks[task_id] = lock

        self._emit_event(EventType.TASK_LOCKED, locked_by, {
            "task_id": task_id,
            "locked_by": locked_by,
            "lock_type": lock_type,
            "reason": reason,
        })
        return lock

    def unlock_task(self, task_id: str, unlocked_by: str) -> bool:
        """Unlock a task.

        Args:
            task_id: The task to unlock.
            unlocked_by: The user or agent releasing the lock.

        Returns:
            True if the task was unlocked.
        """
        if task_id not in self._locks:
            return False

        lock = self._locks[task_id]
        if lock.locked_by != unlocked_by:
            logger.warning("User %s cannot unlock task %s locked by %s",
                           unlocked_by, task_id, lock.locked_by)
            return False

        del self._locks[task_id]
        self._emit_event(EventType.TASK_UNLOCKED, unlocked_by, {
            "task_id": task_id,
            "unlocked_by": unlocked_by,
        })
        return True

    def force_unlock_task(self, task_id: str, admin_id: str) -> bool:
        """Force-unlock a task (admin action)."""
        if task_id not in self._locks:
            return False
        del self._locks[task_id]
        self._emit_event(EventType.TASK_UNLOCKED, admin_id, {
            "task_id": task_id,
            "unlocked_by": admin_id,
            "forced": True,
        })
        return True

    def get_lock(self, task_id: str) -> TaskLock | None:
        """Get the lock on a task, if any."""
        return self._locks.get(task_id)

    def get_all_locks(self) -> list[TaskLock]:
        """Get all active locks."""
        return list(self._locks.values())

    def is_task_locked(self, task_id: str) -> bool:
        """Check if a task is locked."""
        return task_id in self._locks

    # -- Task updates (Kanban sync) -----------------------------------------

    def broadcast_task_update(
        self,
        task_id: str,
        changes: dict[str, Any],
        sender_id: str = "system",
    ) -> RealtimeEvent:
        """Broadcast a task update to all connected users.

        Args:
            task_id: The task that was updated.
            changes: Dict of changed fields and their new values.
            sender_id: Who made the change.

        Returns:
            The emitted event.
        """
        version = self._task_versions.get(task_id, 0) + 1
        self._task_versions[task_id] = version

        return self._emit_event(EventType.TASK_UPDATED, sender_id, {
            "task_id": task_id,
            "changes": changes,
            "version": version,
        })

    def broadcast_task_move(
        self,
        task_id: str,
        from_column: str,
        to_column: str,
        sender_id: str = "system",
    ) -> RealtimeEvent:
        """Broadcast a task column change (Kanban drag-and-drop)."""
        return self._emit_event(EventType.TASK_MOVED, sender_id, {
            "task_id": task_id,
            "from_column": from_column,
            "to_column": to_column,
        })

    # -- Conflict detection -------------------------------------------------

    def detect_conflict(
        self,
        task_id: str,
        user_id: str,
        field_name: str,
        new_value: Any,
        expected_version: int = 0,
    ) -> ConflictRecord | None:
        """Detect if a concurrent modification conflict exists.

        Args:
            task_id: The task being modified.
            user_id: The user making the modification.
            field_name: The field being changed.
            new_value: The new value for the field.
            expected_version: The version the user is editing from.

        Returns:
            ConflictRecord if conflict detected, None otherwise.
        """
        current_version = self._task_versions.get(task_id, 0)
        if expected_version > 0 and current_version > expected_version:
            conflict = ConflictRecord(
                conflict_id=self._next_conflict_id(),
                task_id=task_id,
                user_a=user_id,
                user_b="unknown",
                field_name=field_name,
                value_a=new_value,
                value_b=None,
                resolution=self.conflict_strategy,
            )
            self._conflicts.append(conflict)

            self._emit_event(EventType.CONFLICT_DETECTED, "system", {
                "conflict_id": conflict.conflict_id,
                "task_id": task_id,
                "field": field_name,
            }, target_users=[user_id])

            return conflict
        return None

    def resolve_conflict(self, conflict_id: str, resolved_value: Any) -> bool:
        """Resolve a detected conflict."""
        for conflict in self._conflicts:
            if conflict.conflict_id == conflict_id:
                conflict.resolved = True
                conflict.resolved_value = resolved_value
                return True
        return False

    def get_conflicts(self, resolved: bool | None = None) -> list[ConflictRecord]:
        """Get conflict records."""
        results = list(self._conflicts)
        if resolved is not None:
            results = [c for c in results if c.resolved == resolved]
        return results

    # -- Chat ---------------------------------------------------------------

    def send_chat_message(
        self,
        sender_id: str,
        content: str,
        reply_to: str = "",
        mentions: list[str] | None = None,
    ) -> ChatMessage | None:
        """Send a chat message in the team chat.

        Args:
            sender_id: The user sending the message.
            content: The message content.
            reply_to: Optional message ID to reply to.
            mentions: Optional list of mentioned user IDs.

        Returns:
            ChatMessage if user is connected, None otherwise.
        """
        if sender_id not in self._users:
            return None

        user = self._users[sender_id]
        msg = ChatMessage(
            message_id=self._next_msg_id(),
            sender_id=sender_id,
            sender_name=user.display_name,
            content=content,
            reply_to=reply_to,
            mentions=mentions or [],
        )
        self._chat_messages.append(msg)

        self._emit_event(EventType.CHAT_MESSAGE, sender_id, msg.to_dict())
        return msg

    def get_chat_history(self, limit: int = 50) -> list[ChatMessage]:
        """Get recent chat messages."""
        messages = list(self._chat_messages)
        return messages[-limit:] if limit < len(messages) else messages

    def search_chat(self, query: str) -> list[ChatMessage]:
        """Search chat messages by content."""
        query_lower = query.lower()
        return [m for m in self._chat_messages if query_lower in m.content.lower()]

    # -- Event system -------------------------------------------------------

    def _emit_event(
        self,
        event_type: EventType,
        sender_id: str,
        data: dict[str, Any],
        target_users: list[str] | None = None,
    ) -> RealtimeEvent:
        """Emit a real-time event."""
        event = RealtimeEvent(
            event_id=self._next_event_id(),
            event_type=event_type,
            sender_id=sender_id,
            data=data,
            target_users=target_users or [],
        )
        self._events.append(event)

        # Notify listeners
        for listener in self._event_listeners.get(event_type.value, []):
            try:
                listener(event)
            except Exception as e:
                logger.error("Event listener error: %s", e)

        for listener in self._event_listeners.get("*", []):
            try:
                listener(event)
            except Exception as e:
                logger.error("Wildcard event listener error: %s", e)

        return event

    def on_event(self, event_type: str, callback: Callable) -> None:
        """Register a listener for a specific event type. Use '*' for all events."""
        self._event_listeners.setdefault(event_type, []).append(callback)

    def get_events(
        self,
        event_type: str | None = None,
        sender_id: str | None = None,
        limit: int = 0,
    ) -> list[RealtimeEvent]:
        """Get events with optional filters."""
        results = list(self._events)
        if event_type:
            results = [e for e in results if e.event_type.value == event_type]
        if sender_id:
            results = [e for e in results if e.sender_id == sender_id]
        if limit > 0:
            results = results[-limit:]
        return results

    # -- Notifications ------------------------------------------------------

    def notify_user(self, user_id: str, message: str, data: dict[str, Any] | None = None) -> RealtimeEvent:
        """Send a notification to a specific user."""
        return self._emit_event(EventType.NOTIFICATION, "system", {
            "message": message,
            **(data or {}),
        }, target_users=[user_id])

    def notify_all(self, message: str, data: dict[str, Any] | None = None) -> RealtimeEvent:
        """Send a notification to all connected users."""
        return self._emit_event(EventType.NOTIFICATION, "system", {
            "message": message,
            **(data or {}),
        })

    # -- Agent integration --------------------------------------------------

    def notify_agent_started(self, task_id: str, agent_type: str) -> RealtimeEvent:
        """Notify all users that an agent started working on a task."""
        self.lock_task(task_id, f"agent:{agent_type}", lock_type="agent",
                       reason=f"Agent {agent_type} is working")
        return self._emit_event(EventType.AGENT_STARTED, "system", {
            "task_id": task_id,
            "agent_type": agent_type,
        })

    def notify_agent_completed(self, task_id: str, agent_type: str, success: bool = True) -> RealtimeEvent:
        """Notify all users that an agent completed its work."""
        self.force_unlock_task(task_id, "system")
        return self._emit_event(EventType.AGENT_COMPLETED, "system", {
            "task_id": task_id,
            "agent_type": agent_type,
            "success": success,
        })

    # -- Sync ---------------------------------------------------------------

    def request_sync(self, user_id: str) -> dict[str, Any]:
        """Request a full state sync for a user (e.g., on reconnect).

        Returns:
            Full state snapshot including users, locks, recent events.
        """
        return {
            "project_id": self.project_id,
            "users": [u.to_dict() for u in self.get_connected_users()],
            "locks": [l.to_dict() for l in self.get_all_locks()],
            "recent_events": [e.to_dict() for e in self._events[-50:]],
            "chat_history": [m.to_dict() for m in self.get_chat_history(20)],
            "task_versions": dict(self._task_versions),
            "unresolved_conflicts": [c.to_dict() for c in self.get_conflicts(resolved=False)],
        }

    # -- Stats --------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Get server statistics."""
        online = len(self.get_connected_users())
        return {
            "project_id": self.project_id,
            "total_users": len(self._users),
            "online_users": online,
            "active_locks": len(self._locks),
            "agent_locks": sum(1 for l in self._locks.values() if l.is_agent_lock),
            "total_events": len(self._events),
            "chat_messages": len(self._chat_messages),
            "total_conflicts": len(self._conflicts),
            "unresolved_conflicts": sum(1 for c in self._conflicts if not c.resolved),
        }
