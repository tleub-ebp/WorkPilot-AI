"""
Database Schema Agent — Zero-downtime migration planner.

Generates multi-step migrations (expand → migrate → switch → contract),
detects locks, estimates backfill duration, and produces rollback scripts.

Modules:
    - schema_analyzer: introspect current DB schema
    - migration_planner: generate multi-step migration plans
    - lock_detector: detect potentially blocking DDL operations
    - backfill_estimator: estimate migration duration
    - rollback_generator: generate rollback scripts
"""

from .backfill_estimator import BackfillEstimate, BackfillEstimator
from .lock_detector import LockDetector, LockWarning, LockSeverity
from .migration_planner import (
    MigrationPlan,
    MigrationPlanner,
    MigrationStep,
    MigrationType,
)
from .rollback_generator import RollbackGenerator, RollbackScript
from .schema_analyzer import ColumnInfo, SchemaAnalyzer, TableInfo

__all__ = [
    "SchemaAnalyzer",
    "TableInfo",
    "ColumnInfo",
    "MigrationPlanner",
    "MigrationPlan",
    "MigrationStep",
    "MigrationType",
    "LockDetector",
    "LockWarning",
    "LockSeverity",
    "BackfillEstimator",
    "BackfillEstimate",
    "RollbackGenerator",
    "RollbackScript",
]
