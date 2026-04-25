"""HTTP routes for the Generational Test Archive.

Mounted at `/api/generational-tests`. Endpoints:

* `GET  /list?project_path=...`           — list all generations
* `POST /capture`                         — store a new generation from JUnit XML
* `POST /compare`                         — diff a fresh JUnit XML against a baseline
* `DELETE /{label}?project_path=...`      — drop a stored generation
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from .archive import GenerationalArchive

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/generational-tests", tags=["generational-tests"])


def _validate_project_path(raw: str) -> Path:
    if not raw or not isinstance(raw, str):
        raise ValueError("project_path must be a non-empty string")
    if raw.strip().startswith("-"):
        raise ValueError("project_path must not start with '-'")
    resolved = Path(raw).expanduser().resolve()
    if not resolved.exists() or not resolved.is_dir():
        raise ValueError(f"project_path is not a valid directory: {resolved}")
    return resolved


class CaptureRequest(BaseModel):
    project_path: str = Field(..., description="Project root.")
    label: str = Field(
        ..., description="Stable name for this generation (e.g. 'release-1.2.0')."
    )
    junit_xml: str = Field(..., description="The JUnit XML report content.")


class CompareRequest(BaseModel):
    project_path: str = Field(..., description="Project root.")
    baseline_label: str = Field(
        ..., description="Label of the generation to diff against."
    )
    current_junit_xml: str = Field(..., description="JUnit XML of the current run.")


@router.get("/list")
def list_generations(project_path: str = Query(...)):
    try:
        path = _validate_project_path(project_path)
    except ValueError as e:
        return {"success": False, "error": str(e)}
    try:
        archive = GenerationalArchive(project_dir=path)
        return {"success": True, "generations": archive.list_generations()}
    except Exception as e:  # noqa: BLE001
        logger.exception("list_generations failed")
        return {"success": False, "error": str(e)}


@router.post("/capture")
def capture(req: CaptureRequest):
    try:
        path = _validate_project_path(req.project_path)
    except ValueError as e:
        return {"success": False, "error": str(e)}
    try:
        archive = GenerationalArchive(project_dir=path)
        gen = archive.capture(req.label, junit_xml=req.junit_xml)
        return {
            "success": True,
            "label": gen.label,
            "outcome_count": len(gen.outcomes),
            "passing_count": len(gen.passing_ids),
        }
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:  # noqa: BLE001
        logger.exception("capture failed")
        return {"success": False, "error": str(e)}


@router.post("/compare")
def compare(req: CompareRequest):
    try:
        path = _validate_project_path(req.project_path)
    except ValueError as e:
        return {"success": False, "error": str(e)}
    try:
        archive = GenerationalArchive(project_dir=path)
        report = archive.compare(
            req.baseline_label, current_junit_xml=req.current_junit_xml
        )
        return {"success": True, "report": report.to_dict()}
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:  # noqa: BLE001
        logger.exception("compare failed")
        return {"success": False, "error": str(e)}


@router.delete("/{label}")
def delete(label: str, project_path: str = Query(...)):
    try:
        path = _validate_project_path(project_path)
    except ValueError as e:
        return {"success": False, "error": str(e)}
    try:
        archive = GenerationalArchive(project_dir=path)
        deleted = archive.delete(label)
        return {"success": True, "deleted": deleted}
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:  # noqa: BLE001
        logger.exception("delete failed")
        return {"success": False, "error": str(e)}
