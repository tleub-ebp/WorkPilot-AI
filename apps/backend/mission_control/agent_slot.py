"""
Agent Slot — Represents a single agent in the Mission Control orchestrator.

Each slot tracks:
- Agent identity (id, role, name)
- Assigned LLM provider + model
- Runtime state (idle, running, paused, completed, error)
- Token consumption
- Files being worked on
- Live reasoning / decision tree
"""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentStatus(str, Enum):
    """Runtime status of an agent slot."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"
    WAITING = "waiting"


class AgentRole(str, Enum):
    """Pre-defined agent roles with recommended model tiers."""

    ARCHITECT = "architect"
    CODER = "coder"
    TESTER = "tester"
    REVIEWER = "reviewer"
    DOCUMENTER = "documenter"
    PLANNER = "planner"
    DEBUGGER = "debugger"
    CUSTOM = "custom"


# Recommended model tiers per role
ROLE_MODEL_RECOMMENDATIONS: dict[AgentRole, str] = {
    AgentRole.ARCHITECT: "flagship",
    AgentRole.CODER: "standard",
    AgentRole.TESTER: "fast",
    AgentRole.REVIEWER: "standard",
    AgentRole.DOCUMENTER: "fast",
    AgentRole.PLANNER: "flagship",
    AgentRole.DEBUGGER: "standard",
    AgentRole.CUSTOM: "standard",
}


@dataclass
class TokenUsage:
    """Token consumption tracking for an agent."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0

    def add(self, input_t: int = 0, output_t: int = 0, cost: float = 0.0):
        self.input_tokens += input_t
        self.output_tokens += output_t
        self.total_tokens = self.input_tokens + self.output_tokens
        self.estimated_cost_usd += cost

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
        }


@dataclass
class AgentSlot:
    """
    A single agent slot in Mission Control.

    Represents one running (or idle) agent with its full state.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    role: AgentRole = AgentRole.CUSTOM
    status: AgentStatus = AgentStatus.IDLE

    # LLM configuration
    provider: str = ""
    model: str = ""
    model_label: str = ""

    # Runtime tracking
    current_task: str = ""
    current_step: str = ""
    progress: float = 0.0  # 0.0 - 1.0
    tokens: TokenUsage = field(default_factory=TokenUsage)

    # Files being worked on
    active_files: list[str] = field(default_factory=list)

    # Live reasoning
    current_thinking: str = ""
    last_tool_call: str = ""
    last_tool_input: str = ""

    # Decision tree node IDs (references into DecisionTree)
    decision_path: list[str] = field(default_factory=list)

    # Timing
    started_at: float | None = None
    completed_at: float | None = None
    paused_at: float | None = None

    # Streaming session link
    streaming_session_id: str | None = None

    # Error info
    error_message: str = ""

    def start(self, task: str = ""):
        """Mark agent as running."""
        self.status = AgentStatus.RUNNING
        self.current_task = task
        self.started_at = time.time()
        self.completed_at = None
        self.error_message = ""

    def pause(self):
        """Pause the agent."""
        if self.status == AgentStatus.RUNNING:
            self.status = AgentStatus.PAUSED
            self.paused_at = time.time()

    def resume(self):
        """Resume a paused agent."""
        if self.status == AgentStatus.PAUSED:
            self.status = AgentStatus.RUNNING
            self.paused_at = None

    def complete(self):
        """Mark agent as completed."""
        self.status = AgentStatus.COMPLETED
        self.completed_at = time.time()
        self.progress = 1.0

    def fail(self, error: str = ""):
        """Mark agent as errored."""
        self.status = AgentStatus.ERROR
        self.completed_at = time.time()
        self.error_message = error

    def reset(self):
        """Reset agent to idle state."""
        self.status = AgentStatus.IDLE
        self.current_task = ""
        self.current_step = ""
        self.progress = 0.0
        self.tokens = TokenUsage()
        self.active_files = []
        self.current_thinking = ""
        self.last_tool_call = ""
        self.last_tool_input = ""
        self.decision_path = []
        self.started_at = None
        self.completed_at = None
        self.paused_at = None
        self.error_message = ""

    @property
    def elapsed_seconds(self) -> float:
        """Elapsed time since agent started."""
        if not self.started_at:
            return 0.0
        end = self.completed_at or time.time()
        return round(end - self.started_at, 1)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for API / WebSocket transport."""
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role.value,
            "status": self.status.value,
            "provider": self.provider,
            "model": self.model,
            "model_label": self.model_label,
            "current_task": self.current_task,
            "current_step": self.current_step,
            "progress": self.progress,
            "tokens": self.tokens.to_dict(),
            "active_files": self.active_files,
            "current_thinking": self.current_thinking,
            "last_tool_call": self.last_tool_call,
            "last_tool_input": self.last_tool_input,
            "decision_path": self.decision_path,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "elapsed_seconds": self.elapsed_seconds,
            "streaming_session_id": self.streaming_session_id,
            "error_message": self.error_message,
        }
