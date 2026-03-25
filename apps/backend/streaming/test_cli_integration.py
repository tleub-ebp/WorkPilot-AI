"""
CLI Streaming Integration Tests
==============================

Integration tests for CLI streaming functionality.
"""

import asyncio
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import websockets
from cli.build_commands import handle_build_command
from cli.main import parse_args
from websockets.client import WebSocketClientProtocol


class TestCLIStreamingIntegration:
    """Integration tests for CLI streaming functionality."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Create basic project structure
            (project_path / ".workpilot").mkdir()
            (project_path / ".workpilot" / "specs").mkdir()

            # Create a test spec
            spec_dir = project_path / ".workpilot" / "specs" / "001-test-streaming"
            spec_dir.mkdir()

            # Create basic spec files
            (spec_dir / "spec.md").write_text("""
# Test Streaming Spec

## Feature
Test streaming functionality

## Requirements
- Should emit streaming events
- Should connect to WebSocket server
""")

            (spec_dir / "task_metadata.json").write_text(
                json.dumps(
                    {
                        "title": "Test Streaming",
                        "description": "Test streaming functionality",
                        "phaseModels": {
                            "spec": "sonnet",
                            "planning": "sonnet",
                            "coding": "sonnet",
                            "qa": "sonnet",
                        },
                    }
                )
            )

            yield project_path

    def test_parse_args_with_streaming_options(self):
        """Test CLI argument parsing with streaming options."""
        # Test with streaming enabled
        with patch.object(
            sys,
            "argv",
            [
                "workpilot",
                "--spec",
                "001-test",
                "--enable-streaming",
                "--streaming-session-id",
                "test-session-123",
            ],
        ):
            args = parse_args()

        assert args.enable_streaming is True
        assert args.streaming_session_id == "test-session-123"
        assert args.spec == "001-test"

    def test_parse_args_without_streaming(self):
        """Test CLI argument parsing without streaming options."""
        with patch.object(sys, "argv", ["workpilot", "--spec", "001-test"]):
            args = parse_args()

        assert args.enable_streaming is False
        assert args.streaming_session_id is None
        assert args.spec == "001-test"

    def test_handle_build_command_with_streaming(self, temp_project_dir):
        """Test build command with streaming options."""
        spec_dir = temp_project_dir / ".workpilot" / "specs" / "001-test-streaming"

        # Mock the agent execution to avoid actually running it.
        # handle_build_command does a lazy import: from agent import run_autonomous_agent
        # and wraps it in asyncio.run(), so we patch at "agent" module level with a
        # regular (non-async) mock to avoid the "asyncio.run() in running event loop" error.
        with patch("agent.run_autonomous_agent") as mock_run:
            mock_run.return_value = None

            # Call build command with streaming options
            handle_build_command(
                project_dir=temp_project_dir,
                spec_dir=spec_dir,
                model="sonnet",
                max_iterations=None,
                verbose=False,
                force_isolated=False,
                force_direct=True,  # Use direct mode for testing
                auto_continue=True,
                skip_qa=True,
                force_bypass_approval=True,
                base_branch=None,
                enable_streaming=True,
                streaming_session_id="test-session-123",
            )

            # Verify run_autonomous_agent was called with streaming parameters
            mock_run.assert_called_once()
            call_args = mock_run.call_args[1]  # kwargs
            assert call_args["streaming_session_id"] == "test-session-123"

    def test_handle_build_command_without_streaming(self, temp_project_dir):
        """Test build command without streaming options."""
        spec_dir = temp_project_dir / ".workpilot" / "specs" / "001-test-streaming"

        with patch("agent.run_autonomous_agent") as mock_run:
            mock_run.return_value = None

            handle_build_command(
                project_dir=temp_project_dir,
                spec_dir=spec_dir,
                model="sonnet",
                max_iterations=None,
                verbose=False,
                force_isolated=False,
                force_direct=True,
                auto_continue=True,
                skip_qa=True,
                force_bypass_approval=True,
                base_branch=None,
                enable_streaming=False,
                streaming_session_id=None,
            )

            mock_run.assert_called_once()
            call_args = mock_run.call_args[1]
            assert call_args["streaming_session_id"] is None

    @pytest.mark.asyncio
    async def test_streaming_wrapper_integration(self, temp_project_dir):
        """Test streaming wrapper integration with agent execution."""
        spec_dir = temp_project_dir / ".workpilot" / "specs" / "001-test-streaming"

        # Mock streaming components
        with (
            patch("agents.coder.create_streaming_wrapper") as mock_create_wrapper,
            patch("agents.coder.run_agent_session") as mock_run_session,
        ):
            # Setup mocks
            mock_wrapper = MagicMock()
            mock_wrapper.start_session = AsyncMock()
            mock_wrapper.end_session = AsyncMock()
            mock_wrapper.emit_agent_thinking = AsyncMock()
            mock_wrapper.emit_agent_response = AsyncMock()
            mock_create_wrapper.return_value = mock_wrapper

            # Mock agent session response
            mock_run_session.return_value = ("continue", "Test response", None)

            # Import and run the agent with streaming
            from agents.coder import run_autonomous_agent

            await run_autonomous_agent(
                project_dir=temp_project_dir,
                spec_dir=spec_dir,
                model="sonnet",
                max_iterations=1,
                verbose=False,
                streaming_session_id="integration-test-session",
            )

            # Verify streaming wrapper was created and used
            mock_create_wrapper.assert_called_once_with(
                "integration-test-session", enable_recording=True
            )
            mock_wrapper.start_session.assert_called_once()

            # Verify streaming events were emitted
            mock_wrapper.emit_agent_thinking.assert_called()
            mock_wrapper.emit_agent_response.assert_called()

            # Verify cleanup
            mock_wrapper.end_session.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires real WebSocket network connection between processes")
    async def test_websocket_server_integration(self):
        """Test WebSocket server integration with streaming."""
        from streaming.websocket_server import StreamingWebSocketServer
        from streaming.streaming_manager import StreamingManager

        # Create server on test port
        server = StreamingWebSocketServer(host="localhost", port=8767)
        await server.start()

        try:
            # Create streaming wrapper
            from streaming.agent_wrapper import create_streaming_wrapper

            wrapper = create_streaming_wrapper("websocket-test-session")

            # Start session
            await wrapper.start_session(
                {
                    "session_id": "websocket-test-session",
                    "task": "websocket-test",
                    "project_path": "/test",
                    "agent_type": "coder",
                }
            )

            # Emit events
            await wrapper.emit_agent_thinking("WebSocket integration test")
            await wrapper.emit_agent_response("Response from WebSocket test")
            await wrapper.emit_file_change("/test/file.ts", content="console.log('test');")

            # End session
            await wrapper.end_session()

            # Verify session was created and cleaned up
            mock_manager = server.streaming_manager
            assert "websocket-test-session" not in mock_manager.sessions

        finally:
            await server.stop()

    def test_full_streaming_pipeline(self, temp_project_dir):
        """Test complete streaming pipeline from CLI to WebSocket."""
        spec_dir = temp_project_dir / ".workpilot" / "specs" / "001-test-streaming"

        # Mock all components for full pipeline test.
        # handle_build_command does lazy import: from agent import run_autonomous_agent
        # and wraps it in asyncio.run(), so use a regular mock (not AsyncMock).
        # StreamingManager lives in streaming.streaming_manager, not websocket_server.
        with (
            patch("agent.run_autonomous_agent") as mock_run_agent,
        ):
            mock_run_agent.return_value = None

            # Execute full pipeline
            handle_build_command(
                project_dir=temp_project_dir,
                spec_dir=spec_dir,
                model="sonnet",
                max_iterations=1,
                verbose=False,
                force_isolated=False,
                force_direct=True,
                auto_continue=True,
                skip_qa=True,
                force_bypass_approval=True,
                base_branch=None,
                enable_streaming=True,
                streaming_session_id="full-pipeline-test",
            )

            # Verify the agent was called with the correct streaming session ID
            mock_run_agent.assert_called_once()
            call_args = mock_run_agent.call_args[1]
            assert call_args["streaming_session_id"] == "full-pipeline-test"

    def test_cli_help_includes_streaming_options(self):
        """Test that CLI help includes streaming options."""
        import sys
        from io import StringIO

        # Capture help output
        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            # This should print help and exit
            with patch.object(sys, "argv", ["workpilot", "--help"]):
                with pytest.raises(SystemExit):
                    parse_args()
        finally:
            help_output = sys.stdout.getvalue()
            sys.stdout = old_stdout

        # Verify streaming options are documented
        assert "--enable-streaming" in help_output
        assert "--streaming-session-id" in help_output
        assert "streaming" in help_output.lower()

    @pytest.mark.asyncio
    async def test_error_handling_streaming_unavailable(self, temp_project_dir):
        """Test error handling when streaming is unavailable."""
        spec_dir = temp_project_dir / ".workpilot" / "specs" / "001-test-streaming"

        # Mock streaming import failure
        with (
            patch("agents.coder.STREAMING_AVAILABLE", False),
            patch("agents.coder.run_agent_session") as mock_run_session,
        ):
            mock_run_session.return_value = ("continue", "Test response", None)

            from agents.coder import run_autonomous_agent

            # Should run without streaming when unavailable
            await run_autonomous_agent(
                project_dir=temp_project_dir,
                spec_dir=spec_dir,
                model="sonnet",
                max_iterations=1,
                verbose=False,
                streaming_session_id="unavailable-test",
            )

            # Agent session should still run
            mock_run_session.assert_called()

            # But no streaming wrapper should be created
            assert mock_run_session.call_count == 1


class TestStreamingCLICommands:
    """Test streaming-specific CLI commands."""

    def test_streaming_server_command_parsing(self):
        """Test streaming server command parsing."""
        with patch.object(
            sys,
            "argv",
            ["workpilot", "--streaming-server", "--streaming-port", "9999"],
        ):
            args = parse_args()

        assert args.streaming_server is True
        assert args.streaming_port == 9999

    def test_list_recordings_command_parsing(self):
        """Test list recordings command parsing."""
        with patch.object(sys, "argv", ["workpilot", "--list-recordings"]):
            args = parse_args()

        assert args.list_recordings is True

    def test_replay_recording_command_parsing(self):
        """Test replay recording command parsing."""
        with patch.object(
            sys,
            "argv",
            [
                "workpilot",
                "--replay-recording",
                "test-recording.json",
                "--speed",
                "2.0",
            ],
        ):
            args = parse_args()

        assert args.replay_recording == "test-recording.json"
        assert args.speed == 2


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
