"""
Mission Control API — FastAPI routes for the Mission Control dashboard.

Provides REST endpoints for:
- Session management (start/stop)
- Agent CRUD (create/remove/update)
- Agent control (start/pause/resume/stop)
- State queries (full state, individual agent, decision tree)
- Live event updates (for agent processes to report state)
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .orchestrator import get_mission_control

logger = logging.getLogger(__name__)

# Constants
AGENT_NOT_FOUND = "Agent not found"

router = APIRouter(prefix="/api/mission-control", tags=["mission-control"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class CreateAgentRequest(BaseModel):
    name: str
    role: str = "custom"
    provider: str = ""
    model: str = ""
    model_label: str = ""


class UpdateAgentConfigRequest(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    model_label: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None


class StartAgentRequest(BaseModel):
    task: str = ""


class AgentStateUpdateRequest(BaseModel):
    """Used by agent processes to push live state updates."""
    thinking: Optional[str] = None
    tool_name: Optional[str] = None
    tool_input: Optional[str] = None
    file_path: Optional[str] = None
    file_operation: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    progress: Optional[float] = None
    current_step: Optional[str] = None
    status: Optional[str] = None
    error: Optional[str] = None


class StartSessionRequest(BaseModel):
    name: str = "Mission Control"


# ---------------------------------------------------------------------------
# Session endpoints
# ---------------------------------------------------------------------------

@router.post("/session/start")
async def start_session(req: StartSessionRequest):
    """Start a new Mission Control session."""
    mc = get_mission_control()
    info = mc.start_session()
    return {"success": True, "session": info}


@router.post("/session/stop")
async def stop_session():
    """Stop the current Mission Control session."""
    mc = get_mission_control()
    mc.stop_session()
    return {"success": True}


@router.get("/session")
async def get_session():
    """Get current session info."""
    mc = get_mission_control()
    return {"success": True, "session": mc.get_session_info()}


# ---------------------------------------------------------------------------
# Full state
# ---------------------------------------------------------------------------

@router.get("/state")
async def get_full_state():
    """Get the complete Mission Control state (all agents, trees, events)."""
    mc = get_mission_control()
    return {"success": True, "state": mc.get_full_state()}


# ---------------------------------------------------------------------------
# Agent CRUD
# ---------------------------------------------------------------------------

@router.post("/agents")
async def create_agent(req: CreateAgentRequest):
    """Create a new agent slot."""
    mc = get_mission_control()
    slot = mc.create_agent(
        name=req.name,
        role=req.role,
        provider=req.provider,
        model=req.model,
        model_label=req.model_label,
    )
    return {"success": True, "agent": slot.to_dict()}


@router.get("/agents")
async def list_agents():
    """List all agent slots."""
    mc = get_mission_control()
    return {"success": True, "agents": mc.get_all_agents()}


@router.get("/agents/{agent_id}", responses={404: {"description": AGENT_NOT_FOUND}})
async def get_agent(agent_id: str):
    """Get a specific agent slot."""
    mc = get_mission_control()
    slot = mc.get_agent(agent_id)
    if not slot:
        raise HTTPException(status_code=404, detail=AGENT_NOT_FOUND)
    return {"success": True, "agent": slot.to_dict()}


@router.put("/agents/{agent_id}", responses={404: {"description": AGENT_NOT_FOUND}})
async def update_agent(agent_id: str, req: UpdateAgentConfigRequest):
    """Update agent configuration."""
    mc = get_mission_control()
    slot = mc.update_agent_config(
        agent_id,
        provider=req.provider,
        model=req.model,
        model_label=req.model_label,
        name=req.name,
        role=req.role,
    )
    if not slot:
        raise HTTPException(status_code=404, detail=AGENT_NOT_FOUND)
    return {"success": True, "agent": slot.to_dict()}


@router.delete("/agents/{agent_id}", responses={404: {"description": AGENT_NOT_FOUND}})
async def remove_agent(agent_id: str):
    """Remove an agent slot."""
    mc = get_mission_control()
    removed = mc.remove_agent(agent_id)
    if not removed:
        raise HTTPException(status_code=404, detail=AGENT_NOT_FOUND)
    return {"success": True}


# ---------------------------------------------------------------------------
# Agent control
# ---------------------------------------------------------------------------

@router.post("/agents/{agent_id}/start", responses={404: {"description": AGENT_NOT_FOUND}})
async def start_agent(agent_id: str, req: StartAgentRequest):
    """Start an agent with a task."""
    mc = get_mission_control()
    ok = mc.start_agent(agent_id, req.task)
    if not ok:
        raise HTTPException(status_code=404, detail=AGENT_NOT_FOUND)
    return {"success": True}


@router.post("/agents/{agent_id}/pause", responses={404: {"description": AGENT_NOT_FOUND}})
async def pause_agent(agent_id: str):
    """Pause a running agent."""
    mc = get_mission_control()
    ok = mc.pause_agent(agent_id)
    if not ok:
        raise HTTPException(status_code=404, detail=AGENT_NOT_FOUND)
    return {"success": True}


@router.post("/agents/{agent_id}/resume", responses={404: {"description": AGENT_NOT_FOUND}})
async def resume_agent(agent_id: str):
    """Resume a paused agent."""
    mc = get_mission_control()
    ok = mc.resume_agent(agent_id)
    if not ok:
        raise HTTPException(status_code=404, detail=AGENT_NOT_FOUND)
    return {"success": True}


@router.post("/agents/{agent_id}/stop", responses={404: {"description": AGENT_NOT_FOUND}})
async def stop_agent(agent_id: str):
    """Stop an agent."""
    mc = get_mission_control()
    ok = mc.stop_agent(agent_id)
    if not ok:
        raise HTTPException(status_code=404, detail=AGENT_NOT_FOUND)
    return {"success": True}


# ---------------------------------------------------------------------------
# Live state updates (called by agent processes)
# ---------------------------------------------------------------------------

@router.post("/agents/{agent_id}/update", responses={404: {"description": AGENT_NOT_FOUND}})
async def update_agent_state(agent_id: str, req: AgentStateUpdateRequest):
    """Push a live state update from an agent process."""
    mc = get_mission_control()
    slot = mc.get_agent(agent_id)
    if not slot:
        raise HTTPException(status_code=404, detail=AGENT_NOT_FOUND)

    if req.thinking is not None:
        mc.update_agent_thinking(agent_id, req.thinking)
    if req.tool_name is not None:
        mc.update_agent_tool_call(agent_id, req.tool_name, req.tool_input or "")
    if req.file_path is not None:
        mc.update_agent_file(agent_id, req.file_path)
    if req.input_tokens is not None or req.output_tokens is not None:
        mc.update_agent_tokens(
            agent_id,
            input_tokens=req.input_tokens or 0,
            output_tokens=req.output_tokens or 0,
            cost_usd=req.cost_usd or 0.0,
        )
    if req.progress is not None:
        mc.update_agent_progress(agent_id, req.progress, req.current_step or "")
    if req.status is not None:
        mc.update_agent_status(agent_id, req.status, req.error or "")

    return {"success": True, "agent": slot.to_dict()}


# ---------------------------------------------------------------------------
# Decision tree
# ---------------------------------------------------------------------------

@router.get("/agents/{agent_id}/decision-tree", responses={404: {"description": AGENT_NOT_FOUND}})
async def get_decision_tree(agent_id: str):
    """Get the full decision tree for an agent."""
    mc = get_mission_control()
    tree = mc.get_decision_tree(agent_id)
    if tree is None:
        raise HTTPException(status_code=404, detail=AGENT_NOT_FOUND)
    return {"success": True, "tree": tree}


@router.get("/agents/{agent_id}/decision-path")
async def get_decision_path(agent_id: str):
    """Get the flat decision path for an agent."""
    mc = get_mission_control()
    path = mc.get_decision_path(agent_id)
    return {"success": True, "path": path}


# ---------------------------------------------------------------------------
# Event log
# ---------------------------------------------------------------------------

@router.get("/events")
async def get_events(limit: int = 50):
    """Get recent Mission Control events."""
    mc = get_mission_control()
    events = mc.get_event_log(limit)
    return {"success": True, "events": events}
