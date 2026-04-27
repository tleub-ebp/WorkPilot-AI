"""HTTP routes for the AuditTrail.

Mounted at `/api/audit-trail`. Endpoints:

* `POST /append`             — append one event
* `POST /append-decision`    — convenience for DECISION_MADE events
* `GET  /events`             — filter events (actor / kind / since / until)
* `GET  /replay/{cid}`       — replay all events for a correlation_id
* `GET  /verify`             — confirm chain integrity
* `GET  /trails`             — list trails on disk
"""

from __future__ import annotations

import logging
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import APIRouter, Query
from fastapi import Path as PathParam
from pydantic import BaseModel, Field

from .trail import AuditEventKind, AuditTrail, Decision

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audit-trail", tags=["audit-trail"])

# One trail instance per (storage_dir, name) so concurrent appends
# don't cross streams.
_trails: dict[tuple[str, str], AuditTrail] = {}
_trails_lock = Lock()


def _validate_dir(raw: str) -> Path:
    if not raw or raw.strip().startswith("-"):
        raise ValueError("storage_dir must not be empty or start with '-'")
    p = Path(raw).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def _get_trail(storage_dir: str, name: str) -> AuditTrail:
    path = _validate_dir(storage_dir)
    key = (str(path), name)
    with _trails_lock:
        trail = _trails.get(key)
        if trail is None:
            trail = AuditTrail(storage_dir=path, name=name)
            _trails[key] = trail
        return trail


class AppendRequest(BaseModel):
    storage_dir: str
    trail_name: str = Field("default", min_length=1, max_length=128)
    kind: str = Field(..., min_length=1)
    actor: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1)
    summary: str = ""
    payload: dict[str, Any] | None = None


class AppendDecisionRequest(BaseModel):
    storage_dir: str
    trail_name: str = Field("default", min_length=1, max_length=128)
    actor: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1)
    decision_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    chosen_option: str = Field(..., min_length=1)
    rejected_options: list[str] | None = None
    rationale: str = ""
    risk_score: float = 0.0


@router.post("/append")
def append(req: AppendRequest):
    try:
        trail = _get_trail(req.storage_dir, req.trail_name)
        evt = trail.append(
            kind=req.kind,
            actor=req.actor,
            correlation_id=req.correlation_id,
            summary=req.summary,
            payload=req.payload,
        )
        return {"success": True, "event": evt.to_dict()}
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:  # noqa: BLE001
        logger.exception("append failed")
        return {"success": False, "error": str(e)}


@router.post("/append-decision")
def append_decision(req: AppendDecisionRequest):
    try:
        trail = _get_trail(req.storage_dir, req.trail_name)
        decision = Decision(
            decision_id=req.decision_id,
            title=req.title,
            chosen_option=req.chosen_option,
            rejected_options=tuple(req.rejected_options or ()),
            rationale=req.rationale,
            risk_score=req.risk_score,
        )
        evt = trail.append_decision(
            actor=req.actor,
            correlation_id=req.correlation_id,
            decision=decision,
        )
        return {"success": True, "event": evt.to_dict()}
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:  # noqa: BLE001
        logger.exception("append_decision failed")
        return {"success": False, "error": str(e)}


@router.get("/events")
def events(
    storage_dir: str = Query(...),
    trail_name: str = Query("default"),
    actor: str | None = Query(None),
    kind: str | None = Query(None),
    since: float | None = Query(None),
    until: float | None = Query(None),
):
    try:
        trail = _get_trail(storage_dir, trail_name)
        # Validate the kind early to give a clean 400 instead of leaking
        # the underlying ValueError later.
        if kind is not None:
            try:
                AuditEventKind(kind)
            except ValueError as e:
                return {"success": False, "error": str(e)}
        results = trail.filter(actor=actor, kind=kind, since=since, until=until)
        return {
            "success": True,
            "events": [e.to_dict() for e in results],
            "count": len(results),
        }
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:  # noqa: BLE001
        logger.exception("events failed")
        return {"success": False, "error": str(e)}


@router.get("/replay/{correlation_id}")
def replay(
    correlation_id: str = PathParam(..., min_length=1, max_length=256),
    storage_dir: str = Query(...),
    trail_name: str = Query("default"),
):
    try:
        trail = _get_trail(storage_dir, trail_name)
        bundle = trail.replay(correlation_id)
        return {"success": True, "bundle": bundle.to_dict()}
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:  # noqa: BLE001
        logger.exception("replay failed")
        return {"success": False, "error": str(e)}


@router.get("/verify")
def verify(storage_dir: str = Query(...), trail_name: str = Query("default")):
    try:
        trail = _get_trail(storage_dir, trail_name)
        report = trail.verify()
        return {"success": True, "integrity": report.to_dict()}
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:  # noqa: BLE001
        logger.exception("verify failed")
        return {"success": False, "error": str(e)}


@router.get("/trails")
def list_trails(storage_dir: str = Query(...)):
    try:
        path = _validate_dir(storage_dir)
        return {"success": True, "trails": AuditTrail.list_trails(path)}
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:  # noqa: BLE001
        logger.exception("list_trails failed")
        return {"success": False, "error": str(e)}
