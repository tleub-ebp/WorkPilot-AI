"""
Replay API — FastAPI endpoints for the Agent Replay & Debug Mode.

Provides endpoints for:
- Listing, loading, and deleting replay sessions
- Getting session details with full timeline
- File heatmap data
- Breakpoint management
- A/B session comparison
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .recorder import get_replay_recorder

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/replay", tags=["replay"])

SESSION_NOT_FOUND = "Replay session not found"


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class AddBreakpointRequest(BaseModel):
    breakpoint_type: str  # tool_call, file_change, decision, error, token_threshold, step_index, pattern_match
    condition: str = ""
    description: str = ""


class CompareSessionsRequest(BaseModel):
    session_a_id: str
    session_b_id: str


class DeleteSessionsRequest(BaseModel):
    session_ids: list[str]


# ---------------------------------------------------------------------------
# Session list / CRUD
# ---------------------------------------------------------------------------

@router.get("/sessions")
async def list_sessions():
    """List all saved replay sessions (summaries)."""
    recorder = get_replay_recorder()
    sessions = recorder.list_sessions()
    return {"success": True, "sessions": sessions, "count": len(sessions)}


@router.get("/sessions/{session_id}", responses={404: {"description": "Replay session not found"}})
async def get_session(session_id: str):
    """Get a complete replay session with all steps."""
    recorder = get_replay_recorder()
    session = recorder.load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND)
    return {"success": True, "session": session.to_dict()}


@router.delete("/sessions/{session_id}", responses={404: {"description": "Replay session not found"}})
async def delete_session(session_id: str):
    """Delete a replay session."""
    recorder = get_replay_recorder()
    deleted = recorder.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND)
    return {"success": True}


@router.post("/sessions/bulk-delete")
async def bulk_delete_sessions(req: DeleteSessionsRequest):
    """Delete multiple replay sessions at once."""
    recorder = get_replay_recorder()
    deleted_count = 0
    for sid in req.session_ids:
        if recorder.delete_session(sid):
            deleted_count += 1
    return {"success": True, "deleted": deleted_count}


# ---------------------------------------------------------------------------
# Session details
# ---------------------------------------------------------------------------

@router.get("/sessions/{session_id}/steps", responses={404: {"description": "Replay session not found"}})
async def get_session_steps(
    session_id: str,
    offset: int = 0,
    limit: int = 100,
    step_type: Optional[str] = None,
):
    """Get steps for a session with optional filtering and pagination."""
    recorder = get_replay_recorder()
    session = recorder.load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND)

    steps = session.steps
    if step_type:
        steps = [s for s in steps if s.step_type.value == step_type]

    total = len(steps)
    steps = steps[offset:offset + limit]

    return {
        "success": True,
        "steps": [s.to_dict() for s in steps],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/sessions/{session_id}/step/{step_index}", responses={404: {"description": "Session or step not found"}})
async def get_step_detail(session_id: str, step_index: int):
    """Get detailed info for a specific step."""
    recorder = get_replay_recorder()
    session = recorder.load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND)

    if step_index < 0 or step_index >= len(session.steps):
        raise HTTPException(status_code=404, detail="Step not found")

    step = session.steps[step_index]
    return {"success": True, "step": step.to_dict()}


# ---------------------------------------------------------------------------
# Heatmap
# ---------------------------------------------------------------------------

@router.get("/sessions/{session_id}/heatmap", responses={404: {"description": "Replay session not found"}})
async def get_file_heatmap(session_id: str):
    """Get file heatmap data — frequency of file touches by the agent."""
    recorder = get_replay_recorder()
    session = recorder.load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND)

    heatmap = session.file_heatmap()
    max_count = max(heatmap.values()) if heatmap else 1

    entries = [
        {
            "file_path": fp,
            "touch_count": count,
            "intensity": count / max_count,  # 0.0 to 1.0
        }
        for fp, count in heatmap.items()
    ]

    return {
        "success": True,
        "heatmap": entries,
        "total_files": len(entries),
        "max_touches": max_count,
    }


# ---------------------------------------------------------------------------
# Token timeline
# ---------------------------------------------------------------------------

@router.get("/sessions/{session_id}/token-timeline", responses={404: {"description": "Replay session not found"}})
async def get_token_timeline(session_id: str):
    """Get token consumption over time for charting."""
    recorder = get_replay_recorder()
    session = recorder.load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND)

    return {
        "success": True,
        "timeline": session.token_timeline(),
        "total_tokens": session.total_tokens,
        "total_cost_usd": session.total_cost_usd,
    }


# ---------------------------------------------------------------------------
# Tool usage stats
# ---------------------------------------------------------------------------

@router.get("/sessions/{session_id}/tool-stats", responses={404: {"description": "Replay session not found"}})
async def get_tool_stats(session_id: str):
    """Get tool usage statistics for a session."""
    recorder = get_replay_recorder()
    session = recorder.load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND)

    stats = session.tool_usage_stats()
    return {
        "success": True,
        "tool_stats": stats,
        "total_tool_calls": session.total_tool_calls,
    }


# ---------------------------------------------------------------------------
# Breakpoints
# ---------------------------------------------------------------------------

@router.get("/sessions/{session_id}/breakpoints", responses={404: {"description": "Replay session not found"}})
async def get_breakpoints(session_id: str):
    """Get breakpoints for a session."""
    recorder = get_replay_recorder()
    session = recorder.load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND)

    return {
        "success": True,
        "breakpoints": [b.to_dict() for b in session.breakpoints],
    }


@router.post("/sessions/{session_id}/breakpoints", responses={404: {"description": "Session not active or not found"}})
async def add_breakpoint(session_id: str, req: AddBreakpointRequest):
    """Add a breakpoint to an active session."""
    recorder = get_replay_recorder()
    bp = recorder.add_breakpoint(
        session_id,
        breakpoint_type=req.breakpoint_type,
        condition=req.condition,
        description=req.description,
    )
    if not bp:
        raise HTTPException(status_code=404, detail="Session not active or not found")
    return {"success": True, "breakpoint": bp.to_dict()}


@router.delete("/sessions/{session_id}/breakpoints/{breakpoint_id}", responses={404: {"description": "Session or breakpoint not found"}})
async def remove_breakpoint(session_id: str, breakpoint_id: str):
    """Remove a breakpoint from a session."""
    recorder = get_replay_recorder()
    removed = recorder.remove_breakpoint(session_id, breakpoint_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Session or breakpoint not found")
    return {"success": True}


# ---------------------------------------------------------------------------
# A/B Comparison
# ---------------------------------------------------------------------------

@router.post("/compare", responses={404: {"description": "Session A or B not found"}, 500: {"description": "Failed to compare sessions"}})
async def compare_sessions(req: CompareSessionsRequest):
    """Compare two replay sessions side by side (A/B comparison)."""
    recorder = get_replay_recorder()

    session_a = recorder.load_session(req.session_a_id)
    session_b = recorder.load_session(req.session_b_id)

    if not session_a:
        raise HTTPException(status_code=404, detail=f"Session A not found: {req.session_a_id}")
    if not session_b:
        raise HTTPException(status_code=404, detail=f"Session B not found: {req.session_b_id}")

    comparison = recorder.compare_sessions(req.session_a_id, req.session_b_id)
    if not comparison:
        raise HTTPException(status_code=500, detail="Failed to compare sessions")

    return {
        "success": True,
        "comparison": comparison.to_dict(),
        "session_a": session_a.to_summary(),
        "session_b": session_b.to_summary(),
    }
