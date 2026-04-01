"""
Tests for Streaming Development Mode
"""

import asyncio
import json
import pytest
import sys
from pathlib import Path
from datetime import datetime

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from streaming import (
    StreamingManager,
    StreamingEvent,
    EventType,
    SessionRecorder,
    StreamingAgentWrapper,
)


class TestStreamingManager:
    """Test StreamingManager functionality."""
    
    @pytest.mark.asyncio
    async def test_start_session(self):
        """Test starting a streaming session."""
        manager = StreamingManager()
        
        await manager.start_session("test-session-1", {"task": "test"})
        
        sessions = manager.get_active_sessions()
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == "test-session-1"
        assert sessions[0]["status"] == "active"
    
    @pytest.mark.asyncio
    async def test_end_session(self):
        """Test ending a streaming session."""
        manager = StreamingManager()
        
        await manager.start_session("test-session-2", {"task": "test"})
        await manager.end_session("test-session-2")
        
        sessions = manager.get_active_sessions()
        assert len(sessions) == 0
    
    @pytest.mark.asyncio
    async def test_emit_code_change(self):
        """Test emitting code change events."""
        manager = StreamingManager()
        
        await manager.start_session("test-session-3", {"task": "test"})
        await manager.emit_code_change(
            session_id="test-session-3",
            file_path="test.py",
            change_type="update",
            content="print('hello')",
        )
        
        # Event count should increment
        session_info = manager.get_session_info("test-session-3")
        assert session_info["event_count"] >= 1
    
    @pytest.mark.asyncio
    async def test_emit_multiple_events(self):
        """Test emitting multiple event types."""
        manager = StreamingManager()
        
        await manager.start_session("test-session-4", {"task": "test"})
        
        # Emit various events
        await manager.emit_agent_thinking("test-session-4", "Analyzing code...")
        await manager.emit_command("test-session-4", "pytest")
        await manager.emit_test_run("test-session-4", "pytest tests/")
        await manager.emit_test_result("test-session-4", True, "All passed")
        await manager.emit_progress("test-session-4", 50, "Half done")
        
        session_info = manager.get_session_info("test-session-4")
        assert session_info["event_count"] >= 5


class TestSessionRecorder:
    """Test SessionRecorder functionality."""
    
    def test_start_recording(self, tmp_path):
        """Test starting a recording."""
        recorder = SessionRecorder(recordings_dir=tmp_path)
        
        recorder.start_recording("test-rec-1", {"task": "test"})
        
        assert "test-rec-1" in recorder._active_recordings
    
    def test_record_event(self, tmp_path):
        """Test recording an event."""
        recorder = SessionRecorder(recordings_dir=tmp_path)
        recorder.start_recording("test-rec-2", {"task": "test"})
        
        event = StreamingEvent(
            event_type=EventType.CODE_CHANGE,
            timestamp=1234567890.0,
            data={"file": "test.py"},
            session_id="test-rec-2",
        )
        
        recorder.record_event(event)
        
        recording = recorder._active_recordings["test-rec-2"]
        assert len(recording.events) == 1
        assert recording.events[0].event_type == EventType.CODE_CHANGE
    
    def test_stop_and_save_recording(self, tmp_path):
        """Test stopping and saving a recording to recordings_dir."""
        recorder = SessionRecorder(recordings_dir=tmp_path)
        recorder.start_recording("test-rec-3", {"task": "test"})
        # Add some events
        for i in range(3):
            event = StreamingEvent(
                event_type=EventType.PROGRESS_UPDATE,
                timestamp=1234567890.0 + i,
                data={"progress": i * 30},
                session_id="test-rec-3",
            )
            recorder.record_event(event)
        # Stop recording
        recording = recorder.stop_recording("test-rec-3")
        assert recording is not None
        assert len(recording.events) == 3
        # Check file was saved in recordings_dir
        timestamp = datetime.fromtimestamp(recording.start_time).strftime("%Y%m%d_%H%M%S")
        saved_files = list(tmp_path.glob("*.json"))
        assert len(saved_files) == 1
        assert saved_files[0].name == f"{timestamp}_{recording.session_id}.json"
    
    def test_load_recording(self, tmp_path):
        """Test loading a recording from disk."""
        recorder = SessionRecorder(recordings_dir=tmp_path)
        
        # Create and save a recording
        recorder.start_recording("test-rec-4", {"task": "test"})
        event = StreamingEvent(
            event_type=EventType.SESSION_START,
            timestamp=1234567890.0,
            data={"test": "data"},
            session_id="test-rec-4",
        )
        recorder.record_event(event)
        recording = recorder.stop_recording("test-rec-4")
        filepath = recorder.save_recording(recording)
        
        # Load it back
        loaded = recorder.load_recording(filepath)
        
        assert loaded.session_id == "test-rec-4"
        assert len(loaded.events) == 1
        assert loaded.events[0].event_type == EventType.SESSION_START
    
    def test_list_recordings(self, tmp_path):
        """Test listing all recordings."""
        recorder = SessionRecorder(recordings_dir=tmp_path)
        
        # Create multiple recordings
        for i in range(3):
            recorder.start_recording(f"test-rec-{i}", {"task": f"test-{i}"})
            recorder.stop_recording(f"test-rec-{i}")
        
        recordings = recorder.list_recordings()
        
        assert len(recordings) >= 3


class TestStreamingAgentWrapper:
    """Test StreamingAgentWrapper functionality."""
    
    @pytest.mark.asyncio
    async def test_wrapper_lifecycle(self):
        """Test wrapper start and end session."""
        wrapper = StreamingAgentWrapper("test-wrapper-1", enable_recording=False)
        
        await wrapper.start_session({"task": "test"})
        assert wrapper._is_active
        
        await wrapper.end_session()
        assert not wrapper._is_active
    
    @pytest.mark.asyncio
    async def test_wrapper_events(self):
        """Test wrapper event emission."""
        wrapper = StreamingAgentWrapper("test-wrapper-2", enable_recording=False)
        
        await wrapper.start_session({"task": "test"})
        
        # These should not raise errors
        await wrapper.emit_file_change("test.py", "update")
        await wrapper.emit_command("pytest")
        await wrapper.emit_agent_thinking("Thinking...")
        await wrapper.emit_test_run("pytest tests/")
        await wrapper.emit_progress(50, "Half done")
        
        await wrapper.end_session()
    
    @pytest.mark.asyncio
    async def test_wrapper_inactive_no_emit(self):
        """Test that events are not emitted when wrapper is inactive."""
        wrapper = StreamingAgentWrapper("test-wrapper-3", enable_recording=False)
        
        # Should not raise error even though session not started
        await wrapper.emit_file_change("test.py", "update")
        await wrapper.emit_command("pytest")


class TestEventTypes:
    """Test EventType enumeration."""
    
    def test_all_event_types_exist(self):
        """Test that all expected event types exist."""
        expected_types = [
            "SESSION_START",
            "SESSION_END",
            "CODE_CHANGE",
            "FILE_CREATE",
            "FILE_UPDATE",
            "FILE_DELETE",
            "COMMAND_RUN",
            "COMMAND_OUTPUT",
            "AGENT_THINKING",
            "AGENT_RESPONSE",
            "ERROR",
            "TEST_RUN",
            "TEST_RESULT",
            "COMMIT",
            "CHAT_MESSAGE",
            "INTERVENTION",
            "PROGRESS_UPDATE",
        ]
        
        for event_type in expected_types:
            assert hasattr(EventType, event_type)
    
    def test_event_serialization(self):
        """Test that events can be serialized to dict."""
        event = StreamingEvent(
            event_type=EventType.CODE_CHANGE,
            timestamp=1234567890.0,
            data={"file": "test.py", "content": "print('hello')"},
            session_id="test-event-1",
        )
        
        event_dict = event.to_dict()
        
        assert event_dict["event_type"] == "code_change"
        assert event_dict["timestamp"] == 1234567890.0
        assert event_dict["data"]["file"] == "test.py"
        assert event_dict["session_id"] == "test-event-1"


@pytest.mark.asyncio
async def test_replay_session():
    """Test session replay functionality."""
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        recorder = SessionRecorder(recordings_dir=Path(tmp_dir))
        
        # Create a recording
        recorder.start_recording("replay-test", {"task": "test"})
        
        events = []
        for i in range(5):
            event = StreamingEvent(
                event_type=EventType.PROGRESS_UPDATE,
                timestamp=1234567890.0 + i * 0.1,
                data={"progress": i * 20},
                session_id="replay-test",
            )
            recorder.record_event(event)
            events.append(event)
        
        recording = recorder.stop_recording("replay-test")
        
        # Replay at high speed
        replayed_events = []
        
        async def capture_event(event):
            replayed_events.append(event)
        
        await recorder.replay_session(recording, speed=10.0, callback=capture_event)
        
        assert len(replayed_events) == 5


class TestPauseResume:
    """Test pause/resume functionality."""
    
    @pytest.mark.asyncio
    async def test_pause_session(self):
        """Test pausing a session."""
        manager = StreamingManager()
        
        await manager.start_session("test-pause-1", {"task": "test"})
        await manager.pause_session("test-pause-1")
        
        session_info = manager.get_session_info("test-pause-1")
        assert session_info["status"] == "paused"
    
    @pytest.mark.asyncio
    async def test_resume_session(self):
        """Test resuming a paused session."""
        manager = StreamingManager()
        
        await manager.start_session("test-pause-2", {"task": "test"})
        await manager.pause_session("test-pause-2")
        
        # Verify it's paused
        assert manager.get_session_info("test-pause-2")["status"] == "paused"
        
        # Resume
        await manager.resume_session("test-pause-2")
        
        # Verify it's active again
        assert manager.get_session_info("test-pause-2")["status"] == "active"
    
    @pytest.mark.asyncio
    async def test_pause_resume_toggle(self):
        """Test toggling pause/resume multiple times."""
        manager = StreamingManager()
        
        await manager.start_session("test-pause-3", {"task": "test"})
        
        # First pause
        await manager.pause_session("test-pause-3")
        assert manager.get_session_info("test-pause-3")["status"] == "paused"
        
        # Resume
        await manager.resume_session("test-pause-3")
        assert manager.get_session_info("test-pause-3")["status"] == "active"
        
        # Pause again
        await manager.pause_session("test-pause-3")
        assert manager.get_session_info("test-pause-3")["status"] == "paused"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])