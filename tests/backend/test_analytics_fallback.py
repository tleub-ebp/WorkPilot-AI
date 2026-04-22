"""Tests for the analytics fallback router (``api_minimal``).

The fallback previously returned zeros for every metric, which the
frontend could not distinguish from a legitimately empty dataset. The
updated version surfaces a 503 on every data endpoint and flags
``mode: "fallback"`` on ``/health``. These tests lock that contract.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[2] / "apps" / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


@pytest.fixture(scope="module")
def client():
    from analytics.api_minimal import router  # noqa: E402 — backend path set above
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.mark.parametrize(
    "path",
    [
        "/analytics/overview",
        "/analytics/builds",
        "/analytics/builds/some-id",
        "/analytics/metrics/tokens",
        "/analytics/metrics/qa",
        "/analytics/metrics/agent-performance",
        "/analytics/metrics/errors",
        "/analytics/specs",
    ],
)
def test_data_endpoints_return_503(client, path: str) -> None:
    """Every data endpoint returns 503 with the ``analytics_unavailable`` tag."""
    response = client.get(path)
    assert response.status_code == 503, (
        f"{path} should return 503 in fallback mode, got {response.status_code}"
    )
    body = response.json()
    assert body["detail"]["error"] == "analytics_unavailable"
    assert "reason" in body["detail"]


def test_health_endpoint_reports_fallback_mode(client) -> None:
    """``/health`` stays 200 but flags the fallback so the UI can adapt."""
    response = client.get("/analytics/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["mode"] == "fallback"
    assert "reason" in body
    assert "timestamp" in body
