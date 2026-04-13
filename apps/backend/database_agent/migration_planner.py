"""
Migration Planner — Generate multi-step migration plans.

Destructive changes (rename, type change, drop) are split into the
expand → migrate → switch → contract pattern for zero-downtime.
Non-destructive changes (add column nullable, add index) are single-step.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

from .schema_analyzer import ColumnInfo, SchemaAnalyzer

logger = logging.getLogger(__name__)


class MigrationType(str, Enum):
    NON_DESTRUCTIVE = "non_destructive"
    DESTRUCTIVE = "destructive"


class MigrationPhase(str, Enum):
    EXPAND = "expand"
    MIGRATE = "migrate"
    SWITCH = "switch"
    CONTRACT = "contract"
    SINGLE = "single"  # For non-destructive one-step migrations


@dataclass
class MigrationStep:
    """A single step within a migration plan."""

    phase: MigrationPhase
    description: str
    sql_up: str
    sql_down: str = ""
    estimated_duration_seconds: float = 0.0
    requires_lock: bool = False
    is_reversible: bool = True
    warnings: list[str] = field(default_factory=list)


@dataclass
class MigrationPlan:
    """A complete migration plan with one or more steps."""

    table_name: str
    change_description: str
    migration_type: MigrationType
    steps: list[MigrationStep] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    estimated_total_seconds: float = 0.0

    @property
    def is_destructive(self) -> bool:
        return self.migration_type == MigrationType.DESTRUCTIVE

    @property
    def step_count(self) -> int:
        return len(self.steps)


class MigrationPlanner:
    """Generate migration plans for schema changes.

    Usage::

        planner = MigrationPlanner()
        plan = planner.plan_add_column("users", ColumnInfo(name="email_verified", data_type="BOOLEAN", nullable=True))
        for step in plan.steps:
            print(step.sql_up)
    """

    def __init__(self, analyzer: SchemaAnalyzer | None = None) -> None:
        self._analyzer = analyzer or SchemaAnalyzer()

    def plan_add_column(
        self,
        table_name: str,
        column: ColumnInfo,
        estimated_rows: int = 0,
    ) -> MigrationPlan:
        """Plan adding a new column to a table."""
        if column.nullable or column.default is not None:
            return self._plan_add_column_non_destructive(table_name, column)
        return self._plan_add_column_with_default(table_name, column, estimated_rows)

    def plan_drop_column(
        self,
        table_name: str,
        column_name: str,
    ) -> MigrationPlan:
        """Plan dropping a column (always destructive, multi-step)."""
        plan = MigrationPlan(
            table_name=table_name,
            change_description=f"Drop column '{column_name}' from '{table_name}'",
            migration_type=MigrationType.DESTRUCTIVE,
            warnings=["Data in this column will be permanently lost."],
        )

        plan.steps.append(
            MigrationStep(
                phase=MigrationPhase.EXPAND,
                description=f"Mark column '{column_name}' as deprecated (add comment)",
                sql_up=f"COMMENT ON COLUMN {table_name}.{column_name} IS 'DEPRECATED - scheduled for removal';",
                sql_down=f"COMMENT ON COLUMN {table_name}.{column_name} IS '';",
            )
        )

        plan.steps.append(
            MigrationStep(
                phase=MigrationPhase.SWITCH,
                description=f"Update application code to stop reading/writing '{column_name}'",
                sql_up="-- No SQL: application code change required",
                sql_down="-- No SQL: revert application code change",
                is_reversible=True,
            )
        )

        plan.steps.append(
            MigrationStep(
                phase=MigrationPhase.CONTRACT,
                description=f"Drop column '{column_name}'",
                sql_up=f"ALTER TABLE {table_name} DROP COLUMN {column_name};",
                sql_down="-- WARNING: Cannot restore dropped column data",
                requires_lock=True,
                is_reversible=False,
            )
        )

        return plan

    def plan_rename_column(
        self,
        table_name: str,
        old_name: str,
        new_name: str,
        data_type: str = "TEXT",
        estimated_rows: int = 0,
    ) -> MigrationPlan:
        """Plan renaming a column (destructive, multi-step expand/contract)."""
        plan = MigrationPlan(
            table_name=table_name,
            change_description=f"Rename column '{old_name}' to '{new_name}' in '{table_name}'",
            migration_type=MigrationType.DESTRUCTIVE,
        )

        # Step 1: Expand — add new column
        plan.steps.append(
            MigrationStep(
                phase=MigrationPhase.EXPAND,
                description=f"Add new column '{new_name}'",
                sql_up=f"ALTER TABLE {table_name} ADD COLUMN {new_name} {data_type};",
                sql_down=f"ALTER TABLE {table_name} DROP COLUMN {new_name};",
            )
        )

        # Step 2: Migrate — backfill data
        plan.steps.append(
            MigrationStep(
                phase=MigrationPhase.MIGRATE,
                description=f"Backfill data from '{old_name}' to '{new_name}'",
                sql_up=f"UPDATE {table_name} SET {new_name} = {old_name};",
                sql_down=f"UPDATE {table_name} SET {old_name} = {new_name};",
                estimated_duration_seconds=self._estimate_backfill_time(estimated_rows),
            )
        )

        # Step 3: Switch — update application code
        plan.steps.append(
            MigrationStep(
                phase=MigrationPhase.SWITCH,
                description=f"Update application code to use '{new_name}' instead of '{old_name}'",
                sql_up="-- No SQL: application code change required",
                sql_down="-- No SQL: revert application code change",
            )
        )

        # Step 4: Contract — drop old column
        plan.steps.append(
            MigrationStep(
                phase=MigrationPhase.CONTRACT,
                description=f"Drop old column '{old_name}'",
                sql_up=f"ALTER TABLE {table_name} DROP COLUMN {old_name};",
                sql_down=f"ALTER TABLE {table_name} ADD COLUMN {old_name} {data_type};",
                requires_lock=True,
            )
        )

        plan.estimated_total_seconds = sum(
            s.estimated_duration_seconds for s in plan.steps
        )
        return plan

    def plan_change_type(
        self,
        table_name: str,
        column_name: str,
        old_type: str,
        new_type: str,
        estimated_rows: int = 0,
    ) -> MigrationPlan:
        """Plan changing a column's data type (destructive)."""
        plan = MigrationPlan(
            table_name=table_name,
            change_description=f"Change type of '{column_name}' from {old_type} to {new_type}",
            migration_type=MigrationType.DESTRUCTIVE,
        )

        temp_col = f"{column_name}_new"

        plan.steps.append(
            MigrationStep(
                phase=MigrationPhase.EXPAND,
                description=f"Add temporary column '{temp_col}' with type {new_type}",
                sql_up=f"ALTER TABLE {table_name} ADD COLUMN {temp_col} {new_type};",
                sql_down=f"ALTER TABLE {table_name} DROP COLUMN {temp_col};",
            )
        )

        plan.steps.append(
            MigrationStep(
                phase=MigrationPhase.MIGRATE,
                description=f"Backfill data from '{column_name}' to '{temp_col}' with type cast",
                sql_up=f"UPDATE {table_name} SET {temp_col} = CAST({column_name} AS {new_type});",
                sql_down="-- Reverse cast may not be possible",
                estimated_duration_seconds=self._estimate_backfill_time(estimated_rows),
                warnings=[f"Cast from {old_type} to {new_type} may lose data."],
            )
        )

        plan.steps.append(
            MigrationStep(
                phase=MigrationPhase.SWITCH,
                description="Update application code to use the new column",
                sql_up="-- No SQL: application code change required",
                sql_down="-- No SQL: revert application code change",
            )
        )

        plan.steps.append(
            MigrationStep(
                phase=MigrationPhase.CONTRACT,
                description="Drop old column and rename new",
                sql_up=(
                    f"ALTER TABLE {table_name} DROP COLUMN {column_name};\n"
                    f"ALTER TABLE {table_name} RENAME COLUMN {temp_col} TO {column_name};"
                ),
                sql_down="-- Manual restoration required",
                requires_lock=True,
                is_reversible=False,
            )
        )

        plan.estimated_total_seconds = sum(
            s.estimated_duration_seconds for s in plan.steps
        )
        return plan

    def plan_add_index(
        self,
        table_name: str,
        index_name: str,
        columns: list[str],
        unique: bool = False,
        concurrent: bool = True,
    ) -> MigrationPlan:
        """Plan adding an index (non-destructive but may lock)."""
        cols = ", ".join(columns)
        unique_kw = "UNIQUE " if unique else ""
        concurrent_kw = "CONCURRENTLY " if concurrent else ""

        plan = MigrationPlan(
            table_name=table_name,
            change_description=f"Add {'unique ' if unique else ''}index on ({cols})",
            migration_type=MigrationType.NON_DESTRUCTIVE,
        )

        plan.steps.append(
            MigrationStep(
                phase=MigrationPhase.SINGLE,
                description=f"Create index '{index_name}' on ({cols})",
                sql_up=f"CREATE {unique_kw}INDEX {concurrent_kw}{index_name} ON {table_name} ({cols});",
                sql_down=f"DROP INDEX {index_name};",
                requires_lock=not concurrent,
            )
        )

        if not concurrent:
            plan.warnings.append(
                "Non-concurrent index creation will lock the table. "
                "Consider using CONCURRENTLY for zero-downtime."
            )

        return plan

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _plan_add_column_non_destructive(
        self, table_name: str, column: ColumnInfo
    ) -> MigrationPlan:
        """Add a nullable column or one with a default — single step."""
        default_clause = f" DEFAULT {column.default}" if column.default else ""
        null_clause = "" if column.nullable else " NOT NULL"

        plan = MigrationPlan(
            table_name=table_name,
            change_description=f"Add column '{column.name}' ({column.data_type}) to '{table_name}'",
            migration_type=MigrationType.NON_DESTRUCTIVE,
        )

        plan.steps.append(
            MigrationStep(
                phase=MigrationPhase.SINGLE,
                description=f"Add column '{column.name}'",
                sql_up=f"ALTER TABLE {table_name} ADD COLUMN {column.name} {column.data_type}{null_clause}{default_clause};",
                sql_down=f"ALTER TABLE {table_name} DROP COLUMN {column.name};",
            )
        )

        return plan

    def _plan_add_column_with_default(
        self, table_name: str, column: ColumnInfo, estimated_rows: int
    ) -> MigrationPlan:
        """Add a NOT NULL column without default — needs backfill."""
        plan = MigrationPlan(
            table_name=table_name,
            change_description=f"Add NOT NULL column '{column.name}' to '{table_name}'",
            migration_type=MigrationType.DESTRUCTIVE,
        )

        plan.steps.append(
            MigrationStep(
                phase=MigrationPhase.EXPAND,
                description=f"Add nullable column '{column.name}'",
                sql_up=f"ALTER TABLE {table_name} ADD COLUMN {column.name} {column.data_type};",
                sql_down=f"ALTER TABLE {table_name} DROP COLUMN {column.name};",
            )
        )

        plan.steps.append(
            MigrationStep(
                phase=MigrationPhase.MIGRATE,
                description=f"Backfill default value for '{column.name}'",
                sql_up=f"UPDATE {table_name} SET {column.name} = '' WHERE {column.name} IS NULL;",
                sql_down="-- No reverse needed",
                estimated_duration_seconds=self._estimate_backfill_time(estimated_rows),
            )
        )

        plan.steps.append(
            MigrationStep(
                phase=MigrationPhase.CONTRACT,
                description="Add NOT NULL constraint",
                sql_up=f"ALTER TABLE {table_name} ALTER COLUMN {column.name} SET NOT NULL;",
                sql_down=f"ALTER TABLE {table_name} ALTER COLUMN {column.name} DROP NOT NULL;",
                requires_lock=True,
            )
        )

        plan.estimated_total_seconds = sum(
            s.estimated_duration_seconds for s in plan.steps
        )
        return plan

    @staticmethod
    def _estimate_backfill_time(row_count: int) -> float:
        """Rough estimate: ~100k rows/second for simple updates."""
        if row_count <= 0:
            return 0.0
        return row_count / 100_000
