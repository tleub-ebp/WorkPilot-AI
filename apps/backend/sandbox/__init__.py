"""
Agent Simulation Sandbox — Dry-run before commit.

Allows agents to execute actions in an isolated worktree (or overlay
copy) with mocked external APIs.  After the run, a diff is predicted
and presented for user approval before any changes touch the real
working tree.

Modules:
    - worktree_manager: create and manage isolated Git worktrees
    - mock_api_server: intercept and mock external API calls
    - diff_predictor: produce structured diffs from sandbox runs
    - approval_gate: human-in-the-loop approval flow
    - sandbox_orchestrator: end-to-end sandbox workflow
"""

from .approval_gate import (
    ApprovalDecision,
    ApprovalGate,
    ApprovalRequest,
    FileApproval,
)
from .diff_predictor import (
    ChangeType,
    DiffPrediction,
    DiffPredictor,
    FileDiff,
)
from .mock_api_server import (
    InterceptedRequest,
    MockApiServer,
    MockResponse,
    MockRule,
    MockStrategy,
)
from .sandbox_orchestrator import (
    SandboxOrchestrator,
    SandboxRun,
    SandboxStatus,
)
from .worktree_manager import WorktreeInfo, WorktreeManager

__all__ = [
    "SandboxOrchestrator",
    "SandboxRun",
    "SandboxStatus",
    "WorktreeManager",
    "WorktreeInfo",
    "MockApiServer",
    "MockResponse",
    "MockRule",
    "MockStrategy",
    "InterceptedRequest",
    "DiffPredictor",
    "DiffPrediction",
    "FileDiff",
    "ChangeType",
    "ApprovalGate",
    "ApprovalRequest",
    "ApprovalDecision",
    "FileApproval",
]
