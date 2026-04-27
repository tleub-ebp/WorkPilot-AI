"""HTTP routes for Real-time Pair Programming.

Mounted at `/api/pair-realtime`. Endpoints:

* `POST /rooms`              — create a room
* `GET  /rooms`              — list rooms
* `GET  /rooms/{id}`         — snapshot
* `DELETE /rooms/{id}`       — close room
* `POST /rooms/{id}/join`    — participant joins
* `POST /rooms/{id}/leave`   — participant leaves
* `POST /rooms/{id}/edit`    — submit an edit op
* `POST /rooms/{id}/cursor`  — submit a cursor move
* `POST /rooms/{id}/chat`    — submit a chat message
* `POST /rooms/{id}/suggestion` — submit an AI suggestion
* `GET  /rooms/{id}/ops`     — recent ops (since_sequence)
* `GET  /rooms/{id}/stream`  — Server-Sent Events live stream
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Path, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .session import PairSessionManager, Role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pair-realtime", tags=["pair-realtime"])

_manager = PairSessionManager()


def get_manager() -> PairSessionManager:
    """Test hook — patch this to swap the manager out."""
    return _manager


# ----------------------------------------------------------------------
# Request models


class CreateRoomRequest(BaseModel):
    room_id: str = Field(..., min_length=1, max_length=128)


class JoinRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    display_name: str = Field("", max_length=128)
    role: str = Field("navigator")


class LeaveRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)


class EditRequest(BaseModel):
    actor: str = Field(..., min_length=1)
    file_path: str = Field(..., min_length=1)
    start_line: int = Field(..., ge=0)
    end_line: int = Field(..., ge=0)
    new_text: str = ""


class CursorRequest(BaseModel):
    actor: str = Field(..., min_length=1)
    file_path: str = Field(..., min_length=1)
    line: int = Field(..., ge=0)
    column: int = Field(..., ge=0)


class ChatRequest(BaseModel):
    actor: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1, max_length=4_000)


class SuggestionRequest(BaseModel):
    actor: str = Field(..., min_length=1)
    file_path: str = Field(..., min_length=1)
    suggestion: str = Field(..., min_length=1)
    rationale: str = ""


def _resolve_role(raw: str) -> Role:
    try:
        return Role(raw.lower())
    except ValueError as e:
        raise ValueError(f"unknown role {raw!r} (driver | navigator | ai)") from e


# ----------------------------------------------------------------------
# Room CRUD


@router.post("/rooms")
def create_room(req: CreateRoomRequest):
    try:
        room = get_manager().create_room(req.room_id)
        return {"success": True, "room": room.snapshot().to_dict()}
    except ValueError as e:
        return {"success": False, "error": str(e)}


@router.get("/rooms")
def list_rooms():
    return {"success": True, "rooms": get_manager().list_rooms()}


@router.get("/rooms/{room_id}")
def get_room(room_id: str = Path(..., min_length=1, max_length=128)):
    try:
        return {
            "success": True,
            "room": get_manager().get_room(room_id).snapshot().to_dict(),
        }
    except KeyError:
        return {"success": False, "error": f"unknown room {room_id!r}"}


@router.delete("/rooms/{room_id}")
def close_room(room_id: str = Path(..., min_length=1, max_length=128)):
    closed = get_manager().close_room(room_id)
    return {"success": True, "closed": closed}


# ----------------------------------------------------------------------
# Participant ops


@router.post("/rooms/{room_id}/join")
def join(room_id: str, req: JoinRequest):
    try:
        room = get_manager().get_or_create_room(room_id)
        role = _resolve_role(req.role)
        op = room.join(req.user_id, req.display_name, role=role)
        return {"success": True, "op": op.to_dict()}
    except ValueError as e:
        return {"success": False, "error": str(e)}


@router.post("/rooms/{room_id}/leave")
def leave(room_id: str, req: LeaveRequest):
    try:
        room = get_manager().get_room(room_id)
        op = room.leave(req.user_id)
        return {"success": True, "op": op.to_dict() if op else None}
    except KeyError:
        return {"success": False, "error": f"unknown room {room_id!r}"}


# ----------------------------------------------------------------------
# Operations


@router.post("/rooms/{room_id}/edit")
def edit(room_id: str, req: EditRequest):
    try:
        room = get_manager().get_room(room_id)
        op = room.submit_edit(
            actor=req.actor,
            file_path=req.file_path,
            start_line=req.start_line,
            end_line=req.end_line,
            new_text=req.new_text,
        )
        return {"success": True, "op": op.to_dict()}
    except (KeyError, ValueError) as e:
        return {"success": False, "error": str(e)}


@router.post("/rooms/{room_id}/cursor")
def cursor(room_id: str, req: CursorRequest):
    try:
        room = get_manager().get_room(room_id)
        op = room.submit_cursor(req.actor, req.file_path, req.line, req.column)
        return {"success": True, "op": op.to_dict()}
    except (KeyError, ValueError) as e:
        return {"success": False, "error": str(e)}


@router.post("/rooms/{room_id}/chat")
def chat(room_id: str, req: ChatRequest):
    try:
        room = get_manager().get_room(room_id)
        op = room.submit_chat(req.actor, req.text)
        return {"success": True, "op": op.to_dict()}
    except (KeyError, ValueError) as e:
        return {"success": False, "error": str(e)}


@router.post("/rooms/{room_id}/suggestion")
def suggestion(room_id: str, req: SuggestionRequest):
    try:
        room = get_manager().get_room(room_id)
        op = room.submit_suggestion(
            req.actor, req.file_path, req.suggestion, req.rationale
        )
        return {"success": True, "op": op.to_dict()}
    except (KeyError, ValueError) as e:
        return {"success": False, "error": str(e)}


# ----------------------------------------------------------------------
# Read / stream


@router.get("/rooms/{room_id}/ops")
def recent_ops(
    room_id: str = Path(..., min_length=1, max_length=128),
    since_sequence: int = Query(0, ge=0),
):
    try:
        room = get_manager().get_room(room_id)
        ops = room.recent_ops(since_sequence=since_sequence)
        return {"success": True, "ops": [o.to_dict() for o in ops], "count": len(ops)}
    except KeyError:
        return {"success": False, "error": f"unknown room {room_id!r}"}


@router.get("/rooms/{room_id}/stream")
async def stream(
    room_id: str = Path(..., min_length=1, max_length=128),
    since_sequence: int = Query(0, ge=0),
):
    """Server-Sent Events stream of room operations.

    Each event line is `data: {json}\\n\\n`. The connection stays open;
    clients should reconnect with their last `since_sequence` to resume.
    """
    try:
        room = get_manager().get_room(room_id)
    except KeyError:
        return StreamingResponse(
            iter(
                [
                    f"event: error\ndata: {json.dumps({'error': f'unknown room {room_id!r}'})}\n\n"
                ]
            ),
            media_type="text/event-stream",
        )

    async def event_source():
        try:
            async for op in room.subscribe(since_sequence=since_sequence):
                yield f"data: {json.dumps(op.to_dict())}\n\n"
        except asyncio.CancelledError:
            return

    return StreamingResponse(event_source(), media_type="text/event-stream")
