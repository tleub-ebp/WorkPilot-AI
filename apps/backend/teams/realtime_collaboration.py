"""
Real-time Collaboration System
Multi-user collaborative editing with conflict resolution and chat.
"""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class UserStatus(str, Enum):
    ONLINE = "online"
    BUSY = "busy"
    AWAY = "away"
    OFFLINE = "offline"


class LockType(str, Enum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


class EventType(str, Enum):
    USER_JOIN = "user_join"
    USER_JOINED = "user_joined"  # For backward compatibility
    USER_LEAVE = "user_leave"
    TASK_LOCK = "task_lock"
    TASK_UNLOCK = "task_unlock"
    TASK_UPDATE = "task_update"
    TASK_MOVE = "task_move"
    CHAT_MESSAGE = "chat_message"
    CONFLICT_DETECTED = "conflict_detected"
    CONFLICT_RESOLVED = "conflict_resolved"
    NOTIFICATION = "notification"
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    SYNC_REQUESTED = "sync_requested"


class ConflictResolution(str, Enum):
    MANUAL = "manual"
    AUTO_MERGE = "auto_merge"
    USER_WINS = "user_wins"
    AGENT_WINS = "agent_wins"


@dataclass
class ConnectedUser:
    user_id: str
    display_name: str
    status: UserStatus = UserStatus.ONLINE
    role: str = "developer"
    connected_at: str = field(default_factory=lambda: str(time.time()))
    last_seen: str = field(default_factory=lambda: str(time.time()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "display_name": self.display_name,
            "status": self.status.value,
            "role": self.role,
            "connected_at": self.connected_at,
            "last_seen": self.last_seen,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConnectedUser":
        return cls(
            user_id=data["user_id"],
            display_name=data["display_name"],
            status=UserStatus(data.get("status", "online")),
            role=data.get("role", "developer"),
            connected_at=data.get("connected_at", str(time.time())),
            last_seen=data.get("last_seen", str(time.time())),
        )


@dataclass
class TaskLock:
    task_id: str
    locked_by: str
    lock_type: LockType
    reason: str = ""
    locked_at: str = field(default_factory=lambda: str(time.time()))
    expires_at: str | None = None

    @property
    def is_agent_lock(self) -> bool:
        return self.lock_type == LockType.AGENT

    @property
    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        return time.time() > float(self.expires_at)

    def to_dict(self) -> dict[str, Any]:
        lock_type_value = (
            self.lock_type.value if hasattr(self.lock_type, "value") else self.lock_type
        )
        return {
            "task_id": self.task_id,
            "locked_by": self.locked_by,
            "lock_type": lock_type_value,
            "reason": self.reason,
            "locked_at": self.locked_at,
            "expires_at": self.expires_at,
        }


@dataclass
class RealtimeEvent:
    event_id: str
    event_type: EventType
    sender_id: str
    data: dict[str, Any] = field(default_factory=dict)
    target_users: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: str(time.time()))

    @property
    def is_broadcast(self) -> bool:
        return len(self.target_users) == 0

    def to_dict(self) -> dict[str, Any]:
        event_type_value = (
            self.event_type.value
            if hasattr(self.event_type, "value")
            else self.event_type
        )
        return {
            "event_id": self.event_id,
            "event_type": event_type_value,
            "sender_id": self.sender_id,
            "data": self.data,
            "target_users": self.target_users,
            "timestamp": self.timestamp,
        }


@dataclass
class ChatMessage:
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str = ""
    sender_name: str = ""
    content: str = ""
    timestamp: str = field(default_factory=lambda: str(time.time()))
    message_type: str = "text"  # text, system, emoji
    reply_to: str = ""
    mentions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "content": self.content,
            "timestamp": self.timestamp,
            "message_type": self.message_type,
            "reply_to": self.reply_to,
            "mentions": self.mentions,
        }


@dataclass
class ConflictRecord:
    conflict_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = ""
    user_a: str = ""
    user_b: str = ""
    field_name: str = ""
    value_a: Any = None
    value_b: Any = None
    detected_at: str = field(default_factory=lambda: str(time.time()))
    resolution: ConflictResolution = ConflictResolution.MANUAL
    resolved_by: str | None = None
    resolved_at: str | None = None

    @property
    def resolved(self) -> bool:
        return self.resolved_at is not None

    def to_dict(self) -> dict[str, Any]:
        resolution_value = (
            self.resolution.value
            if hasattr(self.resolution, "value")
            else self.resolution
        )
        return {
            "conflict_id": self.conflict_id,
            "task_id": self.task_id,
            "user_a": self.user_a,
            "user_b": self.user_b,
            "field_name": self.field_name,
            "value_a": self.value_a,
            "value_b": self.value_b,
            "detected_at": self.detected_at,
            "resolution": resolution_value,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at,
        }


class CollaborationServer:
    #: Sentinel used by ``add_event_handler`` and ``on_event`` to subscribe
    #: a listener to *every* event type. Distinct from ``None`` so callers
    #: can still pass ``None`` to mean "not set".
    WILDCARD_EVENT = "*"

    def __init__(self, base_path: Path | None = None):
        self.base_path = base_path or Path(".collaboration")
        self.base_path.mkdir(parents=True, exist_ok=True)

        # Active sessions
        self.users: dict[str, ConnectedUser] = {}
        self.task_locks: dict[str, TaskLock] = {}
        self.chat_messages: list[ChatMessage] = []
        self.events: list[RealtimeEvent] = []
        self.conflicts: dict[str, ConflictRecord] = {}

        # Per-task monotonic version counters for optimistic concurrency:
        # every ``broadcast_task_update`` / ``broadcast_task_move`` increments
        # the version so clients can detect missed updates.
        self.task_versions: dict[str, int] = {}

        # Event handlers — keyed by EventType *or* ``WILDCARD_EVENT``.
        self.event_handlers: dict[EventType | str, list[callable]] = {}

    # User management
    def connect_user(
        self, user_id: str, display_name: str, role: str = "developer"
    ) -> ConnectedUser:
        user = ConnectedUser(user_id=user_id, display_name=display_name, role=role)
        self.users[user_id] = user

        event = RealtimeEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.USER_JOIN,
            sender_id=user_id,
            data={"user": user.to_dict()},
        )
        self._add_event(event)

        return user

    def disconnect_user(self, user_id: str) -> None:
        if user_id in self.users:
            user = self.users[user_id]
            user.status = UserStatus.OFFLINE

            # Release user's locks
            locks_to_remove = [
                task_id
                for task_id, lock in self.task_locks.items()
                if lock.locked_by == user_id
            ]
            for task_id in locks_to_remove:
                self.unlock_task(task_id, user_id)

            event = RealtimeEvent(
                event_id=str(uuid.uuid4()),
                event_type=EventType.USER_LEAVE,
                sender_id=user_id,
                data={"user_id": user_id},
            )
            self._add_event(event)

    def update_user_status(self, user_id: str, status: UserStatus) -> bool:
        if user_id in self.users:
            self.users[user_id].status = status
            self.users[user_id].last_seen = str(time.time())
            event = RealtimeEvent(
                event_id=str(uuid.uuid4()),
                event_type=EventType.USER_JOINED,
                sender_id=user_id,
                data={"user_id": user_id, "status": status.value},
            )
            self._add_event(event)
            return True
        return False

    # Task locking
    def lock_task(
        self,
        task_id: str,
        user_id: str,
        lock_type: LockType = LockType.USER,
        reason: str = "",
    ) -> bool:
        if task_id in self.task_locks and not self.task_locks[task_id].is_expired:
            return False

        lock = TaskLock(
            task_id=task_id, locked_by=user_id, lock_type=lock_type, reason=reason
        )
        self.task_locks[task_id] = lock

        event = RealtimeEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.TASK_LOCK,
            sender_id=user_id,
            data={
                "task_id": task_id,
                "locked_by": user_id,
                "lock_type": lock_type.value,
                "reason": reason,
            },
        )
        self._add_event(event)

        return True

    def unlock_task(self, task_id: str, user_id: str) -> bool:
        if task_id not in self.task_locks:
            return False

        lock = self.task_locks[task_id]
        if lock.locked_by != user_id:
            return False

        del self.task_locks[task_id]

        event = RealtimeEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.TASK_UNLOCK,
            sender_id=user_id,
            data={"task_id": task_id, "unlocked_by": user_id},
        )
        self._add_event(event)

        return True

    def get_task_lock(self, task_id: str) -> TaskLock | None:
        return self.task_locks.get(task_id)

    # Chat functionality
    def send_message(
        self, user_id: str, display_name: str, content: str, message_type: str = "text"
    ) -> ChatMessage:
        message = ChatMessage(
            sender_id=user_id,
            sender_name=display_name,
            content=content,
            message_type=message_type,
        )
        self.chat_messages.append(message)

        event = RealtimeEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.CHAT_MESSAGE,
            sender_id=user_id,
            data={"message": message.to_dict()},
        )
        self._add_event(event)

        return message

    def get_chat_history(self, limit: int = 50) -> list[ChatMessage]:
        return self.chat_messages[-limit:] if limit > 0 else self.chat_messages

    # Conflict management
    def detect_conflict(
        self,
        task_id: str,
        user_a: str,
        user_b: str,
        field_name: str,
        value_a: Any,
        value_b: Any,
    ) -> ConflictRecord:
        conflict = ConflictRecord(
            task_id=task_id,
            user_a=user_a,
            user_b=user_b,
            field_name=field_name,
            value_a=value_a,
            value_b=value_b,
        )
        self.conflicts[conflict.conflict_id] = conflict

        event = RealtimeEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.CONFLICT_DETECTED,
            sender_id="system",
            data={"conflict": conflict.to_dict()},
        )
        self._add_event(event)

        return conflict

    def resolve_conflict(
        self, conflict_id: str, resolution: ConflictResolution, resolved_by: str
    ) -> bool:
        if conflict_id not in self.conflicts:
            return False

        conflict = self.conflicts[conflict_id]
        conflict.resolution = resolution
        conflict.resolved_by = resolved_by
        conflict.resolved_at = str(time.time())

        event = RealtimeEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.CONFLICT_RESOLVED,
            sender_id=resolved_by,
            data={
                "conflict_id": conflict_id,
                "resolution": resolution.value
                if hasattr(resolution, "value")
                else resolution,
                "resolved_by": resolved_by,
            },
        )
        self._add_event(event)

        return True

    # Task broadcast updates (optimistic concurrency via ``task_versions``)
    def broadcast_task_update(
        self,
        task_id: str,
        sender_id: str,
        changes: dict[str, Any] | None = None,
    ) -> int:
        """Broadcast a task update to every subscriber.

        Increments the task's version counter and emits a ``TASK_UPDATE``
        event. Returns the new version so callers can confirm their update
        was applied.

        ``changes`` is a free-form dict of field → new-value pairs; the
        server does not mutate any task store (that's the caller's job),
        it just broadcasts the intent so connected peers can reconcile.
        """
        self.task_versions[task_id] = self.task_versions.get(task_id, 0) + 1
        version = self.task_versions[task_id]
        event = RealtimeEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.TASK_UPDATE,
            sender_id=sender_id,
            data={
                "task_id": task_id,
                "version": version,
                "changes": changes or {},
            },
        )
        self._add_event(event)
        return version

    def broadcast_task_move(
        self,
        task_id: str,
        sender_id: str,
        from_column: str,
        to_column: str,
    ) -> int:
        """Broadcast a Kanban task move (column change).

        Bumps the task version and emits a ``TASK_MOVE`` event. Returns
        the new version.
        """
        self.task_versions[task_id] = self.task_versions.get(task_id, 0) + 1
        version = self.task_versions[task_id]
        event = RealtimeEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.TASK_MOVE,
            sender_id=sender_id,
            data={
                "task_id": task_id,
                "version": version,
                "from_column": from_column,
                "to_column": to_column,
            },
        )
        self._add_event(event)
        return version

    def get_task_version(self, task_id: str) -> int:
        """Return the current version counter for a task (0 if unseen)."""
        return self.task_versions.get(task_id, 0)

    # Chat search
    def search_chat(self, query: str, limit: int = 50) -> list[ChatMessage]:
        """Return chat messages whose content matches ``query``.

        Case-insensitive substring match. Returns at most ``limit``
        messages, newest-first.
        """
        if not query:
            return []
        needle = query.lower()
        hits = [
            msg for msg in self.chat_messages if needle in msg.content.lower()
        ]
        # Newest-first ordering is what chat UIs expect for search results.
        return list(reversed(hits))[:limit] if limit > 0 else list(reversed(hits))

    # Agent integration — bridges agent runs with the collaborative Kanban
    def notify_agent_started(
        self,
        task_id: str,
        agent_id: str,
        agent_type: str = "coder",
    ) -> bool:
        """Mark a task as being worked on by an agent.

        Acquires an agent-typed lock on the task so human users see it as
        taken, and emits ``AGENT_STARTED``. Returns ``True`` when the lock
        was acquired, ``False`` if the task was already locked.
        """
        acquired = self.lock_task(
            task_id,
            agent_id,
            lock_type=LockType.AGENT,
            reason=f"Agent {agent_type} running",
        )
        if not acquired:
            return False
        event = RealtimeEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.AGENT_STARTED,
            sender_id=agent_id,
            data={
                "task_id": task_id,
                "agent_id": agent_id,
                "agent_type": agent_type,
            },
        )
        self._add_event(event)
        return True

    def notify_agent_completed(
        self,
        task_id: str,
        agent_id: str,
        outcome: str = "success",
    ) -> bool:
        """Release the agent's lock on a task and emit ``AGENT_COMPLETED``.

        Returns ``True`` if a lock owned by ``agent_id`` was released,
        ``False`` otherwise — callers can use this to detect out-of-order
        completion events from zombie agents.
        """
        released = self.unlock_task(task_id, agent_id)
        event = RealtimeEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.AGENT_COMPLETED,
            sender_id=agent_id,
            data={
                "task_id": task_id,
                "agent_id": agent_id,
                "outcome": outcome,
                "released": released,
            },
        )
        self._add_event(event)
        return released

    # Sync / notifications — the catch-up pattern after a temporary disconnect
    def request_sync(self, user_id: str, since_event_id: str | None = None) -> dict:
        """Return the state a reconnecting client needs to catch up.

        If ``since_event_id`` is provided, only events emitted *after* that
        event are returned; otherwise the full event log is returned.
        Also returns the current users / task locks / task versions so the
        client has a full snapshot.
        """
        events: list[RealtimeEvent]
        if since_event_id:
            cutoff_index = next(
                (i for i, e in enumerate(self.events) if e.event_id == since_event_id),
                -1,
            )
            events = self.events[cutoff_index + 1 :] if cutoff_index >= 0 else list(
                self.events
            )
        else:
            events = list(self.events)

        event = RealtimeEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.SYNC_REQUESTED,
            sender_id=user_id,
            data={"since_event_id": since_event_id, "event_count": len(events)},
        )
        self._add_event(event)

        return {
            "users": [u.to_dict() for u in self.users.values()],
            "locks": {tid: lock.to_dict() for tid, lock in self.task_locks.items()},
            "task_versions": dict(self.task_versions),
            "events": [e.to_dict() for e in events],
        }

    def notify_user(
        self,
        recipient_id: str,
        message: str,
        sender_id: str = "system",
        level: str = "info",
    ) -> RealtimeEvent:
        """Send a targeted NOTIFICATION event to a single user.

        The event's ``data`` payload carries ``recipient_id`` so frontends
        can filter out notifications not meant for them. Returns the
        emitted event.
        """
        event = RealtimeEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.NOTIFICATION,
            sender_id=sender_id,
            data={
                "recipient_id": recipient_id,
                "message": message,
                "level": level,
            },
        )
        self._add_event(event)
        return event

    # Event handling
    def add_event_handler(
        self, event_type: EventType | str, handler: callable
    ) -> None:
        """Subscribe ``handler`` to ``event_type``.

        Pass :data:`CollaborationServer.WILDCARD_EVENT` (or the string
        ``"*"``) to receive every event. A handler can be registered
        multiple times, which is intentional — fan-out is the caller's
        responsibility.
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)

    def on_event(self, handler: callable) -> None:
        """Shortcut for ``add_event_handler(WILDCARD_EVENT, handler)``."""
        self.add_event_handler(self.WILDCARD_EVENT, handler)

    def get_events(
        self, event_type: EventType | None = None, limit: int = 100
    ) -> list[RealtimeEvent]:
        events = self.events
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:] if limit > 0 else events

    def _add_event(self, event: RealtimeEvent) -> None:
        self.events.append(event)

        # Trigger typed event handlers
        for handler in self.event_handlers.get(event.event_type, ()):
            try:
                handler(event)
            except Exception as e:
                print(f"Event handler error: {e}")

        # Trigger wildcard handlers
        for handler in self.event_handlers.get(self.WILDCARD_EVENT, ()):
            try:
                handler(event)
            except Exception as e:
                print(f"Wildcard event handler error: {e}")

    # Statistics and monitoring
    def get_stats(self) -> dict[str, Any]:
        active_users = len(
            [u for u in self.users.values() if u.status != UserStatus.OFFLINE]
        )
        active_locks = len(
            [lock for lock in self.task_locks.values() if not lock.is_expired]
        )
        unresolved_conflicts = len(
            [c for c in self.conflicts.values() if c.resolution is None]
        )

        return {
            "active_users": active_users,
            "total_users": len(self.users),
            "active_locks": active_locks,
            "total_locks": len(self.task_locks),
            "unresolved_conflicts": unresolved_conflicts,
            "total_conflicts": len(self.conflicts),
            "chat_messages": len(self.chat_messages),
            "total_events": len(self.events),
        }

    def get_connected_users(self) -> list[ConnectedUser]:
        return [u for u in self.users.values() if u.status != UserStatus.OFFLINE]

    def cleanup_expired_locks(self) -> int:
        expired_locks = [
            task_id for task_id, lock in self.task_locks.items() if lock.is_expired
        ]

        for task_id in expired_locks:
            del self.task_locks[task_id]

        return len(expired_locks)
