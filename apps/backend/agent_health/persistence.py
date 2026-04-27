"""Disk persistence + analytics ingest for the AgentHealth monitor.

Two responsibilities:

1. **Persist** the monitor's in-memory ring buffers to JSON on disk so
   they survive process restarts. Format is a single flat file per
   monitor (default: ``.workpilot/agent_health/state.json``).

2. **Ingest** historical agent runs from `analytics/collector.py`'s
   `BuildPhase` table — phases that completed normally become `AgentRun`
   records the monitor can score against, even on a fresh process that
   has no in-memory history yet.

Both are explicit, optional helpers — the base monitor stays pure
in-memory (no I/O dependency).
"""

from __future__ import annotations

import json
import logging
import time
from collections import deque
from pathlib import Path
from typing import Any

from .monitor import AgentRun, HealthMonitor

logger = logging.getLogger(__name__)


_DEFAULT_RELATIVE_PATH = Path(".workpilot") / "agent_health" / "state.json"


# ---------------------------------------------------------------------------
# Disk persistence


def default_state_path(project_dir: str | Path) -> Path:
    return Path(project_dir) / _DEFAULT_RELATIVE_PATH


def save_to_disk(monitor: HealthMonitor, state_path: str | Path) -> Path:
    """Snapshot the monitor's runs + baselines to a JSON file."""
    target = Path(state_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    payload: dict[str, Any] = {
        "version": 1,
        "saved_at": time.time(),
        "window_size": monitor._window_size,  # noqa: SLF001 — internal sync
        "runs": {
            agent: [_run_to_dict(r) for r in list(buf)]
            for agent, buf in monitor._runs.items()
        },
        "baselines": dict(monitor._baselines),
    }
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target


def load_from_disk(monitor: HealthMonitor, state_path: str | Path) -> int:
    """Hydrate `monitor` from disk. Returns the number of runs loaded.

    Does nothing if the state file is missing or unreadable. Existing
    in-memory runs are *replaced* — caller should load before recording
    new ones.
    """
    target = Path(state_path)
    if not target.exists():
        return 0
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Could not read agent_health state at %s: %s", target, e)
        return 0

    if not isinstance(payload, dict) or payload.get("version") != 1:
        logger.warning("Unsupported agent_health state format at %s", target)
        return 0

    monitor._runs.clear()
    monitor._baselines.clear()

    total = 0
    for agent, raw_runs in (payload.get("runs") or {}).items():
        if not isinstance(raw_runs, list):
            continue
        buf: deque[AgentRun] = deque(maxlen=monitor._window_size)
        for raw in raw_runs:
            run = _run_from_dict(raw)
            if run is not None:
                buf.append(run)
                total += 1
        if buf:
            monitor._runs[agent] = buf

    for agent, baseline in (payload.get("baselines") or {}).items():
        try:
            monitor._baselines[agent] = float(baseline)
        except (TypeError, ValueError):
            continue

    return total


def _run_to_dict(run: AgentRun) -> dict[str, Any]:
    return {
        "agent_name": run.agent_name,
        "success": run.success,
        "duration_s": run.duration_s,
        "retries": run.retries,
        "error": run.error,
        "timestamp": run.timestamp,
    }


def _run_from_dict(raw: dict[str, Any]) -> AgentRun | None:
    try:
        return AgentRun(
            agent_name=str(raw["agent_name"]),
            success=bool(raw.get("success", True)),
            duration_s=float(raw.get("duration_s", 0.0)),
            retries=int(raw.get("retries", 0)),
            error=str(raw.get("error", "")),
            timestamp=float(raw.get("timestamp", time.time())),
        )
    except (KeyError, TypeError, ValueError) as e:
        logger.debug("Skipping bad run record: %s", e)
        return None


# ---------------------------------------------------------------------------
# Analytics ingest


def ingest_from_analytics(
    monitor: HealthMonitor,
    *,
    limit: int | None = None,
    spec_id: str | None = None,
) -> int:
    """Backfill the monitor with completed `BuildPhase`s from analytics.

    Each phase becomes one `AgentRun`:
      - `agent_name` = phase.phase_type (planner / coder / qa_reviewer / ...)
      - `success`    = phase.completed_at is not None and not phase.error_message
      - `duration_s` = phase.duration_seconds (0 if never set)
      - `error`      = phase.error_message or ""
      - `timestamp`  = phase.completed_at or phase.started_at (unix)

    Phases without a `phase_type` are skipped — they don't map to an
    agent. Returns the number of runs ingested.
    """
    try:
        from analytics.database import get_db
        from analytics.database_schema import BuildPhase
    except ImportError as e:
        logger.info("analytics module unavailable, skipping ingest: %s", e)
        return 0

    ingested = 0
    db = next(get_db())
    try:
        query = db.query(BuildPhase)
        if spec_id is not None:
            # Phases are joined to builds by build_id, builds carry spec_id.
            from analytics.database_schema import Build  # local import

            query = query.join(Build, Build.id == BuildPhase.build_id).filter(
                Build.spec_id == spec_id
            )
        # Most-recent first — we cap with `limit` and reverse so the
        # ring buffer fills in chronological order.
        query = query.order_by(BuildPhase.started_at.desc())
        if limit:
            query = query.limit(limit)

        for phase in reversed(query.all()):
            agent_name = (phase.phase_type or "").strip()
            if not agent_name:
                continue
            ts = phase.completed_at or phase.started_at
            timestamp = ts.timestamp() if ts is not None else time.time()
            error_msg = phase.error_message or ""
            success = phase.completed_at is not None and not error_msg
            duration = float(phase.duration_seconds or 0.0)
            monitor.record(
                AgentRun(
                    agent_name=agent_name,
                    success=success,
                    duration_s=duration,
                    error=error_msg,
                    timestamp=timestamp,
                )
            )
            ingested += 1
    except Exception as e:
        logger.warning("Analytics ingest failed: %s", e)
    finally:
        try:
            db.close()
        except Exception:
            pass

    return ingested
