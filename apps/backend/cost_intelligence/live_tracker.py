"""
Live Cost Tracker — Real-time token/cost accumulator.

Every LLM call increments a live counter keyed by (scope, scope_id).
Scopes: organisation, project, spec.  The tracker stores data in SQLite
(WAL mode) for persistence and exposes snapshots for the UI.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .catalog import PricingCatalog

logger = logging.getLogger(__name__)


@dataclass
class CostEvent:
    """A single cost event from an LLM call."""

    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0
    thinking_tokens: int = 0
    cost_usd: float = 0.0
    scope: str = "spec"  # organisation | project | spec
    scope_id: str = ""
    agent_id: str = ""
    timestamp: float = field(default_factory=time.time)
    is_retry: bool = False  # Retries due to rate limits are not counted


@dataclass
class TrackerSnapshot:
    """Current state of a tracked scope."""

    scope: str
    scope_id: str
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    event_count: int = 0
    last_updated: float = 0.0


class LiveCostTracker:
    """Real-time cost tracker with in-memory accumulation and SQLite persistence.

    Usage::

        tracker = LiveCostTracker(catalog)
        tracker.record(CostEvent(provider="anthropic", model="claude-sonnet-4-6",
                                 input_tokens=1000, output_tokens=500,
                                 scope="spec", scope_id="spec-001"))
        snapshot = tracker.get_snapshot("spec", "spec-001")
        print(f"Total cost: ${snapshot.total_cost_usd:.4f}")
    """

    def __init__(
        self,
        catalog: PricingCatalog | None = None,
        db_path: Path | None = None,
    ) -> None:
        self._catalog = catalog or PricingCatalog()
        self._lock = threading.Lock()
        self._snapshots: dict[str, TrackerSnapshot] = {}
        self._events: list[CostEvent] = []
        self._db_path = db_path
        if db_path:
            self._init_db()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record(self, event: CostEvent) -> CostEvent:
        """Record an LLM cost event. Skips failed retries.

        If ``event.cost_usd`` is 0 and tokens are provided, cost is
        calculated from the catalog.
        """
        if event.is_retry:
            logger.debug("Skipping retry event for %s/%s", event.provider, event.model)
            return event

        # Auto-calculate cost if not provided
        if event.cost_usd == 0.0 and (event.input_tokens or event.output_tokens):
            event.cost_usd = self._catalog.calculate_cost(
                provider=event.provider,
                model=event.model,
                input_tokens=event.input_tokens,
                output_tokens=event.output_tokens,
                cache_write_tokens=event.cache_write_tokens,
                cache_read_tokens=event.cache_read_tokens,
                thinking_tokens=event.thinking_tokens,
            )

        key = f"{event.scope}:{event.scope_id}"

        with self._lock:
            if key not in self._snapshots:
                self._snapshots[key] = TrackerSnapshot(
                    scope=event.scope, scope_id=event.scope_id
                )

            snap = self._snapshots[key]
            snap.total_input_tokens += event.input_tokens
            snap.total_output_tokens += event.output_tokens
            snap.total_cost_usd += event.cost_usd
            snap.event_count += 1
            snap.last_updated = event.timestamp
            self._events.append(event)

        if self._db_path:
            self._persist_event(event)

        return event

    def get_snapshot(self, scope: str, scope_id: str) -> TrackerSnapshot:
        """Get current snapshot for a scope. Returns empty snapshot if not found."""
        key = f"{scope}:{scope_id}"
        with self._lock:
            return self._snapshots.get(
                key, TrackerSnapshot(scope=scope, scope_id=scope_id)
            )

    def get_total_cost(self, scope: str, scope_id: str) -> float:
        """Get total USD cost for a scope."""
        return self.get_snapshot(scope, scope_id).total_cost_usd

    def get_all_snapshots(self) -> list[TrackerSnapshot]:
        """Get all tracked snapshots."""
        with self._lock:
            return list(self._snapshots.values())

    def get_events(
        self, scope: str | None = None, scope_id: str | None = None
    ) -> list[CostEvent]:
        """Get events, optionally filtered by scope."""
        with self._lock:
            events = list(self._events)
        if scope:
            events = [e for e in events if e.scope == scope]
        if scope_id:
            events = [e for e in events if e.scope_id == scope_id]
        return events

    def reset(self, scope: str | None = None, scope_id: str | None = None) -> None:
        """Reset tracked data. If scope provided, only reset that scope."""
        with self._lock:
            if scope and scope_id:
                key = f"{scope}:{scope_id}"
                self._snapshots.pop(key, None)
                self._events = [
                    e
                    for e in self._events
                    if not (e.scope == scope and e.scope_id == scope_id)
                ]
            else:
                self._snapshots.clear()
                self._events.clear()

    # ------------------------------------------------------------------
    # Persistence (SQLite)
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        try:
            conn = sqlite3.connect(str(self._db_path))
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cost_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    cost_usd REAL DEFAULT 0.0,
                    scope TEXT NOT NULL,
                    scope_id TEXT NOT NULL,
                    agent_id TEXT DEFAULT '',
                    timestamp REAL NOT NULL
                )
                """
            )
            conn.commit()
            conn.close()
        except Exception:
            logger.exception("Failed to init cost tracking DB")

    def _persist_event(self, event: CostEvent) -> None:
        try:
            conn = sqlite3.connect(str(self._db_path))
            conn.execute(
                """
                INSERT INTO cost_events
                    (provider, model, input_tokens, output_tokens, cost_usd,
                     scope, scope_id, agent_id, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.provider,
                    event.model,
                    event.input_tokens,
                    event.output_tokens,
                    event.cost_usd,
                    event.scope,
                    event.scope_id,
                    event.agent_id,
                    event.timestamp,
                ),
            )
            conn.commit()
            conn.close()
        except Exception:
            logger.exception("Failed to persist cost event")
