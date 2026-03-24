#!/usr/bin/env python3
"""Environment Cloner Runner — Captures and reproduces environments locally.

Can be triggered from the frontend UI or run standalone from CLI.

Stdout protocol: ENV_CLONER_EVENT:{json}

Usage:
    python environment_cloner_runner.py --project-dir /path/to/project --action capture
    python environment_cloner_runner.py --project-dir /path/to/project --action reproduce
    python environment_cloner_runner.py --project-dir /path/to/project --action validate
"""

import argparse
import json
import sys
from pathlib import Path

# Ensure backend is in path
backend_path = Path(__file__).parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))


def emit_event(event_type: str, data: dict | None = None, message: str = "") -> None:
    """Emit a structured event on stdout.

    Args:
        event_type: Event type (status, complete, error).
        data: Optional event data payload.
        message: Optional human-readable message.
    """
    event: dict = {"type": event_type}
    if data is not None:
        event["data"] = data
    if message:
        event["message"] = message
    print(
        f"ENV_CLONER_EVENT:{json.dumps(event, default=str, ensure_ascii=False)}",
        flush=True,
    )


def run_capture(project_dir: str, source: str = "auto") -> None:
    """Capture environment configuration.

    Args:
        project_dir: Path to the project root.
        source: Capture source — 'auto', 'compose', or 'containers'.
    """
    from environment.capturer import EnvironmentCapturer

    capturer = EnvironmentCapturer(Path(project_dir))
    emit_event("status", message="Capturing environment configuration...")

    if source == "containers":
        capture = capturer.capture_from_running_containers()
    else:
        # "auto" or "compose" — try compose first
        capture = capturer.capture_from_compose()
        if not capture.services and source == "auto":
            emit_event(
                "status", message="No compose file found, trying running containers..."
            )
            capture = capturer.capture_from_running_containers()

    # Save capture
    output_dir = Path(project_dir) / ".workpilot" / "environment"
    saved_path = capturer.save_capture(capture, output_dir)

    emit_event(
        "complete",
        data={
            "services_count": len(capture.services),
            "env_vars_count": len(capture.env_vars),
            "source": capture.source,
            "saved_to": str(saved_path),
        },
        message=f"Captured {len(capture.services)} services from {capture.source}",
    )


def run_reproduce(project_dir: str) -> None:
    """Reproduce captured environment via Docker Compose.

    Args:
        project_dir: Path to the project root.
    """
    from environment.capturer import EnvironmentCapture
    from environment.generator import ComposeGenerator

    capture_file = (
        Path(project_dir) / ".workpilot" / "environment" / "environment_capture.json"
    )
    if not capture_file.exists():
        emit_event("error", message="No capture found. Run --env-capture first.")
        return

    emit_event("status", message="Loading captured environment...")

    with open(capture_file, encoding="utf-8") as f:
        data = json.load(f)

    # Reconstruct EnvironmentCapture from dict
    from environment.capturer import ServiceCapture

    services = [
        ServiceCapture(
            name=s.get("name", ""),
            image=s.get("image", ""),
            tag=s.get("tag", "latest"),
            ports=s.get("ports", []),
            environment=s.get("environment", {}),
            volumes=s.get("volumes", []),
            depends_on=s.get("depends_on", []),
            health_check=s.get("health_check", {}),
            command=s.get("command", ""),
        )
        for s in data.get("services", [])
    ]

    capture = EnvironmentCapture(
        project_name=data.get("project_name", ""),
        services=services,
        env_vars=data.get("env_vars", {}),
        networks=data.get("networks", []),
        volumes=data.get("volumes", []),
        source=data.get("source", ""),
        captured_at=data.get("captured_at", ""),
    )

    generator = ComposeGenerator(capture)
    output_dir = Path(project_dir) / ".workpilot" / "environment"
    files = generator.write_all(output_dir)

    emit_event(
        "complete",
        data={"files_generated": [str(f) for f in files]},
        message=f"Generated {len(files)} files in {output_dir}",
    )


def run_validate(project_dir: str) -> None:
    """Validate running cloned environment.

    Args:
        project_dir: Path to the project root.
    """
    from environment.validator import EnvironmentValidator

    emit_event("status", message="Validating environment...")

    validator = EnvironmentValidator(Path(project_dir))
    result = validator.validate(timeout=30)

    emit_event(
        "complete",
        data=result.to_dict(),
        message="Validation passed"
        if result.success
        else f"Validation failed: {', '.join(result.errors)}",
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Environment Cloner Runner")
    parser.add_argument("--project-dir", required=True, help="Project directory")
    parser.add_argument(
        "--action",
        required=True,
        choices=["capture", "reproduce", "validate"],
        help="Action to perform",
    )
    parser.add_argument(
        "--source",
        default="auto",
        choices=["auto", "compose", "containers"],
        help="Capture source (default: auto)",
    )
    args = parser.parse_args()

    try:
        if args.action == "capture":
            run_capture(args.project_dir, args.source)
        elif args.action == "reproduce":
            run_reproduce(args.project_dir)
        elif args.action == "validate":
            run_validate(args.project_dir)
    except Exception as e:
        emit_event("error", message=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
