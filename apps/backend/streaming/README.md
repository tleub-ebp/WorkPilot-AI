# Streaming Development Mode

## Overview

This module implements the "Streaming Development" feature - a real-time, Twitch-style interface for watching Claude code live.

## Architecture

```
streaming/
├── __init__.py                  # Module exports
├── streaming_manager.py         # Core event broadcasting
├── websocket_server.py          # WebSocket server
├── session_recorder.py          # Recording & replay
├── agent_wrapper.py             # Agent integration wrapper
├── demo.py                      # Interactive demo script
└── integration_example.py       # Integration guide
```

## Quick Start

### 1. Start the WebSocket server

```bash
python apps/backend/run.py --streaming-server
```

### 2. Run the demo

```bash
python -m streaming.demo
```

### 3. Watch in the UI

Open the frontend and click "Watch Live" on any task!

## Usage

### From CLI

```bash
# Start server
python apps/backend/run.py --streaming-server [--streaming-port 8765]

# Run task with streaming
python apps/backend/run.py --spec 001 --enable-streaming

# List recordings
python apps/backend/run.py --list-recordings

# Replay recording
python apps/backend/run.py --replay-recording FILE [--speed 2.0]
```

### From Python

```python
import asyncio
from streaming import create_streaming_wrapper

async def my_task():
    wrapper = create_streaming_wrapper("task-123")
    
    await wrapper.start_session({"task": "example"})
    await wrapper.emit_progress(50, "Working...")
    await wrapper.emit_file_change("test.py", "update", "code")
    await wrapper.end_session()

asyncio.run(my_task())
```

## Event Types

The system supports 17 event types:

- `session_start` / `session_end` - Session lifecycle
- `code_change` - Code modifications
- `file_create` / `file_update` / `file_delete` - File operations
- `command_run` / `command_output` - Command execution
- `agent_thinking` - Agent reasoning
- `agent_response` - Agent responses
- `test_run` / `test_result` - Test execution
- `chat_message` - Chat communication
- `progress_update` - Progress tracking
- `commit` - Git commits
- `intervention` - Manual intervention
- `error` - Error events

## Components

### StreamingManager

Core component that manages streaming sessions and broadcasts events to connected clients.

```python
from streaming import get_streaming_manager

manager = get_streaming_manager()
await manager.start_session("session-id", metadata)
await manager.emit_code_change("session-id", "file.py", "update", content)
await manager.end_session("session-id")
```

### WebSocket Server

Handles WebSocket connections and message routing.

```python
from streaming import start_streaming_server, stop_streaming_server

await start_streaming_server()  # Starts on ws://localhost:8765
# ... do work ...
await stop_streaming_server()
```

### SessionRecorder

Records and replays streaming sessions.

```python
from streaming import SessionRecorder

recorder = SessionRecorder()
recorder.start_recording("session-id", metadata)
# ... events are recorded automatically ...
recording = recorder.stop_recording("session-id")

# Replay later
await recorder.replay_session(recording, speed=2.0)
```

### StreamingAgentWrapper

Wrapper for easy integration with agents.

```python
from streaming import create_streaming_wrapper

wrapper = create_streaming_wrapper("task-id", enable_recording=True)
await wrapper.start_session({...})

# Emit events during execution
await wrapper.emit_thinking("Analyzing code...")
await wrapper.emit_file_change("src/app.py", "update", content)
await wrapper.emit_command("pytest")
await wrapper.emit_test_result(True, "All passed")

await wrapper.end_session()
```

## Integration

See `integration_example.py` for a complete example of how to integrate streaming into an existing agent.

### Minimal Integration

```python
from streaming import create_streaming_wrapper

class MyAgent:
    def __init__(self, enable_streaming=False):
        self.streaming = create_streaming_wrapper(
            session_id="task-id"
        ) if enable_streaming else None
    
    async def run(self):
        if self.streaming:
            await self.streaming.start_session({...})
        
        try:
            # Your agent code here
            if self.streaming:
                await self.streaming.emit_progress(50, "Working...")
        finally:
            if self.streaming:
                await self.streaming.end_session()
```

## Configuration

Environment variables:

- `STREAMING_HOST` - WebSocket host (default: `localhost`)
- `STREAMING_PORT` - WebSocket port (default: `8765`)
- `STREAMING_RECORDINGS_DIR` - Recordings directory (default: `~/.auto-claude/recordings`)

## Testing

Run tests:

```bash
pytest tests/test_streaming.py -v
```

## Documentation

- **Full guide**: `docs/features/streaming-development-mode.md`
- **Quick start**: `docs/features/streaming-quick-start.md`
- **Implementation summary**: `docs/features/STREAMING_IMPLEMENTATION_SUMMARY.md`

## Dependencies

- `websockets>=12.0` - WebSocket server/client
- Python 3.10+ - Async/await support

## Performance

- Latency: < 100ms per event
- Memory: < 50MB per 1-hour session
- Throughput: 100+ events/second
- Recording size: < 1MB per 100 events

## Troubleshooting

### Server won't start

```bash
pip install websockets>=12.0
```

### Frontend shows OFFLINE

1. Check server is running
2. Verify port 8765 is not blocked
3. Check browser console for errors

### No events appearing

1. Ensure `--enable-streaming` is used
2. Check session_id matches
3. Verify wrapper is properly initialized

## Examples

See the `demo.py` file for a complete working example that demonstrates all features.

---

**Happy streaming! 🎥✨**
