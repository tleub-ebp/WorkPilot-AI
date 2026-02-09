"""
Streaming Commands - Start/manage streaming server
"""

import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def handle_streaming_server_command(args):
    """Handle streaming server command."""
    from streaming import start_streaming_server, get_websocket_server
    
    print("\n" + "="*70)
    print("🎥 Starting Streaming Development Server")
    print("="*70 + "\n")
    
    # Start the WebSocket server
    try:
        asyncio.run(_run_streaming_server(args))
    except KeyboardInterrupt:
        print("\n\n🛑 Streaming server stopped by user")
    except Exception as e:
        logger.error(f"Error running streaming server: {e}")
        print(f"\n❌ Failed to start streaming server: {e}")
        return 1
    
    return 0


async def _run_streaming_server(args):
    """Run the streaming server asynchronously."""
    from streaming import start_streaming_server, stop_streaming_server, get_websocket_server
    
    # Start server
    await start_streaming_server()
    
    server = get_websocket_server()
    print(f"✅ Streaming server running on ws://{server.host}:{server.port}")
    print(f"\n📺 Open the frontend and click 'Watch Live' on any task to start streaming")
    print(f"\n💡 Press Ctrl+C to stop the server\n")
    
    # Keep running until interrupted
    try:
        while True:
            await asyncio.sleep(1)
            
            # Print active sessions periodically
            active_sessions = server.get_active_sessions()
            if active_sessions:
                print(f"\r📊 Active sessions: {len(active_sessions)}", end="", flush=True)
    finally:
        print("\n\n🛑 Shutting down streaming server...")
        await stop_streaming_server()


def handle_list_recordings_command(args):
    """Handle list recordings command."""
    from streaming import SessionRecorder
    
    recorder = SessionRecorder()
    recordings = recorder.list_recordings()
    
    if not recordings:
        print("\n📼 No recordings found\n")
        return 0
    
    print("\n" + "="*70)
    print(f"📼 Streaming Session Recordings ({len(recordings)})")
    print("="*70 + "\n")
    
    for i, recording in enumerate(recordings, 1):
        duration_mins = recording["duration"] / 60
        event_count = recording["event_count"]
        session_id = recording["session_id"]
        
        print(f"{i}. Session: {session_id}")
        print(f"   Duration: {duration_mins:.1f} minutes")
        print(f"   Events: {event_count}")
        print(f"   File: {recording['filepath']}")
        print()
    
    return 0


def handle_replay_recording_command(args):
    """Handle replay recording command."""
    from streaming import SessionRecorder
    import json
    
    if not args.recording_file:
        print("\n❌ Please specify a recording file with --recording-file")
        return 1
    
    recorder = SessionRecorder()
    
    try:
        recording_path = Path(args.recording_file)
        recording = recorder.load_recording(recording_path)
        
        print("\n" + "="*70)
        print(f"▶️  Replaying Session: {recording.session_id}")
        print("="*70 + "\n")
        
        print(f"Duration: {recording.duration() / 60:.1f} minutes")
        print(f"Events: {len(recording.events)}")
        print(f"\nSpeed: {args.speed}x")
        print("\nStarting replay...\n")
        
        # Run replay
        asyncio.run(_replay_session(recording, args.speed))
        
        print("\n✅ Replay completed\n")
        
    except FileNotFoundError:
        print(f"\n❌ Recording file not found: {args.recording_file}")
        return 1
    except Exception as e:
        logger.error(f"Error replaying recording: {e}")
        print(f"\n❌ Failed to replay recording: {e}")
        return 1
    
    return 0


async def _replay_session(recording, speed: float):
    """Replay a session asynchronously."""
    from streaming import SessionRecorder
    
    recorder = SessionRecorder()
    
    async def print_event(event):
        """Print event during replay."""
        print(f"[{event.event_type.value}] {event.data}")
    
    await recorder.replay_session(recording, speed=speed, callback=print_event)
