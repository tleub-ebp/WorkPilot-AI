"""
Backfill Estimator — Estimate migration and backfill duration.

Uses table row counts and operation type to produce time estimates.
100% algorithmic — no LLM dependency.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class OperationType(str, Enum):
    SIMPLE_UPDATE = "simple_update"  # SET col = value
    CAST_UPDATE = "cast_update"  # SET col = CAST(...)
    COPY_TABLE = "copy_table"  # Full table rewrite
    INDEX_BUILD = "index_build"  # CREATE INDEX
    CONSTRAINT_VALIDATE = "constraint_validate"  # VALIDATE CONSTRAINT


# Rough throughput estimates (rows/second) per operation type
_THROUGHPUT: dict[OperationType, int] = {
    OperationType.SIMPLE_UPDATE: 100_000,
    OperationType.CAST_UPDATE: 50_000,
    OperationType.COPY_TABLE: 30_000,
    OperationType.INDEX_BUILD: 80_000,
    OperationType.CONSTRAINT_VALIDATE: 200_000,
}


@dataclass
class BackfillEstimate:
    """Estimation result for a backfill or migration operation."""

    operation: OperationType
    estimated_rows: int
    estimated_seconds: float
    estimated_lock_ms: float = 0.0
    batch_size: int = 10_000
    batch_count: int = 0
    human_readable: str = ""

    @property
    def estimated_minutes(self) -> float:
        return self.estimated_seconds / 60.0


class BackfillEstimator:
    """Estimate duration of backfill and migration operations.

    Usage::

        estimator = BackfillEstimator()
        est = estimator.estimate(OperationType.SIMPLE_UPDATE, row_count=8_000_000)
        print(est.human_readable)  # "estimated: 1.3 min on 8M rows"
    """

    def __init__(self, batch_size: int = 10_000) -> None:
        self._batch_size = batch_size

    def estimate(
        self,
        operation: OperationType,
        row_count: int,
        custom_throughput: int | None = None,
    ) -> BackfillEstimate:
        """Estimate duration for a backfill operation."""
        throughput = custom_throughput or _THROUGHPUT.get(operation, 50_000)
        if row_count <= 0:
            return BackfillEstimate(
                operation=operation,
                estimated_rows=0,
                estimated_seconds=0.0,
                human_readable="instant (0 rows)",
            )

        seconds = row_count / throughput
        batch_count = max(1, (row_count + self._batch_size - 1) // self._batch_size)

        # Lock estimation: brief lock per batch for some operations
        lock_ms = 0.0
        if operation in (OperationType.SIMPLE_UPDATE, OperationType.CAST_UPDATE):
            lock_ms = batch_count * 5  # ~5ms per batch commit

        human = self._format_human(seconds, row_count, lock_ms)

        return BackfillEstimate(
            operation=operation,
            estimated_rows=row_count,
            estimated_seconds=seconds,
            estimated_lock_ms=lock_ms,
            batch_size=self._batch_size,
            batch_count=batch_count,
            human_readable=human,
        )

    def estimate_index_build(
        self, row_count: int, column_count: int = 1, concurrent: bool = True
    ) -> BackfillEstimate:
        """Estimate CREATE INDEX duration."""
        # Multi-column indexes take longer
        throughput = _THROUGHPUT[OperationType.INDEX_BUILD] // max(1, column_count)
        est = self.estimate(
            OperationType.INDEX_BUILD, row_count, custom_throughput=throughput
        )
        if not concurrent:
            est.estimated_lock_ms = est.estimated_seconds * 1000  # Full lock
        return est

    @staticmethod
    def _format_human(seconds: float, row_count: int, lock_ms: float) -> str:
        """Format a human-readable estimate string."""
        if row_count >= 1_000_000_000:
            rows_str = f"{row_count / 1_000_000_000:.1f}B"
        elif row_count >= 1_000_000:
            rows_str = f"{row_count / 1_000_000:.1f}M"
        elif row_count >= 1_000:
            rows_str = f"{row_count / 1_000:.1f}K"
        else:
            rows_str = str(row_count)

        if seconds < 1:
            time_str = f"{seconds * 1000:.0f}ms"
        elif seconds < 60:
            time_str = f"{seconds:.1f}s"
        elif seconds < 3600:
            time_str = f"{seconds / 60:.1f} min"
        else:
            time_str = f"{seconds / 3600:.1f}h"

        lock_str = ""
        if lock_ms > 0:
            if lock_ms < 1000:
                lock_str = f", lock duration: < {lock_ms:.0f}ms"
            else:
                lock_str = f", lock duration: ~{lock_ms / 1000:.1f}s"

        return f"estimated: {time_str} on {rows_str} rows{lock_str}"
