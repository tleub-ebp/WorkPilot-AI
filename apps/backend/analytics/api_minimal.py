"""Minimal fallback router for the Analytics API.

This module is **only mounted when the real DB-backed implementation in
``analytics.api_simple`` fails to initialize** (e.g. missing SQLAlchemy
at runtime, corrupted database file, permission error on the analytics
SQLite file). Wiring lives in ``apps/backend/provider_api.py`` — see the
``try / except`` around ``init_database``.

Previously this module returned zeros for every metric, which looked
like a healthy-but-empty dashboard. That was misleading: the frontend
had no way to tell that analytics were actually *disabled*. We now
return HTTP 503 with a clear reason so the UI can render a proper
"analytics offline" state instead of fake-empty charts.

The ``/health`` endpoint stays as a 200 response so the frontend can
detect the fallback from probes without needing special error handling.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/analytics", tags=["analytics"])

_FALLBACK_REASON = (
    "Analytics database is not available. The real DB-backed router "
    "failed to initialize — see the backend log for the init error. "
    "Start the backend with a writable ``data/analytics.db`` to restore "
    "live analytics."
)


def _analytics_unavailable() -> HTTPException:
    """Build the 503 response used by every data endpoint."""
    return HTTPException(
        status_code=503,
        detail={
            "error": "analytics_unavailable",
            "reason": _FALLBACK_REASON,
        },
    )


@router.get("/overview")
async def get_dashboard_overview(
    days: int = Query(default=30, ge=1, le=365),  # noqa: ARG001 — accepted for API parity
):
    """Return 503 — analytics DB unavailable (fallback router)."""
    raise _analytics_unavailable()


@router.get("/builds")
async def get_builds(
    limit: int = Query(default=50, ge=1, le=100),  # noqa: ARG001
    offset: int = Query(default=0, ge=0),  # noqa: ARG001
    status: str | None = Query(default=None),  # noqa: ARG001
    spec_id: str | None = Query(default=None),  # noqa: ARG001
):
    raise _analytics_unavailable()


@router.get("/builds/{build_id}")
async def get_build_details(build_id: str):  # noqa: ARG001
    raise _analytics_unavailable()


@router.get("/metrics/tokens")
async def get_token_metrics(days: int = Query(default=30, ge=1, le=365)):  # noqa: ARG001
    raise _analytics_unavailable()


@router.get("/metrics/qa")
async def get_qa_metrics(days: int = Query(default=30, ge=1, le=365)):  # noqa: ARG001
    raise _analytics_unavailable()


@router.get("/metrics/agent-performance")
async def get_agent_performance(days: int = Query(default=30, ge=1, le=365)):  # noqa: ARG001
    raise _analytics_unavailable()


@router.get("/metrics/errors")
async def get_error_metrics(days: int = Query(default=30, ge=1, le=365)):  # noqa: ARG001
    raise _analytics_unavailable()


@router.get("/specs")
async def get_specs_summary():
    raise _analytics_unavailable()


@router.get("/health")
async def health_check():
    """Tell callers which router they're talking to.

    Returns 200 even in fallback mode so the frontend can tell the
    difference between "backend is down" and "analytics is in fallback
    mode".
    """
    return {
        "status": "degraded",
        "mode": "fallback",
        "reason": _FALLBACK_REASON,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
