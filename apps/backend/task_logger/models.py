"""
Data models for task logging.
"""

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Optional


class LogPhase(str, Enum):
    """Log phases matching the execution flow."""

    PLANNING = "planning"
    CODING = "coding"
    VALIDATION = "validation"


class LogEntryType(str, Enum):
    """Types of log entries."""

    TEXT = "text"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    PHASE_START = "phase_start"
    PHASE_END = "phase_end"
    ERROR = "error"
    SUCCESS = "success"
    INFO = "info"


@dataclass
class LogEntry:
    """A single log entry."""

    timestamp: str
    type: str
    content: str
    phase: str
    tool_name: Optional[str] = None
    tool_input: Optional[str] = None
    subtask_id: Optional[str] = None
    session: Optional[int] = None
    # New fields for expandable detail view
    detail: Optional[str] = (
        None  # Full content that can be expanded (e.g., file contents, command output)
    )
    subphase: Optional[str] = None  # Subphase grouping (e.g., "PROJECT DISCOVERY", "CONTEXT GATHERING")
    collapsed: Optional[bool] = None  # Whether to show collapsed by default in UI

    def to_dict(self) -> dict:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class PhaseLog:
    """Logs for a single phase."""

    phase: str
    status: str  # "pending", "active", "completed", "failed"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    entries: list = None

    def __post_init__(self):
        if self.entries is None:
            self.entries = []

    def to_dict(self) -> dict:
        return {
            "phase": self.phase,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "entries": self.entries,
        }