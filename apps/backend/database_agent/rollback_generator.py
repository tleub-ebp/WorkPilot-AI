"""
Rollback Generator — Generate rollback scripts for migration plans.

For each migration plan, generates a complete rollback script that
reverses all steps in reverse order.  Marks non-reversible steps
with explicit warnings.

100% algorithmic — no LLM dependency.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .migration_planner import MigrationPlan, MigrationStep

logger = logging.getLogger(__name__)


@dataclass
class RollbackScript:
    """A complete rollback script for a migration plan."""

    plan_description: str
    steps: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    is_fully_reversible: bool = True
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_sql(self) -> str:
        """Generate the full rollback SQL script."""
        lines = [
            f"-- Rollback script for: {self.plan_description}",
            f"-- Generated at: {self.generated_at}",
            "",
        ]

        if self.warnings:
            lines.append("-- ⚠️ WARNINGS:")
            for w in self.warnings:
                lines.append(f"--   {w}")
            lines.append("")

        lines.append("BEGIN;")
        lines.append("")

        for step_sql in self.steps:
            lines.append(step_sql)
            lines.append("")

        lines.append("COMMIT;")
        return "\n".join(lines)


class RollbackGenerator:
    """Generate rollback scripts from migration plans."""

    def generate(self, plan: MigrationPlan) -> RollbackScript:
        """Generate a rollback script for a migration plan.

        Steps are reversed: the last migration step is rolled back first.
        """
        rollback = RollbackScript(plan_description=plan.change_description)

        # Process steps in reverse order
        for step in reversed(plan.steps):
            if not step.is_reversible:
                rollback.is_fully_reversible = False
                rollback.warnings.append(
                    f"Step '{step.description}' is NOT reversible. "
                    f"Manual intervention required."
                )
                rollback.steps.append(
                    f"-- ❌ NON-REVERSIBLE: {step.description}\n"
                    f"-- Original: {step.sql_up}"
                )
            elif step.sql_down and not step.sql_down.startswith("--"):
                rollback.steps.append(
                    f"-- Rollback: {step.description}\n"
                    f"{step.sql_down}"
                )
            else:
                rollback.steps.append(
                    f"-- Manual rollback needed: {step.description}\n"
                    f"-- {step.sql_down or 'No rollback SQL provided'}"
                )

        return rollback

    def generate_multi(self, plans: list[MigrationPlan]) -> list[RollbackScript]:
        """Generate rollback scripts for multiple migration plans."""
        return [self.generate(plan) for plan in plans]

    @staticmethod
    def validate_rollback(rollback: RollbackScript) -> list[str]:
        """Validate a rollback script for completeness. Returns list of issues."""
        issues: list[str] = []

        if not rollback.steps:
            issues.append("Rollback script has no steps.")

        if not rollback.is_fully_reversible:
            issues.append(
                "Rollback is not fully reversible. "
                "Some steps require manual intervention."
            )

        for i, step_sql in enumerate(rollback.steps):
            if "NON-REVERSIBLE" in step_sql:
                issues.append(f"Step {i + 1} is non-reversible.")

        return issues
