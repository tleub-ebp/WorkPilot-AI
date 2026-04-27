"""HTTP routes for the Domain-Specific Agent Factory.

Mounted at `/api/domain-agents`. Three endpoints:

* `GET  /domains`              — list available domains (UI dropdown)
* `GET  /profile/{domain}`     — full profile for one domain
* `POST /build`                — compose a bundle for (domain, role)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Path
from pydantic import BaseModel, Field

from .factory import DomainAgentFactory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/domain-agents", tags=["domain-agents"])


class BuildRequest(BaseModel):
    domain: str = Field(..., description="Domain tag, e.g. 'fintech', 'healthcare'.")
    role: str = Field(
        ..., description="Agent role: 'coder' | 'planner' | 'reviewer' | 'documenter'."
    )


@router.get("/domains")
def list_domains():
    try:
        return {"success": True, "domains": DomainAgentFactory().list_domains()}
    except Exception as e:  # noqa: BLE001
        logger.exception("list_domains failed")
        return {"success": False, "error": str(e)}


@router.get("/profile/{domain}")
def profile(domain: str = Path(..., min_length=1, max_length=64)):
    try:
        p = DomainAgentFactory().get_profile(domain)
        return {"success": True, "profile": p.to_dict()}
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:  # noqa: BLE001
        logger.exception("profile failed")
        return {"success": False, "error": str(e)}


@router.post("/build")
def build(req: BuildRequest):
    try:
        bundle = DomainAgentFactory().build(req.domain, req.role)
        return {"success": True, "bundle": bundle.to_dict()}
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:  # noqa: BLE001
        logger.exception("build failed")
        return {"success": False, "error": str(e)}
