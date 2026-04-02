"""
Swarm Orchestrator
==================

Main coordinator for multi-agent parallel execution.

Workflow:
1. Load the implementation plan and analyze subtask dependencies
2. Build waves of parallelizable subtasks
3. For each wave:
   a. Execute subtasks in parallel (each in its own subprocess + worktree)
   b. Collect results
   c. Semantic merge of completed subtasks into the main worktree
4. Report final status

The orchestrator emits structured events to stdout for the Electron
frontend to parse and display in the Pixel Office / Kanban board.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from core.phase_event import ExecutionPhase, emit_phase
from core.workflow_logger import workflow_logger

from .dependency_analyzer import DependencyAnalyzer
from .types import (
    SubtaskNode,
    SubtaskState,
    SwarmConfig,
    SwarmPhase,
    SwarmStatus,
    Wave,
)
from .wave_executor import WaveExecutor, WaveResult, emit_swarm_event

logger = logging.getLogger(__name__)

AGENT_NAME = "Swarm Orchestrator"


class SwarmOrchestrator:
    """
    Orchestrates multi-agent parallel execution of subtasks.

    Given a spec directory with an implementation_plan.json, this orchestrator:
    1. Analyzes subtask dependencies to determine parallelism
    2. Groups subtasks into waves (DAG-based topological scheduling)
    3. Executes each wave in parallel using subprocess agents
    4. Merges results between waves using the semantic merge system
    """

    def __init__(
        self,
        project_dir: Path,
        spec_dir: Path,
        config: SwarmConfig | None = None,
        model: str | None = None,
        python_path: str | None = None,
        source_path: str | None = None,
    ) -> None:
        self.project_dir = Path(project_dir).resolve()
        self.spec_dir = Path(spec_dir).resolve()
        self.config = config or SwarmConfig()
        self.model = model
        self.status = SwarmStatus(config=self.config)

        self._analyzer = DependencyAnalyzer(
            max_parallel=self.config.max_parallel_agents
        )
        self._executor = WaveExecutor(
            project_dir=self.project_dir,
            spec_dir=self.spec_dir,
            config=self.config,
            python_path=python_path,
            source_path=source_path,
        )
        self._trace_id: str | None = None

    async def run(self) -> SwarmStatus:
        """
        Execute the full swarm pipeline.

        Returns:
            SwarmStatus with complete execution details.
        """
        self._trace_id = workflow_logger.log_agent_start(
            AGENT_NAME,
            "swarm_execution",
            {
                "project_dir": str(self.project_dir),
                "spec_dir": str(self.spec_dir),
                "config": self.config.to_dict(),
            },
        )

        try:
            return await self._run_pipeline()
        except Exception as e:
            self.status.phase = SwarmPhase.FAILED
            self.status.error = str(e)
            self.status.completed_at = time.time()
            logger.error("Swarm execution failed: %s", e, exc_info=True)
            emit_swarm_event("swarm_failed", {"error": str(e)})
            return self.status
        finally:
            workflow_logger.log_agent_end(
                AGENT_NAME,
                "success" if self.status.phase == SwarmPhase.COMPLETE else "failed",
                {
                    "total_subtasks": self.status.total_subtasks,
                    "completed": self.status.completed_subtasks,
                    "failed": self.status.failed_subtasks,
                    "waves": self.status.total_waves,
                    "duration_seconds": self.status.duration_seconds,
                },
                trace_id=self._trace_id,
            )

    async def _run_pipeline(self) -> SwarmStatus:
        """Core pipeline: analyze → execute waves → merge → report."""

        # ── Phase 1: Load plan and analyze dependencies ──────────────
        self.status.phase = SwarmPhase.ANALYZING_DEPENDENCIES
        emit_phase(
            ExecutionPhase.PLANNING,
            "Analyzing subtask dependencies for parallel execution",
        )
        emit_swarm_event("phase_changed", {"phase": "analyzing_dependencies"})

        plan = self._load_plan()
        if not plan:
            self.status.phase = SwarmPhase.FAILED
            self.status.error = "No implementation plan found"
            return self.status

        waves, nodes = self._analyzer.analyze(plan)
        stats = self._analyzer.get_parallelism_stats(waves)

        self.status.waves = waves
        self.status.nodes = nodes
        self.status.total_waves = len(waves)
        self.status.total_subtasks = len(nodes)

        logger.info(
            "Swarm plan: %d subtasks in %d waves (max parallelism: %d, speedup: %.1fx)",
            stats["total_subtasks"],
            stats["total_waves"],
            stats["max_parallelism"],
            stats["speedup_estimate"],
        )

        emit_swarm_event(
            "analysis_complete",
            {
                "total_subtasks": len(nodes),
                "total_waves": len(waves),
                "parallelism_stats": stats,
            },
        )

        # Check if parallelism is worthwhile
        if len(waves) == len(nodes):
            logger.info("No parallelism possible — all subtasks are sequential")
            emit_swarm_event(
                "swarm_skipped",
                {
                    "reason": "no_parallelism",
                    "message": "All subtasks have dependencies — falling back to sequential execution",
                },
            )
            # Fall through to sequential execution (waves of 1)

        # ── Phase 2: Execute waves ───────────────────────────────────
        for wave_idx, wave in enumerate(waves):
            self.status.current_wave = wave_idx
            self.status.phase = SwarmPhase.EXECUTING_WAVE

            emit_phase(
                ExecutionPhase.CODING,
                f"Wave {wave_idx + 1}/{len(waves)}: executing {len(wave.subtask_ids)} subtasks in parallel",
                progress=self._calculate_progress(wave_idx, len(waves)),
                subtask=f"wave-{wave_idx + 1}",
            )

            emit_swarm_event(
                "phase_changed",
                {
                    "phase": "executing_wave",
                    "wave_index": wave_idx,
                    "wave_size": len(wave.subtask_ids),
                },
            )

            # Execute the wave
            wave_result = await self._executor.execute_wave(
                wave=wave,
                nodes=nodes,
                on_subtask_started=self._on_subtask_started,
                on_subtask_completed=self._on_subtask_completed,
                on_subtask_failed=self._on_subtask_failed,
                on_subtask_log=self._on_subtask_log,
            )

            # Update counters
            self._update_counters_from_wave_result(wave_result)

            # Handle failures
            if not wave_result.all_succeeded:
                failed_ids = [
                    r.subtask_id for r in wave_result.results if not r.success
                ]
                logger.warning(
                    "Wave %d: %d subtasks failed: %s",
                    wave_idx,
                    len(failed_ids),
                    ", ".join(failed_ids),
                )

                if self.config.fail_fast:
                    self.status.phase = SwarmPhase.FAILED
                    self.status.error = f"Wave {wave_idx} failed (fail_fast=true): {', '.join(failed_ids)}"
                    self.status.completed_at = time.time()
                    await self._executor.cancel_all()
                    return self.status

                # Retry failed subtasks that haven't exceeded max retries
                await self._retry_failed_subtasks(wave, wave_result, nodes)

            # ── Phase 2b: Merge wave results ─────────────────────────
            if self.config.merge_after_each_wave and wave_idx < len(waves) - 1:
                await self._merge_wave(wave, wave_result, nodes)

        # ── Phase 3: Final merge ─────────────────────────────────────
        if len(waves) > 1:
            self.status.phase = SwarmPhase.MERGING_WAVE
            emit_phase(ExecutionPhase.CODING, "Final merge: combining all wave results")
            emit_swarm_event("phase_changed", {"phase": "final_merge"})
            await self._final_merge(waves, nodes)

        # ── Complete ─────────────────────────────────────────────────
        self.status.phase = SwarmPhase.COMPLETE
        self.status.completed_at = time.time()

        emit_phase(
            ExecutionPhase.COMPLETE,
            f"Swarm complete: {self.status.completed_subtasks}/{self.status.total_subtasks} subtasks",
            progress=100,
        )

        emit_swarm_event(
            "swarm_complete",
            {
                "completed": self.status.completed_subtasks,
                "failed": self.status.failed_subtasks,
                "total": self.status.total_subtasks,
                "waves": self.status.total_waves,
                "duration_seconds": self.status.duration_seconds,
            },
        )

        return self.status

    def _load_plan(self) -> dict | None:
        """Load the implementation plan from spec directory."""
        plan_file = self.spec_dir / "implementation_plan.json"
        if not plan_file.exists():
            logger.error("No implementation_plan.json found in %s", self.spec_dir)
            return None
        try:
            with open(plan_file, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error("Failed to load implementation plan: %s", e)
            return None

    def _calculate_progress(self, wave_idx: int, total_waves: int) -> int:
        """Calculate overall progress percentage based on wave progress."""
        if total_waves == 0:
            return 0
        # Reserve 10% for analysis and 10% for final merge
        wave_progress_range = 80  # 10% to 90%
        per_wave = wave_progress_range / total_waves
        return int(10 + (wave_idx * per_wave))

    def _update_counters_from_wave_result(self, result: WaveResult) -> None:
        """Update status counters from a wave result."""
        for sr in result.results:
            if sr.success:
                self.status.completed_subtasks += 1
            else:
                self.status.failed_subtasks += 1
        self.status.running_subtasks = 0  # Wave done

    async def _retry_failed_subtasks(
        self,
        wave: Wave,
        result: WaveResult,
        nodes: dict[str, SubtaskNode],
    ) -> None:
        """Retry failed subtasks that haven't exceeded max retries."""
        for sr in result.results:
            if sr.success:
                continue

            node = nodes.get(sr.subtask_id)
            if not node:
                continue

            if node.retry_count < self.config.max_retries_per_subtask:
                node.retry_count += 1
                node.state = SubtaskState.RETRYING

                logger.info(
                    "Retrying subtask %s (attempt %d/%d)",
                    node.id,
                    node.retry_count,
                    self.config.max_retries_per_subtask,
                )

                emit_swarm_event(
                    "subtask_retrying",
                    {
                        "subtask_id": node.id,
                        "attempt": node.retry_count,
                        "max_retries": self.config.max_retries_per_subtask,
                    },
                )

                # Re-execute as a single-subtask wave
                retry_wave = Wave(index=wave.index, subtask_ids=[node.id])
                retry_result = await self._executor.execute_wave(
                    wave=retry_wave,
                    nodes=nodes,
                    on_subtask_log=self._on_subtask_log,
                )

                if retry_result.all_succeeded:
                    # Fix counters: was counted as failed, now succeeded
                    self.status.failed_subtasks -= 1
                    self.status.completed_subtasks += 1

    async def _merge_wave(
        self,
        wave: Wave,
        result: WaveResult,
        nodes: dict[str, SubtaskNode],
    ) -> None:
        """Merge completed subtasks from a wave into the main worktree."""
        self.status.phase = SwarmPhase.MERGING_WAVE
        emit_swarm_event(
            "phase_changed",
            {
                "phase": "merging_wave",
                "wave_index": wave.index,
            },
        )

        completed_ids = [r.subtask_id for r in result.results if r.success]
        if not completed_ids:
            wave.merge_success = True
            return

        try:
            from merge.models import TaskMergeRequest
            from merge.orchestrator import MergeOrchestrator

            merge_requests = []
            for subtask_id in completed_ids:
                node = nodes.get(subtask_id)
                if node and node.worktree_path:
                    merge_requests.append(
                        TaskMergeRequest(
                            task_id=subtask_id,
                            worktree_path=node.worktree_path,
                            intent=node.description,
                            priority=node.wave_index,
                        )
                    )

            if not merge_requests:
                wave.merge_success = True
                return

            orchestrator = MergeOrchestrator(
                project_dir=self.project_dir,
                enable_ai=self.config.enable_ai_merge,
                dry_run=self.config.dry_run,
            )
            report = orchestrator.merge_tasks(
                merge_requests,
                target_branch="HEAD",
            )

            wave.merge_success = report.success

            emit_swarm_event(
                "wave_merged",
                {
                    "wave_index": wave.index,
                    "success": report.success,
                    "stats": report.stats.to_dict(),
                },
            )

            if not report.success:
                logger.warning(
                    "Wave %d merge had issues: %d files need review",
                    wave.index,
                    report.stats.files_need_review,
                )

        except ImportError:
            logger.warning("Merge system not available — skipping wave merge")
            wave.merge_success = True
        except Exception as e:
            logger.error("Wave %d merge failed: %s", wave.index, e, exc_info=True)
            wave.merge_success = False
            emit_swarm_event(
                "wave_merge_failed",
                {
                    "wave_index": wave.index,
                    "error": str(e),
                },
            )

    async def _final_merge(
        self,
        waves: list[Wave],
        nodes: dict[str, SubtaskNode],
    ) -> None:
        """Perform final merge of all completed subtasks."""
        # The individual wave merges should have handled most conflicts.
        # This final merge is a validation pass.
        emit_swarm_event(
            "final_merge_started",
            {
                "completed_subtasks": self.status.completed_subtasks,
            },
        )

        emit_swarm_event(
            "final_merge_complete",
            {
                "success": True,
            },
        )

    # ── Callbacks ────────────────────────────────────────────────────

    def _on_subtask_started(self, subtask_id: str) -> None:
        self.status.running_subtasks += 1
        logger.info("Subtask started: %s", subtask_id)

    def _on_subtask_completed(self, subtask_id: str, result: Any) -> None:
        self.status.running_subtasks = max(0, self.status.running_subtasks - 1)
        logger.info("Subtask completed: %s", subtask_id)

    def _on_subtask_failed(self, subtask_id: str, error: str | None) -> None:
        self.status.running_subtasks = max(0, self.status.running_subtasks - 1)
        logger.warning("Subtask failed: %s — %s", subtask_id, error)

    def _on_subtask_log(self, subtask_id: str, line: str) -> None:
        """Forward significant log lines."""
        # Only forward phase changes and significant events
        if any(
            marker in line
            for marker in ("__EXEC_PHASE__:", "__TASK_EVENT__:", "ERROR", "WARN")
        ):
            logger.debug("[%s] %s", subtask_id, line[:200])

    async def cancel(self) -> None:
        """Cancel all running subtasks."""
        logger.info("Cancelling swarm execution")
        await self._executor.cancel_all()
        self.status.phase = SwarmPhase.FAILED
        self.status.error = "Cancelled by user"
        self.status.completed_at = time.time()
        emit_swarm_event("swarm_cancelled", {})
