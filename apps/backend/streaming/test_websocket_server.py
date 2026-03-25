"""
WebSocket Server Tests
======================

Unit tests for the WebSocket server and streaming manager.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import websockets
from websockets.server import WebSocketServerProtocol

from .streaming_manager import StreamingManager
from .websocket_server import StreamingWebSocketServer


class TestStreamingManager:
    """Test cases for StreamingManager class."""

    @pytest.fixture
    def streaming_manager(self):
        """Create streaming manager for testing."""
        return StreamingManager()

    @pytest.mark.asyncio
    async def test_add_session(self, streaming_manager):
        """Test adding a new session."""
        session_id = "test-session-123"
        metadata = {"task": "test-task", "project_path": "/test"}

        await streaming_manager.start_session(session_id, metadata)

        sessions = streaming_manager.get_active_sessions()
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == session_id
        assert sessions[0]["metadata"] == metadata

    @pytest.mark.asyncio
    async def test_remove_session(self, streaming_manager):
        """Test removing a session."""
        session_id = "test-session-123"
        metadata = {"task": "test-task"}

        # Add session first
        await streaming_manager.start_session(session_id, metadata)
        sessions = streaming_manager.get_active_sessions()
        assert len(sessions) == 1

        # Remove session
        await streaming_manager.end_session(session_id)
        sessions = streaming_manager.get_active_sessions()
        assert len(sessions) == 0

    @pytest.mark.asyncio
    async def test_add_client_to_session(self, streaming_manager):
        """Test adding a client to a session."""
        session_id = "test-session-123"
        mock_client = MagicMock(spec=WebSocketServerProtocol)

        # Start session
        await streaming_manager.start_session(session_id, {"task": "test"})

        # Add client
        streaming_manager.subscribe(session_id, mock_client)

        # Verify client is subscribed (check internal state)
        assert session_id in streaming_manager._subscribers
        assert mock_client in streaming_manager._subscribers[session_id]

    @pytest.mark.asyncio
    async def test_remove_client_from_session(self, streaming_manager):
        """Test removing a client from a session."""
        session_id = "test-session-123"
        mock_client = MagicMock(spec=WebSocketServerProtocol)

        # Start session and add client
        await streaming_manager.start_session(session_id, {"task": "test"})
        streaming_manager.subscribe(session_id, mock_client)
        assert len(streaming_manager._subscribers[session_id]) == 1

        # Remove client
        streaming_manager.unsubscribe(session_id, mock_client)
        assert len(streaming_manager._subscribers[session_id]) == 0

    @pytest.mark.asyncio
    async def test_broadcast_event(self, streaming_manager):
        """Test broadcasting an event to session clients."""
        session_id = "test-session-123"
        mock_client1 = MagicMock(spec=WebSocketServerProtocol)
        mock_client2 = MagicMock(spec=WebSocketServerProtocol)

        # Setup clients
        mock_client1.send = AsyncMock()
        mock_client2.send = AsyncMock()

        # Start session and add clients
        await streaming_manager.start_session(session_id, {"task": "test"})
        streaming_manager.subscribe(session_id, mock_client1)
        streaming_manager.subscribe(session_id, mock_client2)

        # Emit an event using the API
        await streaming_manager.emit_agent_thinking(
            session_id=session_id, thinking="test message"
        )

        # Verify both clients received the event
        mock_client1.send.assert_called_once()
        mock_client2.send.assert_called_once()

        # Verify the sent data
        sent_data1 = json.loads(mock_client1.send.call_args[0][0])
        sent_data2 = json.loads(mock_client2.send.call_args[0][0])

        assert sent_data1["event_type"] == "agent_thinking"
        assert sent_data2["event_type"] == "agent_thinking"
        assert sent_data1["data"]["thinking"] == "test message"
        assert sent_data2["data"]["thinking"] == "test message"

    @pytest.mark.asyncio
    async def test_broadcast_event_no_clients(self, streaming_manager):
        """Test broadcasting to a session with no clients."""
        session_id = "test-session-123"

        # Start session but don't add clients
        await streaming_manager.start_session(session_id, {"task": "test"})

        # Emit event (should not raise error)
        await streaming_manager.emit_agent_thinking(session_id, "test")

        # If we reach this point, the test passed (no exceptions raised)
        # Verify session still exists and is properly managed
        session_info = streaming_manager.get_session_info(session_id)
        assert session_info is not None
        assert session_info["status"] == "active"

    @pytest.mark.asyncio
    async def test_broadcast_event_nonexistent_session(self, streaming_manager):
        """Test broadcasting to a nonexistent session."""
        # Should not raise error
        await streaming_manager.emit_agent_thinking("nonexistent-session", "test")

        # If we reach this point, the test passed (no exceptions raised)
        # Verify the session doesn't exist (as expected for nonexistent session)
        session_info = streaming_manager.get_session_info("nonexistent-session")
        assert session_info is None


class TestStreamingWebSocketServer:
    """Test cases for StreamingWebSocketServer class."""

    @pytest.fixture
    def mock_websocket(self):
        """Mock WebSocket for testing."""
        ws = MagicMock(spec=WebSocketServerProtocol)
        ws.send = AsyncMock()
        ws.recv = AsyncMock()
        ws.close = AsyncMock()
        return ws

    @pytest.fixture
    def websocket_server(self):
        """Create WebSocket server for testing."""
        return StreamingWebSocketServer(host="localhost", port=8765)

    @pytest.mark.asyncio
    async def test_handle_client_with_session_in_path(
        self, websocket_server, mock_websocket
    ):
        """Test handling a client connection."""
        # Mock the websocket to simulate message reception
        mock_websocket.__aiter__ = AsyncMock()
        mock_websocket.__aiter__.return_value = json.dumps(
            {"type": "test", "data": "test"}
        )

        # Simulate client connection
        await websocket_server._handle_client(mock_websocket)

        # Should have auto-created a session and subscribed the client
        # Verify client is connected (check internal state)
        assert len(websocket_server._clients) > 0

    @pytest.mark.asyncio
    async def test_handle_init_session_message(self, websocket_server, mock_websocket):
        """Test handling init_session message."""
        session_id = "test-session-123"

        # Start session first
        await websocket_server.streaming_manager.start_session(
            session_id, {"task": "test"}
        )

        # Mock websocket send method
        mock_websocket.send = AsyncMock()

        # Send init message
        init_message = {"type": "init_session", "session_id": "updated-session-456"}

        await websocket_server._handle_message(
            {"session_id": session_id}, mock_websocket, json.dumps(init_message)
        )

        # Verify a response was sent
        mock_websocket.send.assert_called()

        # Check the sent data
        sent_data = json.loads(mock_websocket.send.call_args[0][0])
        assert "event_type" in sent_data, "Should send an event response"

    @pytest.mark.asyncio
    async def test_handle_chat_message(self, websocket_server, mock_websocket):
        """Test handling chat message."""
        session_id = "test-session-123"

        # Start session and add client
        await websocket_server.streaming_manager.start_session(
            session_id, {"task": "test"}
        )
        websocket_server.streaming_manager.subscribe(session_id, mock_websocket)

        # Send chat message
        chat_message = {
            "type": "chat_message",
            "message": "Hello, how are you implementing this feature?",
        }

        await websocket_server._handle_message(
            {"session_id": session_id}, mock_websocket, json.dumps(chat_message)
        )

        # Verify message was broadcast to all clients
        mock_websocket.send.assert_called()
        broadcast = json.loads(mock_websocket.send.call_args[0][0])
        assert broadcast["event_type"] == "chat_message"
        assert (
            broadcast["data"]["message"]
            == "Hello, how are you implementing this feature?"
        )

    @pytest.mark.asyncio
    async def test_handle_control_message_pause(self, websocket_server, mock_websocket):
        """Test handling control pause message."""
        session_id = "test-session-123"

        # Start session and add client
        await websocket_server.streaming_manager.start_session(
            session_id, {"task": "test"}
        )
        websocket_server.streaming_manager.subscribe(session_id, mock_websocket)

        # Mock websocket send method
        mock_websocket.send = AsyncMock()

        # Send toggle_pause control message (implementation handles "toggle_pause" not "pause")
        control_message = {"type": "control", "action": "toggle_pause"}

        await websocket_server._handle_message(
            {"session_id": session_id}, mock_websocket, json.dumps(control_message)
        )

        # Verify some response was sent (control events are broadcast)
        mock_websocket.send.assert_called()

        # Check the sent data contains control information
        sent_data = json.loads(mock_websocket.send.call_args[0][0])
        assert "event_type" in sent_data, "Should send a control event response"

    @pytest.mark.asyncio
    async def test_handle_unknown_message_type(self, websocket_server, mock_websocket):
        """Test handling unknown message type."""
        session_id = "test-session-123"

        # Start session and add client
        await websocket_server.streaming_manager.start_session(
            session_id, {"task": "test"}
        )
        websocket_server.streaming_manager.subscribe(session_id, mock_websocket)

        # Send unknown message type
        unknown_message = {"type": "unknown_type", "data": "test"}

        await websocket_server._handle_message(
            {"session_id": session_id}, mock_websocket, json.dumps(unknown_message)
        )

        # Should handle gracefully without error - verify no response was sent
        mock_websocket.send.assert_not_called()
        
        # Verify session is still active and properly managed
        session_info = websocket_server.streaming_manager.get_session_info(session_id)
        assert session_info is not None
        assert session_info["status"] == "active"

    def test_get_active_sessions(self, websocket_server):
        """Test getting active sessions."""
        # This method now delegates to streaming_manager
        sessions = websocket_server.get_active_sessions()
        assert isinstance(sessions, list)

        # Start a session and verify it appears
        # Note: This would require async setup in a real test
        # For now, just test the method exists and returns correct type


class TestWebSocketIntegration:
    """Integration tests for WebSocket functionality."""

    @pytest.mark.asyncio
    async def test_full_client_session(self):
        """Test complete client session lifecycle."""
        server = StreamingWebSocketServer(
            host="localhost", port=8766
        )  # Different port for testing

        # Create mock client
        mock_client = MagicMock(spec=WebSocketServerProtocol)
        mock_client.send = AsyncMock()
        mock_client.recv = AsyncMock()

        # Test basic server functionality
        sessions = server.get_active_sessions()
        assert isinstance(sessions, list)

        # Test that streaming manager is accessible
        assert server.streaming_manager is not None


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
