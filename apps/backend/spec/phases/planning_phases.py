"""
Planning and Validation Phase Implementations
==============================================

Phases for implementation planning and final validation.
"""

import json
import logging
from typing import TYPE_CHECKING

from task_logger import LogEntryType, LogPhase

from .. import writer
from .models import MAX_RETRIES, PhaseResult

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class PlanningPhaseMixin:
    """Mixin for planning and validation phase methods."""

    def _ensure_plan_deleted(self, plan_file) -> None:
        """Robustly delete the plan file, retrying on Windows lock errors.

        The Electron frontend's file watcher (chokidar) may hold a brief read
        lock on the plan file. On Windows this can cause PermissionError when
        the backend tries to delete it. We retry a few times with a short
        sleep to work around this.
        """
        import time

        for i in range(5):
            try:
                if plan_file.exists():
                    plan_file.unlink()
                return
            except PermissionError:
                if i < 4:
                    time.sleep(0.2)
                else:
                    logger.warning(
                        "Could not delete plan file after retries: %s", plan_file
                    )

    def _log_plan_content(self, plan_file, label: str) -> None:
        """Log the first 500 chars of the plan file for diagnostics."""
        try:
            if plan_file.exists():
                content = plan_file.read_text(encoding="utf-8")[:500]
                try:
                    data = json.loads(plan_file.read_text(encoding="utf-8"))
                    keys = list(data.keys())
                    phases = data.get("phases")
                    phase_count = len(phases) if isinstance(phases, list) else "missing"
                    logger.info(
                        "[planning] %s — keys=%s, phases=%s",
                        label,
                        keys,
                        phase_count,
                    )
                    self.ui.print_status(
                        f"  Plan keys: {keys}, phases: {phase_count}",
                        "info",
                    )
                except json.JSONDecodeError:
                    logger.warning(
                        "[planning] %s — invalid JSON: %s…", label, content[:200]
                    )
                    self.ui.print_status(
                        f"  Plan file is not valid JSON: {content[:200]}…", "warning"
                    )
            else:
                logger.info("[planning] %s — file does not exist", label)
        except OSError as e:
            logger.warning("[planning] %s — read error: %s", label, e)

    async def phase_planning(self) -> PhaseResult:
        """Create the implementation plan."""
        from ..validate_pkg.auto_fix import auto_fix_plan

        plan_file = self.spec_dir / "implementation_plan.json"

        if plan_file.exists():
            result = self.spec_validator.validate_implementation_plan()
            if result.valid:
                self.ui.print_status(
                    "implementation_plan.json already exists and is valid", "success"
                )
                return PhaseResult("planning", True, [str(plan_file)], [], 0)
            self.ui.print_status("Plan exists but invalid, regenerating...", "warning")
            self._log_plan_content(plan_file, "existing invalid plan")
            # Delete the invalid/stub plan file so the planner agent starts fresh.
            # The frontend creates status-only stubs (for XState persistence) that
            # have no phases — these must be removed before the planner runs.
            self._ensure_plan_deleted(plan_file)

        errors = []

        # Try Python script first (deterministic)
        self.ui.print_status("Trying planner.py (deterministic)...", "progress")
        success, output = self._run_script(
            "planner.py", ["--spec-dir", str(self.spec_dir)]
        )

        if success and plan_file.exists():
            result = self.spec_validator.validate_implementation_plan()
            if result.valid:
                self.ui.print_status(
                    "Created valid implementation_plan.json via script", "success"
                )
                stats = writer.get_plan_stats(self.spec_dir)
                if stats:
                    self.task_logger.log(
                        f"Implementation plan created with {stats.get('total_subtasks', 0)} subtasks",
                        LogEntryType.SUCCESS,
                        LogPhase.PLANNING,
                    )
                return PhaseResult("planning", True, [str(plan_file)], [], 0)
            else:
                if auto_fix_plan(self.spec_dir):
                    result = self.spec_validator.validate_implementation_plan()
                    if result.valid:
                        self.ui.print_status(
                            "Auto-fixed implementation_plan.json", "success"
                        )
                        return PhaseResult("planning", True, [str(plan_file)], [], 0)
                self._log_plan_content(plan_file, "script output (invalid)")
                errors.append(f"Script output invalid: {result.errors}")
                # Delete the invalid script output before agent attempts
                self._ensure_plan_deleted(plan_file)

        # Verify spec.md exists before running planner agent — it's the main input
        spec_file = self.spec_dir / "spec.md"
        if not spec_file.exists():
            self.ui.print_status(
                "spec.md does not exist — cannot create plan without spec", "error"
            )
            logger.error(
                "[planning] spec.md not found at %s — skipping planner agent", spec_file
            )
            errors.append("spec.md not found — spec_writing phase may have failed")
            return PhaseResult("planning", False, [], errors, 0)

        # Fall back to agent
        self.ui.print_status("Falling back to planner agent...", "progress")
        self.ui.print_status(
            f"  Spec dir: {self.spec_dir}", "info"
        )
        self.ui.print_status(
            f"  Project dir: {self.project_dir}", "info"
        )

        for attempt in range(MAX_RETRIES):
            # CRITICAL: Delete any stale/invalid plan file before each agent attempt.
            # Without this, the agent may find a leftover file from a previous failed
            # attempt (or from the frontend's XState re-stamp) and either skip writing
            # a new one or produce a plan that merges with stale content.
            self._ensure_plan_deleted(plan_file)

            self.ui.print_status(
                f"Running planner agent (attempt {attempt + 1})...", "progress"
            )

            success, output = await self.run_agent_fn(
                "planner.md",
                phase_name="planning",
            )

            # Log agent result for diagnostics
            output_len = len(output) if output else 0
            logger.info(
                "[planning] Agent attempt %d: success=%s, output_len=%d, plan_exists=%s",
                attempt + 1,
                success,
                output_len,
                plan_file.exists(),
            )
            if not success:
                self.ui.print_status(
                    f"  Agent returned error: {(output or 'no output')[:200]}", "error"
                )

            if success and plan_file.exists():
                self._log_plan_content(
                    plan_file, f"agent attempt {attempt + 1} output"
                )
                result = self.spec_validator.validate_implementation_plan()
                if result.valid:
                    self.ui.print_status(
                        "Created valid implementation_plan.json via agent", "success"
                    )
                    return PhaseResult("planning", True, [str(plan_file)], [], attempt)
                else:
                    if auto_fix_plan(self.spec_dir):
                        result = self.spec_validator.validate_implementation_plan()
                        if result.valid:
                            self.ui.print_status(
                                "Auto-fixed implementation_plan.json", "success"
                            )
                            return PhaseResult(
                                "planning", True, [str(plan_file)], [], attempt
                            )
                    errors.append(f"Agent attempt {attempt + 1}: {result.errors}")
                    self.ui.print_status("Plan created but invalid", "error")
            else:
                # Check if the agent wrote the plan to the project root by mistake
                # (the agent's CWD is project_dir, but the plan should be in spec_dir)
                wrong_path = self.project_dir / "implementation_plan.json"
                if wrong_path.exists():
                    self.ui.print_status(
                        "  Plan written to project root instead of spec dir — moving it",
                        "warning",
                    )
                    logger.warning(
                        "[planning] Agent wrote plan to %s instead of %s",
                        wrong_path,
                        plan_file,
                    )
                    import shutil
                    shutil.move(str(wrong_path), str(plan_file))
                    # Re-validate the moved file
                    result = self.spec_validator.validate_implementation_plan()
                    if result.valid:
                        self.ui.print_status(
                            "Recovered plan from project root — valid", "success"
                        )
                        return PhaseResult(
                            "planning", True, [str(plan_file)], [], attempt
                        )
                    else:
                        if auto_fix_plan(self.spec_dir):
                            result = self.spec_validator.validate_implementation_plan()
                            if result.valid:
                                self.ui.print_status(
                                    "Auto-fixed recovered plan", "success"
                                )
                                return PhaseResult(
                                    "planning", True, [str(plan_file)], [], attempt
                                )
                        errors.append(
                            f"Agent attempt {attempt + 1}: Plan at wrong path and invalid: {result.errors}"
                        )
                        self.ui.print_status("Recovered plan but invalid", "error")
                else:
                    detail = "agent error" if not success else "file not created"
                    errors.append(
                        f"Agent attempt {attempt + 1}: Did not create plan file ({detail}, output={output_len}b)"
                    )

        return PhaseResult("planning", False, [], errors, MAX_RETRIES)

    async def phase_validation(self) -> PhaseResult:
        """Final validation of all spec files with auto-fix retry."""
        for attempt in range(MAX_RETRIES):
            results = self.spec_validator.validate_all()
            all_valid = all(r.valid for r in results)

            for result in results:
                if result.valid:
                    self.ui.print_status(f"{result.checkpoint}: PASS", "success")
                else:
                    self.ui.print_status(f"{result.checkpoint}: FAIL", "error")
                for err in result.errors:
                    print(f"    {self.ui.muted('Error:')} {err}")

            if all_valid:
                print()
                self.ui.print_status("All validation checks passed", "success")
                return PhaseResult("validation", True, [], [], attempt)

            # If not valid, try to auto-fix with AI agent
            if attempt < MAX_RETRIES - 1:
                print()
                self.ui.print_status(
                    f"Attempting auto-fix (attempt {attempt + 1}/{MAX_RETRIES - 1})...",
                    "progress",
                )

                # Collect all errors for the fixer agent
                error_details = []
                for result in results:
                    if not result.valid:
                        error_details.append(
                            f"**{result.checkpoint}** validation failed:"
                        )
                        for err in result.errors:
                            error_details.append(f"  - {err}")
                        if result.fixes:
                            error_details.append("  Suggested fixes:")
                            for fix in result.fixes:
                                error_details.append(f"    - {fix}")

                context_str = f"""
**Spec Directory**: {self.spec_dir}

## Validation Errors to Fix

{chr(10).join(error_details)}

## Files in Spec Directory

The following files exist in the spec directory:
- context.json
- requirements.json
- spec.md
- implementation_plan.json
- project_index.json (if exists)

Read the failed files, understand the errors, and fix them.
"""
                success, output = await self.run_agent_fn(
                    "validation_fixer.md",
                    additional_context=context_str,
                    phase_name="validation",
                )

                if not success:
                    self.ui.print_status("Auto-fix agent failed", "warning")

        # All retries exhausted
        errors = [f"{r.checkpoint}: {err}" for r in results for err in r.errors]
        return PhaseResult("validation", False, [], errors, MAX_RETRIES)
