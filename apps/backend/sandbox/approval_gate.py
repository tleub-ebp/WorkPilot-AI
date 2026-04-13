"""
Approval Gate — Human-in-the-loop for sandbox results.

After a dry-run, the user reviews the predicted diff and either
approves (apply to real working tree), rejects, or partially approves
specific files.
"""

from __future__ import annotations

import logging
import shutil
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .diff_predictor import DiffPrediction

logger = logging.getLogger(__name__)


class ApprovalDecision(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PARTIAL = "partial"


@dataclass
class FileApproval:
    """Per-file approval decision."""

    path: str
    approved: bool = False
    comment: str = ""


@dataclass
class ApprovalRequest:
    """A request for the user to approve sandbox results."""

    id: str
    prediction: DiffPrediction
    decision: ApprovalDecision = ApprovalDecision.PENDING
    file_approvals: list[FileApproval] = field(default_factory=list)
    reviewer: str = ""
    created_at: float = field(default_factory=time.time)
    decided_at: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ApprovalGate:
    """Manage user approval for sandbox dry-run results.

    Usage::

        gate = ApprovalGate()
        req = gate.create_request("run-001", prediction)
        # ... user reviews ...
        gate.approve(req)
        gate.apply(req, sandbox_root, target_root)
    """

    def __init__(self) -> None:
        self._requests: dict[str, ApprovalRequest] = {}

    def create_request(
        self,
        request_id: str,
        prediction: DiffPrediction,
    ) -> ApprovalRequest:
        """Create an approval request for a sandbox prediction."""
        req = ApprovalRequest(
            id=request_id,
            prediction=prediction,
            file_approvals=[FileApproval(path=f.path) for f in prediction.files],
        )
        self._requests[request_id] = req
        return req

    def approve(self, request: ApprovalRequest) -> None:
        """Mark the request as fully approved."""
        request.decision = ApprovalDecision.APPROVED
        request.decided_at = time.time()
        for fa in request.file_approvals:
            fa.approved = True
        logger.info("Approval request %s: APPROVED", request.id)

    def reject(self, request: ApprovalRequest, reason: str = "") -> None:
        """Reject the request."""
        request.decision = ApprovalDecision.REJECTED
        request.decided_at = time.time()
        for fa in request.file_approvals:
            fa.approved = False
            fa.comment = reason
        logger.info("Approval request %s: REJECTED (%s)", request.id, reason)

    def partial_approve(
        self, request: ApprovalRequest, approved_paths: set[str]
    ) -> None:
        """Approve only the specified file paths."""
        request.decision = ApprovalDecision.PARTIAL
        request.decided_at = time.time()
        for fa in request.file_approvals:
            fa.approved = fa.path in approved_paths
        count = sum(1 for fa in request.file_approvals if fa.approved)
        logger.info(
            "Approval request %s: PARTIAL (%d/%d files)",
            request.id,
            count,
            len(request.file_approvals),
        )

    def apply(
        self,
        request: ApprovalRequest,
        sandbox_root: Path,
        target_root: Path,
    ) -> list[str]:
        """Apply approved files from the sandbox to the real working tree.

        Returns the list of file paths that were applied.
        """
        if request.decision == ApprovalDecision.REJECTED:
            logger.warning("Cannot apply rejected request %s", request.id)
            return []

        if request.decision == ApprovalDecision.PENDING:
            logger.warning("Cannot apply pending request %s", request.id)
            return []

        applied: list[str] = []
        for fa in request.file_approvals:
            if not fa.approved:
                continue

            src = sandbox_root / fa.path
            dst = target_root / fa.path

            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                applied.append(fa.path)
            else:
                # File was deleted in sandbox
                if dst.exists():
                    dst.unlink()
                    applied.append(fa.path)

        logger.info(
            "Applied %d files from sandbox %s to %s",
            len(applied),
            sandbox_root,
            target_root,
        )
        return applied

    def get_request(self, request_id: str) -> ApprovalRequest | None:
        return self._requests.get(request_id)

    @property
    def pending_requests(self) -> list[ApprovalRequest]:
        return [
            r for r in self._requests.values() if r.decision == ApprovalDecision.PENDING
        ]
