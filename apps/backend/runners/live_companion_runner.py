#!/usr/bin/env python3
"""
Live Companion Runner

Runs incremental code analysis on file changes detected by the
Electron file watcher. Called per-change (or batched) from the
main process service.

Stdout protocol: LIVE_COMPANION_EVENT:{json}
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
        f"LIVE_COMPANION_EVENT:{json.dumps(event, default=str, ensure_ascii=False)}",
        flush=True,
    )


def emit_status(message: str) -> None:
    emit_event("status", message=message)


async def analyze_change(
    project_dir: str,
    file_path: str,
    change_type: str,
    diff: str = "",
    model: str = "sonnet",
    thinking_level: str = "low",
) -> None:
    """Analyze a single file change and emit suggestions."""
    from live_companion.analyzer import IncrementalAnalyzer
    from live_companion.types import FileChangeEvent

    analyzer = IncrementalAnalyzer(
        project_dir=project_dir,
        model=model,
        thinking_level=thinking_level,
    )

    event = FileChangeEvent(
        file_path=file_path,
        change_type=change_type,
        diff=diff,
    )

    try:
        suggestions = await analyzer.analyze_change(event)

        emit_event(
            "complete",
            data={
                "suggestions": [s.to_dict() for s in suggestions],
                "file_path": file_path,
                "change_type": change_type,
            },
        )
    except Exception as e:
        emit_event("error", message=str(e))
        sys.exit(1)


async def analyze_batch(
    project_dir: str,
    changes_file: str,
    model: str = "sonnet",
    thinking_level: str = "low",
) -> None:
    """Analyze a batch of file changes from a JSON file."""
    from live_companion.analyzer import IncrementalAnalyzer
    from live_companion.types import FileChangeEvent

    analyzer = IncrementalAnalyzer(
        project_dir=project_dir,
        model=model,
        thinking_level=thinking_level,
    )

    try:
        changes_path = Path(changes_file)
        if not changes_path.exists():
            emit_event("error", message=f"Changes file not found: {changes_file}")
            sys.exit(1)

        changes_data = json.loads(changes_path.read_text(encoding="utf-8"))
        all_suggestions = []

        for change in changes_data.get("changes", []):
            event = FileChangeEvent.from_dict(change)
            suggestions = await analyzer.analyze_change(event)
            all_suggestions.extend(suggestions)

        emit_event(
            "complete",
            data={
                "suggestions": [s.to_dict() for s in all_suggestions],
                "files_analyzed": len(changes_data.get("changes", [])),
            },
        )
    except Exception as e:
        emit_event("error", message=str(e))
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Live Companion Runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # analyze-change: single file change
    change_parser = subparsers.add_parser(
        "analyze-change", help="Analyze a single file change"
    )
    change_parser.add_argument("--project-dir", required=True, help="Project directory")
    change_parser.add_argument("--file-path", required=True, help="Changed file path")
    change_parser.add_argument(
        "--change-type",
        required=True,
        choices=["created", "modified", "deleted", "renamed"],
        help="Type of change",
    )
    change_parser.add_argument("--diff", default="", help="File diff content")
    change_parser.add_argument("--model", default="sonnet", help="LLM model")
    change_parser.add_argument("--thinking-level", default="low", help="Thinking level")

    # analyze-batch: batch of changes
    batch_parser = subparsers.add_parser(
        "analyze-batch", help="Analyze a batch of file changes"
    )
    batch_parser.add_argument("--project-dir", required=True, help="Project directory")
    batch_parser.add_argument(
        "--changes-file", required=True, help="JSON file with changes"
    )
    batch_parser.add_argument("--model", default="sonnet", help="LLM model")
    batch_parser.add_argument("--thinking-level", default="low", help="Thinking level")

    args = parser.parse_args()

    try:
        if args.command == "analyze-change":
            asyncio.run(
                analyze_change(
                    project_dir=args.project_dir,
                    file_path=args.file_path,
                    change_type=args.change_type,
                    diff=args.diff,
                    model=args.model,
                    thinking_level=args.thinking_level,
                )
            )
        elif args.command == "analyze-batch":
            asyncio.run(
                analyze_batch(
                    project_dir=args.project_dir,
                    changes_file=args.changes_file,
                    model=args.model,
                    thinking_level=args.thinking_level,
                )
            )
    except KeyboardInterrupt:
        emit_event("error", message="Operation cancelled")
        sys.exit(1)
    except Exception as e:
        emit_event("error", message=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
