"""Tests for Feature 1.2 — Historique et replay des sessions agent.

Tests for SessionRecorder, SessionReplayer, AgentSession, SessionAction,
FileChange, TimelineEntry, and export/import functionality.

40 tests total:
- SessionAction: 3
- FileChange: 4
- AgentSession: 4
- SessionRecorder lifecycle: 6
- SessionRecorder recording: 6
- SessionRecorder queries: 5
- SessionRecorder export/import: 4
- SessionReplayer: 5
- SessionRecorder stats: 3
"""

import json
import os
import sys
from pathlib import Path

import pytest

# Add backend path to sys.path
backend_path = Path(__file__).parent.parent / "apps" / "backend"
sys.path.insert(0, str(backend_path))

from apps.backend.agents.session_history import (
    ActionType,
    AgentSession,
    FileChange,
    SessionAction,
    SessionRecorder,
    SessionReplayer,
    SessionStatus,
    TimelineEntry,
)

# -----------------------------------------------------------------------
# SessionAction
# -----------------------------------------------------------------------

class TestSessionAction:
    def test_create_action(self):
        action = SessionAction(
            action_id="act_1", action_type=ActionType.PROMPT,
            content="Write login code",
        )
        assert action.action_id == "act_1"
        assert action.action_type == ActionType.PROMPT
        assert action.content == "Write login code"
        assert action.timestamp != ""

    def test_action_to_dict(self):
        action = SessionAction(
            action_id="act_1", action_type=ActionType.TOOL_CALL,
            content="read_file", metadata={"tool_name": "Read"},
        )
        d = action.to_dict()
        assert d["action_type"] == "tool_call"
        assert d["metadata"]["tool_name"] == "Read"

    def test_action_from_dict(self):
        d = {
            "action_id": "act_1", "action_type": "response",
            "content": "Here is code", "timestamp": "2026-01-01T00:00:00",
            "metadata": {}, "duration_ms": 150.0,
        }
        action = SessionAction.from_dict(d)
        assert action.action_type == ActionType.RESPONSE
        assert action.duration_ms == 150


# -----------------------------------------------------------------------
# FileChange
# -----------------------------------------------------------------------

class TestFileChange:
    def test_create_file_change(self):
        fc = FileChange(file_path="src/login.py", before="", after="def login(): pass")
        assert fc.file_path == "src/login.py"
        assert fc.change_type == "modify"

    def test_diff_summary_new_file(self):
        fc = FileChange(file_path="f.py", before="", after="line1\nline2", change_type="create")
        assert "+2 lines" in fc.diff_summary

    def test_diff_summary_delete(self):
        fc = FileChange(file_path="f.py", before="line1\nline2", after="", change_type="delete")
        assert "-2 lines" in fc.diff_summary

    def test_file_change_to_dict(self):
        fc = FileChange(file_path="f.py", before="a", after="b")
        d = fc.to_dict()
        assert "diff_summary" in d
        assert d["file_path"] == "f.py"


# -----------------------------------------------------------------------
# AgentSession
# -----------------------------------------------------------------------

class TestAgentSession:
    def test_create_session(self):
        session = AgentSession(
            session_id="s1", project_id="p", task_id="t1",
            agent_type="coder",
        )
        assert session.session_id == "s1"
        assert session.status == SessionStatus.RECORDING
        assert session.started_at != ""

    def test_session_duration(self):
        session = AgentSession(
            session_id="s1", project_id="p", task_id="t1",
            started_at="2026-01-01T00:00:00+00:00",
            ended_at="2026-01-01T00:05:00+00:00",
        )
        assert session.duration_seconds == 300

    def test_session_to_dict(self):
        session = AgentSession(session_id="s1", project_id="p", task_id="t1")
        session.actions.append(SessionAction(
            action_id="a1", action_type=ActionType.PROMPT, content="hello",
        ))
        d = session.to_dict()
        assert d["session_id"] == "s1"
        assert len(d["actions"]) == 1
        assert d["action_count"] == 1

    def test_session_from_dict(self):
        d = {
            "session_id": "s1", "project_id": "p", "task_id": "t1",
            "agent_type": "coder", "status": "completed",
            "actions": [{"action_id": "a1", "action_type": "prompt",
                         "content": "x", "timestamp": "", "metadata": {},
                         "duration_ms": 0}],
            "file_changes": [],
            "started_at": "2026-01-01T00:00:00", "ended_at": None,
            "total_tokens_in": 100, "total_tokens_out": 50,
            "metadata": {},
        }
        session = AgentSession.from_dict(d)
        assert session.status == SessionStatus.COMPLETED
        assert len(session.actions) == 1


# -----------------------------------------------------------------------
# SessionRecorder — lifecycle
# -----------------------------------------------------------------------

class TestSessionRecorderLifecycle:
    def setup_method(self):
        self.recorder = SessionRecorder(project_id="proj-1")

    def test_start_session(self):
        session = self.recorder.start_session("task-1", agent_type="coder")
        assert session.project_id == "proj-1"
        assert session.task_id == "task-1"
        assert session.status == SessionStatus.RECORDING

    def test_end_session_completed(self):
        session = self.recorder.start_session("task-1")
        ended = self.recorder.end_session(session.session_id, status="completed")
        assert ended.status == SessionStatus.COMPLETED
        assert ended.ended_at is not None

    def test_end_session_failed(self):
        session = self.recorder.start_session("task-1")
        ended = self.recorder.end_session(session.session_id, status="failed")
        assert ended.status == SessionStatus.FAILED

    def test_end_session_not_found(self):
        result = self.recorder.end_session("nonexistent")
        assert result is None

    def test_get_session(self):
        session = self.recorder.start_session("task-1")
        found = self.recorder.get_session(session.session_id)
        assert found is not None
        assert found.session_id == session.session_id

    def test_get_session_not_found(self):
        assert self.recorder.get_session("nonexistent") is None


# -----------------------------------------------------------------------
# SessionRecorder — recording
# -----------------------------------------------------------------------

class TestSessionRecorderRecording:
    def setup_method(self):
        self.recorder = SessionRecorder(project_id="proj-1")
        self.session = self.recorder.start_session("task-1")

    def test_record_action(self):
        action = self.recorder.record_action(
            self.session.session_id, "prompt", "Hello world",
        )
        assert action is not None
        assert action.action_type == ActionType.PROMPT

    def test_record_action_with_metadata(self):
        self.recorder.record_action(
            self.session.session_id, "response", "Code here",
            metadata={"input_tokens": 100, "output_tokens": 50},
        )
        assert self.session.total_tokens_in == 100
        assert self.session.total_tokens_out == 50

    def test_record_action_not_found(self):
        result = self.recorder.record_action("nonexistent", "prompt", "x")
        assert result is None

    def test_record_action_ended_session(self):
        self.recorder.end_session(self.session.session_id)
        result = self.recorder.record_action(self.session.session_id, "prompt", "x")
        assert result is None

    def test_record_file_change_create(self):
        fc = self.recorder.record_file_change(
            self.session.session_id, "new.py", "", "def hello(): pass",
        )
        assert fc is not None
        assert fc.change_type == "create"

    def test_record_file_change_modify(self):
        fc = self.recorder.record_file_change(
            self.session.session_id, "f.py", "old", "new",
        )
        assert fc.change_type == "modify"


# -----------------------------------------------------------------------
# SessionRecorder — queries
# -----------------------------------------------------------------------

class TestSessionRecorderQueries:
    def setup_method(self):
        self.recorder = SessionRecorder(project_id="proj-1")
        self.s1 = self.recorder.start_session("task-1", agent_type="coder")
        self.s2 = self.recorder.start_session("task-2", agent_type="planner")
        self.recorder.end_session(self.s2.session_id, status="completed")

    def test_list_sessions_all(self):
        sessions = self.recorder.list_sessions()
        assert len(sessions) == 2

    def test_list_sessions_by_task(self):
        sessions = self.recorder.list_sessions(task_id="task-1")
        assert len(sessions) == 1

    def test_list_sessions_by_agent_type(self):
        sessions = self.recorder.list_sessions(agent_type="planner")
        assert len(sessions) == 1

    def test_list_sessions_by_status(self):
        sessions = self.recorder.list_sessions(status="completed")
        assert len(sessions) == 1

    def test_get_timeline(self):
        self.recorder.record_action(self.s1.session_id, "prompt", "Write code")
        self.recorder.record_action(self.s1.session_id, "response", "Here is code")
        timeline = self.recorder.get_timeline(self.s1.session_id)
        assert len(timeline) == 2
        assert timeline[0].action_type == "prompt"
        assert timeline[1].action_type == "response"


# -----------------------------------------------------------------------
# SessionRecorder — export/import
# -----------------------------------------------------------------------

class TestSessionRecorderExport:
    def setup_method(self):
        self.recorder = SessionRecorder(project_id="proj-1")
        self.session = self.recorder.start_session("task-1")
        self.recorder.record_action(self.session.session_id, "prompt", "Test prompt")
        self.recorder.record_file_change(self.session.session_id, "f.py", "", "code")
        self.recorder.end_session(self.session.session_id)

    def test_export_session_json(self):
        exported = self.recorder.export_session(self.session.session_id)
        assert exported != ""
        data = json.loads(exported)
        assert data["session_id"] == self.session.session_id

    def test_export_nonexistent(self):
        assert self.recorder.export_session("nonexistent") == ""

    def test_import_session(self):
        exported = self.recorder.export_session(self.session.session_id)
        new_recorder = SessionRecorder(project_id="proj-2")
        imported = new_recorder.import_session(exported)
        assert imported is not None
        assert imported.session_id == self.session.session_id

    def test_import_invalid_json(self):
        result = self.recorder.import_session("not json")
        assert result is None


# -----------------------------------------------------------------------
# SessionReplayer
# -----------------------------------------------------------------------

class TestSessionReplayer:
    def setup_method(self):
        self.recorder = SessionRecorder(project_id="proj-1")
        self.session = self.recorder.start_session("task-1")
        self.recorder.record_action(self.session.session_id, "prompt", "Original prompt 1")
        self.recorder.record_action(self.session.session_id, "response", "Response 1")
        self.recorder.record_action(self.session.session_id, "prompt", "Original prompt 2")
        self.recorder.record_file_change(self.session.session_id, "f.py", "", "code")
        self.recorder.end_session(self.session.session_id)
        self.replayer = SessionReplayer()

    def test_prepare_replay(self):
        replay = self.replayer.prepare_replay(self.session)
        assert replay.status == SessionStatus.REPLAYING
        assert len(replay.actions) == 3

    def test_prepare_replay_with_modified_prompt(self):
        replay = self.replayer.prepare_replay(
            self.session, modified_prompts={0: "Modified prompt 1"},
        )
        assert replay.actions[0].content == "Modified prompt 1"
        assert replay.actions[2].content == "Original prompt 2"

    def test_compare_sessions(self):
        replay = self.replayer.prepare_replay(self.session)
        comparison = self.replayer.compare_sessions(self.session, replay)
        assert comparison["action_count_a"] == 3
        assert comparison["action_count_b"] == 3

    def test_list_replays(self):
        self.replayer.prepare_replay(self.session)
        replays = self.replayer.list_replays()
        assert len(replays) == 1

    def test_get_replay(self):
        replay = self.replayer.prepare_replay(self.session)
        found = self.replayer.get_replay(replay.session_id)
        assert found is not None


# -----------------------------------------------------------------------
# SessionRecorder — stats
# -----------------------------------------------------------------------

class TestSessionRecorderStats:
    def test_stats_empty(self):
        recorder = SessionRecorder()
        stats = recorder.get_stats()
        assert stats["total_sessions"] == 0

    def test_stats_with_data(self):
        recorder = SessionRecorder(project_id="p")
        s = recorder.start_session("t1")
        recorder.record_action(s.session_id, "prompt", "x")
        recorder.record_file_change(s.session_id, "f.py", "", "code")
        recorder.end_session(s.session_id)
        stats = recorder.get_stats()
        assert stats["total_sessions"] == 1
        assert stats["completed"] == 1
        assert stats["total_actions"] == 1
        assert stats["total_file_changes"] == 1

    def test_stats_multiple_sessions(self):
        recorder = SessionRecorder(project_id="p")
        s1 = recorder.start_session("t1")
        recorder.end_session(s1.session_id, status="completed")
        s2 = recorder.start_session("t2")
        recorder.end_session(s2.session_id, status="failed")
        stats = recorder.get_stats()
        assert stats["total_sessions"] == 2
        assert stats["completed"] == 1
        assert stats["failed"] == 1
