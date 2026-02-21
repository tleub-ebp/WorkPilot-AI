"""
Streaming Agent Wrapper Tests
============================

Unit tests for the StreamingAgentWrapper and related streaming functionality.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import tempfile
import os

from agent_wrapper import StreamingAgentWrapper, create_streaming_wrapper
from websocket_server import StreamingManager


class TestStreamingAgentWrapper:
    """Test cases for StreamingAgentWrapper class."""

    @pytest.fixture
    def mock_streaming_manager(self):
        """Mock streaming manager for testing."""
        manager = MagicMock(spec=StreamingManager)
        manager.start_session = AsyncMock()
        manager.end_session = AsyncMock()
        manager.broadcast_event = AsyncMock()
        return manager

    @pytest.fixture
    def streaming_wrapper(self, mock_streaming_manager):
        """Create streaming wrapper with mocked dependencies."""
        with patch('agent_wrapper.get_streaming_manager', return_value=mock_streaming_manager):
            wrapper = StreamingAgentWrapper("test-session-123", enable_recording=False)
            return wrapper

    def test_init(self, streaming_wrapper):
        """Test wrapper initialization."""
        assert streaming_wrapper.session_id == "test-session-123"
        assert streaming_wrapper.enable_recording is False
        assert streaming_wrapper.recorder is None
        assert streaming_wrapper._is_active is False

    @pytest.mark.asyncio
    async def test_start_session(self, streaming_wrapper, mock_streaming_manager):
        """Test starting a streaming session."""
        metadata = {
            "session_id": "test-session-123",
            "task": "test-task",
            "project_path": "/test/path",
            "agent_type": "coder",
            "model": "claude-3",
        }

        await streaming_wrapper.start_session(metadata)

        assert streaming_wrapper._is_active is True
        mock_streaming_manager.start_session.assert_called_once_with("test-session-123", metadata)

    @pytest.mark.asyncio
    async def test_end_session(self, streaming_wrapper, mock_streaming_manager):
        """Test ending a streaming session."""
        # First start the session
        await streaming_wrapper.start_session({"session_id": "test-session-123"})
        assert streaming_wrapper._is_active is True

        # Then end it
        await streaming_wrapper.end_session()

        assert streaming_wrapper._is_active is False
        mock_streaming_manager.end_session.assert_called_once_with("test-session-123")

    @pytest.mark.asyncio
    async def test_emit_agent_thinking(self, streaming_wrapper, mock_streaming_manager):
        """Test emitting agent thinking events."""
        await streaming_wrapper.start_session({"session_id": "test-session-123"})
        
        thinking = "Analyzing the code structure..."
        await streaming_wrapper.emit_agent_thinking(thinking)

        expected_event = {
            "event_type": "agent_thinking",
            "timestamp": pytest.approx(float, rel=1e-6),
            "data": {
                "thinking": thinking,
                "session_id": "test-session-123"
            },
            "session_id": "test-session-123"
        }
        
        mock_streaming_manager.broadcast_event.assert_called_once()
        call_args = mock_streaming_manager.broadcast_event.call_args[0]
        assert call_args[0] == "test-session-123"
        assert call_args[1]["event_type"] == "agent_thinking"
        assert call_args[1]["data"]["thinking"] == thinking

    @pytest.mark.asyncio
    async def test_emit_agent_response(self, streaming_wrapper, mock_streaming_manager):
        """Test emitting agent response events."""
        await streaming_wrapper.start_session({"session_id": "test-session-123"})
        
        response = "I'll implement the feature using React hooks..."
        await streaming_wrapper.emit_agent_response(response)

        mock_streaming_manager.broadcast_event.assert_called_once()
        call_args = mock_streaming_manager.broadcast_event.call_args[0]
        assert call_args[1]["event_type"] == "agent_response"
        assert call_args[1]["data"]["response"] == response

    @pytest.mark.asyncio
    async def test_emit_file_change(self, streaming_wrapper, mock_streaming_manager):
        """Test emitting file change events."""
        await streaming_wrapper.start_session({"session_id": "test-session-123"})
        
        file_path = "/test/path/src/components/Test.tsx"
        content = "export default function Test() { return <div>Test</div>; }"
        await streaming_wrapper.emit_file_change(file_path, content)

        mock_streaming_manager.broadcast_event.assert_called_once()
        call_args = mock_streaming_manager.broadcast_event.call_args[0]
        assert call_args[1]["event_type"] == "file_change"
        assert call_args[1]["data"]["file_path"] == file_path
        assert call_args[1]["data"]["content"] == content

    @pytest.mark.asyncio
    async def test_emit_command(self, streaming_wrapper, mock_streaming_manager):
        """Test emitting command events."""
        await streaming_wrapper.start_session({"session_id": "test-session-123"})
        
        command = "npm install"
        await streaming_wrapper.emit_command(command, "/test/path")

        mock_streaming_manager.broadcast_event.assert_called_once()
        call_args = mock_streaming_manager.broadcast_event.call_args[0]
        assert call_args[1]["event_type"] == "command"
        assert call_args[1]["data"]["command"] == command
        assert call_args[1]["data"]["working_dir"] == "/test/path"

    @pytest.mark.asyncio
    async def test_emit_error(self, streaming_wrapper, mock_streaming_manager):
        """Test emitting error events."""
        await streaming_wrapper.start_session({"session_id": "test-session-123"})
        
        error_msg = "Failed to compile TypeScript"
        await streaming_wrapper.emit_error(error_msg)

        mock_streaming_manager.broadcast_event.assert_called_once()
        call_args = mock_streaming_manager.broadcast_event.call_args[0]
        assert call_args[1]["event_type"] == "error"
        assert call_args[1]["data"]["error"] == error_msg

    @pytest.mark.asyncio
    async def test_no_emit_when_inactive(self, streaming_wrapper, mock_streaming_manager):
        """Test that events are not emitted when session is inactive."""
        # Don't start the session
        assert streaming_wrapper._is_active is False

        await streaming_wrapper.emit_agent_thinking("test thinking")
        await streaming_wrapper.emit_agent_response("test response")
        await streaming_wrapper.emit_file_change("/test/file", "content")

        # Should not have been called
        mock_streaming_manager.broadcast_event.assert_not_called()


class TestCreateStreamingWrapper:
    """Test cases for create_streaming_wrapper function."""

    @patch('agent_wrapper.StreamingAgentWrapper')
    @patch('agent_wrapper.get_streaming_manager')
    def test_create_wrapper_success(self, mock_get_manager, mock_wrapper_class):
        """Test successful wrapper creation."""
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager
        
        mock_wrapper = MagicMock()
        mock_wrapper_class.return_value = mock_wrapper

        result = create_streaming_wrapper("test-session", enable_recording=True)

        mock_wrapper_class.assert_called_once_with("test-session", enable_recording=True)
        assert result == mock_wrapper

    @patch('agent_wrapper.StreamingAgentWrapper')
    @patch('agent_wrapper.get_streaming_manager')
    def test_create_wrapper_default_recording(self, mock_get_manager, mock_wrapper_class):
        """Test wrapper creation with default recording setting."""
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager
        
        mock_wrapper = MagicMock()
        mock_wrapper_class.return_value = mock_wrapper

        result = create_streaming_wrapper("test-session")

        mock_wrapper_class.assert_called_once_with("test-session", enable_recording=True)
        assert result == mock_wrapper


class TestStreamingIntegration:
    """Integration tests for streaming functionality."""

    @pytest.mark.asyncio
    async def test_full_session_lifecycle(self):
        """Test complete session lifecycle with multiple events."""
        # Create a real streaming manager for integration test
        manager = StreamingManager()
        
        # Mock the broadcast to capture events
        events = []
        async def capture_broadcast(session_id, event):
            events.append((session_id, event))
        
        manager.broadcast_event = capture_broadcast
        
        # Create wrapper
        wrapper = StreamingAgentWrapper("integration-test", enable_recording=False)
        wrapper.streaming_manager = manager

        # Start session
        metadata = {
            "session_id": "integration-test",
            "task": "integration-test-task",
            "project_path": "/test",
            "agent_type": "coder"
        }
        await wrapper.start_session(metadata)

        # Emit various events
        await wrapper.emit_agent_thinking("Starting implementation...")
        await wrapper.emit_file_change("/test/app.ts", "console.log('test');")
        await wrapper.emit_command("npm run build", "/test")
        await wrapper.emit_agent_response("Implementation completed successfully")
        await wrapper.emit_error("Warning: Deprecated API used")

        # End session
        await wrapper.end_session()

        # Verify events were captured
        assert len(events) == 5
        assert events[0][1]["event_type"] == "agent_thinking"
        assert events[1][1]["event_type"] == "file_change"
        assert events[2][1]["event_type"] == "command"
        assert events[3][1]["event_type"] == "agent_response"
        assert events[4][1]["event_type"] == "error"

        # Verify session is inactive
        assert wrapper._is_active is False


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
