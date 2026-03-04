"""
WebSocket Server for Streaming Development Mode.

Provides real-time event broadcasting to frontend clients.
"""

import json
import logging
import time
import os
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


def _is_port_available(port: int) -> bool:
    """Check if port is available."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        result = sock.connect_ex(('localhost', port))
        return result != 0
    finally:
        sock.close()


def _should_kill_process(pid: int, name: str, cmdline: list, create_time: float, port: int) -> tuple[bool, str]:
    """Determine if a process should be killed."""
    current_pid = os.getpid()
    
    # NEVER kill our own process
    if pid == current_pid:
        return False, "Skipping our own process"
    
    process_age = time.time() - create_time
    cmdline_str = ' '.join(cmdline).lower()
    
    # Check for stale WebSocket server processes
    is_stale_websocket = (
        'websocket_server.py' in cmdline_str and
        process_age > 30 and
        'auto-claude' not in cmdline_str.lower()
    )
    
    # Check for orphaned processes
    is_orphaned = (
        name.lower().startswith('python') and
        process_age > 300 and  # 5 minutes
        port == 8765
    )
    
    if is_stale_websocket:
        return True, f"Killing stale WebSocket process (age: {process_age:.1f}s)"
    elif is_orphaned:
        return True, f"Killing orphaned process (age: {process_age:.1f}s)"
    else:
        return False, f"Preserving active process (age: {process_age:.1f}s)"


def _kill_process_safely(proc: psutil.Process, pid: int, name: str) -> None:
    """Kill a process safely with graceful termination."""
    logger.info(f"Terminating process {pid} ({name})")
    proc.terminate()
    
    # Wait for graceful termination
    time.sleep(1)
    
    # Force kill if still running
    if proc.is_running():
        logger.warning(f"Force killing process {pid}")
        proc.kill()


def _is_target_connection(conn, port: int) -> bool:
    """Check if connection matches our target port and IP criteria."""
    return (conn.status == 'LISTEN' and 
            conn.laddr.port == port and 
            (conn.laddr.ip == '127.0.0.1' or conn.laddr.ip == '0.0.0.0' or conn.laddr.ip == '::1'))


def _process_single_process(proc, port: int) -> bool:
    """Process a single process and return True if it was killed."""
    try:
        connections = proc.connections()
        for conn in connections:
            if not _is_target_connection(conn, port):
                continue
        
        pid = proc.info['pid']
        name = proc.info['name']
        cmdline = proc.info.get('cmdline', [])
        create_time = proc.info.get('create_time', 0)
        
        should_kill, reason = _should_kill_process(pid, name, cmdline, create_time, port)
        logger.info(f"Process {pid} ({name}): {reason}")
        
        if should_kill:
            _kill_process_safely(proc, pid, name)
            return True
        return False
        
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def _handle_post_kill_cleanup(port: int) -> bool:
    """Handle cleanup after killing processes."""
    # Wait for processes to fully terminate
    time.sleep(2)
    
    if not _is_port_available(port):
        logger.error(f"Port {port} is still occupied after killing stale processes")
        return False
    else:
        logger.info(f"Port {port} is now available after cleaning stale processes")
        return True


def kill_processes_on_port(port: int) -> bool:
    """Kill only stale WebSocket server processes, preserving active live coding sessions."""
    try:
        if _is_port_available(port):
            logger.info(f"Port {port} is already available")
            return True
            
        logger.warning(f"Port {port} is occupied, checking for stale processes...")
        
        killed_any = False
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            if _process_single_process(proc, port):
                killed_any = True
                
        if killed_any:
            return _handle_post_kill_cleanup(port)
        else:
            logger.info(f"No stale processes found on port {port}, preserving existing processes")
            return True
            
    except Exception as e:
        logger.error(f"Error checking processes on port {port}: {e}")
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
            
    def _process_request(self, path, request_headers):
        """Process incoming WebSocket connection requests."""
        return None

    def _extract_websocket_path(self, websocket: WebSocketServerProtocol) -> str:
        """Extract path from websocket connection."""
        path = "/stream/default"  # Default fallback

        try:
            if hasattr(websocket, 'path'):
                path = websocket.path
            elif hasattr(websocket, 'scope'):
                scope = websocket.scope
                if scope and 'path' in scope:
                    path = scope['path']
        except Exception as e:
            logger.error(f"Error extracting path: {e}")
            
        return path

    def _extract_session_id(self, path: str, websocket: WebSocketServerProtocol) -> str:
        """Extract session ID from path and websocket."""
        connection_id = id(websocket)
        session_id = f"session-{connection_id}"
        
        # Try to extract a more meaningful session ID if possible
        if path != "/stream/default":
            path_parts = path.strip("/").split("/")
            if len(path_parts) >= 2 and path_parts[0] == "stream":
                session_id = path_parts[1]
                
        return session_id

    async def _setup_session(self, session_id: str) -> None:
        """Setup streaming session if it doesn't exist."""
        session_info = self.streaming_manager.get_session_info(session_id)
        if not session_info:
            await self.streaming_manager.start_session(session_id, {
                "session_id": session_id,
                "task": "Live Coding Session",
                "project_path": "unknown",
                "auto_created": True,
                "status": "watching"
            })
            logger.info(f"Auto-created session {session_id} for client connection")

    async def _register_client(self, session_id: str, websocket: WebSocketServerProtocol) -> None:
        """Register client with session and streaming manager."""
        if session_id not in self._clients:
            self._clients[session_id] = set()
        self._clients[session_id].add(websocket)
        await self.streaming_manager.subscribe(session_id, websocket)
        logger.info(f"Client connected to session {session_id}")

    async def _send_welcome_message(self, session_id: str, websocket: WebSocketServerProtocol, session_info) -> None:
        """Send welcome message to client."""
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

    async def _cleanup_client(self, session_id: str, websocket: WebSocketServerProtocol) -> None:
        """Clean up client connection."""
        self._clients[session_id].discard(websocket)
        await self.streaming_manager.unsubscribe(session_id, websocket)
        logger.info(f"Client cleanup completed for session {session_id}")

    async def _handle_client(self, websocket: WebSocketServerProtocol):
        """Handle a client connection."""
        # Use a mutable container for session_id so _handle_message can update it
        # when init_session changes the session. A plain string variable would not
        # be updated by the child method due to Python scoping rules.
        ctx = {"session_id": None}
        try:
            # Extract path and session ID
            path = self._extract_websocket_path(websocket)
            ctx["session_id"] = self._extract_session_id(path, websocket)
            logger.info(f"New connection for session {ctx['session_id']} from {websocket.remote_address}")

            # Setup session if needed
            await self._setup_session(ctx["session_id"])

            # Register client
            await self._register_client(ctx["session_id"], websocket)

            # Send welcome message
            session_info = self.streaming_manager.get_session_info(ctx["session_id"])
            await self._send_welcome_message(ctx["session_id"], websocket, session_info)

            # Handle incoming messages
            try:
                async for message in websocket:
                    await self._handle_message(ctx, websocket, message)
            except websockets.exceptions.ConnectionClosed:
                logger.info(f"Client disconnected from session {ctx['session_id']}")
            except websockets.exceptions.ConnectionClosedOK:
                logger.info(f"Client cleanly disconnected from session {ctx['session_id']}")
            except websockets.exceptions.ConnectionClosedError as e:
                logger.warning(f"Client connection closed with error from session {ctx['session_id']}: {e}")
            except websockets.exceptions.InvalidMessage as e:
                logger.warning(f"Invalid message received from session {ctx['session_id']}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error in client handler for session {ctx['session_id']}: {e}")
            finally:
                await self._cleanup_client(ctx["session_id"], websocket)

        except Exception as e:
            logger.error(f"Critical error in _handle_client: {e}")
            # Ensure cleanup even if connection fails early
            try:
                if ctx["session_id"]:
                    await self._cleanup_client(ctx["session_id"], websocket)
            except Exception as cleanup_error:
                logger.error(f"Error during cleanup: {cleanup_error}")
            
    async def _handle_message(
        self,
        ctx: dict,
        websocket: WebSocketServerProtocol,
        message: str
    ):
        """Handle incoming message from client.

        Args:
            ctx: Mutable dict with 'session_id' key — updated by init_session so
                 subsequent messages use the correct session.
        """
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            session_id = ctx["session_id"]

            # Special handling for session initialization
            if msg_type == "init_session":
                # Client is sending the actual session ID
                actual_session_id = data.get("session_id")
                if actual_session_id and actual_session_id != session_id:
                    logger.info(f"Client requested session change: {session_id} -> {actual_session_id}")

                    # Move client to the requested session
                    if session_id in self._clients:
                        self._clients[session_id].discard(websocket)
                    await self.streaming_manager.unsubscribe(session_id, websocket)
                    logger.info(f"Unsubscribed from old session: {session_id}")

                    session_id = actual_session_id
                    ctx["session_id"] = session_id  # Update the mutable context

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

            if msg_type == "agent_event":
                # Agent process is publishing an event — broadcast to all subscribers
                event_data = data.get("event")
                if event_data:
                    from .streaming_manager import StreamingEvent, EventType
                    # Use session_id from event data as authoritative source
                    event_session = event_data.get("session_id", session_id)
                    try:
                        event = StreamingEvent(
                            event_type=EventType(event_data.get("event_type", "agent_thinking")),
                            timestamp=event_data.get("timestamp", time.time()),
                            data=event_data.get("data", {}),
                            session_id=event_session,
                        )
                        logger.info(f"Broadcasting agent event '{event_data.get('event_type')}' to session {event_session} ({len(self._clients.get(event_session, set()))} subscribers)")
                        await self._broadcast_to_subscribers(event_session, event, exclude=websocket)
                    except (ValueError, KeyError) as e:
                        logger.warning(f"Invalid agent event: {e}")

            elif msg_type == "chat_message":
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
            
    async def _broadcast_to_subscribers(self, session_id: str, event, exclude=None):
        """Broadcast an event to all subscribers of a session, optionally excluding the sender."""
        subscribers = self._clients.get(session_id, set())
        event_json = json.dumps(event.to_dict())
        disconnected = set()

        for ws in subscribers:
            if ws is exclude:
                continue
            try:
                await ws.send(event_json)
            except Exception as e:
                logger.warning(f"Failed to send event to subscriber: {e}")
                disconnected.add(ws)

        for ws in disconnected:
            subscribers.discard(ws)
            await self.streaming_manager.unsubscribe(session_id, ws)

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