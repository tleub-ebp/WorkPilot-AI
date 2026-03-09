#!/usr/bin/env python3
"""
Learning Loop Runner

Analyzes completed builds to extract success/failure patterns that
optimize future agent behavior. Can be triggered from the frontend UI
or run standalone from CLI.

Stdout protocol: LEARNING_LOOP_EVENT:{json}
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Optional

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
    print(f"LEARNING_LOOP_EVENT:{json.dumps(event, default=str, ensure_ascii=False)}", flush=True)


def emit_status(message: str, progress: int = 0) -> None:
    """Emit a status update."""
    emit_event("status", message=message, data={"progress": progress})


def emit_stream_chunk(chunk: str) -> None:
    """Emit a streaming output chunk."""
    emit_event("stream_chunk", data=chunk)


async def run_analysis(
    project_dir: str,
    spec_id: Optional[str] = None,
    model: str = "sonnet",
    thinking_level: str = "medium",
) -> None:
    """Run learning loop analysis."""
    from learning_loop.service import LearningLoopService

    service = LearningLoopService(
        project_dir=Path(project_dir),
        model=model,
        thinking_level=thinking_level,
    )

    def status_callback(message: str) -> None:
        emit_status(message)
        emit_stream_chunk(f"[Status] {message}\n")

    try:
        if spec_id:
            # Single-build analysis
            spec_dir = Path(project_dir) / ".auto-claude" / "specs" / spec_id
            if not spec_dir.exists():
                emit_event("error", message=f"Spec directory not found: {spec_id}")
                return

            emit_status(f"Analyzing build {spec_id}...", progress=10)
            report = await service.run_post_build_analysis(
                spec_dir=spec_dir,
                status_callback=status_callback,
            )
        else:
            # Full project analysis
            emit_status("Running full project analysis...", progress=10)
            report = await service.run_full_analysis(
                limit=20,
                status_callback=status_callback,
            )

        # Emit results
        emit_status("Analysis complete", progress=100)
        summary = service.get_summary()
        patterns = service.get_patterns()

        emit_event("complete", data={
            "report": report.to_dict(),
            "summary": summary,
            "patterns": patterns,
        })

    except Exception as e:
        emit_event("error", message=str(e))
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Learning Loop Runner")
    parser.add_argument("--project-dir", required=True, help="Path to the project directory")
    parser.add_argument("--spec-id", help="Analyze a specific build (spec ID)")
    parser.add_argument("--model", default="sonnet", help="LLM model to use")
    parser.add_argument("--thinking-level", default="medium", help="Thinking level")
    args = parser.parse_args()

    try:
        asyncio.run(run_analysis(
            project_dir=args.project_dir,
            spec_id=args.spec_id,
            model=args.model,
            thinking_level=args.thinking_level,
        ))
    except KeyboardInterrupt:
        emit_event("error", message="Analysis cancelled by user")
        sys.exit(1)
    except Exception as e:
        emit_event("error", message=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
