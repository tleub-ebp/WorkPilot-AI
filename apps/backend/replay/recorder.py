"""
Replay Recorder — Records structured agent sessions for replay & debug.

Hooks into the existing streaming agent wrapper to capture every event
with full context for later replay, including file diffs, decision trees,
and token consumption tracking.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any

from .models import (
    ABComparison,
    Breakpoint,
    BreakpointType,
    FileDiff,
    ReplaySession,
    ReplayStep,
    ReplayStepType,
)

logger = logging.getLogger(__name__)


class ReplayRecorder:
    """
    Records agent sessions into structured ReplaySession objects.

    Features:
    - Automatic step recording with timestamps and durations
    - File diff tracking at each step
    - Token consumption tracking with cumulative totals
    - Decision tree linking
    - Breakpoint evaluation during recording
    - Persistent storage to disk (JSON)
    """

    def __init__(self, storage_dir: Path | None = None):
        self._storage_dir = storage_dir or Path.home() / ".workpilot" / "replays"
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._active_sessions: dict[str, ReplaySession] = {}
        self._step_counter: dict[str, int] = {}

    # -------------------------------------------------------------------
    # Session lifecycle
    # -------------------------------------------------------------------

    def start_session(
        self,
        session_id: str,
        metadata: dict[str, Any],
    ) -> ReplaySession:
        """Start recording a new replay session."""
        session = ReplaySession(
            session_id=session_id,
            agent_id=metadata.get("agent_id"),
            agent_name=metadata.get("agent_name", "Agent"),
            agent_role=metadata.get("agent_type", "coder"),
            provider=metadata.get("provider", ""),
            model=metadata.get("model", ""),
            model_label=metadata.get("model_label", ""),
            task_description=metadata.get("task", ""),
            project_path=metadata.get("project_path", ""),
            start_time=time.time(),
            status="recording",
            tags=metadata.get("tags", []),
        )

        self._active_sessions[session_id] = session
        self._step_counter[session_id] = 0

        # Record session start step
        self._add_step(
            session_id,
            ReplayStepType.SESSION_START,
            {
                "label": "Session Started",
                "description": f"Agent '{session.agent_name}' started task: {session.task_description[:200]}",
            },
        )

        logger.info(f"Replay recording started: {session_id}")
        return session

    def end_session(self, session_id: str) -> ReplaySession | None:
        """End recording and persist the session."""
        session = self._active_sessions.get(session_id)
        if not session:
            return None

        session.end_time = time.time()
        session.status = "completed"

        # Record session end step
        self._add_step(
            session_id,
            ReplayStepType.SESSION_END,
            {
                "label": "Session Completed",
                "description": f"Completed in {session.duration_seconds:.1f}s — "
                f"{session.total_tokens} tokens, {session.total_tool_calls} tool calls",
            },
        )

        # Compute final stats
        self._finalize_stats(session)

        # Persist to disk
        self.save_session(session)

        # Cleanup
        del self._active_sessions[session_id]
        del self._step_counter[session_id]

        logger.info(
            f"Replay recording ended: {session_id} ({session.step_count} steps)"
        )
        return session

    # -------------------------------------------------------------------
    # Event recording
    # -------------------------------------------------------------------

    def record_thinking(self, session_id: str, thinking: str) -> ReplayStep | None:
        """Record an agent thinking/reasoning event."""
        return self._add_step(
            session_id,
            ReplayStepType.AGENT_THINKING,
            {
                "label": "Agent Thinking",
                "reasoning": thinking[:2000],
                "description": thinking[:200],
            },
        )

    def record_response(
        self,
        session_id: str,
        response: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_usd: float = 0.0,
    ) -> ReplayStep | None:
        """Record an agent response with token usage."""
        return self._add_step(
            session_id,
            ReplayStepType.AGENT_RESPONSE,
            {
                "label": "Agent Response",
                "description": response[:500],
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost_usd,
            },
        )

    def record_tool_call(
        self,
        session_id: str,
        tool_name: str,
        tool_input: str | None = None,
        tool_input_dict: dict[str, Any] | None = None,
    ) -> ReplayStep | None:
        """Record a tool call event."""
        session = self._active_sessions.get(session_id)
        if session:
            session.total_tool_calls += 1

        return self._add_step(
            session_id,
            ReplayStepType.TOOL_CALL,
            {
                "label": f"Tool: {tool_name}",
                "tool_name": tool_name,
                "tool_input": tool_input_dict or {},
                "description": f"{tool_name}: {tool_input[:200]}"
                if tool_input
                else tool_name,
            },
        )

    def record_tool_result(
        self,
        session_id: str,
        tool_name: str,
        output: str | None = None,
        success: bool = True,
    ) -> ReplayStep | None:
        """Record a tool result event."""
        return self._add_step(
            session_id,
            ReplayStepType.TOOL_RESULT,
            {
                "label": f"Result: {tool_name}",
                "tool_name": tool_name,
                "tool_output": output[:2000] if output else "",
                "description": f"{'✓' if success else '✗'} {tool_name}",
            },
        )

    def record_file_change(
        self,
        session_id: str,
        file_path: str,
        operation: str = "update",
        before_content: str | None = None,
        after_content: str | None = None,
    ) -> ReplayStep | None:
        """Record a file change with diff information."""
        session = self._active_sessions.get(session_id)
        if not session:
            return None

        session.total_file_changes += 1
        if file_path not in session.files_touched:
            session.files_touched.append(file_path)

        step_type = {
            "create": ReplayStepType.FILE_CREATE,
            "update": ReplayStepType.FILE_UPDATE,
            "delete": ReplayStepType.FILE_DELETE,
            "read": ReplayStepType.FILE_READ,
        }.get(operation, ReplayStepType.FILE_UPDATE)

        # Build diff
        diff = FileDiff(
            file_path=file_path,
            operation=operation,
            before_content=before_content[:5000] if before_content else None,
            after_content=after_content[:5000] if after_content else None,
            line_count_before=before_content.count("\n") + 1 if before_content else 0,
            line_count_after=after_content.count("\n") + 1 if after_content else 0,
        )

        # Compute simple diff lines
        if before_content and after_content:
            diff.diff_lines = _compute_simple_diff(before_content, after_content)

        step = self._add_step(
            session_id,
            step_type,
            {
                "label": f"File {operation}: {_short_path(file_path)}",
                "description": f"{operation.title()} {file_path}",
            },
        )

        if step:
            step.file_diffs.append(diff)

        return step

    def record_command(
        self,
        session_id: str,
        command: str,
        cwd: str | None = None,
    ) -> ReplayStep | None:
        """Record a command execution."""
        return self._add_step(
            session_id,
            ReplayStepType.COMMAND_RUN,
            {
                "label": f"Command: {command[:60]}",
                "description": command,
                "tool_input": {"command": command, "cwd": cwd},
            },
        )

    def record_command_output(
        self,
        session_id: str,
        output: str,
        is_error: bool = False,
    ) -> ReplayStep | None:
        """Record command output."""
        return self._add_step(
            session_id,
            ReplayStepType.COMMAND_OUTPUT,
            {
                "label": "Command Output" + (" (Error)" if is_error else ""),
                "description": output[:500],
                "tool_output": output[:5000],
            },
        )

    def record_decision(
        self,
        session_id: str,
        description: str,
        options: list[str],
        chosen: str,
        reasoning: str = "",
    ) -> ReplayStep | None:
        """Record a decision point."""
        return self._add_step(
            session_id,
            ReplayStepType.DECISION,
            {
                "label": f"Decision: {description[:60]}",
                "description": description,
                "reasoning": reasoning,
                "options_considered": options,
                "chosen_option": chosen,
            },
        )

    def record_error(
        self,
        session_id: str,
        error_message: str,
        error_type: str = "unknown",
    ) -> ReplayStep | None:
        """Record an error event."""
        return self._add_step(
            session_id,
            ReplayStepType.ERROR,
            {
                "label": f"Error: {error_type}",
                "description": error_message[:500],
            },
        )

    def record_progress(
        self,
        session_id: str,
        progress: float,
        current_step: str = "",
    ) -> ReplayStep | None:
        """Record a progress update."""
        return self._add_step(
            session_id,
            ReplayStepType.PROGRESS,
            {
                "label": f"Progress: {progress:.0%}",
                "description": current_step,
            },
        )

    def record_test(
        self,
        session_id: str,
        test_command: str,
        success: bool | None = None,
        details: str | None = None,
    ) -> ReplayStep | None:
        """Record test run/result."""
        step_type = (
            ReplayStepType.TEST_RESULT
            if success is not None
            else ReplayStepType.TEST_RUN
        )

        # Extract the test status icon for better readability
        if success is True:
            status_icon = "✓"
        elif success is False:
            status_icon = "✗"
        else:
            status_icon = "⟳"

        return self._add_step(
            session_id,
            step_type,
            {
                "label": f"Test {status_icon}: {test_command[:60]}",
                "description": details or test_command,
                "tool_input": {"command": test_command},
                "tool_output": details,
            },
        )

    # -------------------------------------------------------------------
    # Breakpoints
    # -------------------------------------------------------------------

    def add_breakpoint(
        self,
        session_id: str,
        breakpoint_type: str,
        condition: str,
        description: str = "",
    ) -> Breakpoint | None:
        """Add a breakpoint to a session."""
        session = self._active_sessions.get(session_id)
        if not session:
            return None

        bp = Breakpoint(
            breakpoint_type=BreakpointType(breakpoint_type),
            condition=condition,
            description=description,
        )
        session.breakpoints.append(bp)
        return bp

    def remove_breakpoint(self, session_id: str, breakpoint_id: str) -> bool:
        """Remove a breakpoint from a session."""
        session = self._active_sessions.get(session_id)
        if not session:
            return False

        session.breakpoints = [b for b in session.breakpoints if b.id != breakpoint_id]
        return True

    def check_breakpoints(self, session_id: str, step: ReplayStep) -> list[Breakpoint]:
        """Check if any breakpoints are hit by the given step."""
        session = self._active_sessions.get(session_id)
        if not session:
            return []

        hit = []
        for bp in session.breakpoints:
            if not bp.enabled:
                continue
            if self._breakpoint_matches(bp, step):
                bp.hit_count += 1
                step.is_breakpoint = True
                step.breakpoint_id = bp.id
                hit.append(bp)

        return hit

    # -------------------------------------------------------------------
    # Storage
    # -------------------------------------------------------------------

    def save_session(self, session: ReplaySession) -> Path:
        """Save a replay session to disk."""
        filepath = self._storage_dir / f"{session.session_id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info(f"Replay session saved: {filepath}")
        return filepath

    def load_session(self, session_id: str) -> ReplaySession | None:
        """Load a replay session from disk."""
        filepath = self._storage_dir / f"{session_id}.json"
        if not filepath.exists():
            return None

        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
            return ReplaySession.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load replay session {session_id}: {e}")
            return None

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all saved replay sessions (summaries only)."""
        sessions = []
        for filepath in self._storage_dir.glob("*.json"):
            try:
                with open(filepath, encoding="utf-8") as f:
                    data = json.load(f)
                session = ReplaySession.from_dict(data)
                sessions.append(session.to_summary())
            except Exception as e:
                logger.warning(f"Failed to load {filepath}: {e}")
        return sorted(sessions, key=lambda x: x["start_time"], reverse=True)

    def delete_session(self, session_id: str) -> bool:
        """Delete a saved replay session."""
        filepath = self._storage_dir / f"{session_id}.json"
        if filepath.exists():
            filepath.unlink()
            return True
        return False

    # -------------------------------------------------------------------
    # A/B Comparison
    # -------------------------------------------------------------------

    def compare_sessions(
        self, session_a_id: str, session_b_id: str
    ) -> ABComparison | None:
        """Compare two replay sessions side by side."""
        a = self.load_session(session_a_id)
        b = self.load_session(session_b_id)
        if not a or not b:
            return None

        files_a = set(a.files_touched)
        files_b = set(b.files_touched)

        tools_a = set(a.tool_usage_stats().keys())
        tools_b = set(b.tool_usage_stats().keys())

        comparison = ABComparison(
            session_a_id=session_a_id,
            session_b_id=session_b_id,
            token_diff=b.total_tokens - a.total_tokens,
            cost_diff=b.total_cost_usd - a.total_cost_usd,
            duration_diff=b.duration_seconds - a.duration_seconds,
            step_count_diff=b.step_count - a.step_count,
            tool_calls_diff=b.total_tool_calls - a.total_tool_calls,
            file_changes_diff=b.total_file_changes - a.total_file_changes,
            common_files=sorted(files_a & files_b),
            unique_files_a=sorted(files_a - files_b),
            unique_files_b=sorted(files_b - files_a),
            common_tools=sorted(tools_a & tools_b),
            unique_tools_a=sorted(tools_a - tools_b),
            unique_tools_b=sorted(tools_b - tools_a),
        )

        return comparison

    # -------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------

    def _add_step(
        self,
        session_id: str,
        step_type: ReplayStepType,
        data: dict[str, Any],
    ) -> ReplayStep | None:
        """Add a step to the active session."""
        session = self._active_sessions.get(session_id)
        if not session:
            return None

        idx = self._step_counter.get(session_id, 0)
        self._step_counter[session_id] = idx + 1

        # Compute duration from previous step
        duration_ms = 0.0
        if session.steps:
            duration_ms = (time.time() - session.steps[-1].timestamp) * 1000

        # Cumulative tokens
        input_tokens = data.get("input_tokens", 0)
        output_tokens = data.get("output_tokens", 0)
        cost_usd = data.get("cost_usd", 0.0)
        session.total_tokens += input_tokens + output_tokens
        session.total_cost_usd += cost_usd

        step = ReplayStep(
            step_index=idx,
            step_type=step_type,
            timestamp=time.time(),
            duration_ms=duration_ms,
            label=data.get("label", ""),
            description=data.get("description", ""),
            reasoning=data.get("reasoning", ""),
            tool_name=data.get("tool_name"),
            tool_input=data.get("tool_input"),
            tool_output=data.get("tool_output"),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cumulative_tokens=session.total_tokens,
            cost_usd=cost_usd,
            cumulative_cost_usd=session.total_cost_usd,
            options_considered=data.get("options_considered", []),
            chosen_option=data.get("chosen_option"),
        )

        # Link to previous step
        if session.steps:
            step.parent_step_id = session.steps[-1].id
            session.steps[-1].children_step_ids.append(step.id)

        session.steps.append(step)

        # Check breakpoints
        self.check_breakpoints(session_id, step)

        return step

    def _finalize_stats(self, session: ReplaySession) -> None:
        """Compute final aggregate stats."""
        session.total_tool_calls = sum(
            1 for s in session.steps if s.step_type == ReplayStepType.TOOL_CALL
        )
        session.total_file_changes = sum(
            1
            for s in session.steps
            if s.step_type
            in (
                ReplayStepType.FILE_CREATE,
                ReplayStepType.FILE_UPDATE,
                ReplayStepType.FILE_DELETE,
            )
        )
        all_files = set()
        for s in session.steps:
            for d in s.file_diffs:
                all_files.add(d.file_path)
        session.files_touched = sorted(all_files)

    @staticmethod
    def _breakpoint_matches(bp: Breakpoint, step: ReplayStep) -> bool:
        """Check if a breakpoint matches a step."""
        if bp.breakpoint_type == BreakpointType.TOOL_CALL:
            return step.step_type == ReplayStepType.TOOL_CALL and (
                not bp.condition or bp.condition == step.tool_name
            )
        elif bp.breakpoint_type == BreakpointType.FILE_CHANGE:
            return step.step_type in (
                ReplayStepType.FILE_CREATE,
                ReplayStepType.FILE_UPDATE,
                ReplayStepType.FILE_DELETE,
            ) and (
                not bp.condition
                or any(bp.condition in d.file_path for d in step.file_diffs)
            )
        elif bp.breakpoint_type == BreakpointType.DECISION:
            return step.step_type == ReplayStepType.DECISION
        elif bp.breakpoint_type == BreakpointType.ERROR:
            return step.step_type == ReplayStepType.ERROR
        elif bp.breakpoint_type == BreakpointType.TOKEN_THRESHOLD:
            try:
                threshold = int(bp.condition)
                return step.cumulative_tokens >= threshold
            except ValueError:
                return False
        elif bp.breakpoint_type == BreakpointType.STEP_INDEX:
            try:
                target_idx = int(bp.condition)
                return step.step_index == target_idx
            except ValueError:
                return False
        elif bp.breakpoint_type == BreakpointType.PATTERN_MATCH:
            return bp.condition.lower() in step.description.lower()
        return False


def _short_path(path: str) -> str:
    """Shorten a file path for display."""
    parts = path.replace("\\", "/").split("/")
    if len(parts) <= 3:
        return path
    return f".../{'/'.join(parts[-3:])}"


def _compute_simple_diff(before: str, after: str) -> list[str]:
    """Compute a simple line-based diff."""
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    diff_lines = []

    # Simple diff: show added/removed lines
    before_set = set(before_lines)
    after_set = set(after_lines)

    for line in before_lines:
        if line not in after_set:
            diff_lines.append(f"- {line}")
    for line in after_lines:
        if line not in before_set:
            diff_lines.append(f"+ {line}")

    return diff_lines[:200]  # Limit output


# Global instance
_replay_recorder: ReplayRecorder | None = None


def get_replay_recorder() -> ReplayRecorder:
    """Get or create the global replay recorder instance."""
    global _replay_recorder
    if _replay_recorder is None:
        _replay_recorder = ReplayRecorder()
    return _replay_recorder
