"""
Carbon Profiler Runner

Reads a carbon ledger from `.workpilot/carbon-ledger.json` (if present)
and produces an aggregated CarbonReport. The ledger format is a list
of records:

    [
      {"source": "llm_cloud", "provider": "anthropic",
       "model": "claude-sonnet-4", "tokens_in": 1200, "tokens_out": 500,
       "duration_s": 4.2, "timestamp": 1705320000},
      {"source": "ci_cd", "duration_s": 320, "runner_type": "standard"},
      ...
    ]

If no ledger exists, returns an empty report so the UI can show
guidance instead of failing.

Output protocol (one JSON object per line, prefixed):
    CARBON_EVENT:{"type": "progress", "data": {"status": "..."}}
    CARBON_RESULT:{...full report dict...}
    CARBON_ERROR:<message>
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

from carbon_profiler.energy_tracker import (  # noqa: E402
    ComputeSource,
    EnergyTracker,
)


def _emit(prefix: str, payload: Any) -> None:
    print(f"{prefix}:{json.dumps(payload, default=str)}", flush=True)


def _emit_event(event_type: str, data: dict[str, Any]) -> None:
    _emit("CARBON_EVENT", {"type": event_type, "data": data})


def _isoformat(ts: float) -> str:
    if not ts:
        return ""
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _record_to_dict(record: Any) -> dict[str, Any]:
    return {
        "source": record.source.value,
        "provider": record.provider,
        "model": record.model,
        "tokensIn": record.tokens_in,
        "tokensOut": record.tokens_out,
        "durationS": record.duration_s,
        "kwh": record.kwh,
        "co2G": record.co2_g,
        "timestamp": _isoformat(record.timestamp),
    }


def _ingest_ledger(tracker: EnergyTracker, ledger: list[dict[str, Any]]) -> None:
    for entry in ledger:
        source = entry.get("source", "llm_cloud")
        if source == "ci_cd":
            tracker.record_ci_run(
                duration_s=float(entry.get("duration_s", 0)),
                runner_type=entry.get("runner_type", "standard"),
            )
        else:
            tracker.record_llm_call(
                provider=entry.get("provider", ""),
                model=entry.get("model", ""),
                tokens_in=int(entry.get("tokens_in", 0)),
                tokens_out=int(entry.get("tokens_out", 0)),
                duration_s=float(entry.get("duration_s", 0)),
                source=ComputeSource(source)
                if source in {s.value for s in ComputeSource}
                else ComputeSource.LLM_CLOUD,
            )


def _empty_result(reason: str) -> dict[str, Any]:
    return {
        "records": [],
        "totalKwh": 0.0,
        "totalCo2G": 0.0,
        "periodStart": "",
        "periodEnd": "",
        "byProvider": {},
        "byModel": {},
        "summary": reason,
    }


def run_scan(project_path: Path, region: str) -> dict[str, Any]:
    _emit_event("start", {"status": "Loading carbon ledger..."})
    ledger_path = project_path / ".workpilot" / "carbon-ledger.json"
    if not ledger_path.exists():
        _emit_event("complete", {"records": 0})
        return _empty_result(
            f"No ledger at {ledger_path}. Record activity to .workpilot/carbon-ledger.json to populate this report."
        )

    try:
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return _empty_result(f"Failed to read ledger: {exc}")

    if not isinstance(ledger, list):
        return _empty_result("Ledger must be a JSON array of records.")

    tracker = EnergyTracker(region=region)
    _ingest_ledger(tracker, ledger)
    _emit_event("progress", {"status": f"Aggregating {len(ledger)} records..."})

    report = tracker.generate_report()
    result = {
        "records": [_record_to_dict(r) for r in report.records],
        "totalKwh": report.total_kwh,
        "totalCo2G": report.total_co2_g,
        "periodStart": _isoformat(report.period_start),
        "periodEnd": _isoformat(report.period_end),
        "byProvider": report.by_provider,
        "byModel": report.by_model,
        "summary": report.summary,
    }
    _emit_event("complete", {"records": len(report.records)})
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Carbon Profiler Runner")
    parser.add_argument("--project-path", required=True, help="Project root path")
    parser.add_argument(
        "--region",
        default="global_avg",
        help="Grid region for carbon intensity (us-east, eu-west, ...)",
    )
    args = parser.parse_args()

    project_path = Path(args.project_path)
    if not project_path.exists():
        _emit("CARBON_ERROR", f"Project path does not exist: {project_path}")
        sys.exit(1)

    try:
        result = run_scan(project_path, args.region)
        _emit("CARBON_RESULT", result)
    except Exception as exc:  # noqa: BLE001
        _emit("CARBON_ERROR", str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
