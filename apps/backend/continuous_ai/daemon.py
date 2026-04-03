"""
Continuous AI Daemon
====================

Main orchestrator that runs an asyncio event loop, scheduling
module polls at their configured intervals and dispatching actions.

The daemon runs as a long-lived process, typically spawned by the
Electron frontend and managed via IPC. It emits structured JSON
events to stdout for the frontend to parse.

Architecture:
    - Each module (cicd_watcher, dependency_sentinel, issue_responder)
      has its own poll interval and action budget
    - The daemon schedules polls using asyncio.sleep between intervals
    - Actions that need approval are emitted as events; the frontend
      can approve/reject them via IPC
    - A daily budget cap prevents runaway API costs
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from core.workflow_logger import workflow_logger

from .cicd_watcher import CICDWatcher
from .dependency_sentinel import DependencySentinel
from .issue_responder import IssueResponder
from .types import (
    ActionStatus,
    CICDWatcherConfig,
    ContinuousAIConfig,
    ContinuousAIStatus,
    DaemonAction,
    DaemonModule,
    DependencySentinelConfig,
    IssueResponderConfig,
    ModuleName,
    ModuleState,
)

logger = logging.getLogger(__name__)

DAEMON_EVENT_PREFIX = "__DAEMON_EVENT__:"


def emit_daemon_event(event_type: str, payload: dict[str, Any] | None = None) -> None:
    """Emit a daemon event to stdout for frontend parsing."""
    event = {"type": event_type, "timestamp": time.time(), **(payload or {})}
    try:
        print(f"{DAEMON_EVENT_PREFIX}{json.dumps(event, default=str)}", flush=True)
    except (OSError, UnicodeEncodeError):
        pass


class ContinuousAIDaemon:
    """
    Main daemon that orchestrates all continuous AI modules.

    Usage:
        daemon = ContinuousAIDaemon(project_dir, config)
        await daemon.start()    # Runs until cancelled
        await daemon.stop()     # Graceful shutdown
    """

    def __init__(
        self,
        project_dir: Path,
        config: ContinuousAIConfig,
    ) -> None:
        self.project_dir = Path(project_dir).resolve()
        self.config = config
        self._data_dir = self.project_dir / ".workpilot" / "continuous-ai"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        # Initialize status
        self.status = ContinuousAIStatus(
            daily_budget_usd=config.daily_budget_usd,
        )

        # Initialize modules
        self._modules: dict[str, DaemonModule] = {}
        self._watchers: dict[
            str, CICDWatcher | DependencySentinel | IssueResponder
        ] = {}
        self._tasks: list[asyncio.Task] = []
        self._running = False
        self._pending_actions: dict[str, DaemonAction] = {}

        self._init_modules()

    def _init_modules(self) -> None:
        """Initialize all daemon modules based on config."""
        # CI/CD Watcher
        cicd_module = DaemonModule(
            name=ModuleName.CICD_WATCHER,
            state=ModuleState.IDLE
            if self.config.cicd_watcher.enabled
            else ModuleState.DISABLED,
        )
        self._modules["cicd_watcher"] = cicd_module
        self.status.modules["cicd_watcher"] = cicd_module
        if self.config.cicd_watcher.enabled:
            self._watchers["cicd_watcher"] = CICDWatcher(
                self.project_dir, self.config.cicd_watcher, cicd_module
            )

        # Dependency Sentinel
        deps_module = DaemonModule(
            name=ModuleName.DEPENDENCY_SENTINEL,
            state=ModuleState.IDLE
            if self.config.dependency_sentinel.enabled
            else ModuleState.DISABLED,
        )
        self._modules["dependency_sentinel"] = deps_module
        self.status.modules["dependency_sentinel"] = deps_module
        if self.config.dependency_sentinel.enabled:
            self._watchers["dependency_sentinel"] = DependencySentinel(
                self.project_dir, self.config.dependency_sentinel, deps_module
            )

        # Issue Responder
        issue_module = DaemonModule(
            name=ModuleName.ISSUE_RESPONDER,
            state=ModuleState.IDLE
            if self.config.issue_responder.enabled
            else ModuleState.DISABLED,
        )
        self._modules["issue_responder"] = issue_module
        self.status.modules["issue_responder"] = issue_module
        if self.config.issue_responder.enabled:
            self._watchers["issue_responder"] = IssueResponder(
                self.project_dir, self.config.issue_responder, issue_module
            )

    async def start(self) -> None:
        """Start the daemon. Runs until stop() is called."""
        if self._running:
            return

        self._running = True
        self.status.running = True
        self.status.started_at = time.time()

        trace_id = workflow_logger.log_agent_start(
            "Continuous AI Daemon",
            "daemon_start",
            {
                "project_dir": str(self.project_dir),
                "enabled_modules": [
                    k
                    for k, m in self._modules.items()
                    if m.state != ModuleState.DISABLED
                ],
            },
        )

        emit_daemon_event(
            "daemon_started",
            {
                "project_dir": str(self.project_dir),
                "enabled_modules": [
                    k
                    for k, m in self._modules.items()
                    if m.state != ModuleState.DISABLED
                ],
            },
        )

        logger.info(
            "Continuous AI daemon started with %d enabled modules",
            self.status.enabled_modules_count,
        )

        try:
            # Launch poll loops for each enabled module
            module_configs = {
                "cicd_watcher": self.config.cicd_watcher,
                "dependency_sentinel": self.config.dependency_sentinel,
                "issue_responder": self.config.issue_responder,
            }

            for module_name, watcher in self._watchers.items():
                config = module_configs.get(module_name)
                if config and config.enabled:
                    task = asyncio.create_task(
                        self._poll_loop(module_name, watcher, config)
                    )
                    self._tasks.append(task)

            # Wait for all tasks (they run forever until cancelled)
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)

        except asyncio.CancelledError:
            logger.info("Daemon cancelled")
        finally:
            self._running = False
            self.status.running = False
            workflow_logger.log_agent_end(
                "Continuous AI Daemon",
                "stopped",
                {
                    "total_actions": sum(
                        m.total_actions for m in self._modules.values()
                    ),
                    "total_cost_usd": self.status.total_cost_today_usd,
                },
                trace_id=trace_id,
            )
            emit_daemon_event("daemon_stopped", {})

    async def stop(self) -> None:
        """Gracefully stop the daemon."""
        logger.info("Stopping continuous AI daemon")
        self._running = False
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()
        self._save_status()
        emit_daemon_event("daemon_stopped", {})

    async def approve_action(self, action_id: str) -> DaemonAction | None:
        """Approve a pending action for execution."""
        action = self._pending_actions.get(action_id)
        if not action or action.status != ActionStatus.NEEDS_APPROVAL:
            return None

        action.status = ActionStatus.PENDING
        module_name = action.module.value
        watcher = self._watchers.get(module_name)
        if watcher:
            action = await watcher.act(action)
            self.status.recent_actions.append(action)
            self.status.total_cost_today_usd += action.cost_usd
            emit_daemon_event("action_completed", action.to_dict())

        del self._pending_actions[action_id]
        return action

    async def reject_action(self, action_id: str) -> DaemonAction | None:
        """Reject a pending action."""
        action = self._pending_actions.pop(action_id, None)
        if action:
            action.status = ActionStatus.CANCELLED
            emit_daemon_event("action_rejected", {"action_id": action_id})
        return action

    def get_status(self) -> dict[str, Any]:
        """Get current daemon status as a dict."""
        return self.status.to_dict()

    async def _poll_loop(
        self,
        module_name: str,
        watcher: CICDWatcher | DependencySentinel | IssueResponder,
        config: CICDWatcherConfig | DependencySentinelConfig | IssueResponderConfig,
    ) -> None:
        """
        Poll loop for a single module.

        Runs at the configured interval, checking for new items
        and dispatching actions.
        """
        while self._running:
            try:
                # Budget check
                if self.status.is_over_budget:
                    logger.info("Daily budget exceeded — pausing %s", module_name)
                    emit_daemon_event(
                        "budget_exceeded",
                        {
                            "module": module_name,
                            "spent": self.status.total_cost_today_usd,
                            "budget": self.status.daily_budget_usd,
                        },
                    )
                    await asyncio.sleep(3600)  # Check again in 1 hour
                    continue

                # Quiet hours check
                if self._is_quiet_hours(config):
                    logger.debug("Quiet hours — skipping %s poll", module_name)
                    await asyncio.sleep(config.poll_interval_seconds)
                    continue

                # Poll
                emit_daemon_event("module_polling", {"module": module_name})
                actions = await watcher.poll()

                for action in actions:
                    emit_daemon_event("action_detected", action.to_dict())

                    if action.status == ActionStatus.NEEDS_APPROVAL:
                        self._pending_actions[action.id] = action
                        emit_daemon_event("action_needs_approval", action.to_dict())
                    elif action.status == ActionStatus.PENDING and config.auto_act:
                        # Auto-execute
                        action = await watcher.act(action)
                        self.status.recent_actions.append(action)
                        self.status.total_cost_today_usd += action.cost_usd
                        emit_daemon_event("action_completed", action.to_dict())

                emit_daemon_event(
                    "module_poll_complete",
                    {
                        "module": module_name,
                        "actions_found": len(actions),
                    },
                )

            except Exception as e:
                logger.error("Error in %s poll loop: %s", module_name, e, exc_info=True)
                emit_daemon_event(
                    "module_error",
                    {
                        "module": module_name,
                        "error": str(e),
                    },
                )

            # Wait for next poll interval
            await asyncio.sleep(config.poll_interval_seconds)

    @staticmethod
    def _is_quiet_hours(
        config: CICDWatcherConfig | DependencySentinelConfig | IssueResponderConfig,
    ) -> bool:
        """Check if we're in quiet hours."""
        if not config.quiet_hours_start or not config.quiet_hours_end:
            return False

        try:
            now = datetime.now()
            current_time = now.hour * 60 + now.minute

            start_parts = config.quiet_hours_start.split(":")
            end_parts = config.quiet_hours_end.split(":")
            start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
            end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])

            if start_minutes <= end_minutes:
                return start_minutes <= current_time <= end_minutes
            # Overnight quiet hours (e.g., 22:00 to 07:00)
            return current_time >= start_minutes or current_time <= end_minutes

        except (ValueError, IndexError):
            return False

    def _save_status(self) -> None:
        """Persist current status to disk."""
        status_file = self._data_dir / "status.json"
        try:
            with open(status_file, "w", encoding="utf-8") as f:
                json.dump(self.status.to_dict(), f, indent=2)
        except OSError as e:
            logger.debug("Failed to save daemon status: %s", e)
