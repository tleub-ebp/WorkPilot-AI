"""
Spec Refinement Runner

Discovers persisted refinement histories under
``<project>/.workpilot/refinement-histories/*.json`` and returns them in the
canonical shape consumed by the frontend store.

Output protocol (one JSON object per line, prefixed):
    SPEC_REFINEMENT_EVENT:{"type": "progress", "data": {"status": "..."}}
    SPEC_REFINEMENT_RESULT:{"histories": [...]}
    SPEC_REFINEMENT_ERROR:<message>
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from spec_refinement import (  # noqa: E402
    FeedbackSignal,
    RefinementEngine,
    RefinementHistory,
    RefinementIteration,
    RefinementStatus,
    SignalType,
)

HISTORIES_SUBDIR = Path(".workpilot") / "refinement-histories"


def _emit(prefix: str, payload: Any) -> None:
    print(f"{prefix}:{json.dumps(payload, default=str)}", flush=True)


def _emit_event(event_type: str, data: dict[str, Any]) -> None:
    _emit("SPEC_REFINEMENT_EVENT", {"type": event_type, "data": data})


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _signal_to_dict(signal: FeedbackSignal) -> dict[str, Any]:
    return {
        "signalType": signal.signal_type.value,
        "source": signal.source,
        "message": signal.message,
        "severity": signal.severity,
        "timestamp": _iso(signal.timestamp),
    }


def _iteration_to_dict(it: RefinementIteration) -> dict[str, Any]:
    return {
        "iteration": it.iteration,
        "signals": [_signal_to_dict(s) for s in it.signals],
        "changesMade": list(it.changes_made),
        "qualityScore": it.quality_score,
        "timestamp": _iso(it.timestamp),
    }


def _history_to_dict(history: RefinementHistory) -> dict[str, Any]:
    return {
        "specId": history.spec_id,
        "iterations": [_iteration_to_dict(it) for it in history.iterations],
        "status": history.status.value,
        "convergenceScore": history.convergence_score,
        "currentIteration": history.current_iteration,
        "isConverging": history.is_converging,
        "summary": history.summary,
    }


def _parse_signal(raw: dict[str, Any]) -> FeedbackSignal | None:
    try:
        return FeedbackSignal(
            signal_type=SignalType(raw.get("signalType", raw.get("signal_type"))),
            source=str(raw.get("source", "")),
            message=str(raw.get("message", "")),
            severity=str(raw.get("severity", "medium")),
        )
    except (ValueError, KeyError):
        return None


def _parse_iteration(raw: dict[str, Any]) -> RefinementIteration:
    signals_raw = raw.get("signals", []) or []
    signals = [s for s in (_parse_signal(s) for s in signals_raw) if s is not None]
    return RefinementIteration(
        iteration=int(raw.get("iteration", 0)),
        spec_snapshot=str(raw.get("specSnapshot", raw.get("spec_snapshot", ""))),
        signals=signals,
        changes_made=list(raw.get("changesMade", raw.get("changes_made", []))),
        quality_score=float(raw.get("qualityScore", raw.get("quality_score", 0.0))),
    )


def _load_history(file_path: Path) -> RefinementHistory | None:
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None

    spec_id = str(data.get("specId", data.get("spec_id", file_path.stem)))
    iterations_raw = data.get("iterations", []) or []
    iterations = [_parse_iteration(it) for it in iterations_raw]

    history = RefinementHistory(
        spec_id=spec_id,
        iterations=iterations,
    )

    try:
        status_value = data.get("status", "draft")
        history.status = RefinementStatus(status_value)
    except ValueError:
        history.status = RefinementStatus.DRAFT

    history.convergence_score = float(
        data.get("convergenceScore", data.get("convergence_score", 0.0))
    )
    return history


def _discover_histories(project_path: Path) -> list[Path]:
    histories_dir = project_path / HISTORIES_SUBDIR
    if not histories_dir.exists():
        return []
    return sorted(p for p in histories_dir.glob("*.json") if p.is_file())


def run_scan(project_path: Path) -> dict[str, Any]:
    _emit_event("start", {"status": "Discovering refinement histories..."})
    history_files = _discover_histories(project_path)

    if not history_files:
        _emit_event(
            "complete",
            {"status": "No refinement histories found", "histories": 0},
        )
        return {"histories": []}

    _emit_event(
        "progress",
        {"status": f"Found {len(history_files)} history file(s), parsing..."},
    )

    engine = RefinementEngine()
    histories: list[dict[str, Any]] = []
    for file_path in history_files:
        history = _load_history(file_path)
        if history is None:
            _emit_event(
                "progress", {"status": f"Skipped unreadable file {file_path.name}"}
            )
            continue
        # Refresh convergence based on current iterations
        if len(history.iterations) >= 2:
            engine._update_convergence(history)  # noqa: SLF001
        histories.append(_history_to_dict(history))

    _emit_event("complete", {"histories": len(histories)})
    return {"histories": histories}


def main() -> None:
    parser = argparse.ArgumentParser(description="Spec Refinement Runner")
    parser.add_argument("--project-path", required=True, help="Project root path")
    args = parser.parse_args()

    project_path = Path(args.project_path)
    if not project_path.exists():
        _emit("SPEC_REFINEMENT_ERROR", f"Project path does not exist: {project_path}")
        sys.exit(1)

    try:
        result = run_scan(project_path)
        _emit("SPEC_REFINEMENT_RESULT", result)
    except Exception as exc:  # noqa: BLE001
        _emit("SPEC_REFINEMENT_ERROR", str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
