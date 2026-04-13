"""
Sandbox Orchestrator — Coordinate dry-run execution of agent actions.

Ties together WorktreeManager, MockApiServer, DiffPredictor, and
ApprovalGate into a single workflow:

  1. Create a snapshot (worktree).
  2. Intercept API calls (mock server).
  3. Run the agent action inside the sandbox.
  4. Predict the diff.
  5. Present to the user for approval.
  6. Apply approved changes to the real working tree.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .approval_gate import ApprovalGate, ApprovalRequest
from .diff_predictor import DiffPrediction, DiffPredictor
from .mock_api_server import MockApiServer
from .worktree_manager import WorktreeInfo, WorktreeManager

logger = logging.getLogger(__name__)


class SandboxStatus(str, Enum):
    INITIALIZING = "initializing"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    APPLYING = "applying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SandboxRun:
    """Tracks the lifecycle of a single sandbox dry-run."""

    id: str
    repo_root: Path
    status: SandboxStatus = SandboxStatus.INITIALIZING
    worktree: WorktreeInfo | None = None
    prediction: DiffPrediction | None = None
    approval: ApprovalRequest | None = None
    applied_files: list[str] = field(default_factory=list)
    error: str | None = None
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class SandboxOrchestrator:
    """End-to-end sandbox simulation orchestrator.

    Usage::

        orch = SandboxOrchestrator(repo_root=Path("/my/repo"))
        run = orch.start_run()
        # ... execute agent action(s) inside run.worktree.path ...
        prediction = orch.predict_diff(run)
        orch.request_approval(run)
        # ... user approves ...
        orch.apply_approved(run)
        orch.finish_run(run)
    """

    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root
        self._worktree_mgr = WorktreeManager(repo_root)
        self._mock_server = MockApiServer()
        self._diff_predictor = DiffPredictor()
        self._approval_gate = ApprovalGate()
        self._runs: dict[str, SandboxRun] = {}

    @property
    def mock_server(self) -> MockApiServer:
        return self._mock_server

    @property
    def approval_gate(self) -> ApprovalGate:
        return self._approval_gate

    def start_run(self, ref: str = "HEAD") -> SandboxRun:
        """Create a new sandbox run with an isolated worktree."""
        run_id = f"sandbox-{uuid.uuid4().hex[:8]}"
        run = SandboxRun(id=run_id, repo_root=self._repo_root)

        try:
            run.worktree = self._worktree_mgr.create_snapshot(ref)
            run.status = SandboxStatus.RUNNING
            logger.info(
                "Sandbox run %s started (worktree=%s)", run_id, run.worktree.path
            )
        except Exception as exc:
            run.status = SandboxStatus.FAILED
            run.error = str(exc)
            logger.error("Sandbox run %s failed to start: %s", run_id, exc)

        self._runs[run_id] = run
        return run

    def execute_in_sandbox(
        self,
        run: SandboxRun,
        action: Callable[[Path], Any],
    ) -> Any:
        """Execute a callable inside the sandbox worktree.

        The *action* receives the sandbox path and can modify files freely.
        """
        if run.worktree is None:
            raise RuntimeError(f"Run {run.id} has no worktree")

        run.status = SandboxStatus.RUNNING
        try:
            result = action(run.worktree.path)
            return result
        except Exception as exc:
            run.status = SandboxStatus.FAILED
            run.error = str(exc)
            raise

    def predict_diff(self, run: SandboxRun) -> DiffPrediction:
        """Compare sandbox state with original to produce a diff."""
        if run.worktree is None:
            raise RuntimeError(f"Run {run.id} has no worktree")

        run.prediction = self._diff_predictor.predict(
            self._repo_root, run.worktree.path
        )
        run.status = SandboxStatus.AWAITING_APPROVAL
        return run.prediction

    def request_approval(self, run: SandboxRun) -> ApprovalRequest:
        """Create an approval request for the predicted diff."""
        if run.prediction is None:
            raise RuntimeError(f"Run {run.id} has no prediction yet")

        run.approval = self._approval_gate.create_request(run.id, run.prediction)
        return run.approval

    def apply_approved(self, run: SandboxRun) -> list[str]:
        """Apply approved sandbox changes to the real working tree."""
        if run.approval is None:
            raise RuntimeError(f"Run {run.id} has no approval request")
        if run.worktree is None:
            raise RuntimeError(f"Run {run.id} has no worktree")

        run.status = SandboxStatus.APPLYING
        run.applied_files = self._approval_gate.apply(
            run.approval, run.worktree.path, self._repo_root
        )
        return run.applied_files

    def finish_run(self, run: SandboxRun) -> None:
        """Clean up sandbox resources and mark the run complete."""
        if run.worktree:
            self._worktree_mgr.cleanup(run.worktree)

        run.status = SandboxStatus.COMPLETED
        run.finished_at = time.time()
        logger.info("Sandbox run %s completed", run.id)

    def cancel_run(self, run: SandboxRun) -> None:
        """Cancel and clean up an in-progress run."""
        if run.worktree:
            self._worktree_mgr.cleanup(run.worktree)

        run.status = SandboxStatus.CANCELLED
        run.finished_at = time.time()
        logger.info("Sandbox run %s cancelled", run.id)

    def get_run(self, run_id: str) -> SandboxRun | None:
        return self._runs.get(run_id)

    def cleanup_all(self) -> None:
        """Clean up all sandbox resources."""
        self._worktree_mgr.cleanup_all()
        for run in self._runs.values():
            if run.status == SandboxStatus.RUNNING:
                run.status = SandboxStatus.CANCELLED
