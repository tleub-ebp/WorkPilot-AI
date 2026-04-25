"""HTTP routes for the CI/CD Anomaly Detective.

Mounted at `/api/cicd-anomaly`. Two endpoints:

* `POST /scan`     — scan one log blob
* `POST /analyse`  — scan many logs and surface recurring patterns
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .detective import AnomalyDetective

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cicd-anomaly", tags=["cicd-anomaly"])


class LogSample(BaseModel):
    label: str = Field("", description="Human-readable label, e.g. 'build-1234'.")
    text: str = Field(..., description="Raw log content.")


class ScanRequest(BaseModel):
    log: str = Field(..., description="The CI log to scan.")
    label: str = Field("", description="Optional label propagated to signals.")


class AnalyseRequest(BaseModel):
    samples: list[LogSample] = Field(
        ..., description="One entry per log to analyse. Empty list = empty report."
    )


@router.post("/scan")
def scan(req: ScanRequest):
    try:
        signals = AnomalyDetective().scan(req.log, log_label=req.label)
        return {
            "success": True,
            "signal_count": len(signals),
            "signals": [s.to_dict() for s in signals],
        }
    except Exception as e:  # noqa: BLE001
        logger.exception("scan failed")
        return {"success": False, "error": str(e)}


@router.post("/analyse")
def analyse(req: AnalyseRequest):
    try:
        report = AnomalyDetective().analyse([(s.label, s.text) for s in req.samples])
        return {"success": True, "report": report.to_dict()}
    except Exception as e:  # noqa: BLE001
        logger.exception("analyse failed")
        return {"success": False, "error": str(e)}
