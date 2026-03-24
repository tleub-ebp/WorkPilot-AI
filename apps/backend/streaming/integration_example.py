"""
Integration Example - How to add streaming to an existing agent

This file demonstrates how to integrate streaming mode into your agent execution.
"""

import asyncio
from pathlib import Path

from streaming import create_streaming_wrapper


class StreamingEnabledAgent:
    """
    Example of how to wrap an existing agent with streaming capabilities.

    This pattern can be applied to any agent/task execution in WorkPilot AI.
    """

    def __init__(self, task_id: str, enable_streaming: bool = False):
        self.task_id = task_id
        self.enable_streaming = enable_streaming
        self.streaming_wrapper = None

        if enable_streaming:
            self.streaming_wrapper = create_streaming_wrapper(
                session_id=task_id, enable_recording=True
            )

    async def execute_task(
        self, spec_name: str, project_path: Path, task_description: str
    ):
        """Execute a task with optional streaming."""

        # Start streaming session if enabled
        if self.streaming_wrapper:
            await self.streaming_wrapper.start_session(
                {
                    "task_id": self.task_id,
                    "spec_name": spec_name,
                    "project_path": str(project_path),
                    "description": task_description,
                }
            )

        try:
            # Phase 1: Planning
            await self._emit_progress(10, "Planning implementation...")
            await self._emit_thinking(
                "Analyzing the requirements and planning the approach..."
            )

            plan = await self._create_implementation_plan(task_description)

            # Phase 2: Implementation
            await self._emit_progress(30, "Implementing changes...")
            await self._emit_thinking("Starting implementation based on the plan...")

            for step in plan:
                await self._implement_step(step)

            # Phase 3: Testing
            await self._emit_progress(70, "Running tests...")
            await self._emit_thinking("Validating the implementation with tests...")

            test_success = await self._run_tests()

            # Phase 4: Finalization
            await self._emit_progress(90, "Finalizing...")
            await self._emit_response(
                "Implementation completed successfully!", tokens_used=1500
            )

            await self._emit_progress(100, "Complete!")

            return {"success": True, "test_passed": test_success}

        finally:
            # End streaming session if enabled
            if self.streaming_wrapper:
                await self.streaming_wrapper.end_session()

    async def _create_implementation_plan(self, description: str):
        """Create implementation plan (example)."""
        await self._emit_thinking("Breaking down the task into actionable steps...")

        # Simulate planning
        await asyncio.sleep(1)

        return [
            {"action": "create_file", "file": "src/feature.py"},
            {"action": "create_test", "file": "tests/test_feature.py"},
            {"action": "update_docs", "file": "README.md"},
        ]

    async def _implement_step(self, step):
        """Implement a single step."""
        action = step["action"]
        file_path = step["file"]

        await self._emit_thinking(f"Working on: {action} for {file_path}")

        if action == "create_file":
            content = "# Implementation code here\npass"
            await self._emit_file_change(file_path, "create", content)

        elif action == "create_test":
            content = "def test_feature():\n    assert True"
            await self._emit_file_change(file_path, "create", content)

        elif action == "update_docs":
            content = "# Feature Documentation\nThis feature does X, Y, Z."
            await self._emit_file_change(file_path, "update", content)

        # Simulate work
        await asyncio.sleep(0.5)

    async def _run_tests(self):
        """Run tests (example)."""
        test_command = "pytest tests/"

        await self._emit_command(test_command)
        await asyncio.sleep(1)
        await self._emit_command_output("All tests passed! ✅")

        await self._emit_test_result(True, "All tests passed successfully")

        return True

    # Helper methods for streaming events

    async def _emit_progress(self, progress: float, status: str):
        """Emit progress update."""
        if self.streaming_wrapper:
            await self.streaming_wrapper.emit_progress(progress, status)

    async def _emit_thinking(self, thinking: str):
        """Emit agent thinking."""
        if self.streaming_wrapper:
            await self.streaming_wrapper.emit_agent_thinking(thinking)

    async def _emit_response(self, response: str, tokens_used: int | None = None):
        """Emit agent response."""
        if self.streaming_wrapper:
            await self.streaming_wrapper.emit_agent_response(response, tokens_used)

    async def _emit_file_change(
        self, file_path: str, operation: str, content: str | None = None
    ):
        """Emit file change."""
        if self.streaming_wrapper:
            await self.streaming_wrapper.emit_file_change(file_path, operation, content)

    async def _emit_command(self, command: str):
        """Emit command execution."""
        if self.streaming_wrapper:
            await self.streaming_wrapper.emit_command(command)

    async def _emit_command_output(self, output: str, is_error: bool = False):
        """Emit command output."""
        if self.streaming_wrapper:
            await self.streaming_wrapper.emit_command_output(output, is_error)

    async def _emit_test_result(self, success: bool, details: str | None = None):
        """Emit test result."""
        if self.streaming_wrapper:
            await self.streaming_wrapper.emit_test_result(success, details)


# Example usage
async def main():
    """Example of how to use the streaming-enabled agent."""

    # Create agent with streaming enabled
    agent = StreamingEnabledAgent(
        task_id="example-task-001",
        enable_streaming=True,  # Set to False to disable streaming
    )

    # Execute task
    result = await agent.execute_task(
        spec_name="001-example-feature",
        project_path=Path.cwd(),
        task_description="Implement a simple example feature",
    )

    print(f"\nTask completed: {result}")


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())


# ============================================================================
# INTEGRATION GUIDE
# ============================================================================
"""
To integrate streaming into your existing agent:

1. Import the wrapper:
   from streaming import create_streaming_wrapper

2. In your agent __init__, add:
   self.streaming_wrapper = None
   if enable_streaming:
       self.streaming_wrapper = create_streaming_wrapper(session_id)

3. At the start of execution, call:
   if self.streaming_wrapper:
       await self.streaming_wrapper.start_session(metadata)

4. Throughout execution, emit events:
   - await self.streaming_wrapper.emit_progress(50, "Working...")
   - await self.streaming_wrapper.emit_thinking("Analyzing...")
   - await self.streaming_wrapper.emit_file_change("file.py", "update", content)
   - await self.streaming_wrapper.emit_command("pytest")
   - etc.

5. At the end, call:
   if self.streaming_wrapper:
       await self.streaming_wrapper.end_session()

That's it! Your agent now broadcasts in real-time to the streaming UI.
"""

# ============================================================================
# MINIMAL INTEGRATION EXAMPLE
# ============================================================================
"""
# In your existing agent.py:

from streaming import create_streaming_wrapper

class YourExistingAgent:
    def __init__(self, ..., enable_streaming=False):
        # ... existing code ...
        self.streaming = create_streaming_wrapper(task_id) if enable_streaming else None
    
    async def run(self):
        if self.streaming:
            await self.streaming.start_session({...})
        
        try:
            # Your existing code
            await self.do_work()
            
            # Add streaming events where appropriate:
            if self.streaming:
                await self.streaming.emit_progress(50, "Working...")
        
        finally:
            if self.streaming:
                await self.streaming.end_session()
"""
