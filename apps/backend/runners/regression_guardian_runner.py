"""
Regression Guardian Runner

Discovers APM incident payloads under ``<project>/.workpilot/incidents/*.json``
and runs them through the Regression Guardian pipeline (parse → dedup →
generate → fixtures). Returns a list of results ready for the frontend
dashboard.

Output protocol (one JSON object per line, prefixed):
    REGRESSION_GUARDIAN_EVENT:{"type": "progress", "data": {"status": "..."}}
    REGRESSION_GUARDIAN_RESULT:{"results": [...]}
    REGRESSION_GUARDIAN_ERROR:<message>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from regression_guardian import (  # noqa: E402
    DedupChecker,
    Incident,
    PipelineResult,
    TestFramework,
    WebhookHandler,
)

INCIDENTS_SUBDIR = Path(".workpilot") / "incidents"


def _emit(prefix: str, payload: Any) -> None:
    print(f"{prefix}:{json.dumps(payload, default=str)}", flush=True)


def _emit_event(event_type: str, data: dict[str, Any]) -> None:
    _emit("REGRESSION_GUARDIAN_EVENT", {"type": event_type, "data": data})


def _incident_to_dict(incident: Incident) -> dict[str, Any]:
    return {
        "id": incident.id,
        "source": incident.source.value,
        "title": incident.title,
        "severity": incident.severity.value,
        "exceptionType": incident.exception_type,
        "exceptionMessage": incident.exception_message,
        "stackFrames": [
            {
                "file": f.file,
                "function": f.function,
                "line": f.line,
                "column": f.column,
                "context": f.context,
            }
            for f in incident.stack_frames
        ],
        "service": incident.service,
        "environment": incident.environment,
        "faultingFile": incident.faulting_file,
        "faultingFunction": incident.faulting_function,
    }


def _pipeline_result_to_dict(result: PipelineResult) -> dict[str, Any] | None:
    if result.incident is None:
        return None

    generated_test = None
    if result.test is not None:
        generated_test = {
            "incidentId": result.test.incident_id,
            "framework": result.test.framework.value,
            "filePath": result.test.file_path,
            "code": result.test.test_code,
            "isDuplicate": False,
        }

    is_duplicate = bool(result.dedup and result.dedup.is_duplicate)
    duplicate_path = (
        result.dedup.similar_test_path
        if result.dedup and result.dedup.is_duplicate
        else ""
    )
    fixture_data: dict[str, Any] = {}
    if result.fixtures:
        for fix in result.fixtures:
            if hasattr(fix, "name") and hasattr(fix, "data"):
                fixture_data[fix.name] = fix.data

    return {
        "incident": _incident_to_dict(result.incident),
        "generatedTest": generated_test,
        "isDuplicate": is_duplicate,
        "duplicatePath": duplicate_path or "",
        "fixtureData": fixture_data,
    }


def _discover_incidents(project_path: Path) -> list[Path]:
    incidents_dir = project_path / INCIDENTS_SUBDIR
    if not incidents_dir.exists():
        return []
    return sorted(p for p in incidents_dir.glob("*.json") if p.is_file())


def run_scan(project_path: Path) -> dict[str, Any]:
    _emit_event("start", {"status": "Discovering incident payloads..."})
    incident_files = _discover_incidents(project_path)

    if not incident_files:
        _emit_event(
            "complete",
            {"status": "No incidents found", "results": 0},
        )
        return {"results": []}

    _emit_event(
        "progress",
        {"status": f"Processing {len(incident_files)} incident(s)..."},
    )

    handler = WebhookHandler(
        framework=TestFramework.PYTEST,
        dedup_checker=DedupChecker(),
    )
    results: list[dict[str, Any]] = []
    for file_path in incident_files:
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            _emit_event("progress", {"status": f"Skipped {file_path.name}: {exc}"})
            continue

        pipeline_result = handler.handle(payload)
        converted = _pipeline_result_to_dict(pipeline_result)
        if converted is not None:
            results.append(converted)

    _emit_event("complete", {"results": len(results)})
    return {"results": results}


def main() -> None:
    parser = argparse.ArgumentParser(description="Regression Guardian Runner")
    parser.add_argument("--project-path", required=True, help="Project root path")
    args = parser.parse_args()

    project_path = Path(args.project_path)
    if not project_path.exists():
        _emit(
            "REGRESSION_GUARDIAN_ERROR",
            f"Project path does not exist: {project_path}",
        )
        sys.exit(1)

    try:
        result = run_scan(project_path)
        _emit("REGRESSION_GUARDIAN_RESULT", result)
    except Exception as exc:  # noqa: BLE001
        _emit("REGRESSION_GUARDIAN_ERROR", str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
