"""Real-time Pair Programming — session manager.

Concurrency model
-----------------

* One `PairRoom` per session.
* Each room has a ring-buffer of the most recent `Operation`s + a set of
  `Participant`s.
* Subscribers receive live ops via an `asyncio.Queue` per subscription.
  Late joiners can re-fetch the recent history via `recent_ops()`.

We deliberately avoid CRDTs/OT here: operations are coarse (insert,
delete, replace, cursor, chat) with **last-write-wins** semantics. The
target use case is "two humans talking it out + watching each other type"
— not Google Docs character-level merging. That keeps the MVP shippable
in a few hundred LoC.

Thread safety: the manager + room state mutations are protected by a
`Lock`. The async queues used for subscriptions are per-subscriber so
they don't need locks of their own.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
import uuid
from collections import deque
from collections.abc import AsyncIterator
from dataclasses import asdict, dataclass, field
from enum import Enum
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)


_ROOM_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class Role(str, Enum):
    DRIVER = "driver"  # the one currently writing code
    NAVIGATOR = "navigator"  # observers, can suggest
    AI = "ai"  # an AI participant


class OperationKind(str, Enum):
    EDIT = "edit"  # text replace at a range
    CURSOR = "cursor"  # cursor / selection move
    CHAT = "chat"  # human-readable chat message
    SUGGESTION = "suggestion"  # AI suggestion (non-applied)
    JOIN = "join"  # participant joined
    LEAVE = "leave"  # participant left
    ROLE_CHANGE = "role_change"


@dataclass
class Participant:
    user_id: str
    display_name: str
    role: Role = Role.NAVIGATOR
    joined_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["role"] = self.role.value
        return d


@dataclass(frozen=True)
class Operation:
    """One broadcast-able operation. Immutable once recorded."""

    op_id: str
    sequence: int
    kind: OperationKind
    actor: str  # user_id of the participant
    timestamp: float
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["kind"] = self.kind.value
        return d


@dataclass
class RoomSnapshot:
    room_id: str
    created_at: float
    participants: list[Participant]
    op_count: int
    last_op_sequence: int
    closed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "room_id": self.room_id,
            "created_at": self.created_at,
            "participants": [p.to_dict() for p in self.participants],
            "op_count": self.op_count,
            "last_op_sequence": self.last_op_sequence,
            "closed": self.closed,
        }


# ----------------------------------------------------------------------
# Room


class PairRoom:
    """One collaborative session. Holds participants + op history + subscribers."""

    DEFAULT_HISTORY = 500  # ops kept in the ring buffer
    DEFAULT_QUEUE_BUFFER = 100  # per-subscriber backlog before drop
    INACTIVE_PARTICIPANT_TIMEOUT = 300.0  # seconds

    def __init__(self, room_id: str, history: int = DEFAULT_HISTORY) -> None:
        if not _ROOM_NAME_RE.fullmatch(room_id):
            raise ValueError(f"Invalid room_id {room_id!r}")
        self.room_id = room_id
        self.created_at = time.time()
        self._participants: dict[str, Participant] = {}
        self._ops: deque[Operation] = deque(maxlen=history)
        self._subscribers: dict[str, asyncio.Queue[Operation]] = {}
        self._sequence = 0
        self._closed = False
        self._lock = Lock()

    # ------------------------------------------------------------------
    # Participants

    def join(
        self, user_id: str, display_name: str, role: Role = Role.NAVIGATOR
    ) -> Operation:
        if not user_id:
            raise ValueError("user_id is required")
        with self._lock:
            if self._closed:
                raise ValueError("room is closed")
            if user_id not in self._participants:
                self._participants[user_id] = Participant(
                    user_id=user_id,
                    display_name=display_name or user_id,
                    role=role,
                )
            else:
                self._participants[user_id].last_seen = time.time()
        return self._record_op(
            kind=OperationKind.JOIN,
            actor=user_id,
            payload={"display_name": display_name, "role": role.value},
        )

    def leave(self, user_id: str) -> Operation | None:
        with self._lock:
            if user_id not in self._participants:
                return None
            self._participants.pop(user_id, None)
        return self._record_op(
            kind=OperationKind.LEAVE,
            actor=user_id,
            payload={},
        )

    def set_role(self, user_id: str, role: Role) -> Operation:
        with self._lock:
            if user_id not in self._participants:
                raise ValueError(f"unknown user {user_id!r}")
            self._participants[user_id].role = role
        return self._record_op(
            kind=OperationKind.ROLE_CHANGE,
            actor=user_id,
            payload={"role": role.value},
        )

    def participants(self) -> list[Participant]:
        with self._lock:
            return list(self._participants.values())

    # ------------------------------------------------------------------
    # Operations

    def submit_edit(
        self,
        actor: str,
        file_path: str,
        start_line: int,
        end_line: int,
        new_text: str,
    ) -> Operation:
        self._touch(actor)
        return self._record_op(
            kind=OperationKind.EDIT,
            actor=actor,
            payload={
                "file_path": file_path,
                "start_line": start_line,
                "end_line": end_line,
                "new_text": new_text,
            },
        )

    def submit_cursor(
        self, actor: str, file_path: str, line: int, column: int
    ) -> Operation:
        self._touch(actor)
        return self._record_op(
            kind=OperationKind.CURSOR,
            actor=actor,
            payload={"file_path": file_path, "line": line, "column": column},
        )

    def submit_chat(self, actor: str, text: str) -> Operation:
        if not text or len(text) > 4_000:
            raise ValueError("chat text must be 1..4000 chars")
        self._touch(actor)
        return self._record_op(
            kind=OperationKind.CHAT, actor=actor, payload={"text": text}
        )

    def submit_suggestion(
        self, actor: str, file_path: str, suggestion: str, rationale: str = ""
    ) -> Operation:
        self._touch(actor)
        return self._record_op(
            kind=OperationKind.SUGGESTION,
            actor=actor,
            payload={
                "file_path": file_path,
                "suggestion": suggestion,
                "rationale": rationale,
            },
        )

    def recent_ops(self, since_sequence: int = 0) -> list[Operation]:
        with self._lock:
            return [op for op in self._ops if op.sequence >= since_sequence]

    # ------------------------------------------------------------------
    # Subscriptions (transport-agnostic)

    async def subscribe(
        self, since_sequence: int = 0, queue_buffer: int = DEFAULT_QUEUE_BUFFER
    ) -> AsyncIterator[Operation]:
        """Yield ops as they're recorded. Replays missed history first."""
        sub_id = uuid.uuid4().hex
        queue: asyncio.Queue[Operation] = asyncio.Queue(maxsize=queue_buffer)

        with self._lock:
            self._subscribers[sub_id] = queue
            backlog = [op for op in self._ops if op.sequence >= since_sequence]

        try:
            for op in backlog:
                yield op
            while True:
                try:
                    op = await queue.get()
                except asyncio.CancelledError:
                    break
                yield op
        finally:
            with self._lock:
                self._subscribers.pop(sub_id, None)

    # ------------------------------------------------------------------
    # Lifecycle

    def close(self) -> None:
        with self._lock:
            self._closed = True
            self._participants.clear()
            self._subscribers.clear()

    def is_closed(self) -> bool:
        with self._lock:
            return self._closed

    def snapshot(self) -> RoomSnapshot:
        with self._lock:
            return RoomSnapshot(
                room_id=self.room_id,
                created_at=self.created_at,
                participants=list(self._participants.values()),
                op_count=len(self._ops),
                last_op_sequence=self._sequence - 1 if self._sequence else -1,
                closed=self._closed,
            )

    # ------------------------------------------------------------------
    # Internals

    def _touch(self, user_id: str) -> None:
        with self._lock:
            if user_id in self._participants:
                self._participants[user_id].last_seen = time.time()

    def _record_op(
        self, kind: OperationKind, actor: str, payload: dict[str, Any]
    ) -> Operation:
        with self._lock:
            if self._closed:
                raise ValueError("room is closed")
            seq = self._sequence
            self._sequence += 1
            op = Operation(
                op_id=uuid.uuid4().hex,
                sequence=seq,
                kind=kind,
                actor=actor,
                timestamp=time.time(),
                payload=payload,
            )
            self._ops.append(op)
            # Snapshot subscribers under lock so we don't miss/race a leave.
            subs = list(self._subscribers.items())

        for sub_id, queue in subs:
            try:
                queue.put_nowait(op)
            except asyncio.QueueFull:
                # Slow consumer — drop them rather than backing up
                # everyone else. They can reconnect with `since_sequence`.
                logger.warning(
                    "Dropping slow subscriber %s on room %s", sub_id, self.room_id
                )
                with self._lock:
                    self._subscribers.pop(sub_id, None)
        return op


# ----------------------------------------------------------------------
# Manager


class PairSessionManager:
    """Process-wide registry of `PairRoom`s."""

    def __init__(self) -> None:
        self._rooms: dict[str, PairRoom] = {}
        self._lock = Lock()

    def create_room(self, room_id: str) -> PairRoom:
        with self._lock:
            if room_id in self._rooms:
                raise ValueError(f"Room {room_id!r} already exists")
            room = PairRoom(room_id=room_id)
            self._rooms[room_id] = room
            return room

    def get_room(self, room_id: str) -> PairRoom:
        with self._lock:
            room = self._rooms.get(room_id)
            if room is None:
                raise KeyError(room_id)
            return room

    def get_or_create_room(self, room_id: str) -> PairRoom:
        with self._lock:
            room = self._rooms.get(room_id)
            if room is None:
                room = PairRoom(room_id=room_id)
                self._rooms[room_id] = room
            return room

    def close_room(self, room_id: str) -> bool:
        with self._lock:
            room = self._rooms.pop(room_id, None)
        if room is None:
            return False
        room.close()
        return True

    def list_rooms(self) -> list[str]:
        with self._lock:
            return sorted(self._rooms.keys())

    def reset(self) -> None:
        """Test-only escape hatch."""
        with self._lock:
            for room in self._rooms.values():
                room.close()
            self._rooms.clear()
