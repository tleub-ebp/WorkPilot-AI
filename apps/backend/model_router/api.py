"""HTTP routes for the Adaptive Model Router.

Mounted at `/api/model-router`. Two endpoints:

* `POST /route`     — pick a single model for a task
* `POST /compare`   — return the choice for every quality tier (useful for
                       "would have cost X with Haiku" UI)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .router import ModelRouter, QualityTier

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/model-router", tags=["model-router"])


class RouteRequest(BaseModel):
    prompt: str = Field("", description="The prompt that will be sent to the model.")
    hint: str | None = Field(
        None,
        description="Optional task class override — one of: trivial, simple_edit, "
        "multi_file, architecture, review, planning, ideation, documentation.",
    )
    tier: str | None = Field(
        None,
        description="Optional quality tier override — one of: budget, balanced, premium.",
    )
    expected_output_tokens: int = Field(
        1_000,
        ge=1,
        le=200_000,
        description="Rough estimate used to compute the dollar cost.",
    )
    available: list[str] | None = Field(
        None,
        description="Provider names the user has configured. If omitted, the router "
        "considers any provider with pricing data.",
    )


def _resolve_tier(value: str | None) -> QualityTier | None:
    if not value:
        return None
    try:
        return QualityTier(value.lower())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {value}") from e


@router.post("/route")
def route(req: RouteRequest):
    """Pick the cheapest acceptable model for the requested task."""
    try:
        tier = _resolve_tier(req.tier)
        engine = ModelRouter(available=req.available)
        choice = engine.route(
            prompt=req.prompt,
            hint=req.hint,
            tier=tier,
            expected_output_tokens=req.expected_output_tokens,
        )
        return {"success": True, "choice": choice.to_dict()}
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001 — surface as 500 with safe message
        logger.exception("ModelRouter.route failed")
        return {"success": False, "error": str(e)}


@router.post("/compare")
def compare(req: RouteRequest):
    """Return one ModelChoice per tier — useful for cost-comparison UIs."""
    try:
        engine = ModelRouter(available=req.available)
        comparison = engine.compare(
            prompt=req.prompt,
            hint=req.hint,
            expected_output_tokens=req.expected_output_tokens,
        )
        return {
            "success": True,
            "by_tier": {tier: choice.to_dict() for tier, choice in comparison.items()},
        }
    except Exception as e:  # noqa: BLE001
        logger.exception("ModelRouter.compare failed")
        return {"success": False, "error": str(e)}
