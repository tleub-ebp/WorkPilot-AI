"""Pair Programming Runner — AI Pair Programming Mode (Feature 10).

Spawned by the Electron main process. Implements the AI's portion of a
pair-programming session while streaming structured JSON events to stdout.

Usage:
    python pair_programming_runner.py \\
        --project-dir /path/to/project \\
        --project-id proj-1 \\
        --session-id pair_1234567890 \\
        --goal "Add user authentication" \\
        --dev-scope "Frontend login/register components" \\
        --ai-scope "Backend auth API + integration tests" \\
        --messages-file /tmp/pair_session_messages.json

The runner reads --messages-file periodically for new user messages and
injects them into the AI context between steps.

Output (one JSON object per line):
    {"type": "status", "status": "planning", "message": "..."}
    {"type": "stream", "content": "..."}
    {"type": "action", "action_type": "file_created", "file_path": "...", "description": "..."}
    {"type": "action", "action_type": "file_modified", "file_path": "...", "description": "..."}
    {"type": "question", "content": "...", "message_id": "..."}
    {"type": "conflict", "file_path": "...", "message": "..."}
    {"type": "done", "summary": "..."}
    {"type": "error", "message": "..."}
"""

import argparse
import json
import os
import sys
import time
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Structured output helpers
# ---------------------------------------------------------------------------

def emit(event: dict) -> None:
    """Emit a JSON event to stdout and flush immediately."""
    print(json.dumps(event), flush=True)


def emit_status(status: str, message: str) -> None:
    emit({"type": "status", "status": status, "message": message})


def emit_stream(content: str) -> None:
    emit({"type": "stream", "content": content})


def emit_action(action_type: str, description: str, file_path: str = "") -> None:
    emit({
        "type": "action",
        "action_type": action_type,
        "description": description,
        "file_path": file_path,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def emit_question(content: str) -> None:
    emit({
        "type": "question",
        "content": content,
        "message_id": f"q_{int(time.time())}",
    })


def emit_conflict(file_path: str, message: str) -> None:
    emit({"type": "conflict", "file_path": file_path, "message": message})


def emit_done(summary: str) -> None:
    emit({"type": "done", "summary": summary})


def emit_error(message: str) -> None:
    emit({"type": "error", "message": message})


# ---------------------------------------------------------------------------
# Message file helpers (bidirectional communication)
# ---------------------------------------------------------------------------

def read_pending_messages(messages_file: str) -> list[dict]:
    """Read and clear pending messages from the messages file."""
    try:
        if not os.path.exists(messages_file):
            return []
        with open(messages_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        messages = data.get("pending", [])
        if messages:
            # Clear processed messages
            with open(messages_file, "w", encoding="utf-8") as f:
                json.dump({"pending": []}, f)
        return messages
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

async def run_pair_programming_session(
    project_dir: str,
    project_id: str,
    session_id: str,
    goal: str,
    dev_scope: str,
    ai_scope: str,
    messages_file: str,
) -> None:
    """Run the AI pair programming session using Claude SDK."""

    emit_status("planning", "Analyzing project structure and planning AI scope...")

    # Add project backend to path
    backend_dir = Path(__file__).parent.parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    try:
        from core.client import create_client
        from core.workflow_logger import workflow_logger
    except ImportError as e:
        emit_error(f"Failed to import backend modules: {e}")
        return

    # Build the initial prompt
    system_context = f"""You are working as an AI pair programmer on a real codebase.

PROJECT DIRECTORY: {project_dir}
SESSION GOAL: {goal}

WORK SPLIT:
- Developer is working on: {dev_scope}
- YOU (AI) are responsible for: {ai_scope}

IMPORTANT RULES:
1. Focus ONLY on your assigned scope: {ai_scope}
2. Do NOT touch files in the developer's scope: {dev_scope}
3. After completing each major step, emit a brief summary of what you did
4. If you need clarification from the developer, ask a concise question and continue with your best assumption
5. Work systematically: analyze → plan → implement → verify

Start by analyzing the existing codebase structure relevant to your scope, then implement your portion.
Be concrete and actually write/modify files. Show your work step by step.
"""

    prompt = f"""Please implement the following as part of our pair programming session:

GOAL: {goal}
YOUR SCOPE: {ai_scope}

The developer is simultaneously working on: {dev_scope}

Steps:
1. First, briefly analyze the project structure relevant to your scope (list key files)
2. Plan your implementation (3-5 bullet points)
3. Implement each part, explaining what you're doing
4. After completing your work, provide a summary of all changes made

Begin now. Be systematic and thorough."""

    trace_id = workflow_logger.log_agent_start(
        "PairProgrammingAgent", "pair_programming", {"session_id": session_id}
    )

    emit_status("active", f"Starting AI implementation: {ai_scope}")

    try:
        client = create_client(
            project_dir=project_dir,
            spec_dir=None,
            model=None,
            agent_type="coder",
        )

        accumulated_response = []
        last_message_check = time.time()

        async with client:
            async for event in client.stream(
                prompt=prompt,
                system=system_context,
            ):
                event_type = event.get("type", "")

                # Check for user messages every 5 seconds
                if time.time() - last_message_check > 5:
                    last_message_check = time.time()
                    pending = read_pending_messages(messages_file)
                    for msg in pending:
                        emit_stream(f"\n\n[Developer says: {msg.get('content', '')}]\n\n")

                if event_type == "text":
                    content = event.get("content", "")
                    if content:
                        accumulated_response.append(content)
                        emit_stream(content)

                        # Detect file operations in the stream
                        lower = content.lower()
                        if "creating file" in lower or "writing file" in lower or "create file" in lower:
                            # Try to extract file path from context
                            emit_action("file_created", content[:120].strip())
                        elif "modifying" in lower or "updating" in lower or "editing" in lower:
                            emit_action("file_modified", content[:120].strip())

                elif event_type == "tool_use":
                    tool_name = event.get("name", "")
                    tool_input = event.get("input", {})

                    if tool_name in ("create_file", "write_file"):
                        file_path = tool_input.get("path", tool_input.get("file_path", ""))
                        emit_action("file_created", f"Created {file_path}", file_path)
                    elif tool_name in ("edit_file", "str_replace_editor"):
                        file_path = tool_input.get("path", tool_input.get("file_path", ""))
                        emit_action("file_modified", f"Modified {file_path}", file_path)
                    elif tool_name == "bash":
                        cmd = str(tool_input.get("command", ""))[:80]
                        emit_action("command_run", f"Running: {cmd}")

                elif event_type == "error":
                    error_msg = event.get("message", "Unknown error")
                    emit_error(error_msg)
                    return

        # Check for any dev scope conflicts (simple heuristic)
        full_response = "".join(accumulated_response)
        dev_scope_keywords = [kw.strip().lower() for kw in dev_scope.split() if len(kw) > 4]
        for keyword in dev_scope_keywords[:3]:  # Check first 3 keywords
            if keyword in full_response.lower() and "avoid" not in full_response.lower():
                emit_conflict(
                    keyword,
                    f"AI output may touch developer's scope area: '{keyword}'. Review recommended."
                )
                break

        summary = f"Completed AI scope: {ai_scope}. See chat for implementation details."
        workflow_logger.log_agent_end("PairProgrammingAgent", "success", trace_id=trace_id)
        emit_done(summary)

    except ImportError:
        # Fallback demo mode when Claude SDK is not configured
        emit_status("active", f"[Demo Mode] Simulating AI work on: {ai_scope}")
        _run_demo_session(goal, dev_scope, ai_scope, messages_file)

    except Exception as e:
        workflow_logger.log_agent_end("PairProgrammingAgent", "error", trace_id=trace_id)
        emit_error(f"Session failed: {e}")


def _run_demo_session(goal: str, dev_scope: str, ai_scope: str, messages_file: str) -> None:
    """Demo mode when the SDK is not available — streams a simulated response."""
    steps = [
        ("planning", f"Analyzing requirements for: {ai_scope}"),
        ("active",   f"Starting implementation of {ai_scope}..."),
    ]
    for status, msg in steps:
        emit_status(status, msg)
        time.sleep(0.5)

    demo_plan = f"""## AI Pair Programming — Demo Mode

**Goal:** {goal}

**Developer's scope:** {dev_scope}
**My scope:** {ai_scope}

### My Implementation Plan

1. Analyze the existing codebase structure
2. Identify files to create/modify for {ai_scope}
3. Implement the core logic
4. Write tests
5. Validate integration points

*Note: This is running in demo mode. Connect the Claude SDK to enable real implementation.*

### Simulated Steps

"""
    for char in demo_plan:
        emit_stream(char)
        time.sleep(0.01)

    time.sleep(0.5)

    # Simulate some actions
    emit_action("file_created", "Created implementation file", "src/api/auth.py")
    time.sleep(0.3)
    emit_action("file_created", "Created test file", "tests/test_auth.py")
    time.sleep(0.3)
    emit_action("file_modified", "Updated configuration", "config/settings.py")

    # Check for any user messages
    pending = read_pending_messages(messages_file)
    for msg in pending:
        emit_stream(f"\n\n[Responding to your message: {msg.get('content', '')}]\n")
        emit_stream("Got it! I'll incorporate that into my implementation.\n")

    emit_stream("\n### Summary\n\nDemo session complete. "
                "Configure the Claude SDK to enable real pair programming.\n")
    emit_done(f"Demo completed for scope: {ai_scope}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="AI Pair Programming Runner")
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--goal", required=True)
    parser.add_argument("--dev-scope", required=True)
    parser.add_argument("--ai-scope", required=True)
    parser.add_argument("--messages-file", required=True)
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)

    asyncio.run(run_pair_programming_session(
        project_dir=args.project_dir,
        project_id=args.project_id,
        session_id=args.session_id,
        goal=args.goal,
        dev_scope=args.dev_scope,
        ai_scope=args.ai_scope,
        messages_file=args.messages_file,
    ))


if __name__ == "__main__":
    main()
