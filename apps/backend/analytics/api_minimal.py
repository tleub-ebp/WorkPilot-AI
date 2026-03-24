"""
Minimal Analytics API endpoints for the Build Analytics Dashboard.
This version doesn't depend on database to avoid initialization issues.
"""

from datetime import datetime

from fastapi import APIRouter, Query

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
async def get_dashboard_overview(days: int = Query(default=30, ge=1, le=365)):
    """Get dashboard overview with key metrics (mock data for now)."""
    # Return mock data for testing
    return {
        "total_builds": 0,
        "successful_builds": 0,
        "success_rate": 0.0,
        "total_tokens_used": 0,
        "total_cost_usd": 0.0,
        "avg_build_duration": 0.0,
        "recent_builds": [],
        "top_error_types": [],
        "phase_performance": [],
    }


@router.get("/builds")
async def get_builds(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: str | None = Query(default=None),
    spec_id: str | None = Query(default=None),
):
    """Get paginated list of builds with optional filtering (mock data)."""
    return []


@router.get("/builds/{build_id}")
async def get_build_details(build_id: str):
    """Get detailed information about a specific build (mock data)."""
    return {"build": None, "phases": [], "qa_results": [], "errors": []}


@router.get("/metrics/tokens")
async def get_token_metrics(days: int = Query(default=30, ge=1, le=365)):
    """Get token usage metrics over time (mock data)."""
    return []


@router.get("/metrics/qa")
async def get_qa_metrics(days: int = Query(default=30, ge=1, le=365)):
    """Get QA performance metrics over time (mock data)."""
    return []


@router.get("/metrics/agent-performance")
async def get_agent_performance(days: int = Query(default=30, ge=1, le=365)):
    """Get agent performance metrics (mock data)."""
    return []


@router.get("/metrics/errors")
async def get_error_metrics(days: int = Query(default=30, ge=1, le=365)):
    """Get error metrics and patterns (mock data)."""
    return []


@router.get("/specs")
async def get_specs_summary():
    """Get summary of all specs and their performance (mock data)."""
    return []


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
