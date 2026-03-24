"""
Data models for Agent Replay & Debug Mode.

Structured recording of each agent session step: tool calls, file modifications,
reasoning, tokens consumed, decisions made.
"""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ReplayStepType(str, Enum):
    """Types of replay steps."""

    SESSION_START = "session_start"
    SESSION_END = "session_end"
    AGENT_THINKING = "agent_thinking"
    AGENT_RESPONSE = "agent_response"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    FILE_READ = "file_read"
    FILE_CREATE = "file_create"
    FILE_UPDATE = "file_update"
    FILE_DELETE = "file_delete"
    COMMAND_RUN = "command_run"
    COMMAND_OUTPUT = "command_output"
    TEST_RUN = "test_run"
    TEST_RESULT = "test_result"
    DECISION = "decision"
    ERROR = "error"
    PROGRESS = "progress"
    BREAKPOINT_HIT = "breakpoint_hit"


class BreakpointType(str, Enum):
    """Types of breakpoints for debug mode."""

    TOOL_CALL = "tool_call"
    FILE_CHANGE = "file_change"
    DECISION = "decision"
    ERROR = "error"
    TOKEN_THRESHOLD = "token_threshold"
    STEP_INDEX = "step_index"
    PATTERN_MATCH = "pattern_match"


@dataclass
class FileDiff:
    """Represents a file diff at a specific step."""

    file_path: str
    operation: str  # create, update, delete, read
    before_content: str | None = None
    after_content: str | None = None
    diff_lines: list[str] | None = None
    line_count_before: int = 0
    line_count_after: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "operation": self.operation,
            "before_content": self.before_content,
            "after_content": self.after_content,
            "diff_lines": self.diff_lines,
            "line_count_before": self.line_count_before,
            "line_count_after": self.line_count_after,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FileDiff":
        return cls(
            file_path=data["file_path"],
            operation=data["operation"],
            before_content=data.get("before_content"),
            after_content=data.get("after_content"),
            diff_lines=data.get("diff_lines"),
            line_count_before=data.get("line_count_before", 0),
            line_count_after=data.get("line_count_after", 0),
        )


@dataclass
class ReplayStep:
    """A single step in the agent replay timeline."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    step_index: int = 0
    step_type: ReplayStepType = ReplayStepType.AGENT_THINKING
    timestamp: float = field(default_factory=time.time)
    duration_ms: float = 0.0

    # Content
    label: str = ""
    description: str = ""
    reasoning: str = ""

    # Tool call details
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    tool_output: str | None = None

    # File changes at this step
    file_diffs: list[FileDiff] = field(default_factory=list)

    # Token usage at this step
    input_tokens: int = 0
    output_tokens: int = 0
    cumulative_tokens: int = 0
    cost_usd: float = 0.0
    cumulative_cost_usd: float = 0.0

    # Decision tree link
    decision_node_id: str | None = None
    parent_step_id: str | None = None
    children_step_ids: list[str] = field(default_factory=list)

    # Options considered at decision points
    options_considered: list[str] = field(default_factory=list)
    chosen_option: str | None = None

    # Breakpoint info
    is_breakpoint: bool = False
    breakpoint_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "step_index": self.step_index,
            "step_type": self.step_type.value,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "label": self.label,
            "description": self.description,
            "reasoning": self.reasoning,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "tool_output": self.tool_output,
            "file_diffs": [d.to_dict() for d in self.file_diffs],
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cumulative_tokens": self.cumulative_tokens,
            "cost_usd": self.cost_usd,
            "cumulative_cost_usd": self.cumulative_cost_usd,
            "decision_node_id": self.decision_node_id,
            "parent_step_id": self.parent_step_id,
            "children_step_ids": self.children_step_ids,
            "options_considered": self.options_considered,
            "chosen_option": self.chosen_option,
            "is_breakpoint": self.is_breakpoint,
            "breakpoint_id": self.breakpoint_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReplayStep":
        step = cls(
            id=data["id"],
            step_index=data["step_index"],
            step_type=ReplayStepType(data["step_type"]),
            timestamp=data["timestamp"],
            duration_ms=data.get("duration_ms", 0.0),
            label=data.get("label", ""),
            description=data.get("description", ""),
            reasoning=data.get("reasoning", ""),
            tool_name=data.get("tool_name"),
            tool_input=data.get("tool_input"),
            tool_output=data.get("tool_output"),
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            cumulative_tokens=data.get("cumulative_tokens", 0),
            cost_usd=data.get("cost_usd", 0.0),
            cumulative_cost_usd=data.get("cumulative_cost_usd", 0.0),
            decision_node_id=data.get("decision_node_id"),
            parent_step_id=data.get("parent_step_id"),
            children_step_ids=data.get("children_step_ids", []),
            options_considered=data.get("options_considered", []),
            chosen_option=data.get("chosen_option"),
            is_breakpoint=data.get("is_breakpoint", False),
            breakpoint_id=data.get("breakpoint_id"),
        )
        step.file_diffs = [FileDiff.from_dict(d) for d in data.get("file_diffs", [])]
        return step


@dataclass
class Breakpoint:
    """A debug breakpoint configuration."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    breakpoint_type: BreakpointType = BreakpointType.TOOL_CALL
    enabled: bool = True
    condition: str = ""  # e.g., tool name, file pattern, token count
    description: str = ""
    hit_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "breakpoint_type": self.breakpoint_type.value,
            "enabled": self.enabled,
            "condition": self.condition,
            "description": self.description,
            "hit_count": self.hit_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Breakpoint":
        return cls(
            id=data["id"],
            breakpoint_type=BreakpointType(data["breakpoint_type"]),
            enabled=data.get("enabled", True),
            condition=data.get("condition", ""),
            description=data.get("description", ""),
            hit_count=data.get("hit_count", 0),
        )


@dataclass
class ReplaySession:
    """A complete recorded agent session for replay."""

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str | None = None
    agent_name: str = ""
    agent_role: str = ""

    # LLM config used
    provider: str = ""
    model: str = ""
    model_label: str = ""

    # Task info
    task_description: str = ""
    project_path: str = ""

    # Timing
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None

    # Steps
    steps: list[ReplayStep] = field(default_factory=list)

    # Breakpoints
    breakpoints: list[Breakpoint] = field(default_factory=list)

    # Aggregate stats
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    total_tool_calls: int = 0
    total_file_changes: int = 0
    files_touched: list[str] = field(default_factory=list)

    # Status
    status: str = "recording"  # recording, completed, error

    # Tags for organization
    tags: list[str] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    @property
    def step_count(self) -> int:
        return len(self.steps)

    def file_heatmap(self) -> dict[str, int]:
        """Compute file touch frequency across all steps."""
        heatmap: dict[str, int] = {}
        for step in self.steps:
            for diff in step.file_diffs:
                heatmap[diff.file_path] = heatmap.get(diff.file_path, 0) + 1
        return dict(sorted(heatmap.items(), key=lambda x: x[1], reverse=True))

    def tool_usage_stats(self) -> dict[str, int]:
        """Compute tool usage frequency."""
        stats: dict[str, int] = {}
        for step in self.steps:
            if step.tool_name:
                stats[step.tool_name] = stats.get(step.tool_name, 0) + 1
        return dict(sorted(stats.items(), key=lambda x: x[1], reverse=True))

    def token_timeline(self) -> list[dict[str, Any]]:
        """Get token consumption over time."""
        timeline = []
        for step in self.steps:
            if step.input_tokens > 0 or step.output_tokens > 0:
                timeline.append(
                    {
                        "step_index": step.step_index,
                        "timestamp": step.timestamp,
                        "input_tokens": step.input_tokens,
                        "output_tokens": step.output_tokens,
                        "cumulative": step.cumulative_tokens,
                        "cost_usd": step.cost_usd,
                        "cumulative_cost_usd": step.cumulative_cost_usd,
                    }
                )
        return timeline

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "agent_role": self.agent_role,
            "provider": self.provider,
            "model": self.model,
            "model_label": self.model_label,
            "task_description": self.task_description,
            "project_path": self.project_path,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.duration_seconds,
            "step_count": self.step_count,
            "steps": [s.to_dict() for s in self.steps],
            "breakpoints": [b.to_dict() for b in self.breakpoints],
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost_usd,
            "total_tool_calls": self.total_tool_calls,
            "total_file_changes": self.total_file_changes,
            "files_touched": self.files_touched,
            "file_heatmap": self.file_heatmap(),
            "tool_usage_stats": self.tool_usage_stats(),
            "token_timeline": self.token_timeline(),
            "status": self.status,
            "tags": self.tags,
        }

    def to_summary(self) -> dict[str, Any]:
        """Lightweight summary for list views."""
        return {
            "session_id": self.session_id,
            "agent_name": self.agent_name,
            "agent_role": self.agent_role,
            "provider": self.provider,
            "model_label": self.model_label,
            "task_description": self.task_description,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.duration_seconds,
            "step_count": self.step_count,
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost_usd,
            "total_tool_calls": self.total_tool_calls,
            "total_file_changes": self.total_file_changes,
            "status": self.status,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReplaySession":
        session = cls(
            session_id=data["session_id"],
            agent_id=data.get("agent_id"),
            agent_name=data.get("agent_name", ""),
            agent_role=data.get("agent_role", ""),
            provider=data.get("provider", ""),
            model=data.get("model", ""),
            model_label=data.get("model_label", ""),
            task_description=data.get("task_description", ""),
            project_path=data.get("project_path", ""),
            start_time=data["start_time"],
            end_time=data.get("end_time"),
            total_tokens=data.get("total_tokens", 0),
            total_cost_usd=data.get("total_cost_usd", 0.0),
            total_tool_calls=data.get("total_tool_calls", 0),
            total_file_changes=data.get("total_file_changes", 0),
            files_touched=data.get("files_touched", []),
            status=data.get("status", "completed"),
            tags=data.get("tags", []),
        )
        session.steps = [ReplayStep.from_dict(s) for s in data.get("steps", [])]
        session.breakpoints = [
            Breakpoint.from_dict(b) for b in data.get("breakpoints", [])
        ]
        return session


@dataclass
class ABComparison:
    """A/B comparison of two replay sessions."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    session_a_id: str = ""
    session_b_id: str = ""
    created_at: float = field(default_factory=time.time)

    # Computed comparison data
    token_diff: int = 0
    cost_diff: float = 0.0
    duration_diff: float = 0.0
    step_count_diff: int = 0
    tool_calls_diff: int = 0
    file_changes_diff: int = 0

    # Detailed comparisons
    common_files: list[str] = field(default_factory=list)
    unique_files_a: list[str] = field(default_factory=list)
    unique_files_b: list[str] = field(default_factory=list)
    common_tools: list[str] = field(default_factory=list)
    unique_tools_a: list[str] = field(default_factory=list)
    unique_tools_b: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "session_a_id": self.session_a_id,
            "session_b_id": self.session_b_id,
            "created_at": self.created_at,
            "token_diff": self.token_diff,
            "cost_diff": self.cost_diff,
            "duration_diff": self.duration_diff,
            "step_count_diff": self.step_count_diff,
            "tool_calls_diff": self.tool_calls_diff,
            "file_changes_diff": self.file_changes_diff,
            "common_files": self.common_files,
            "unique_files_a": self.unique_files_a,
            "unique_files_b": self.unique_files_b,
            "common_tools": self.common_tools,
            "unique_tools_a": self.unique_tools_a,
            "unique_tools_b": self.unique_tools_b,
        }
