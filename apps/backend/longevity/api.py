"""HTTP routes for the Longevity Scorer.

Mounted at `/api/longevity`. One endpoint:

* `POST /score`  — run a full debt scan + scoring on a project path
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .scorer import score_codebase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/longevity", tags=["longevity"])


class ScoreRequest(BaseModel):
    project_path: str = Field(..., description="Absolute path to the project root.")


def _validate_project_path(raw: str) -> Path:
    """Same defensive validation we apply to other path-taking endpoints."""
    if not raw or not isinstance(raw, str):
        raise ValueError("project_path must be a non-empty string")
    if raw.strip().startswith("-"):
        raise ValueError("project_path must not start with '-'")
    resolved = Path(raw).expanduser().resolve()
    if not resolved.exists():
        raise ValueError(f"project_path does not exist: {resolved}")
    if not resolved.is_dir():
        raise ValueError(f"project_path is not a directory: {resolved}")
    return resolved


@router.post("/score")
def score(req: ScoreRequest):
    """Compute a fresh longevity score for the project at `project_path`."""
    try:
        path = _validate_project_path(req.project_path)
    except ValueError as e:
        return {"success": False, "error": str(e)}
    try:
        report = score_codebase(path)
        return {"success": True, "report": report.to_dict()}
    except Exception as e:  # noqa: BLE001
        logger.exception("LongevityScorer.score_codebase failed")
        return {"success": False, "error": str(e)}
