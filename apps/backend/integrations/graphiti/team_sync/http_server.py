"""
Team Knowledge Sync — HTTP Server (Feature 31)
================================================

A minimal FastAPI server that lets team members pull/push memory
snapshots over HTTP when a shared folder is not available.

Start with:
    python runners/team_sync_runner.py --serve --project /path/to/project

Endpoints:
    GET  /status          — Server health + config summary
    GET  /snapshots       — List all snapshots stored on this server
    GET  /snapshots/{id}  — Download a specific member's snapshot
    POST /push            — Upload your local snapshot to this server
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _get_server_dir(project_dir: Path) -> Path:
    """Directory where the HTTP server stores incoming snapshots."""
    d = project_dir / ".workpilot" / "team_sync" / "server"
    d.mkdir(parents=True, exist_ok=True)
    return d


def create_app(project_dir: Path, team_id: str, member_id: str):
    """
    Create and return the FastAPI application.

    Args:
        project_dir: Project root (used to locate stored snapshots)
        team_id:     Team identifier (informational)
        member_id:   This server's owner member ID
    """
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.responses import JSONResponse
    except ImportError as e:
        raise RuntimeError(
            "FastAPI is required for HTTP server mode. "
            "Install it with: pip install fastapi uvicorn"
        ) from e

    app = FastAPI(
        title="WorkPilot Team Knowledge Sync",
        description="Share Graphiti memory snapshots across team members",
        version="1.0.0",
    )

    server_dir = _get_server_dir(project_dir)

    @app.get("/status")
    def get_status() -> dict:
        """Health check and server info."""
        snapshots = list(server_dir.glob("*_snapshot.json"))
        return {
            "status": "ok",
            "team_id": team_id,
            "host_member_id": member_id,
            "snapshot_count": len(snapshots),
            "server_time": datetime.now(timezone.utc).isoformat(),
        }

    @app.get("/snapshots")
    def list_snapshots() -> list[dict]:
        """Return metadata (without full episode list) for all stored snapshots."""
        result: list[dict] = []
        for snap_file in sorted(server_dir.glob("*_snapshot.json")):
            try:
                with open(snap_file, encoding="utf-8") as f:
                    snap: dict = json.load(f)
                # Return full snapshot so peers can import episodes
                result.append(snap)
            except Exception as e:
                logger.warning(f"Could not read {snap_file}: {e}")
        return result

    @app.get("/snapshots/{member}")
    def get_snapshot(member: str) -> Any:
        """Download a specific member's snapshot."""
        snap_file = server_dir / f"{member}_snapshot.json"
        if not snap_file.exists():
            raise HTTPException(
                status_code=404, detail=f"No snapshot for member: {member}"
            )
        try:
            with open(snap_file, encoding="utf-8") as f:
                return JSONResponse(content=json.load(f))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/push")
    async def receive_push(request_body: dict) -> dict:
        """Accept a snapshot upload from a team member."""
        incoming_member = request_body.get("member_id")
        if not incoming_member:
            raise HTTPException(status_code=400, detail="Missing member_id in snapshot")

        # Sanitise filename
        safe_member = "".join(c for c in incoming_member if c.isalnum() or c in "-_.")
        snap_file = server_dir / f"{safe_member}_snapshot.json"

        try:
            with open(snap_file, "w", encoding="utf-8") as f:
                json.dump(request_body, f, indent=2, ensure_ascii=False)
            episode_count = request_body.get("episode_count", 0)
            logger.info(
                f"[TeamSync Server] Received {episode_count} episodes from {incoming_member}"
            )
            return {
                "success": True,
                "stored_as": str(snap_file),
                "episode_count": episode_count,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    return app


def start_server(
    project_dir: Path,
    team_id: str,
    member_id: str,
    host: str = "0.0.0.0",
    port: int = 7749,
) -> None:
    """
    Start the uvicorn server (blocking).

    Args:
        project_dir: Project root directory
        team_id:     Team identifier
        member_id:   This server owner's member ID
        host:        Bind address
        port:        Bind port
    """
    try:
        import uvicorn
    except ImportError as e:
        raise RuntimeError(
            "uvicorn is required to run the HTTP server. "
            "Install it with: pip install uvicorn"
        ) from e

    app = create_app(project_dir, team_id, member_id)
    logger.info(f"[TeamSync] Starting HTTP server on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")
