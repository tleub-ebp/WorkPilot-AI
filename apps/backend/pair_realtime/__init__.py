"""Real-time Pair Programming.

In-memory session manager for multi-user collaborative coding rooms.
Handles participant join/leave, operation broadcast (edits, cursor moves,
chat), and replay of recent history for late joiners.

Different from `agents/pair_programming.py` which is a single-user
interactive session with an LLM (the AI proposes, the user approves).
This module is **multi-user**: several humans + optionally an AI all
talking to the same room, each operation broadcast to every other
subscriber.

Transport-agnostic: the manager exposes a `subscribe()` async generator
that yields operations. The HTTP layer wires that to Server-Sent Events
(simpler than WebSocket and already supported by FastAPI).
"""

from .session import (
    Operation,
    OperationKind,
    PairRoom,
    PairSessionManager,
    Participant,
    Role,
    RoomSnapshot,
)

__all__ = [
    "Operation",
    "OperationKind",
    "PairRoom",
    "PairSessionManager",
    "Participant",
    "Role",
    "RoomSnapshot",
]
