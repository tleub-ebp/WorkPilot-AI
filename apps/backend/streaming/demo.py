"""
Demo script for Streaming Development Mode

This script demonstrates how to use the streaming mode with a simple example.
"""

import asyncio
import time
from pathlib import Path

from streaming import (
    create_streaming_wrapper,
    start_streaming_server,
    stop_streaming_server,
)


async def demo_streaming_session():
    """Run a demo streaming session with simulated agent activity."""

    print("\n" + "=" * 70)
    print("🎥 Streaming Development Mode - DEMO")
    print("=" * 70 + "\n")

    # Start WebSocket server
    print("1️⃣  Starting WebSocket server...")
    await start_streaming_server()
    await asyncio.sleep(1)

    print("✅ Server started on ws://localhost:8765")
    print("\n📺 Open the frontend and click 'Watch Live' to see this demo in action!\n")
    print("⏳ Starting demo in 5 seconds...\n")

    await asyncio.sleep(5)

    # Create streaming wrapper
    session_id = f"demo-{int(time.time())}"
    wrapper = create_streaming_wrapper(session_id, enable_recording=True)

    # Start session
    print("2️⃣  Starting streaming session...")
    await wrapper.start_session(
        {
            "session_id": session_id,
            "task": "Demo Task - Build a simple feature",
            "project_path": str(Path.cwd()),
        }
    )

    print("✅ Session started!")
    print(f"   Session ID: {session_id}\n")

    # Simulate agent activity
    steps = [
        {
            "progress": 10,
            "status": "Analyzing project structure...",
            "thinking": "I need to understand the current codebase structure before making changes.",
            "wait": 2,
        },
        {
            "progress": 25,
            "status": "Creating new component...",
            "file": "src/components/NewFeature.tsx",
            "content": "import React from 'react';\n\nexport function NewFeature() {\n  return <div>Hello World!</div>;\n}",
            "wait": 3,
        },
        {
            "progress": 40,
            "status": "Adding tests...",
            "thinking": "Tests are crucial to ensure the component works correctly.",
            "file": "tests/test_new_feature.py",
            "content": "def test_new_feature():\n    assert True",
            "wait": 2,
        },
        {
            "progress": 55,
            "status": "Running tests...",
            "command": "pytest tests/test_new_feature.py",
            "wait": 3,
        },
        {
            "progress": 70,
            "status": "Tests passed!",
            "test_result": True,
            "wait": 2,
        },
        {
            "progress": 85,
            "status": "Updating documentation...",
            "file": "README.md",
            "content": "# New Feature\n\nThis feature does amazing things!",
            "wait": 2,
        },
        {
            "progress": 100,
            "status": "Build complete!",
            "response": "Successfully created the new feature with tests and documentation.",
            "wait": 2,
        },
    ]

    for i, step in enumerate(steps, 1):
        print(f"\n📊 Step {i}/{len(steps)}: {step['status']}")

        # Progress update
        await wrapper.emit_progress(
            progress=step["progress"],
            status=step["status"],
            current_step=f"Step {i}/{len(steps)}",
        )

        # Agent thinking
        if "thinking" in step:
            await wrapper.emit_agent_thinking(step["thinking"])
            print(f"   💭 {step['thinking']}")

        # File changes
        if "file" in step:
            await wrapper.emit_file_change(
                file_path=step["file"],
                operation="update",
                content=step.get("content"),
            )
            print(f"   📝 Modified: {step['file']}")

        # Command execution
        if "command" in step:
            await wrapper.emit_command(step["command"])
            print(f"   ⚡ Running: {step['command']}")
            await asyncio.sleep(1)
            await wrapper.emit_command_output("All tests passed! ✅")

        # Test results
        if "test_result" in step:
            await wrapper.emit_test_result(
                success=step["test_result"],
                details="All tests passed successfully",
            )
            print("   ✅ Tests: PASSED")

        # Agent response
        if "response" in step:
            await wrapper.emit_agent_response(
                response=step["response"],
                tokens_used=1250,
            )
            print(f"   💬 {step['response']}")

        # Wait before next step
        await asyncio.sleep(step["wait"])

    # Send final chat message
    print("\n💬 Sending completion message...")
    await wrapper.emit_chat_message(
        message="The feature has been successfully implemented! Feel free to review the changes.",
        author="Claude",
        author_type="agent",
    )

    # End session
    print("\n3️⃣  Ending session...")
    await wrapper.end_session()

    print("\n✅ Demo completed!")
    print("\n📼 Recording saved to: ~/.auto-claude/recordings/")
    print("\n💡 You can replay it with:")
    print("   python apps/backend/run.py --list-recordings")
    print("   python apps/backend/run.py --replay-recording <file>\n")

    # Keep server running for a bit
    print("⏳ Server will keep running for 30 seconds...")
    print("   Press Ctrl+C to stop\n")

    try:
        await asyncio.sleep(30)
    except KeyboardInterrupt:
        pass

    # Stop server
    print("\n4️⃣  Stopping server...")
    await stop_streaming_server()
    print("✅ Server stopped\n")
    print("=" * 70)
    print("Demo finished! Thanks for watching! 🎬")
    print("=" * 70 + "\n")


def main():
    """Main entry point."""
    try:
        asyncio.run(demo_streaming_session())
    except KeyboardInterrupt:
        print("\n\n🛑 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
