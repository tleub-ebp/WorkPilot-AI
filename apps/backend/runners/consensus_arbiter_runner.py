"""
Consensus Arbiter Runner

Discovers persisted agent opinion payloads under
``<project>/.workpilot/agent-opinions/*.json`` and runs them through the
Consensus Arbiter engine to detect and resolve inter-agent conflicts.

Each JSON payload must be a list of opinion objects, e.g.::

    [
      {
        "agent_name": "SecurityAgent",
        "domain": "security",
        "recommendation": "Reject unvalidated input",
        "confidence": 0.9,
        "reasoning": "SQL injection risk",
        "affected_files": ["api/handler.py"]
      }
    ]

Output protocol (one JSON object per line, prefixed):
    CONSENSUS_ARBITER_EVENT:{"type": "progress", "data": {"status": "..."}}
    CONSENSUS_ARBITER_RESULT:{"result": {...}}
    CONSENSUS_ARBITER_ERROR:<message>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from consensus_arbiter import (  # noqa: E402
    AgentDomain,
    AgentOpinion,
    ArbiterEngine,
    Conflict,
    ConsensusResult,
)

OPINIONS_SUBDIR = Path(".workpilot") / "agent-opinions"


def _emit(prefix: str, payload: Any) -> None:
    print(f"{prefix}:{json.dumps(payload, default=str)}", flush=True)


def _emit_event(event_type: str, data: dict[str, Any]) -> None:
    _emit("CONSENSUS_ARBITER_EVENT", {"type": event_type, "data": data})


def _opinion_from_dict(data: dict[str, Any]) -> AgentOpinion:
    domain_raw = str(data.get("domain", "qa")).lower()
    try:
        domain = AgentDomain(domain_raw)
    except ValueError:
        domain = AgentDomain.QA
    return AgentOpinion(
        agent_name=str(data.get("agent_name") or data.get("agentName") or "Unknown"),
        domain=domain,
        recommendation=str(data.get("recommendation", "")),
        confidence=float(data.get("confidence", 0.5)),
        reasoning=str(data.get("reasoning", "")),
        affected_files=list(
            data.get("affected_files") or data.get("affectedFiles") or []
        ),
    )


def _opinion_to_dict(opinion: AgentOpinion) -> dict[str, Any]:
    return {
        "agentName": opinion.agent_name,
        "domain": opinion.domain.value,
        "recommendation": opinion.recommendation,
        "confidence": opinion.confidence,
        "reasoning": opinion.reasoning,
        "affectedFiles": list(opinion.affected_files),
    }


def _conflict_to_dict(conflict: Conflict) -> dict[str, Any]:
    return {
        "topic": conflict.topic,
        "opinions": [_opinion_to_dict(op) for op in conflict.opinions],
        "severity": conflict.severity.value,
        "resolved": conflict.resolved,
        "resolution": conflict.resolution,
        "strategyUsed": conflict.strategy_used.value
        if conflict.strategy_used
        else None,
    }


def _result_to_dict(result: ConsensusResult) -> dict[str, Any]:
    return {
        "conflicts": [_conflict_to_dict(c) for c in result.conflicts],
        "resolvedCount": result.resolved_count,
        "escalatedCount": result.escalated_count,
        "consensusSummary": result.consensus_summary,
        "allResolved": result.all_resolved,
    }


def _discover_opinion_files(project_path: Path) -> list[Path]:
    opinions_dir = project_path / OPINIONS_SUBDIR
    if not opinions_dir.exists():
        return []
    return sorted(p for p in opinions_dir.glob("*.json") if p.is_file())


def run_scan(project_path: Path) -> dict[str, Any]:
    _emit_event("start", {"status": "Discovering agent opinion payloads..."})
    opinion_files = _discover_opinion_files(project_path)

    if not opinion_files:
        _emit_event("complete", {"status": "No opinions found", "results": 0})
        return {
            "result": {
                "conflicts": [],
                "resolvedCount": 0,
                "escalatedCount": 0,
                "consensusSummary": "",
                "allResolved": True,
            }
        }

    opinions: list[AgentOpinion] = []
    for file_path in opinion_files:
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            _emit_event("progress", {"status": f"Skipped {file_path.name}: {exc}"})
            continue

        if isinstance(payload, dict):
            payload = [payload]
        if not isinstance(payload, list):
            continue

        for item in payload:
            if isinstance(item, dict):
                opinions.append(_opinion_from_dict(item))

    _emit_event(
        "progress",
        {"status": f"Arbitrating {len(opinions)} opinion(s)..."},
    )

    engine = ArbiterEngine()
    conflicts = engine.detect_conflicts(opinions)
    result = engine.resolve(conflicts)

    _emit_event("complete", {"results": len(result.conflicts)})
    return {"result": _result_to_dict(result)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Consensus Arbiter Runner")
    parser.add_argument("--project-path", required=True, help="Project root path")
    args = parser.parse_args()

    project_path = Path(args.project_path)
    if not project_path.exists():
        _emit(
            "CONSENSUS_ARBITER_ERROR",
            f"Project path does not exist: {project_path}",
        )
        sys.exit(1)

    try:
        result = run_scan(project_path)
        _emit("CONSENSUS_ARBITER_RESULT", result)
    except Exception as exc:  # noqa: BLE001
        _emit("CONSENSUS_ARBITER_ERROR", str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
