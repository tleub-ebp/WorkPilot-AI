"""
Takeover Detector for the Live Companion.

Monitors developer activity to detect when they appear to be stuck.
When inactivity exceeds a threshold, proposes an AI takeover for the
file the developer was working on.
"""

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .types import TakeoverProposal, TakeoverStatus

logger = logging.getLogger(__name__)


@dataclass
class FileActivity:
    """Tracks activity on a specific file."""

    file_path: str
    last_change_at: float = 0.0
    change_count: int = 0
    total_lines_changed: int = 0

    @property
    def inactive_seconds(self) -> int:
        if self.last_change_at == 0:
            return 0
        return int(time.time() - self.last_change_at)


class TakeoverDetector:
    """Detects when the developer is stuck and proposes AI takeover."""

    def __init__(
        self,
        inactivity_threshold_seconds: int = 120,
        min_changes_before_detect: int = 3,
    ):
        self.inactivity_threshold = inactivity_threshold_seconds
        self.min_changes = min_changes_before_detect
        self._file_activities: dict[str, FileActivity] = {}
        self._proposed_files: set[str] = set()

    def record_change(self, file_path: str, lines_changed: int = 1) -> None:
        """Record a file change event."""
        if file_path not in self._file_activities:
            self._file_activities[file_path] = FileActivity(file_path=file_path)

        activity = self._file_activities[file_path]
        activity.last_change_at = time.time()
        activity.change_count += 1
        activity.total_lines_changed += lines_changed

        # Clear proposed state if the developer is actively editing
        self._proposed_files.discard(file_path)

    def check_for_stuck_files(self) -> list[TakeoverProposal]:
        """Check for files where the developer appears stuck."""
        proposals = []

        for file_path, activity in self._file_activities.items():
            if file_path in self._proposed_files:
                continue

            if activity.change_count < self.min_changes:
                continue

            inactive = activity.inactive_seconds
            if inactive < self.inactivity_threshold:
                continue

            # Developer has been inactive on a file they were actively editing
            proposal = TakeoverProposal(
                proposal_id=TakeoverProposal.generate_id(),
                file_path=file_path,
                reason="inactivity",
                description=(
                    f"You've been inactive on {Path(file_path).name} for "
                    f"{inactive // 60}m{inactive % 60}s after {activity.change_count} edits. "
                    f"Would you like AI to help with this file?"
                ),
                inactivity_seconds=inactive,
                status=TakeoverStatus.PROPOSED,
            )

            self._proposed_files.add(file_path)
            proposals.append(proposal)

        return proposals

    def dismiss_proposal(self, file_path: str) -> None:
        """Mark a file as dismissed (don't propose again until new activity)."""
        self._proposed_files.add(file_path)

    def accept_proposal(self, file_path: str) -> None:
        """Mark a takeover as accepted."""
        self._proposed_files.add(file_path)

    def reset_file(self, file_path: str) -> None:
        """Reset tracking for a file."""
        self._file_activities.pop(file_path, None)
        self._proposed_files.discard(file_path)

    def reset_all(self) -> None:
        """Reset all tracking state."""
        self._file_activities.clear()
        self._proposed_files.clear()

    def get_activity_summary(self) -> dict[str, Any]:
        """Get a summary of tracked file activities."""
        return {
            "tracked_files": len(self._file_activities),
            "proposed_files": len(self._proposed_files),
            "files": {
                path: {
                    "change_count": a.change_count,
                    "inactive_seconds": a.inactive_seconds,
                    "total_lines_changed": a.total_lines_changed,
                }
                for path, a in self._file_activities.items()
            },
        }
