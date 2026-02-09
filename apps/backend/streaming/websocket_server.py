"""
WebSocket Server for Streaming Development Mode.

Provides real-time event broadcasting to frontend clients.
"""

import json
import logging
from typing import Any

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    WebSocketServerProtocol = None

from .session_recorder import SessionRecorder
from .streaming_manager import get_streaming_manager

logger = logging.getLogger(__name__)


class StreamingWebSocketServer:
    """
    WebSocket server for streaming development sessions.

    Handles client connections and message routing for the streaming mode.
    """

    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.streaming_manager = get_streaming_manager()
        self.session_recorder = SessionRecorder()
        self._server = None
        self._clients: dict[str, set[Any]] = {}
        
    async def start(self):
        """Start the WebSocket server."""
        if not WEBSOCKETS_AVAILABLE:
            logger.warning(
                "websockets package not installed. "
                "Streaming mode will not be available. "
                "Install with: pip install websockets"
            )
            return
            
        try:
            self._server = await websockets.serve(
                self._handle_client,
                self.host,
                self.port
            )
            logger.info(f"Streaming WebSocket server started on ws://{self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            
    async def stop(self):
        """Stop the WebSocket server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("Streaming WebSocket server stopped")
            
    async def _handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle a client connection."""
        # Extract session_id from path: /stream/{session_id}
        path_parts = path.strip("/").split("/")
        if len(path_parts) < 2 or path_parts[0] != "stream":
            await websocket.close(1008, "Invalid path")
            return
            
        session_id = path_parts[1]
        
        # Register client
        if session_id not in self._clients:
            self._clients[session_id] = set()
        self._clients[session_id].add(websocket)
        
        # Subscribe to streaming manager
        await self.streaming_manager.subscribe(session_id, websocket)
        
        logger.info(f"Client connected to session {session_id}")
        
        try:
            # Handle incoming messages
            async for message in websocket:
                await self._handle_message(session_id, websocket, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected from session {session_id}")
        finally:
            # Unregister client
            self._clients[session_id].discard(websocket)
            await self.streaming_manager.unsubscribe(session_id, websocket)
            
    async def _handle_message(
        self,
        session_id: str,
        websocket: WebSocketServerProtocol,
        message: str
    ):
        """Handle incoming message from client."""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "chat_message":
                # User sent a chat message
                await self.streaming_manager.emit_chat_message(
                    session_id=session_id,
                    message=data.get("message", ""),
                    author="User",
                    author_type="user",
                )
                
            elif msg_type == "control":
                # Control command (pause/resume/stop)
                action = data.get("action")
                await self._handle_control(session_id, action)
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON message: {message}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            
    async def _handle_control(self, session_id: str, action: str):
        """Handle control commands."""
        if action == "toggle_pause":
            # Get current session status
            session_info = self.streaming_manager.get_session_info(session_id)
            
            if not session_info:
                logger.warning(f"Session not found: {session_id}")
                return
            
            # Toggle pause/resume based on current status
            if session_info.get("status") == "paused":
                await self.streaming_manager.resume_session(session_id)
                logger.info(f"Session resumed: {session_id}")
            else:
                await self.streaming_manager.pause_session(session_id)
                logger.info(f"Session paused: {session_id}")
                
        elif action == "stop":
            # Stop the session
            await self.streaming_manager.end_session(session_id)
            logger.info(f"Stop requested for session {session_id}")
    def get_active_sessions(self):
        """Get list of active streaming sessions."""
        return self.streaming_manager.get_active_sessions()


# Global server instance
_websocket_server: StreamingWebSocketServer | None = None


def get_websocket_server() -> StreamingWebSocketServer:
    """Get or create the global WebSocket server instance."""
    global _websocket_server
    if _websocket_server is None:
        _websocket_server = StreamingWebSocketServer()
    return _websocket_server


async def start_streaming_server():
    """Start the streaming WebSocket server."""
    server = get_websocket_server()
    await server.start()


async def stop_streaming_server():
    """Stop the streaming WebSocket server."""
    server = get_websocket_server()
    await server.stop()
