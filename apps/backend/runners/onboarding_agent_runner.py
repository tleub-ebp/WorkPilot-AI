"""
Onboarding Agent Runner

Runs the OnboardingEngine against a project to generate a contextual
onboarding guide (tech stack, key files, conventions, getting started).

Output protocol (one JSON object per line, prefixed):
    ONBOARDING_EVENT:{"type": "progress", "data": {"status": "..."}}
    ONBOARDING_RESULT:{"guide": {...}}
    ONBOARDING_ERROR:<message>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from onboarding_agent import (  # noqa: E402
    OnboardingEngine,
    OnboardingGuide,
)


def _emit(prefix: str, payload: Any) -> None:
    print(f"{prefix}:{json.dumps(payload, default=str)}", flush=True)


def _emit_event(event_type: str, data: dict[str, Any]) -> None:
    _emit("ONBOARDING_EVENT", {"type": event_type, "data": data})


def _extract_commands(markdown: str) -> list[str]:
    commands: list[str] = []
    for line in markdown.splitlines():
        stripped = line.strip()
        # Strip leading list markers like "1." or "-" then look for backtick code
        match = re.search(r"`([^`]+)`", stripped)
        if match:
            commands.append(match.group(1))
    return commands


def _guide_to_dict(guide: OnboardingGuide) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []

    # Overview step from key files
    if guide.key_files:
        overview_content = "\n".join(
            f"- {kf.path}: {kf.reason}" for kf in guide.key_files
        )
        steps.append(
            {
                "section": "overview",
                "title": "Key files to read first",
                "content": overview_content,
                "commands": [],
                "estimatedMinutes": max(5, len(guide.key_files) * 2),
            }
        )

    # Setup step from getting_started
    getting_started = guide.sections.get("getting_started", "")
    if getting_started:
        steps.append(
            {
                "section": "setup",
                "title": "Getting started",
                "content": getting_started,
                "commands": _extract_commands(getting_started),
                "estimatedMinutes": 10,
            }
        )

    # Conventions step
    if guide.conventions:
        convention_content = "\n".join(
            f"- **{c.name}**: {c.description}" for c in guide.conventions
        )
        steps.append(
            {
                "section": "conventions",
                "title": "Coding conventions",
                "content": convention_content,
                "commands": [],
                "estimatedMinutes": 5,
            }
        )

    total_minutes = (
        sum(int(step.get("estimatedMinutes", 0)) for step in steps)
        or guide.estimated_reading_time_min
    )

    summary = (
        f"{guide.project_name}: {len(guide.tech_stack)} technologies, "
        f"{len(guide.key_files)} key files, {len(guide.conventions)} conventions."
    )

    return {
        "projectName": guide.project_name,
        "techStack": list(guide.tech_stack),
        "steps": steps,
        "totalEstimatedMinutes": total_minutes,
        "generatedAt": datetime.now(tz=timezone.utc).isoformat(),
        "summary": summary,
    }


def run_scan(project_path: Path) -> dict[str, Any]:
    _emit_event("start", {"status": "Analyzing project structure..."})
    engine = OnboardingEngine()
    guide = engine.generate(project_path)
    _emit_event(
        "progress",
        {
            "status": (
                f"Generated guide with {len(guide.key_files)} key file(s) and "
                f"{len(guide.conventions)} convention(s)"
            )
        },
    )
    result = {"guide": _guide_to_dict(guide)}
    _emit_event("complete", {"steps": len(result["guide"]["steps"])})
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Onboarding Agent Runner")
    parser.add_argument("--project-path", required=True, help="Project root path")
    args = parser.parse_args()

    project_path = Path(args.project_path)
    if not project_path.exists():
        _emit("ONBOARDING_ERROR", f"Project path does not exist: {project_path}")
        sys.exit(1)

    try:
        result = run_scan(project_path)
        _emit("ONBOARDING_RESULT", result)
    except Exception as exc:  # noqa: BLE001
        _emit("ONBOARDING_ERROR", str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
