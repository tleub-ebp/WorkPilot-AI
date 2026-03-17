"""
Agent Decision Logger
=====================

Lightweight structured logger that records key agent decisions during execution.
Emits decision entries as __TASK_EVENT__: DECISION_LOG_ENTRY events so they flow
through the existing frontend event pipeline without any new protocol.

Also persists entries to decision_log.json in the spec directory for historical
access after the agent session ends.

Decision types captured:
  - tool_call         : Tool invocations (name, input summary, outcome)
  - file_read         : Files the agent read for context
  - file_write        : Files the agent created or modified
  - reasoning         : Notable reasoning / thinking blocks
  - decision          : Explicit decision point with alternatives considered
  - phase_transition  : Agent phase changes (planning → coding → QA)
  - error_recovery    : How the agent handled an error or failure
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from core.task_event import TaskEventEmitter, load_task_event_context

# Maximum entries kept in the JSON file (oldest are dropped when exceeded)
MAX_LOG_ENTRIES = 500
# Maximum length of text summaries stored in entries
MAX_SUMMARY_LENGTH = 300

DECISION_LOG_FILE = "decision_log.json"


class DecisionType:
    TOOL_CALL = "tool_call"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    REASONING = "reasoning"
    DECISION = "decision"
    PHASE_TRANSITION = "phase_transition"
    ERROR_RECOVERY = "error_recovery"


@dataclass
class DecisionEntry:
    """A single logged agent decision."""

    id: int                              # Auto-incremented within a session
    session_id: str                      # Identifies the agent session
    agent_type: str                      # planner | coder | qa_reviewer | qa_fixer
    decision_type: str                   # See DecisionType constants
    timestamp: str                       # ISO8601 UTC

    # Content (all optional — populated depending on decision_type)
    summary: str = ""                    # One-line description shown in the timeline
    tool_name: Optional[str] = None      # For tool_call entries
    tool_input_summary: Optional[str] = None
    tool_outcome: Optional[str] = None   # success | error | partial
    files: list[str] = field(default_factory=list)  # Paths for file_read/write
    alternatives: list[str] = field(default_factory=list)  # For decision entries
    selected: Optional[str] = None       # Chosen option for decision entries
    reasoning_text: Optional[str] = None # Truncated reasoning for reasoning entries
    phase_from: Optional[str] = None
    phase_to: Optional[str] = None
    error_type: Optional[str] = None
    recovery_approach: Optional[str] = None
    subtask_id: Optional[str] = None     # Current subtask being worked on

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "DecisionEntry":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class AgentDecisionLogger:
    """
    Records and emits structured decision entries for a single agent session.

    Usage:
        logger = AgentDecisionLogger(spec_dir, agent_type="coder", session_id="coder-1")
        logger.log_tool_call("Write", {"path": "src/foo.py"}, outcome="success")
        logger.log_reasoning("Decided to split implementation into two subtasks.")
        logger.log_decision("approach", alternatives=["A", "B"], selected="A")
    """

    def __init__(
        self,
        spec_dir: Path,
        agent_type: str,
        session_id: str,
        emit_events: bool = True,
    ):
        self.spec_dir = Path(spec_dir)
        self.agent_type = agent_type
        self.session_id = session_id
        self._emit_events = emit_events
        self._counter = 0

        # Load existing log for counter continuity
        existing = self._load_existing()
        if existing:
            self._counter = max((e.get("id", 0) for e in existing), default=0) + 1

        # Lazy-init emitter only when needed
        self._emitter: Optional[TaskEventEmitter] = None

    # ── Public logging API ─────────────────────────────────────────────────

    def log_tool_call(
        self,
        tool_name: str,
        tool_input: dict,
        outcome: str = "success",
        subtask_id: Optional[str] = None,
    ) -> None:
        """Log a tool invocation with a concise input summary."""
        input_summary = self._summarize_tool_input(tool_name, tool_input)
        entry = self._make_entry(
            decision_type=DecisionType.TOOL_CALL,
            summary=f"{tool_name}: {input_summary}",
            tool_name=tool_name,
            tool_input_summary=input_summary,
            tool_outcome=outcome,
            subtask_id=subtask_id,
        )
        self._record(entry)

    def log_file_read(self, file_path: str, subtask_id: Optional[str] = None) -> None:
        """Log that the agent read a file for context."""
        entry = self._make_entry(
            decision_type=DecisionType.FILE_READ,
            summary=f"Read {file_path}",
            files=[file_path],
            subtask_id=subtask_id,
        )
        self._record(entry)

    def log_file_write(
        self,
        file_path: str,
        action: str = "write",
        subtask_id: Optional[str] = None,
    ) -> None:
        """Log that the agent created or modified a file."""
        entry = self._make_entry(
            decision_type=DecisionType.FILE_WRITE,
            summary=f"{action.capitalize()} {file_path}",
            files=[file_path],
            subtask_id=subtask_id,
        )
        self._record(entry)

    def log_reasoning(self, text: str, subtask_id: Optional[str] = None) -> None:
        """Log a notable reasoning block."""
        truncated = text[:MAX_SUMMARY_LENGTH] + ("…" if len(text) > MAX_SUMMARY_LENGTH else "")
        entry = self._make_entry(
            decision_type=DecisionType.REASONING,
            summary=truncated[:120],
            reasoning_text=truncated,
            subtask_id=subtask_id,
        )
        self._record(entry)

    def log_decision(
        self,
        topic: str,
        alternatives: list[str],
        selected: str,
        reasoning: Optional[str] = None,
        subtask_id: Optional[str] = None,
    ) -> None:
        """Log an explicit decision point with alternatives and chosen option."""
        entry = self._make_entry(
            decision_type=DecisionType.DECISION,
            summary=f"Decision on {topic}: chose '{selected}'",
            alternatives=alternatives,
            selected=selected,
            reasoning_text=reasoning[:MAX_SUMMARY_LENGTH] if reasoning else None,
            subtask_id=subtask_id,
        )
        self._record(entry)

    def log_phase_transition(self, phase_from: str, phase_to: str) -> None:
        """Log a transition between execution phases."""
        entry = self._make_entry(
            decision_type=DecisionType.PHASE_TRANSITION,
            summary=f"Phase: {phase_from} → {phase_to}",
            phase_from=phase_from,
            phase_to=phase_to,
        )
        self._record(entry)

    def log_error_recovery(
        self,
        error_type: str,
        recovery_approach: str,
        subtask_id: Optional[str] = None,
    ) -> None:
        """Log how the agent handled an error."""
        entry = self._make_entry(
            decision_type=DecisionType.ERROR_RECOVERY,
            summary=f"Recovered from {error_type}: {recovery_approach[:80]}",
            error_type=error_type,
            recovery_approach=recovery_approach,
            subtask_id=subtask_id,
        )
        self._record(entry)

    # ── Internals ──────────────────────────────────────────────────────────

    def _make_entry(self, decision_type: str, summary: str, **kwargs) -> DecisionEntry:
        entry_id = self._counter
        self._counter += 1
        return DecisionEntry(
            id=entry_id,
            session_id=self.session_id,
            agent_type=self.agent_type,
            decision_type=decision_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            summary=summary[:MAX_SUMMARY_LENGTH],
            **kwargs,
        )

    def _record(self, entry: DecisionEntry) -> None:
        """Persist to file and emit as a task event."""
        self._append_to_file(entry)
        if self._emit_events:
            self._emit(entry)

    def _emit(self, entry: DecisionEntry) -> None:
        """Emit the entry as a DECISION_LOG_ENTRY task event."""
        if self._emitter is None:
            try:
                self._emitter = TaskEventEmitter.from_spec_dir(self.spec_dir)
            except Exception:
                return
        try:
            self._emitter.emit("DECISION_LOG_ENTRY", {"entry": entry.to_dict()})
        except Exception:
            pass  # Non-critical — logging must never break the agent

    def _append_to_file(self, entry: DecisionEntry) -> None:
        """Append the entry to decision_log.json, capping at MAX_LOG_ENTRIES."""
        log_file = self.spec_dir / DECISION_LOG_FILE
        try:
            entries = self._load_existing()
            entries.append(entry.to_dict())
            # Trim oldest entries if we exceed the cap
            if len(entries) > MAX_LOG_ENTRIES:
                entries = entries[-MAX_LOG_ENTRIES:]
            log_file.write_text(json.dumps(entries, indent=2), encoding="utf-8")
        except Exception:
            pass  # Non-critical

    def _load_existing(self) -> list[dict]:
        log_file = self.spec_dir / DECISION_LOG_FILE
        if not log_file.exists():
            return []
        try:
            data = json.loads(log_file.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    @staticmethod
    def _summarize_tool_input(tool_name: str, tool_input: dict) -> str:
        """Build a concise one-line summary of a tool call input."""
        tool_lower = tool_name.lower()

        if "read" in tool_lower or "view" in tool_lower:
            return tool_input.get("file_path", tool_input.get("path", ""))
        if "write" in tool_lower or "edit" in tool_lower:
            path = tool_input.get("file_path", tool_input.get("path", ""))
            return path if path else str(tool_input)[:80]
        if "bash" in tool_lower or "execute" in tool_lower:
            cmd = tool_input.get("command", "")
            return cmd[:120] if cmd else str(tool_input)[:80]
        if "search" in tool_lower or "grep" in tool_lower:
            pattern = tool_input.get("pattern", tool_input.get("query", ""))
            return f"'{pattern}'" if pattern else str(tool_input)[:80]
        if "glob" in tool_lower:
            return tool_input.get("pattern", str(tool_input)[:80])

        # Generic: show first key=value pair
        if tool_input:
            first_key = next(iter(tool_input))
            return f"{first_key}={str(tool_input[first_key])[:60]}"
        return ""


# =============================================================================
# Convenience function for session.py integration
# =============================================================================

def create_decision_logger(
    spec_dir: Path,
    agent_type: str,
    subtask_id: Optional[str] = None,
) -> AgentDecisionLogger:
    """
    Create a session-scoped decision logger.

    Args:
        spec_dir: Spec directory (for file persistence and event context)
        agent_type: 'planner' | 'coder' | 'qa_reviewer' | 'qa_fixer'
        subtask_id: Current subtask being executed

    Returns:
        Ready-to-use AgentDecisionLogger
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    session_id = f"{agent_type}-{ts}"
    return AgentDecisionLogger(
        spec_dir=spec_dir,
        agent_type=agent_type,
        session_id=session_id,
    )
