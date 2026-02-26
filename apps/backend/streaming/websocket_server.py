"""
WebSocket Server for Streaming Development Mode.

Provides real-time event broadcasting to frontend clients.
"""

import json
import logging
import time
import subprocess
import psutil
import socket
from typing import Any, Optional

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


def kill_processes_on_port(port: int) -> bool:
    """Kill all processes using the specified port. Only targets processes actually listening on this specific port."""
    try:
        # Check if port is available first
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        
        if result != 0:
            logger.info(f"Port {port} is already available")
            return True
            
        logger.warning(f"Port {port} is occupied, attempting to kill processes...")
        
        # Find processes using the port - be very specific
        killed_any = False
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                connections = proc.connections()
                for conn in connections:
                    # Be very specific: only kill processes LISTENING on the exact port
                    if (conn.status == 'LISTEN' and 
                        conn.laddr.port == port and 
                        (conn.laddr.ip == '127.0.0.1' or conn.laddr.ip == '0.0.0.0' or conn.laddr.ip == '::1')):
                        
                        pid = proc.info['pid']
                        name = proc.info['name']
                        cmdline = proc.info.get('cmdline', [])
                        
                        # Additional safety: only kill processes that are actually WebSocket-related
                        # or Python processes that are clearly using this port
                        is_websocket_process = (
                            'websocket' in ' '.join(cmdline).lower() or
                            'ws_server' in ' '.join(cmdline).lower() or
                            port == 8765  # We know this is our WebSocket port
                        )
                        
                        if is_websocket_process:
                            logger.info(f"Killing WebSocket process {pid} ({name}) using port {port}")
                            proc.terminate()
                            killed_any = True
                            
                            # Wait a bit for graceful termination
                            time.sleep(1)
                            
                            # Force kill if still running
                            if proc.is_running():
                                logger.warning(f"Force killing WebSocket process {pid}")
                                proc.kill()
                        else:
                            logger.info(f"Skipping non-WebSocket process {pid} ({name}) on port {port}")
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
                
        if killed_any:
            # Wait for processes to fully terminate
            time.sleep(2)
            
            # Verify port is now available
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            
            if result == 0:
                logger.error(f"Port {port} is still occupied after killing processes")
                return False
            else:
                logger.info(f"Port {port} is now available after killing processes")
                return True
        else:
            logger.warning(f"No processes found using port {port}, but port is occupied")
            return False
            
    except Exception as e:
        logger.error(f"Error killing processes on port {port}: {e}")
        return False


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
        self._connection_paths: dict[int, str] = {}  # Store path by connection ID
        
    async def start(self):
        """Start the WebSocket server."""
        if not WEBSOCKETS_AVAILABLE:
            logger.warning(
                "websockets package not installed. "
                "Streaming mode will not be available. "
                "Install with: pip install websockets"
            )
            return
            
        # Try to kill processes using the port if it's occupied
        if not kill_processes_on_port(self.port):
            logger.error(f"Could not free port {self.port}, WebSocket server will not start")
            return
            
        try:
            # In websockets v16, we need to use a different approach
            # The handler receives only the websocket connection
            self._server = await websockets.serve(
                self._handle_client,
                self.host,
                self.port,
                # Add error handling at the server level
                process_request=self._process_request,
                # Set reasonable limits to prevent abuse
                max_size=10_000_000,  # 10MB max message size
                ping_interval=20,      # Send ping every 20 seconds
                ping_timeout=10,       # Wait 10 seconds for pong response
                close_timeout=10,      # Wait 10 seconds for close handshake
            )
            logger.info(f"Streaming WebSocket server started on ws://{self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            # Don't re-raise, just log and continue without WebSocket support
            
    async def stop(self):
        """Stop the WebSocket server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("Streaming WebSocket server stopped")
            
    async def _process_request(self, path, request_headers):
        """Process incoming WebSocket connection requests."""
        # Store the path for later use in the handler
        # We'll use the connection's ID to store the path
        logger.info(f"WebSocket connection request to path: {path}")
        return None

    async def _handle_client(self, websocket: WebSocketServerProtocol):
        """Handle a client connection."""
        try:
            logger.info(" NEW CONNECTION RECEIVED!")
            logger.info(f" WebSocket object: {websocket}")
            logger.info(f" Local address: {websocket.local_address}")
            logger.info(f" Remote address: {websocket.remote_address}")
                    
            # In websockets v16, we need to extract the path from the websocket object
            # Let's try different approaches to get the path
            
            path = "/stream/default"  # Default fallback
            
            # Try to get path from websocket attributes
            try:
                # Method 1: Check if path attribute exists
                if hasattr(websocket, 'path'):
                    path = websocket.path
                    logger.info(f"Found path via websocket.path: {path}")
                # Method 2: Check if request_headers has path info
                elif hasattr(websocket, 'request_headers'):
                    # The path might be in the request headers or connection info
                    logger.info(f"Request headers: {dict(websocket.request_headers)}")
                # Method 3: Check if there's a scope attribute (ASGI style)
                elif hasattr(websocket, 'scope'):
                    scope = websocket.scope
                    if scope and 'path' in scope:
                        path = scope['path']
                        logger.info(f"Found path via scope: {path}")
                # Method 4: Check connection attributes
                elif hasattr(websocket, 'local_address') and hasattr(websocket, 'remote_address'):
                    # We can't get the path from these, but we can log the connection info
                    logger.info(f"Connection: {websocket.local_address} <-> {websocket.remote_address}")
            except Exception as e:
                logger.error(f"Error extracting path: {e}")
            
            # For now, we'll use a simple approach: extract session ID from a message
            # or use a default session
            logger.info(f"Using path: {path}")
            
            # For testing, let's use the full path if we can determine it from the connection
            # Otherwise, we'll create a session based on the connection ID
            
            # Use connection ID as session identifier for now
            connection_id = id(websocket)
            session_id = f"session-{connection_id}"
            
            # Try to extract a more meaningful session ID if possible
            if path != "/stream/default":
                path_parts = path.strip("/").split("/")
                if len(path_parts) >= 2 and path_parts[0] == "stream":
                    session_id = path_parts[1]
            
            logger.info(f"Client connecting with session ID: {session_id}")
            
            # Check if session exists, if not, create a default one
            session_info = self.streaming_manager.get_session_info(session_id)
            if not session_info:
                # Auto-create a session for watching purposes
                await self.streaming_manager.start_session(session_id, {
                    "session_id": session_id,
                    "task": "Live Coding Session",
                    "project_path": "unknown",
                    "auto_created": True,
                    "status": "watching"
                })
                logger.info(f"Auto-created session {session_id} for client connection")
            
            # Register client
            if session_id not in self._clients:
                self._clients[session_id] = set()
            self._clients[session_id].add(websocket)
            
            # Subscribe to streaming manager
            await self.streaming_manager.subscribe(session_id, websocket)
            
            logger.info(f"Client connected to session {session_id}")
            
            # Send welcome message
            try:
                welcome_event = {
                    "event_type": "session_start",
                    "timestamp": time.time(),
                    "data": {
                        "session_id": session_id,
                        "message": "Connected to streaming session",
                        "auto_created": session_info is None
                    },
                    "session_id": session_id,
                }
                await websocket.send(json.dumps(welcome_event))
            except Exception as e:
                logger.warning(f"Failed to send welcome message: {e}")
            
            try:
                # Handle incoming messages
                async for message in websocket:
                    await self._handle_message(session_id, websocket, message)
            except websockets.exceptions.ConnectionClosed:
                logger.info(f"Client disconnected from session {session_id}")
            except websockets.exceptions.ConnectionClosedOK:
                logger.info(f"Client cleanly disconnected from session {session_id}")
            except websockets.exceptions.ConnectionClosedError as e:
                logger.warning(f"Client connection closed with error from session {session_id}: {e}")
            except websockets.exceptions.InvalidMessage as e:
                logger.warning(f"Invalid message received from session {session_id}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error in client handler for session {session_id}: {e}")
            finally:
                # Unregister client
                self._clients[session_id].discard(websocket)
                await self.streaming_manager.unsubscribe(session_id, websocket)
                logger.info(f"Client cleanup completed for session {session_id}")
                
        except Exception as e:
            logger.error(f"Critical error in _handle_client: {e}")
            # Ensure cleanup even if connection fails early
            try:
                if 'session_id' in locals():
                    self._clients[session_id].discard(websocket)
                    await self.streaming_manager.unsubscribe(session_id, websocket)
            except Exception as cleanup_error:
                logger.error(f"Error during cleanup: {cleanup_error}")
            
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
            
            # Special handling for session initialization
            if msg_type == "init_session":
                # Client is sending the actual session ID
                actual_session_id = data.get("session_id")
                if actual_session_id and actual_session_id != session_id:
                    logger.info(f"Client requested session change: {session_id} -> {actual_session_id}")
                    
                    # Move client to the requested session
                    self._clients[session_id].discard(websocket)
                    await self.streaming_manager.unsubscribe(session_id, websocket)
                    logger.info(f"Unsubscribed from old session: {session_id}")
                    
                    session_id = actual_session_id
                    
                    # Check if new session exists, create if needed
                    session_info = self.streaming_manager.get_session_info(session_id)
                    if not session_info:
                        await self.streaming_manager.start_session(session_id, {
                            "session_id": session_id,
                            "task": "Live Coding Session",
                            "project_path": "unknown",
                            "auto_created": True,
                            "status": "watching"
                        })
                        logger.info(f"Auto-created session {session_id}")
                    
                    # Register with new session
                    if session_id not in self._clients:
                        self._clients[session_id] = set()
                    self._clients[session_id].add(websocket)
                    await self.streaming_manager.subscribe(session_id, websocket)
                    logger.info(f"Subscribed to new session: {session_id}")
                    
                    # Send confirmation
                    confirmation = {
                        "event_type": "session_confirmed",
                        "timestamp": time.time(),
                        "data": {
                            "session_id": session_id,
                            "message": f"Connected to session {session_id}"
                        },
                        "session_id": session_id,
                    }
                    await websocket.send(json.dumps(confirmation))
                    logger.info(f"Sent confirmation for session: {session_id}")
                    return
            
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
_websocket_server: Optional[StreamingWebSocketServer] = None


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