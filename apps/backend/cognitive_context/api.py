"""HTTP routes for the Cognitive Context Optimizer.

Mounted at `/api/cognitive-context`. One endpoint:

* `POST /optimize` — score + slice + pack candidate files into a token budget.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .optimizer import CognitiveContextOptimizer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cognitive-context", tags=["cognitive-context"])


class OptimizeRequest(BaseModel):
    prompt: str = Field("", description="The user task or instruction.")
    candidate_files: list[str] = Field(
        ...,
        description="Absolute paths (or relative to project_dir) of files to consider.",
    )
    project_dir: str | None = Field(
        None,
        description="Optional project root for resolving relative file paths.",
    )
    token_budget: int = Field(8_000, ge=100, le=200_000)
    explicit_mentions: list[str] | None = Field(
        None, description="Filenames the prompt explicitly names — boosted heavily."
    )
    recent_files: list[str] | None = Field(
        None, description="Recently-edited paths — modest score boost."
    )


def _validate_optional_dir(raw: str | None) -> Path | None:
    if not raw:
        return None
    if raw.strip().startswith("-"):
        raise ValueError("project_dir must not start with '-'")
    resolved = Path(raw).expanduser().resolve()
    if not resolved.exists() or not resolved.is_dir():
        raise ValueError(f"project_dir is not a valid directory: {resolved}")
    return resolved


@router.post("/optimize")
def optimize(req: OptimizeRequest):
    try:
        project_dir = _validate_optional_dir(req.project_dir)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    try:
        engine = CognitiveContextOptimizer(project_dir=project_dir)
        result = engine.optimize(
            prompt=req.prompt,
            candidate_files=req.candidate_files,
            token_budget=req.token_budget,
            explicit_mentions=req.explicit_mentions,
            recent_files=req.recent_files,
        )
        return {"success": True, "context": result.to_dict()}
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:  # noqa: BLE001
        logger.exception("optimize failed")
        return {"success": False, "error": str(e)}
