"""
Lock Detector — Detect potentially blocking DDL operations.

Analyzes SQL statements for operations that acquire heavy locks
(ACCESS EXCLUSIVE, SHARE ROW EXCLUSIVE) and suggests non-blocking
alternatives when available.

100% algorithmic — no LLM dependency.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class LockSeverity(str, Enum):
    NONE = "none"
    LOW = "low"  # Brief lock, milliseconds
    MEDIUM = "medium"  # Seconds, may affect queries
    HIGH = "high"  # Long lock, blocks reads/writes
    CRITICAL = "critical"  # Very long lock on large tables


@dataclass
class LockWarning:
    """A warning about a potentially blocking DDL operation."""

    sql_statement: str
    severity: LockSeverity
    lock_type: str
    description: str
    suggestion: str | None = None
    estimated_lock_ms: float = 0.0


# Patterns that indicate heavy locks
_LOCK_PATTERNS: list[dict] = [
    {
        "pattern": re.compile(
            r"ALTER\s+TABLE\s+\w+\s+ADD\s+COLUMN\s+\w+\s+\w+.*NOT\s+NULL(?!\s+DEFAULT)",
            re.IGNORECASE,
        ),
        "severity": LockSeverity.HIGH,
        "lock_type": "ACCESS EXCLUSIVE",
        "description": "Adding NOT NULL column without DEFAULT requires full table rewrite.",
        "suggestion": (
            "Add the column as nullable first, backfill, then set NOT NULL. "
            "Or use DEFAULT (PG 11+ makes this instant)."
        ),
    },
    {
        "pattern": re.compile(
            r"CREATE\s+INDEX\s+(?!CONCURRENTLY)\w+\s+ON",
            re.IGNORECASE,
        ),
        "severity": LockSeverity.HIGH,
        "lock_type": "SHARE",
        "description": "CREATE INDEX blocks writes during index build.",
        "suggestion": "Use CREATE INDEX CONCURRENTLY to avoid blocking writes.",
    },
    {
        "pattern": re.compile(
            r"ALTER\s+TABLE\s+\w+\s+DROP\s+COLUMN",
            re.IGNORECASE,
        ),
        "severity": LockSeverity.MEDIUM,
        "lock_type": "ACCESS EXCLUSIVE",
        "description": "DROP COLUMN acquires ACCESS EXCLUSIVE lock.",
        "suggestion": "Schedule during low-traffic window or use expand/contract pattern.",
    },
    {
        "pattern": re.compile(
            r"ALTER\s+TABLE\s+\w+\s+ALTER\s+COLUMN\s+\w+\s+(?:SET\s+DATA\s+)?TYPE",
            re.IGNORECASE,
        ),
        "severity": LockSeverity.CRITICAL,
        "lock_type": "ACCESS EXCLUSIVE",
        "description": "Changing column type requires full table rewrite and ACCESS EXCLUSIVE lock.",
        "suggestion": "Use expand/contract: add new column, backfill, switch, drop old.",
    },
    {
        "pattern": re.compile(
            r"ALTER\s+TABLE\s+\w+\s+RENAME",
            re.IGNORECASE,
        ),
        "severity": LockSeverity.MEDIUM,
        "lock_type": "ACCESS EXCLUSIVE",
        "description": "RENAME acquires ACCESS EXCLUSIVE lock (brief).",
        "suggestion": None,
    },
    {
        "pattern": re.compile(
            r"ALTER\s+TABLE\s+\w+\s+ADD\s+CONSTRAINT.*FOREIGN\s+KEY",
            re.IGNORECASE,
        ),
        "severity": LockSeverity.HIGH,
        "lock_type": "SHARE ROW EXCLUSIVE",
        "description": "Adding FK constraint validates all existing rows (long on big tables).",
        "suggestion": "Use NOT VALID first, then VALIDATE CONSTRAINT separately.",
    },
]


class LockDetector:
    """Analyze SQL statements for potentially blocking lock operations."""

    def analyze(self, sql: str) -> list[LockWarning]:
        """Analyze one or more SQL statements for lock risks."""
        warnings: list[LockWarning] = []
        statements = self._split_statements(sql)

        for stmt in statements:
            stmt = stmt.strip()
            if not stmt:
                continue
            for rule in _LOCK_PATTERNS:
                if rule["pattern"].search(stmt):
                    warnings.append(
                        LockWarning(
                            sql_statement=stmt,
                            severity=rule["severity"],
                            lock_type=rule["lock_type"],
                            description=rule["description"],
                            suggestion=rule.get("suggestion"),
                        )
                    )

        return warnings

    def has_critical_locks(self, sql: str) -> bool:
        """Quick check if SQL has any critical lock operations."""
        warnings = self.analyze(sql)
        return any(w.severity == LockSeverity.CRITICAL for w in warnings)

    def suggest_safe_alternative(self, sql: str) -> str | None:
        """If a single statement has a known safer alternative, return it."""
        upper = sql.upper().strip()

        # CREATE INDEX → CREATE INDEX CONCURRENTLY
        if re.match(r"CREATE\s+INDEX\s+(?!CONCURRENTLY)", upper):
            return re.sub(
                r"(CREATE\s+)(INDEX)",
                r"\1INDEX CONCURRENTLY",
                sql,
                count=1,
                flags=re.IGNORECASE,
            )

        return None

    @staticmethod
    def _split_statements(sql: str) -> list[str]:
        """Split SQL into individual statements."""
        return [s.strip() for s in sql.split(";") if s.strip()]
