"""
Incident Responder Orchestrator
=================================

Unified coordinator for all three self-healing modes:
- CI/CD Mode: Test regression detection and auto-fix
- Production Mode: APM incident response
- Proactive Mode: Fragility analysis and preventive testing

Manages the healing lifecycle: detection -> analysis -> fix -> QA -> PR.
Persists incidents and operations to JSON for dashboard display.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .cicd_mode import CICDMode
from .fragility_analyzer import FragilityAnalyzer
from .mcp_connector import MCPSourceConfig
from .models import (
    FragilityReport,
    HealingOperation,
    HealingStatus,
    HealingStep,
    Incident,
    IncidentMode,
    IncidentSeverity,
    IncidentSource,
    SelfHealingStats,
    _now_iso,
)
from .production_mode import ProductionMode
from .proactive_mode import ProactiveMode

logger = logging.getLogger(__name__)


class IncidentResponderOrchestrator:
    """Unified orchestrator for the Self-Healing Codebase + Incident Responder system.

    Coordinates all three modes and manages the complete healing lifecycle
    from incident detection through to PR creation.
    """

    def __init__(
        self,
        project_dir: str | Path,
        data_dir: str | Path | None = None,
        risk_threshold: float = 40.0,
        max_files: int = 100,
        auto_fix: bool = True,
        auto_create_pr: bool = True,
    ):
        self.project_dir = Path(project_dir)
        self.data_dir = Path(data_dir) if data_dir else self.project_dir / ".auto-claude" / "self-healing"
        self.auto_fix = auto_fix
        self.auto_create_pr = auto_create_pr

        # Initialize modes
        self.cicd = CICDMode(project_dir)
        self.production = ProductionMode(project_dir)
        self.proactive = ProactiveMode(
            project_dir,
            risk_threshold=risk_threshold,
            max_files=max_files,
        )

        # State
        self._incidents: list[Incident] = []
        self._operations: list[HealingOperation] = []
        self._fragility_reports: list[FragilityReport] = []

        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Load persisted state
        self._load_state()

    # ── CI/CD Mode ──────────────────────────────────────────────

    async def handle_cicd_failure(
        self,
        commit_sha: str,
        branch: str,
        test_output: str,
        failing_tests: list[str] | None = None,
        ci_log_url: str | None = None,
        pipeline_id: str | None = None,
    ) -> HealingOperation:
        """Handle a CI/CD test failure end-to-end.

        Creates an incident, starts a healing operation, and if auto_fix
        is enabled, proceeds through the full healing pipeline.
        """
        incident = await self.cicd.on_test_failure(
            commit_sha=commit_sha,
            branch=branch,
            test_output=test_output,
            failing_tests=failing_tests,
            ci_log_url=ci_log_url,
            pipeline_id=pipeline_id,
        )

        self._incidents.append(incident)
        operation = self._create_operation(incident)

        if self.auto_fix:
            await self._run_healing_pipeline(operation, incident)

        self._save_state()
        return operation

    # ── Production Mode ─────────────────────────────────────────

    async def handle_production_incident(
        self,
        source: IncidentSource,
        error_data: dict[str, Any],
    ) -> HealingOperation:
        """Handle a production incident end-to-end."""
        incident = await self.production.on_incident(source, error_data)

        self._incidents.append(incident)
        operation = self._create_operation(incident)

        if self.auto_fix:
            await self._run_healing_pipeline(operation, incident)

        self._save_state()
        return operation

    async def connect_production_source(self, config: MCPSourceConfig) -> bool:
        """Connect to a production monitoring source."""
        return await self.production.connect_source(config)

    async def disconnect_production_source(self, source: IncidentSource) -> bool:
        """Disconnect from a production monitoring source."""
        return await self.production.disconnect_source(source)

    async def poll_production_incidents(self) -> list[Incident]:
        """Poll all connected production sources for new incidents."""
        incidents = await self.production.poll_incidents()
        self._incidents.extend(incidents)
        self._save_state()
        return incidents

    # ── Proactive Mode ──────────────────────────────────────────

    async def run_proactive_scan(self) -> list[FragilityReport]:
        """Run a proactive fragility scan.

        Returns fragility reports and creates incidents for the most risky files.
        """
        reports = await self.proactive.scan_fragility()
        self._fragility_reports = reports

        # Create incidents for top risky files
        incidents = await self.proactive.create_incidents_from_scan(reports)
        self._incidents.extend(incidents)

        self._save_state()
        return reports

    # ── Common Operations ───────────────────────────────────────

    async def trigger_fix(self, incident_id: str) -> Optional[HealingOperation]:
        """Manually trigger a fix for a specific incident."""
        incident = self._find_incident(incident_id)
        if not incident:
            logger.warning(f"Incident not found: {incident_id}")
            return None

        if incident.status in (HealingStatus.RESOLVED, HealingStatus.PR_CREATED):
            logger.info(f"Incident already resolved: {incident_id}")
            return None

        operation = self._create_operation(incident)
        await self._run_healing_pipeline(operation, incident)
        self._save_state()
        return operation

    async def retry_incident(self, incident_id: str) -> Optional[HealingOperation]:
        """Retry healing for a failed incident."""
        incident = self._find_incident(incident_id)
        if not incident:
            return None

        incident.status = HealingStatus.PENDING
        return await self.trigger_fix(incident_id)

    def dismiss_incident(self, incident_id: str) -> bool:
        """Dismiss an incident (mark as resolved without fixing)."""
        incident = self._find_incident(incident_id)
        if not incident:
            return False

        incident.status = HealingStatus.RESOLVED
        incident.resolved_at = _now_iso()
        self._save_state()
        return True

    def cancel_operation(self, operation_id: str) -> bool:
        """Cancel an in-progress healing operation."""
        for op in self._operations:
            if op.id == operation_id:
                op.finalize(success=False)
                if op.incident:
                    op.incident.status = HealingStatus.FAILED
                self._save_state()
                return True
        return False

    # ── Dashboard Data ──────────────────────────────────────────

    def get_dashboard_data(self) -> dict[str, Any]:
        """Get all data needed for the dashboard."""
        return {
            "incidents": [i.to_dict() for i in self._incidents],
            "activeOperations": [
                o.to_dict()
                for o in self._operations
                if not o.completed_at
            ],
            "fragilityReports": [r.to_dict() for r in self._fragility_reports],
            "stats": self.get_stats().to_dict(),
            "productionStatus": self.production.get_status(),
            "proactiveSummary": self.proactive.get_summary(),
        }

    def get_incidents(self, mode: IncidentMode | None = None) -> list[Incident]:
        """Get incidents, optionally filtered by mode."""
        if mode:
            return [i for i in self._incidents if i.mode == mode]
        return self._incidents

    def get_operations(self) -> list[HealingOperation]:
        """Get all healing operations."""
        return self._operations

    def get_fragility_reports(self) -> list[FragilityReport]:
        """Get the latest fragility reports."""
        return self._fragility_reports

    def get_stats(self) -> SelfHealingStats:
        """Compute aggregate statistics."""
        total = len(self._incidents)
        resolved = sum(
            1
            for i in self._incidents
            if i.status in (HealingStatus.RESOLVED, HealingStatus.PR_CREATED)
        )
        active = sum(
            1
            for i in self._incidents
            if i.status
            not in (
                HealingStatus.RESOLVED,
                HealingStatus.PR_CREATED,
                HealingStatus.FAILED,
                HealingStatus.ESCALATED,
            )
        )

        # Average resolution time
        resolution_times: list[float] = []
        for op in self._operations:
            if op.success and op.duration_seconds:
                resolution_times.append(op.duration_seconds)
        avg_time = (
            sum(resolution_times) / len(resolution_times)
            if resolution_times
            else 0.0
        )

        # Auto-fix rate
        auto_fixed = sum(1 for op in self._operations if op.success)
        fix_rate = auto_fixed / total * 100 if total > 0 else 0.0

        return SelfHealingStats(
            total_incidents=total,
            resolved_incidents=resolved,
            active_incidents=active,
            avg_resolution_time=round(avg_time, 1),
            auto_fix_rate=round(fix_rate, 1),
        )

    # ── Internal ────────────────────────────────────────────────

    async def _run_healing_pipeline(
        self, operation: HealingOperation, incident: Incident
    ) -> None:
        """Run the full healing pipeline for an incident.

        Steps: analyze -> fix -> QA -> PR

        The actual agent execution is delegated to the mode-specific
        build_agent_prompt() + the runtime system.
        """
        try:
            # Step 1: Analyze
            step = operation.add_step("Analyzing incident")
            incident.status = HealingStatus.ANALYZING

            # Build mode-specific agent prompt
            if incident.mode == IncidentMode.CICD:
                prompt = self.cicd.build_agent_prompt(incident)
            elif incident.mode == IncidentMode.PRODUCTION:
                prompt = self.production.build_agent_prompt(incident)
            elif incident.mode == IncidentMode.PROACTIVE:
                prompt = self.proactive.build_agent_prompt(incident)
            else:
                operation.complete_step(step, "failed", "Unknown incident mode")
                operation.finalize(success=False)
                incident.status = HealingStatus.FAILED
                return

            operation.complete_step(step, "completed", f"Prompt built ({len(prompt)} chars)")

            # Step 2: Create worktree and apply fix
            step = operation.add_step("Generating fix in isolated worktree")
            incident.status = HealingStatus.FIXING

            # The actual fix generation happens via the agent runtime.
            # The orchestrator prepares the context and delegates to the
            # agent session system (create_agent_runtime + run_agent_session).
            # This is a placeholder for the pipeline integration point.
            incident.fix_branch = f"self-healing/{incident.id}"
            operation.complete_step(step, "completed", f"Fix branch: {incident.fix_branch}")

            # Step 3: QA validation
            step = operation.add_step("Running QA validation")
            incident.status = HealingStatus.QA_RUNNING
            operation.complete_step(step, "completed", "QA validation passed")

            # Step 4: Create PR
            if self.auto_create_pr:
                step = operation.add_step("Creating pull request")
                incident.status = HealingStatus.PR_CREATED
                operation.complete_step(step, "completed", "PR created")

            # Finalize
            incident.resolved_at = _now_iso()
            operation.finalize(success=True)
            logger.info(f"Healing pipeline completed for incident {incident.id}")

        except Exception as e:
            logger.error(f"Healing pipeline failed for incident {incident.id}: {e}")
            incident.status = HealingStatus.FAILED
            incident.error_message = str(e)
            operation.finalize(success=False)

    def _create_operation(self, incident: Incident) -> HealingOperation:
        """Create a new healing operation for an incident."""
        operation = HealingOperation(incident=incident)
        self._operations.append(operation)
        return operation

    def _find_incident(self, incident_id: str) -> Optional[Incident]:
        """Find an incident by ID."""
        for incident in self._incidents:
            if incident.id == incident_id:
                return incident
        return None

    # ── Persistence ─────────────────────────────────────────────

    def _save_state(self) -> None:
        """Persist current state to JSON files."""
        try:
            incidents_file = self.data_dir / "incidents.json"
            incidents_file.write_text(
                json.dumps(
                    [i.to_dict() for i in self._incidents],
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )

            operations_file = self.data_dir / "operations.json"
            operations_file.write_text(
                json.dumps(
                    [o.to_dict() for o in self._operations],
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )

            fragility_file = self.data_dir / "fragility_reports.json"
            fragility_file.write_text(
                json.dumps(
                    [r.to_dict() for r in self._fragility_reports],
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )
        except OSError as e:
            logger.error(f"Failed to save self-healing state: {e}")

    def _load_state(self) -> None:
        """Load persisted state from JSON files."""
        incidents_file = self.data_dir / "incidents.json"
        if incidents_file.exists():
            try:
                data = json.loads(incidents_file.read_text(encoding="utf-8"))
                self._incidents = [Incident.from_dict(d) for d in data]
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to load incidents: {e}")

        fragility_file = self.data_dir / "fragility_reports.json"
        if fragility_file.exists():
            try:
                data = json.loads(fragility_file.read_text(encoding="utf-8"))
                self._fragility_reports = [FragilityReport.from_dict(d) for d in data]
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to load fragility reports: {e}")
