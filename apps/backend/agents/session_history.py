"""Session History & Replay — Record and replay agent sessions with full traceability.

Records the entirety of agent sessions (prompts, responses, actions, file changes)
and allows replay with modified prompts for debugging and improvement.

Feature 1.2 — Historique et replay des sessions agent.

Example:
    >>> from apps.backend.agents.session_history import SessionRecorder, SessionReplayer
    >>> recorder = SessionRecorder(project_id="proj-1")
    >>> session = recorder.start_session("task-42", agent_type="coder")
    >>> recorder.record_action(session.session_id, "prompt", content="Write login code")
    >>> recorder.record_action(session.session_id, "response", content="Here is the code...")
    >>> recorder.record_file_change(session.session_id, "src/login.py", "", "def login():...")
    >>> recorder.end_session(session.session_id, status="completed")
    >>> export = recorder.export_session(session.session_id)
"""

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ActionType(str, Enum):
    """Type of action recorded in a session."""

    PROMPT = "prompt"
    RESPONSE = "response"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    COMMAND = "command"
    ERROR = "error"
    DECISION = "decision"
    PLAN = "plan"


class SessionStatus(str, Enum):
    """Status of a recorded session."""

    RECORDING = "recording"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REPLAYING = "replaying"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class SessionAction:
    """A single action within an agent session.

    Attributes:
        action_id: Unique identifier for this action.
        action_type: Type of action.
        content: Main content/payload.
        timestamp: When the action occurred.
        metadata: Additional context (e.g. tool name, file path, tokens used).
        duration_ms: How long the action took in milliseconds.
    """

    action_id: str
    action_type: ActionType
    content: str
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        data = asdict(self)
        data["action_type"] = (
            self.action_type.value
            if isinstance(self.action_type, ActionType)
            else self.action_type
        )
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "SessionAction":
        data["action_type"] = ActionType(data["action_type"])
        return cls(**data)


@dataclass
class FileChange:
    """A file change recorded during a session.

    Attributes:
        file_path: Path to the changed file.
        before: Content before the change (empty string for new files).
        after: Content after the change (empty string for deletions).
        change_type: Type of change (create, modify, delete).
        timestamp: When the change happened.
    """

    file_path: str
    before: str
    after: str
    change_type: str = "modify"
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    @property
    def diff_summary(self) -> str:
        """Generate a brief summary of the change."""
        if self.change_type == "create":
            lines = self.after.count("\n") + 1
            return f"+{lines} lines (new file)"
        elif self.change_type == "delete":
            lines = self.before.count("\n") + 1
            return f"-{lines} lines (deleted)"
        else:
            before_lines = set(self.before.splitlines())
            after_lines = set(self.after.splitlines())
            added = len(after_lines - before_lines)
            removed = len(before_lines - after_lines)
            return f"+{added} / -{removed} lines"

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "before": self.before,
            "after": self.after,
            "change_type": self.change_type,
            "timestamp": self.timestamp,
            "diff_summary": self.diff_summary,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FileChange":
        data.pop("diff_summary", None)
        return cls(**data)


@dataclass
class AgentSession:
    """A complete recorded agent session.

    Attributes:
        session_id: Unique session identifier.
        project_id: The project this session belongs to.
        task_id: The task being worked on.
        agent_type: Type of agent (planner, coder, qa, refactorer, etc.).
        status: Current session status.
        actions: Ordered list of actions in the session.
        file_changes: File changes made during the session.
        started_at: When the session started.
        ended_at: When the session ended (None if still recording).
        total_tokens_in: Total input tokens consumed.
        total_tokens_out: Total output tokens consumed.
        metadata: Additional session metadata.
    """

    session_id: str
    project_id: str
    task_id: str
    agent_type: str = "coder"
    status: SessionStatus = SessionStatus.RECORDING
    actions: list[SessionAction] = field(default_factory=list)
    file_changes: list[FileChange] = field(default_factory=list)
    started_at: str = ""
    ended_at: str | None = None
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.started_at:
            self.started_at = datetime.now(timezone.utc).isoformat()

    @property
    def duration_seconds(self) -> float:
        """Calculate session duration in seconds."""
        if not self.ended_at:
            return 0.0
        try:
            start = datetime.fromisoformat(self.started_at)
            end = datetime.fromisoformat(self.ended_at)
            return (end - start).total_seconds()
        except (ValueError, TypeError):
            return 0.0

    @property
    def action_count(self) -> int:
        return len(self.actions)

    @property
    def file_change_count(self) -> int:
        return len(self.file_changes)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "agent_type": self.agent_type,
            "status": self.status.value
            if isinstance(self.status, SessionStatus)
            else self.status,
            "actions": [a.to_dict() for a in self.actions],
            "file_changes": [f.to_dict() for f in self.file_changes],
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "total_tokens_in": self.total_tokens_in,
            "total_tokens_out": self.total_tokens_out,
            "metadata": self.metadata,
            "duration_seconds": self.duration_seconds,
            "action_count": self.action_count,
            "file_change_count": self.file_change_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentSession":
        data.pop("duration_seconds", None)
        data.pop("action_count", None)
        data.pop("file_change_count", None)
        actions = [SessionAction.from_dict(a) for a in data.pop("actions", [])]
        file_changes = [FileChange.from_dict(f) for f in data.pop("file_changes", [])]
        data["status"] = SessionStatus(data["status"])
        session = cls(**data)
        session.actions = actions
        session.file_changes = file_changes
        return session


@dataclass
class TimelineEntry:
    """A single entry in the visual timeline of a session.

    Attributes:
        index: Position in the timeline.
        timestamp: When this entry occurred.
        action_type: Type of action.
        summary: Short human-readable summary.
        details: Detailed content (truncated).
    """

    index: int
    timestamp: str
    action_type: str
    summary: str
    details: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# SessionRecorder
# ---------------------------------------------------------------------------


class SessionRecorder:
    """Records agent sessions for later replay and analysis.

    Stores all prompts, responses, tool calls, file changes, and metadata
    during an agent's execution of a task.
    """

    def __init__(self, project_id: str = "") -> None:
        self.project_id = project_id
        self._sessions: dict[str, AgentSession] = {}
        self._action_counter: int = 0
        self._session_counter: int = 0
        logger.info("SessionRecorder initialized for project %s", project_id)

    def start_session(
        self,
        task_id: str,
        agent_type: str = "coder",
        metadata: dict[str, Any] | None = None,
    ) -> AgentSession:
        """Start recording a new agent session.

        Args:
            task_id: The task being worked on.
            agent_type: Type of agent (planner, coder, qa, etc.).
            metadata: Optional additional metadata.

        Returns:
            The newly created AgentSession.
        """
        self._session_counter += 1
        session_id = f"session_{self._session_counter}_{int(time.time())}"
        session = AgentSession(
            session_id=session_id,
            project_id=self.project_id,
            task_id=task_id,
            agent_type=agent_type,
            status=SessionStatus.RECORDING,
            metadata=metadata or {},
        )
        self._sessions[session_id] = session
        logger.info("Started session %s for task %s", session_id, task_id)
        return session

    def record_action(
        self,
        session_id: str,
        action_type: str,
        content: str,
        metadata: dict[str, Any] | None = None,
        duration_ms: float = 0.0,
    ) -> SessionAction | None:
        """Record an action in a session.

        Args:
            session_id: The session to record into.
            action_type: Type of action (prompt, response, tool_call, etc.).
            content: The action content.
            metadata: Optional metadata (tool name, tokens, etc.).
            duration_ms: How long the action took.

        Returns:
            The created SessionAction or None if session not found.
        """
        session = self._sessions.get(session_id)
        if not session:
            logger.warning("Session %s not found", session_id)
            return None

        if session.status != SessionStatus.RECORDING:
            logger.warning(
                "Session %s is not recording (status: %s)", session_id, session.status
            )
            return None

        self._action_counter += 1
        at = (
            ActionType(action_type)
            if action_type in [a.value for a in ActionType]
            else ActionType.RESPONSE
        )

        action = SessionAction(
            action_id=f"act_{self._action_counter}",
            action_type=at,
            content=content,
            metadata=metadata or {},
            duration_ms=duration_ms,
        )
        session.actions.append(action)

        # Track tokens from metadata
        if metadata:
            session.total_tokens_in += metadata.get("input_tokens", 0)
            session.total_tokens_out += metadata.get("output_tokens", 0)

        return action

    def record_file_change(
        self,
        session_id: str,
        file_path: str,
        before: str,
        after: str,
    ) -> FileChange | None:
        """Record a file change in a session.

        Args:
            session_id: The session to record into.
            file_path: Path to the changed file.
            before: Content before the change.
            after: Content after the change.

        Returns:
            The created FileChange or None if session not found.
        """
        session = self._sessions.get(session_id)
        if not session:
            return None

        if before == "" and after != "":
            change_type = "create"
        elif before != "" and after == "":
            change_type = "delete"
        else:
            change_type = "modify"

        change = FileChange(
            file_path=file_path,
            before=before,
            after=after,
            change_type=change_type,
        )
        session.file_changes.append(change)
        return change

    def end_session(
        self,
        session_id: str,
        status: str = "completed",
    ) -> AgentSession | None:
        """End a recording session.

        Args:
            session_id: The session to end.
            status: Final status (completed, failed, cancelled).

        Returns:
            The finalized AgentSession or None if not found.
        """
        session = self._sessions.get(session_id)
        if not session:
            return None

        session.status = (
            SessionStatus(status)
            if status in [s.value for s in SessionStatus]
            else SessionStatus.COMPLETED
        )
        session.ended_at = datetime.now(timezone.utc).isoformat()
        logger.info("Ended session %s with status %s", session_id, status)
        return session

    # -- Query methods -------------------------------------------------------

    def get_session(self, session_id: str) -> AgentSession | None:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    def list_sessions(
        self,
        task_id: str | None = None,
        agent_type: str | None = None,
        status: str | None = None,
    ) -> list[AgentSession]:
        """List sessions with optional filters."""
        sessions = list(self._sessions.values())
        if task_id:
            sessions = [s for s in sessions if s.task_id == task_id]
        if agent_type:
            sessions = [s for s in sessions if s.agent_type == agent_type]
        if status:
            sessions = [s for s in sessions if s.status.value == status]
        return sessions

    def get_timeline(self, session_id: str) -> list[TimelineEntry]:
        """Get a visual timeline of a session's actions.

        Returns:
            List of TimelineEntry objects suitable for UI rendering.
        """
        session = self._sessions.get(session_id)
        if not session:
            return []

        entries = []
        for i, action in enumerate(session.actions):
            summary = self._summarize_action(action)
            details = action.content[:500] if action.content else ""
            entries.append(
                TimelineEntry(
                    index=i,
                    timestamp=action.timestamp,
                    action_type=action.action_type.value,
                    summary=summary,
                    details=details,
                )
            )
        return entries

    def get_file_diffs(self, session_id: str) -> list[dict]:
        """Get file-by-file diffs for a session.

        Returns:
            List of dicts with file_path, change_type, before, after, diff_summary.
        """
        session = self._sessions.get(session_id)
        if not session:
            return []
        return [fc.to_dict() for fc in session.file_changes]

    # -- Export / Import -----------------------------------------------------

    def export_session(self, session_id: str) -> str:
        """Export a session as JSON string for sharing or audit.

        Returns:
            JSON string of the full session, or empty string if not found.
        """
        session = self._sessions.get(session_id)
        if not session:
            return ""
        return json.dumps(session.to_dict(), indent=2)

    def import_session(self, json_str: str) -> AgentSession | None:
        """Import a session from JSON string.

        Returns:
            The imported AgentSession or None on error.
        """
        try:
            data = json.loads(json_str)
            session = AgentSession.from_dict(data)
            self._sessions[session.session_id] = session
            return session
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error("Failed to import session: %s", e)
            return None

    # -- Stats ---------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Get overall statistics."""
        sessions = list(self._sessions.values())
        return {
            "total_sessions": len(sessions),
            "completed": sum(
                1 for s in sessions if s.status == SessionStatus.COMPLETED
            ),
            "failed": sum(1 for s in sessions if s.status == SessionStatus.FAILED),
            "recording": sum(
                1 for s in sessions if s.status == SessionStatus.RECORDING
            ),
            "total_actions": sum(s.action_count for s in sessions),
            "total_file_changes": sum(s.file_change_count for s in sessions),
            "total_tokens_in": sum(s.total_tokens_in for s in sessions),
            "total_tokens_out": sum(s.total_tokens_out for s in sessions),
        }

    # -- Helpers -------------------------------------------------------------

    @staticmethod
    def _summarize_action(action: SessionAction) -> str:
        """Create a short summary of an action for the timeline."""
        type_summaries = {
            ActionType.PROMPT: "Sent prompt to agent",
            ActionType.RESPONSE: "Agent responded",
            ActionType.TOOL_CALL: f"Called tool: {action.metadata.get('tool_name', 'unknown')}",
            ActionType.TOOL_RESULT: "Tool returned result",
            ActionType.FILE_READ: f"Read file: {action.metadata.get('file_path', '?')}",
            ActionType.FILE_WRITE: f"Wrote file: {action.metadata.get('file_path', '?')}",
            ActionType.FILE_DELETE: f"Deleted file: {action.metadata.get('file_path', '?')}",
            ActionType.COMMAND: f"Ran command: {action.content[:60]}",
            ActionType.ERROR: f"Error: {action.content[:80]}",
            ActionType.DECISION: "Made decision",
            ActionType.PLAN: "Updated plan",
        }
        return type_summaries.get(
            action.action_type, f"Action: {action.action_type.value}"
        )


# ---------------------------------------------------------------------------
# SessionReplayer
# ---------------------------------------------------------------------------


class SessionReplayer:
    """Replay recorded sessions with optional prompt modifications.

    Allows replaying a session step-by-step, modifying prompts,
    and comparing results between original and replayed sessions.
    """

    def __init__(self) -> None:
        self._replay_sessions: dict[str, AgentSession] = {}
        logger.info("SessionReplayer initialized")

    def prepare_replay(
        self,
        original_session: AgentSession,
        modified_prompts: dict[int, str] | None = None,
    ) -> AgentSession:
        """Prepare a replay session from an original session.

        Args:
            original_session: The session to replay.
            modified_prompts: Dict mapping action index to new prompt content.

        Returns:
            A new AgentSession configured for replay.
        """
        replay_id = f"replay_{original_session.session_id}_{int(time.time())}"
        replay = AgentSession(
            session_id=replay_id,
            project_id=original_session.project_id,
            task_id=original_session.task_id,
            agent_type=original_session.agent_type,
            status=SessionStatus.REPLAYING,
            metadata={
                "original_session_id": original_session.session_id,
                "modified_prompt_indices": list((modified_prompts or {}).keys()),
            },
        )

        # Copy actions, replacing prompts where specified
        for i, action in enumerate(original_session.actions):
            new_content = action.content
            if (
                modified_prompts
                and i in modified_prompts
                and action.action_type == ActionType.PROMPT
            ):
                new_content = modified_prompts[i]

            replay_action = SessionAction(
                action_id=f"replay_{action.action_id}",
                action_type=action.action_type,
                content=new_content,
                metadata={**action.metadata, "original_action_id": action.action_id},
                duration_ms=action.duration_ms,
            )
            replay.actions.append(replay_action)

        self._replay_sessions[replay_id] = replay
        return replay

    def get_replay(self, replay_id: str) -> AgentSession | None:
        """Get a replay session by ID."""
        return self._replay_sessions.get(replay_id)

    def compare_sessions(
        self,
        session_a: AgentSession,
        session_b: AgentSession,
    ) -> dict[str, Any]:
        """Compare two sessions (original vs replay or two different runs).

        Returns:
            Dict with comparison metrics.
        """
        return {
            "session_a_id": session_a.session_id,
            "session_b_id": session_b.session_id,
            "action_count_a": session_a.action_count,
            "action_count_b": session_b.action_count,
            "file_changes_a": session_a.file_change_count,
            "file_changes_b": session_b.file_change_count,
            "tokens_in_a": session_a.total_tokens_in,
            "tokens_in_b": session_b.total_tokens_in,
            "tokens_out_a": session_a.total_tokens_out,
            "tokens_out_b": session_b.total_tokens_out,
            "duration_a": session_a.duration_seconds,
            "duration_b": session_b.duration_seconds,
            "same_file_changes": self._compare_file_changes(session_a, session_b),
        }

    @staticmethod
    def _compare_file_changes(
        session_a: AgentSession,
        session_b: AgentSession,
    ) -> dict[str, str]:
        """Compare file changes between sessions.

        Returns:
            Dict mapping file_path to comparison status (same, different, only_a, only_b).
        """
        files_a = {fc.file_path: fc for fc in session_a.file_changes}
        files_b = {fc.file_path: fc for fc in session_b.file_changes}
        all_files = set(files_a.keys()) | set(files_b.keys())

        result: dict[str, str] = {}
        for f in all_files:
            if f in files_a and f in files_b:
                if files_a[f].after == files_b[f].after:
                    result[f] = "same"
                else:
                    result[f] = "different"
            elif f in files_a:
                result[f] = "only_a"
            else:
                result[f] = "only_b"
        return result

    def list_replays(self) -> list[AgentSession]:
        """List all replay sessions."""
        return list(self._replay_sessions.values())

    def get_stats(self) -> dict[str, Any]:
        """Get replay statistics."""
        return {
            "total_replays": len(self._replay_sessions),
        }
