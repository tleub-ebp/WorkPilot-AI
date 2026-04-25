"""HTTP routes for the Agent Health Monitor.

Mounted at `/api/agent-health`. The monitor is a process-singleton so
callers across requests share the same in-memory ring buffer.

* `POST /record`               — record one agent run
* `POST /record-batch`         — bulk record (e.g. on startup, replay history)
* `GET  /score/{agent_name}`   — score a specific agent
* `GET  /scores`               — score all known agents
* `POST /reset`                — reset one or all agent histories
"""

from __future__ import annotations

import logging
import threading

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field

from .monitor import AgentRun, HealthMonitor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent-health", tags=["agent-health"])

# Module-level singleton — protected by a lock so concurrent record() calls
# don't collide on the deque.
_monitor_lock = threading.Lock()
_monitor: HealthMonitor | None = None


def _get_monitor() -> HealthMonitor:
    global _monitor
    with _monitor_lock:
        if _monitor is None:
            _monitor = HealthMonitor()
        return _monitor


class RecordRunRequest(BaseModel):
    agent_name: str = Field(..., min_length=1, max_length=128)
    success: bool = True
    duration_s: float = Field(0.0, ge=0.0)
    retries: int = Field(0, ge=0)
    error: str = ""


class RecordBatchRequest(BaseModel):
    runs: list[RecordRunRequest]


class ResetRequest(BaseModel):
    agent_name: str | None = Field(
        None,
        description="If omitted, resets every agent's history.",
    )


@router.post("/record")
def record(req: RecordRunRequest):
    try:
        _get_monitor().record(
            AgentRun(
                agent_name=req.agent_name,
                success=req.success,
                duration_s=req.duration_s,
                retries=req.retries,
                error=req.error,
            )
        )
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        logger.exception("record failed")
        return {"success": False, "error": str(e)}


@router.post("/record-batch")
def record_batch(req: RecordBatchRequest):
    try:
        runs = [
            AgentRun(
                agent_name=r.agent_name,
                success=r.success,
                duration_s=r.duration_s,
                retries=r.retries,
                error=r.error,
            )
            for r in req.runs
        ]
        _get_monitor().record_many(runs)
        return {"success": True, "recorded": len(runs)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        logger.exception("record-batch failed")
        return {"success": False, "error": str(e)}


@router.get("/score/{agent_name}")
def score(agent_name: str = Path(..., min_length=1, max_length=128)):
    try:
        result = _get_monitor().score(agent_name)
        if result is None:
            return {
                "success": True,
                "score": None,
                "reason": "not enough recorded runs (need ≥ 3)",
            }
        return {"success": True, "score": result.to_dict()}
    except Exception as e:  # noqa: BLE001
        logger.exception("score failed")
        return {"success": False, "error": str(e)}


@router.get("/scores")
def scores():
    try:
        all_scores = _get_monitor().score_all()
        return {
            "success": True,
            "scores": [s.to_dict() for s in all_scores],
            "agents_known": _get_monitor().known_agents(),
        }
    except Exception as e:  # noqa: BLE001
        logger.exception("scores failed")
        return {"success": False, "error": str(e)}


@router.post("/reset")
def reset(req: ResetRequest):
    try:
        _get_monitor().reset(req.agent_name)
        return {"success": True}
    except Exception as e:  # noqa: BLE001
        logger.exception("reset failed")
        return {"success": False, "error": str(e)}
