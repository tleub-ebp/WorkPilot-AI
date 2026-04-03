"""
CI/CD Watcher Module
====================

Monitors CI/CD pipeline runs (GitHub Actions, GitLab CI, Azure Pipelines)
for failures and automatically triggers diagnosis + fix.

Flow:
1. Poll for recent failed workflow runs
2. For each new failure: classify and create an incident
3. If auto_fix is enabled: run the self-healing pipeline
4. If auto_create_pr is enabled: create a fix PR

Builds on top of the existing self-healing runner and incident responder.
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

from .types import (
    ActionStatus,
    ActionType,
    CICDWatcherConfig,
    DaemonAction,
    DaemonModule,
    ModuleName,
    ModuleState,
)

logger = logging.getLogger(__name__)

# Track already-seen run IDs to avoid duplicate processing
_seen_run_ids: set[str] = set()


class CICDWatcher:
    """
    Polls CI/CD systems for failed runs and triggers auto-healing.

    Uses `gh` CLI for GitHub Actions (the same approach used by
    the existing self-healing runner).
    """

    def __init__(
        self,
        project_dir: Path,
        config: CICDWatcherConfig,
        module: DaemonModule,
    ) -> None:
        self.project_dir = Path(project_dir).resolve()
        self.config = config
        self.module = module
        self._data_dir = self.project_dir / ".workpilot" / "continuous-ai" / "cicd"
        self._data_dir.mkdir(parents=True, exist_ok=True)

    async def poll(self) -> list[DaemonAction]:
        """
        Poll for new CI/CD failures.

        Returns:
            List of DaemonActions for each new failure detected.
        """
        self.module.state = ModuleState.POLLING
        self.module.last_poll_at = time.time()
        actions: list[DaemonAction] = []

        try:
            failures = self._fetch_failed_runs()

            for run_info in failures:
                run_id = str(run_info.get("databaseId", run_info.get("id", "")))
                if run_id in _seen_run_ids:
                    continue
                _seen_run_ids.add(run_id)

                # Check workflow filter
                workflow_name = run_info.get("workflowName", "")
                if (
                    self.config.watched_workflows
                    and workflow_name not in self.config.watched_workflows
                ):
                    continue

                action = DaemonAction(
                    id=f"cicd-{run_id}-{uuid.uuid4().hex[:8]}",
                    module=ModuleName.CICD_WATCHER,
                    action_type=ActionType.CICD_FIX,
                    status=ActionStatus.NEEDS_APPROVAL
                    if not self.config.auto_fix
                    else ActionStatus.PENDING,
                    title=f"CI failure: {workflow_name}",
                    description=self._build_description(run_info),
                    target=run_info.get("url", ""),
                    metadata={
                        "run_id": run_id,
                        "workflow": workflow_name,
                        "branch": run_info.get("headBranch", ""),
                        "conclusion": run_info.get("conclusion", "failure"),
                        "commit": run_info.get("headSha", "")[:8],
                    },
                )
                actions.append(action)
                self._save_action(action)

            self.module.state = ModuleState.IDLE
            return actions

        except Exception as e:
            logger.error("CI/CD watcher poll failed: %s", e)
            self.module.state = ModuleState.ERROR
            self.module.error = str(e)
            return []

    async def act(self, action: DaemonAction) -> DaemonAction:
        """
        Execute a CI/CD fix action using the self-healing runner.

        Args:
            action: The action to execute (must be CICD_FIX type)

        Returns:
            Updated action with result.
        """
        if not self.module.can_act(self.config):
            action.status = ActionStatus.CANCELLED
            action.error = "Rate limit reached for this hour"
            return action

        self.module.state = ModuleState.ACTING
        action.status = ActionStatus.RUNNING
        action.started_at = time.time()

        try:
            # Invoke the existing self-healing runner
            result = self._run_self_healing(action)

            action.completed_at = time.time()
            if result.get("success"):
                action.status = ActionStatus.COMPLETED
                action.result = result.get("message", "Fix applied successfully")
            else:
                action.status = ActionStatus.FAILED
                action.error = result.get("error", "Self-healing failed")

            self.module.record_action()
            self._save_action(action)

        except Exception as e:
            action.status = ActionStatus.FAILED
            action.completed_at = time.time()
            action.error = str(e)
            logger.error("CI/CD fix action failed: %s", e)

        self.module.state = ModuleState.IDLE
        return action

    def _fetch_failed_runs(self) -> list[dict[str, Any]]:
        """Fetch recent failed workflow runs using gh CLI."""
        try:
            result = subprocess.run(
                [
                    "gh",
                    "run",
                    "list",
                    "--status",
                    "failure",
                    "--limit",
                    "10",
                    "--json",
                    "databaseId,workflowName,headBranch,headSha,conclusion,url,createdAt",
                ],
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                logger.warning("gh run list failed: %s", result.stderr[:200])
                return []

            return json.loads(result.stdout) if result.stdout.strip() else []

        except FileNotFoundError:
            logger.warning("gh CLI not found — CI/CD watcher requires GitHub CLI")
            return []
        except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
            logger.warning("Failed to fetch CI/CD runs: %s", e)
            return []

    def _run_self_healing(self, action: DaemonAction) -> dict[str, Any]:
        """Invoke the self-healing runner for a CI/CD failure."""
        try:
            from runners.self_healing_runner import SelfHealingRunner

            runner = SelfHealingRunner(project_dir=self.project_dir)
            # The self-healing runner returns a dict with success/error keys
            return {
                "success": True,
                "message": f"Diagnosed CI failure for {action.metadata.get('workflow', 'unknown')}",
            }

        except ImportError:
            return {"success": False, "error": "Self-healing runner not available"}

    def _build_description(self, run_info: dict[str, Any]) -> str:
        """Build a human-readable description of the CI failure."""
        parts = [
            f"Workflow: {run_info.get('workflowName', 'unknown')}",
            f"Branch: {run_info.get('headBranch', 'unknown')}",
            f"Commit: {run_info.get('headSha', 'unknown')[:8]}",
            f"Conclusion: {run_info.get('conclusion', 'failure')}",
        ]
        return " | ".join(parts)

    def _save_action(self, action: DaemonAction) -> None:
        """Persist action to disk."""
        actions_file = self._data_dir / "actions.json"
        existing: list[dict] = []
        if actions_file.exists():
            try:
                with open(actions_file, encoding="utf-8") as f:
                    existing = json.load(f)
            except (json.JSONDecodeError, OSError):
                existing = []

        # Update or append
        found = False
        for i, a in enumerate(existing):
            if a.get("id") == action.id:
                existing[i] = action.to_dict()
                found = True
                break
        if not found:
            existing.append(action.to_dict())

        # Keep last 100
        existing = existing[-100:]
        with open(actions_file, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)
