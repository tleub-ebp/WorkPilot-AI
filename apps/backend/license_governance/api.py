"""HTTP routes for the License Scanner.

Mounted at `/api/license-governance`. Two endpoints:

* `POST /scan`           — discover deps + classify + apply a policy
* `POST /classify`       — classify a single licence string (debugging helper)
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .scanner import (
    DependencyRecord,
    LicenseCategory,
    LicensePolicy,
    LicenseScanner,
    classify_license,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/license-governance", tags=["license-governance"])


def _validate_project_path(raw: str) -> Path:
    if not raw or not isinstance(raw, str):
        raise ValueError("project_path must be a non-empty string")
    if raw.strip().startswith("-"):
        raise ValueError("project_path must not start with '-'")
    resolved = Path(raw).expanduser().resolve()
    if not resolved.exists() or not resolved.is_dir():
        raise ValueError(f"project_path is not a valid directory: {resolved}")
    return resolved


_POLICY_PRESETS = {
    "permissive_only": LicensePolicy.permissive_only,
    "open_source_friendly": LicensePolicy.open_source_friendly,
    "saas_safe": LicensePolicy.saas_safe,
}


class LicenseOverride(BaseModel):
    name: str
    license: str | None = None


class ScanRequest(BaseModel):
    project_path: str = Field(..., description="Project root.")
    policy: str = Field(
        "permissive_only",
        description=(
            "Preset policy: 'permissive_only' (MIT/BSD/Apache/...) | "
            "'open_source_friendly' (+ LGPL/MPL) | 'saas_safe' (alias of permissive_only, "
            "explicitly excludes AGPL)."
        ),
    )
    license_overrides: list[LicenseOverride] | None = Field(
        None,
        description=(
            "Per-package licence overrides — useful when callers already know "
            "a dep's licence (e.g. fetched from the registry). Maps name → licence."
        ),
    )


class ClassifyRequest(BaseModel):
    license: str = Field(..., description="Free-form licence string to classify.")


@router.post("/scan")
def scan(req: ScanRequest):
    try:
        path = _validate_project_path(req.project_path)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    if req.policy not in _POLICY_PRESETS:
        return {
            "success": False,
            "error": f"Unknown policy preset {req.policy!r}; choose one of {sorted(_POLICY_PRESETS)}.",
        }

    overrides = {o.name: o.license for o in (req.license_overrides or [])}

    def resolver(dep: DependencyRecord) -> str | None:
        return overrides.get(dep.name, dep.declared_license)

    try:
        scanner = LicenseScanner(
            project_dir=path,
            policy=_POLICY_PRESETS[req.policy](),
            resolver=resolver,
        )
        report = scanner.scan()
        return {"success": True, "report": report.to_dict()}
    except Exception as e:  # noqa: BLE001
        logger.exception("license scan failed")
        return {"success": False, "error": str(e)}


@router.post("/classify")
def classify(req: ClassifyRequest):
    try:
        cat = classify_license(req.license)
        return {
            "success": True,
            "license": req.license,
            "category": cat.value,
            "is_permissive": cat
            in (LicenseCategory.PERMISSIVE, LicenseCategory.PUBLIC_DOMAIN),
        }
    except Exception as e:  # noqa: BLE001
        logger.exception("classify failed")
        return {"success": False, "error": str(e)}
