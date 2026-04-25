"""HTTP routes for the Architecture Drift Detector.

Mounted at `/api/architecture/drift`. Three endpoints:

* `POST /scan`              — run an architecture validation and return the report
* `POST /save-baseline`     — capture the current state as the new baseline
* `POST /compare`           — scan + compare against the saved baseline (drift!)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from architecture.config import infer_architecture_config, load_architecture_config
from architecture.models import ArchitectureReport
from architecture.rules_engine import ArchitectureRulesEngine
from fastapi import APIRouter
from pydantic import BaseModel, Field

from .detector import DriftDetector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/architecture/drift", tags=["architecture-drift"])


class ProjectPathRequest(BaseModel):
    project_path: str = Field(..., description="Absolute path to the project root.")


def _validate_project_path(raw: str) -> Path:
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


def _run_validation(project_dir: Path) -> tuple[ArchitectureReport, str]:
    """Load (or infer) the architecture config and run validation.

    Returns the report and a marker indicating whether config was explicit
    or inferred — the frontend can use that to nudge users to commit a real
    config file.
    """
    config = load_architecture_config(project_dir)
    config_source = "explicit"
    if config is None:
        config = infer_architecture_config(project_dir)
        config_source = "inferred"
    if config is None:
        # Truly nothing to work with — return an empty report rather than
        # crashing, the frontend will display a "no architecture config" state.
        return ArchitectureReport(
            passed=True, summary="No architecture config available"
        ), "none"

    engine = ArchitectureRulesEngine(project_dir, config)
    report = engine.validate()
    report.config_source = config_source
    return report, config_source


@router.post("/scan")
def scan(req: ProjectPathRequest) -> dict[str, Any]:
    """Run the architecture validator on the project. No baseline involved."""
    try:
        path = _validate_project_path(req.project_path)
    except ValueError as e:
        return {"success": False, "error": str(e)}
    try:
        report, source = _run_validation(path)
        return {"success": True, "config_source": source, "report": report.to_dict()}
    except Exception as e:  # noqa: BLE001
        logger.exception("Architecture scan failed")
        return {"success": False, "error": str(e)}


@router.post("/save-baseline")
def save_baseline(req: ProjectPathRequest) -> dict[str, Any]:
    """Snapshot the current architecture report as the new drift baseline."""
    try:
        path = _validate_project_path(req.project_path)
    except ValueError as e:
        return {"success": False, "error": str(e)}
    try:
        report, source = _run_validation(path)
        baseline_path = DriftDetector(project_dir=path).save_baseline(report)
        return {
            "success": True,
            "config_source": source,
            "baseline_path": str(baseline_path),
            "violation_count": len(report.violations) + len(report.warnings),
        }
    except Exception as e:  # noqa: BLE001
        logger.exception("Save baseline failed")
        return {"success": False, "error": str(e)}


@router.post("/compare")
def compare(req: ProjectPathRequest) -> dict[str, Any]:
    """Scan the project and report drift relative to the saved baseline."""
    try:
        path = _validate_project_path(req.project_path)
    except ValueError as e:
        return {"success": False, "error": str(e)}
    try:
        report, source = _run_validation(path)
        drift = DriftDetector(project_dir=path).compare(report)
        return {
            "success": True,
            "config_source": source,
            "drift": drift.to_dict(),
        }
    except Exception as e:  # noqa: BLE001
        logger.exception("Drift compare failed")
        return {"success": False, "error": str(e)}
