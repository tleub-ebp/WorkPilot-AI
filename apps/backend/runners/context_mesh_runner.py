#!/usr/bin/env python3
"""
Context Mesh Runner

Runs cross-project intelligence analysis to detect patterns, generate
engineering handbook entries, identify skill transfers, and produce
contextual recommendations across all registered projects.

Stdout protocol: CONTEXT_MESH_EVENT:{json}
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# Add the apps/backend directory to the Python path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))


def emit_event(event_type: str, data: Any = None, message: str = "") -> None:
    """Emit a structured event to stdout for frontend consumption."""
    event = {"type": event_type}
    if data is not None:
        event["data"] = data
    if message:
        event["message"] = message
    print(
        f"CONTEXT_MESH_EVENT:{json.dumps(event, default=str, ensure_ascii=False)}",
        flush=True,
    )


def emit_status(message: str, progress: int = 0) -> None:
    """Emit a status update."""
    emit_event("status", message=message, data={"progress": progress})


def emit_stream_chunk(chunk: str) -> None:
    """Emit a streaming output chunk."""
    emit_event("stream_chunk", data=chunk)


# ── Commands ────────────────────────────────────────────────────


async def run_analysis(
    model: str = "sonnet",
    thinking_level: str = "medium",
) -> None:
    """Run full cross-project mesh analysis."""
    from context_mesh.mesh_service import ContextMeshService
    from context_mesh.storage import ContextMeshStorage

    storage = ContextMeshStorage()
    service = ContextMeshService(
        storage=storage,
        model=model,
        thinking_level=thinking_level,
    )

    def status_callback(message: str) -> None:
        emit_status(message)
        emit_stream_chunk(f"[Status] {message}\n")

    try:
        report = await service.run_analysis(status_callback=status_callback)

        emit_status("Analysis complete", progress=100)
        summary = storage.get_summary()

        emit_event(
            "complete",
            data={
                "report": report.to_dict(),
                "summary": summary,
            },
        )

    except Exception as e:
        emit_event("error", message=str(e))
        sys.exit(1)


async def register_project(project_path: str) -> None:
    """Register a project in the context mesh."""
    from context_mesh.mesh_service import ContextMeshService

    service = ContextMeshService()

    try:
        project = service.register_project(project_path)
        emit_event(
            "complete",
            data={"project": project.to_dict()},
            message=f"Registered project: {project.project_name}",
        )
    except Exception as e:
        emit_event("error", message=str(e))
        sys.exit(1)


async def unregister_project(project_path: str) -> None:
    """Unregister a project from the context mesh."""
    from context_mesh.mesh_service import ContextMeshService

    service = ContextMeshService()

    try:
        service.unregister_project(project_path)
        emit_event(
            "complete",
            message=f"Unregistered project: {project_path}",
        )
    except Exception as e:
        emit_event("error", message=str(e))
        sys.exit(1)


async def get_summary() -> None:
    """Get mesh summary."""
    from context_mesh.storage import ContextMeshStorage

    storage = ContextMeshStorage()

    try:
        summary = storage.get_summary()
        emit_event("complete", data={"summary": summary})
    except Exception as e:
        emit_event("error", message=str(e))
        sys.exit(1)


async def get_recommendations(project_path: str, phase: str = "") -> None:
    """Get recommendations for a project."""
    from context_mesh.mesh_service import ContextMeshService

    service = ContextMeshService()

    try:
        recs = await service.get_recommendations_for_project(
            project_path=project_path,
            phase=phase,
        )
        emit_event(
            "complete",
            data={"recommendations": [r.to_dict() for r in recs]},
        )
    except Exception as e:
        emit_event("error", message=str(e))
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Context Mesh Runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Run cross-project analysis")
    analyze_parser.add_argument("--model", default="sonnet", help="LLM model to use")
    analyze_parser.add_argument(
        "--thinking-level", default="medium", help="Thinking level"
    )

    # register command
    register_parser = subparsers.add_parser("register", help="Register a project")
    register_parser.add_argument(
        "--project-dir", required=True, help="Path to the project"
    )

    # unregister command
    unregister_parser = subparsers.add_parser("unregister", help="Unregister a project")
    unregister_parser.add_argument(
        "--project-dir", required=True, help="Path to the project"
    )

    # summary command
    subparsers.add_parser("summary", help="Get mesh summary")

    # recommendations command
    recs_parser = subparsers.add_parser(
        "recommendations", help="Get recommendations for a project"
    )
    recs_parser.add_argument("--project-dir", required=True, help="Path to the project")
    recs_parser.add_argument("--phase", default="", help="Filter by phase")

    args = parser.parse_args()

    try:
        if args.command == "analyze":
            asyncio.run(
                run_analysis(
                    model=args.model,
                    thinking_level=args.thinking_level,
                )
            )
        elif args.command == "register":
            asyncio.run(register_project(args.project_dir))
        elif args.command == "unregister":
            asyncio.run(unregister_project(args.project_dir))
        elif args.command == "summary":
            asyncio.run(get_summary())
        elif args.command == "recommendations":
            asyncio.run(
                get_recommendations(
                    project_path=args.project_dir,
                    phase=args.phase,
                )
            )
    except KeyboardInterrupt:
        emit_event("error", message="Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        emit_event("error", message=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
