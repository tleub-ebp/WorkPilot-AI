#!/usr/bin/env python3
"""
End-to-End Streaming Test
========================

Complete end-to-end test for streaming live coding functionality.
This script tests the entire pipeline from CLI to WebSocket to frontend.
"""

import asyncio
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import websockets
from websockets.client import WebSocketClientProtocol

# Configuration
TEST_PORT = 8768
WEBSOCKET_URL = f"ws://localhost:{TEST_PORT}"
BACKEND_PATH = Path(__file__).parent / "apps" / "backend"

class StreamingE2ETest:
    """End-to-end streaming test suite."""

    def __init__(self):
        self.server_process = None
        self.websocket_clients = []
        self.test_results = []

    async def setup_test_environment(self):
        """Set up test environment with temporary project."""
        # Create temporary project directory
        self.temp_dir = Path(tempfile.mkdtemp(prefix="streaming-test-"))
        print(f"📁 Created test directory: {self.temp_dir}")
        
        # Create project structure
        project_dir = self.temp_dir / "test-project"
        project_dir.mkdir()
        
        # Create auto-claude structure
        auto_claude_dir = project_dir / "auto-claude"
        auto_claude_dir.mkdir()
        
        specs_dir = auto_claude_dir / "specs"
        specs_dir.mkdir()
        
        # Create test spec
        spec_dir = specs_dir / "001-streaming-test"
        spec_dir.mkdir()
        
        # Create spec files
        (spec_dir / "spec.md").write_text("""
# Streaming Test Spec

## Feature
Test streaming live coding functionality

## Description
This spec tests the complete streaming pipeline from agent execution to WebSocket broadcasting.

## Requirements
1. Agent should emit thinking events
2. Agent should emit response events
3. Agent should emit file change events
4. Events should be broadcast via WebSocket
5. Frontend should receive events in real-time

## Implementation Plan
- Create a simple React component
- Add basic styling
- Test file modification events
""")
        
        (spec_dir / "task_metadata.json").write_text(json.dumps({
            "title": "Streaming Test",
            "description": "Test streaming functionality",
            "phaseModels": {
                "spec": "haiku",
                "planning": "haiku",
                "coding": "haiku",
                "qa": "haiku"
            }
        }))
        
        self.project_dir = project_dir
        self.spec_dir = spec_dir
        print("✅ Test environment created")

    async def start_websocket_server(self):
        """Start WebSocket server for testing."""
        print("🚀 Starting WebSocket server...")
        
        server_script = f"""
import asyncio
import sys
sys.path.append('{BACKEND_PATH}')

from streaming.websocket_server import StreamingWebSocketServer

async def main():
    server = StreamingWebSocketServer(host="localhost", port={TEST_PORT})
    await server.start()
    print(f"WebSocket server started on port {TEST_PORT}")
    try:
        await asyncio.Future()  # Run forever
    except asyncio.CancelledError:
        await server.stop()
        print("WebSocket server stopped")

if __name__ == "__main__":
    asyncio.run(main())
"""
        
        self.server_process = subprocess.Popen([
            sys.executable, "-c", server_script
        ], cwd=BACKEND_PATH, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for server to start
        await self.wait_for_server()
        print(f"✅ WebSocket server started on port {TEST_PORT}")

    async def wait_for_server(self, max_attempts=30):
        """Wait for WebSocket server to be ready."""
        for i in range(max_attempts):
            try:
                async with websockets.connect(WEBSOCKET_URL, timeout=1) as ws:
                    await ws.close()
                    return
            except Exception:
                await asyncio.sleep(0.5)
        raise Exception("WebSocket server failed to start")

    async def create_websocket_client(self, session_id: str) -> WebSocketClientProtocol:
        """Create and connect a WebSocket client."""
        print(f"🔌 Connecting WebSocket client for session: {session_id}")
        
        ws = await websockets.connect(WEBSOCKET_URL)
        self.websocket_clients.append(ws)
        
        # Send init message
        init_message = {
            "type": "init_session",
            "session_id": session_id
        }
        await ws.send(json.dumps(init_message))
        
        # Wait for confirmation
        response = await ws.recv()
        confirmation = json.loads(response)
        
        if confirmation.get("event_type") == "session_confirmed":
            print(f"✅ Session confirmed: {confirmation['data']['session_id']}")
            return ws
        else:
            raise Exception(f"Unexpected response: {response}")

    async def test_streaming_events(self, session_id: str):
        """Test streaming events flow."""
        print(f"🎬 Testing streaming events for session: {session_id}")
        
        ws = await self.create_websocket_client(session_id)
        
        # Simulate streaming events (normally from agent)
        test_events = [
            {
                "event_type": "agent_thinking",
                "timestamp": time.time(),
                "data": {
                    "thinking": "Analyzing requirements for streaming test...",
                    "session_id": session_id
                },
                "session_id": session_id
            },
            {
                "event_type": "file_change",
                "timestamp": time.time(),
                "data": {
                    "file_path": str(self.project_dir / "src" / "components" / "StreamingTest.tsx"),
                    "content": "export default function StreamingTest() { return <div>Streaming Test</div>; }",
                    "session_id": session_id
                },
                "session_id": session_id
            },
            {
                "event_type": "command",
                "timestamp": time.time(),
                "data": {
                    "command": "npm run build",
                    "working_dir": str(self.project_dir),
                    "session_id": session_id
                },
                "session_id": session_id
            },
            {
                "event_type": "agent_response",
                "timestamp": time.time(),
                "data": {
                    "response": "Streaming test completed successfully! All events were broadcast correctly.",
                    "session_id": session_id
                },
                "session_id": session_id
            }
        ]
        
        received_events = []
        
        async def receive_events():
            try:
                while len(received_events) < len(test_events):
                    message = await ws.recv()
                    event = json.loads(message)
                    received_events.append(event)
                    
                    event_type = event.get("event_type")
                    print(f"📨 Received event: {event_type}")
                    
                    # Verify event structure
                    assert "timestamp" in event
                    assert "data" in event
                    assert "session_id" in event
                    
            except websockets.exceptions.ConnectionClosed:
                pass  # Exit gracefully when connection closes
        
        # Start receiving events
        receive_task = asyncio.create_task(receive_events())
        
        # Send test events
        for event in test_events:
            await ws.send(json.dumps(event))
            await asyncio.sleep(0.1)  # Small delay between events
        
        # Wait for all events to be received
        await receive_task
        
        # Verify all events were received
        assert len(received_events) == len(test_events)
        
        # Verify event types match
        received_types = [event["event_type"] for event in received_events]
        expected_types = [event["event_type"] for event in test_events]
        assert received_types == expected_types
        
        print(f"✅ All {len(test_events)} streaming events received correctly")
        
        await ws.close()

    async def test_cli_with_streaming(self):
        """Test CLI integration with streaming."""
        print("🧪 Testing CLI with streaming options...")
        
        # Test argument parsing
        from cli.main import parse_args
        
        args = parse_args([
            '--spec', '001-streaming-test',
            '--project-dir', str(self.project_dir),
            '--enable-streaming',
            '--streaming-session-id', 'cli-test-session',
            '--direct',  # Use direct mode for testing
            '--auto-continue',
            '--force'
        ])
        
        assert args.enable_streaming is True
        assert args.streaming_session_id == 'cli-test-session'
        assert args.spec == '001-streaming-test'
        
        print("✅ CLI arguments parsed correctly")

    async def test_agent_wrapper_integration(self):
        """Test agent wrapper integration."""
        print("🤖 Testing agent wrapper integration...")
        
        # Mock the streaming manager
        import sys
        sys.path.append(str(BACKEND_PATH))
        
        from streaming.agent_wrapper import StreamingAgentWrapper
        from streaming.websocket_server import StreamingManager
        
        # Create test manager
        manager = StreamingManager()
        
        # Create wrapper
        wrapper = StreamingAgentWrapper("wrapper-test-session", enable_recording=False)
        wrapper.streaming_manager = manager
        
        # Start session
        await wrapper.start_session({
            "session_id": "wrapper-test-session",
            "task": "wrapper-test",
            "project_path": str(self.project_dir),
            "agent_type": "coder"
        })
        
        # Test event emission
        await wrapper.emit_agent_thinking("Wrapper thinking test")
        await wrapper.emit_agent_response("Wrapper response test")
        await wrapper.emit_file_change("/test/file", "test content")
        
        # End session
        await wrapper.end_session()
        
        print("✅ Agent wrapper integration test passed")

    async def test_multiple_clients(self):
        """Test multiple clients in same session."""
        print("👥 Testing multiple clients in same session...")
        
        session_id = "multi-client-test"
        
        # Create multiple clients
        clients = []
        for i in range(3):
            client = await self.create_websocket_client(f"{session_id}-client-{i}")
            clients.append(client)
        
        # Send chat message from first client
        chat_message = {
            "type": "chat_message",
            "message": "Hello from multi-client test!"
        }
        
        await clients[0].send(json.dumps(chat_message))
        
        # All clients should receive the message
        received_messages = []
        for client in clients:
            message = await client.recv()
            event = json.loads(message)
            received_messages.append(event)
        
        # Verify all clients received the chat message
        for msg in received_messages:
            assert msg["event_type"] == "chat_message"
            assert msg["data"]["message"] == "Hello from multi-client test!"
        
        # Close all clients
        for client in clients:
            await client.close()
        
        print(f"✅ Multi-client test passed with {len(clients)} clients")

    async def test_error_handling(self):
        """Test error handling in streaming."""
        print("⚠️ Testing error handling...")
        
        ws = await self.create_websocket_client("error-test-session")
        
        # Send error event
        error_event = {
            "event_type": "error",
            "timestamp": time.time(),
            "data": {
                "error": "Test error message",
                "details": "This is a test error for validation",
                "session_id": "error-test-session"
            },
            "session_id": "error-test-session"
        }
        
        await ws.send(json.dumps(error_event))
        
        # Should receive error event without crashing
        response = await ws.recv()
        event = json.loads(response)
        
        assert event["event_type"] == "error"
        assert event["data"]["error"] == "Test error message"
        
        await ws.close()
        print("✅ Error handling test passed")

    async def cleanup(self):
        """Clean up test environment."""
        print("🧹 Cleaning up test environment...")
        
        # Close WebSocket clients
        for client in self.websocket_clients:
            try:
                await client.close()
            except Exception:
                pass
        
        # Stop server process
        if self.server_process:
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
        
        # Clean up temporary directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        print("✅ Cleanup completed")

    async def run_all_tests(self):
        """Run all streaming tests."""
        print("Starting End-to-End Streaming Tests")
        print("=" * 50)
        
        try:
            await self.setup_test_environment()
            await self.start_websocket_server()
            await self.test_cli_with_streaming()
            await self.test_agent_wrapper_integration()
            await self.test_streaming_events("e2e-test-session")
            await self.test_multiple_clients()
            await self.test_error_handling()
            
            print("=" * 50)
            print("All streaming tests passed!")
            return True
            
        except Exception as e:
            print(f"Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            await self.cleanup()


async def main():
    """Main test runner."""
    tester = StreamingE2ETest()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
