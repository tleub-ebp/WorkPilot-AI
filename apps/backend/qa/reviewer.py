"""
QA Reviewer Agent Session
==========================

Runs QA validation sessions to review implementation against
acceptance criteria.

Memory Integration:
- Retrieves past patterns, gotchas, and insights before QA session
- Saves QA findings (bugs, patterns, validation outcomes) after session
"""

from pathlib import Path

# Memory integration for cross-session learning
from agents.memory_manager import get_graphiti_context, save_session_memory
from claude_agent_sdk import ClaudeSDKClient
from claude_agent_sdk.types import ResultMessage
from debug import debug, debug_detailed, debug_error, debug_section, debug_success
from prompts_pkg import get_qa_reviewer_prompt
from security.tool_input_validator import get_safe_tool_input
from task_logger import (
    LogEntryType,
    LogPhase,
    get_task_logger,
)

from .criteria import get_qa_signoff_status, load_implementation_plan, save_implementation_plan

try:
    from core.usage_tracker import record_qa_result as _ut_record_qa
except ImportError:
    _ut_record_qa = None  # type: ignore[assignment]

import re
from datetime import datetime, timezone


def _extract_verdict_from_response(response_text: str) -> str | None:
    """
    Parse the QA agent's response text to extract APPROVED/REJECTED verdict.

    This is a fallback for when the agent doesn't properly update
    implementation_plan.json. We look for clear verdict signals in the
    agent's output text.

    Returns: "approved", "rejected", or None if inconclusive.
    """
    if not response_text:
        return None

    text_upper = response_text.upper()

    # Look for explicit sign-off patterns
    # Pattern: "SIGN-OFF: APPROVED" or "Sign-off: REJECTED"
    signoff_match = re.search(
        r"SIGN[\-\s]*OFF\s*:\s*(APPROVED|REJECTED)",
        text_upper,
    )
    if signoff_match:
        return signoff_match.group(1).lower()

    # Pattern: "Status: APPROVED" or "Status: REJECTED"
    status_match = re.search(
        r"STATUS\s*:\s*(APPROVED|REJECTED)",
        text_upper,
    )
    if status_match:
        return status_match.group(1).lower()

    # Pattern: "QA VALIDATION COMPLETE" + "APPROVED ✓" or "REJECTED ✗"
    if "QA VALIDATION COMPLETE" in text_upper:
        if "APPROVED" in text_upper:
            return "approved"
        if "REJECTED" in text_upper:
            return "rejected"

    return None


def _programmatic_qa_signoff(
    spec_dir: Path,
    verdict: str,
    qa_session: int,
) -> bool:
    """
    Programmatically write the qa_signoff to implementation_plan.json.

    This is a fallback when the agent produces a clear verdict in its
    response text but fails to update the file itself.

    Returns True if successfully written.
    """
    plan = load_implementation_plan(spec_dir)
    if not plan:
        return False

    now = datetime.now(timezone.utc).isoformat()

    if verdict == "approved":
        plan["qa_signoff"] = {
            "status": "approved",
            "timestamp": now,
            "qa_session": qa_session,
            "report_file": "qa_report.md",
            "tests_passed": {},
            "verified_by": "qa_agent (auto-extracted from response)",
        }
    elif verdict == "rejected":
        plan["qa_signoff"] = {
            "status": "rejected",
            "timestamp": now,
            "qa_session": qa_session,
            "issues_found": [],
            "fix_request_file": "QA_FIX_REQUEST.md",
        }
    else:
        return False

    return save_implementation_plan(spec_dir, plan)


# =============================================================================
# QA REVIEWER SESSION
# =============================================================================


async def run_qa_agent_session(
    client: ClaudeSDKClient,
    project_dir: Path,
    spec_dir: Path,
    qa_session: int,
    max_iterations: int,
    verbose: bool = False,
    previous_error: dict | None = None,
) -> tuple[str, str]:
    """
    Run a QA reviewer agent session.

    Args:
        client: Claude SDK client
        project_dir: Project root directory (for capability detection)
        spec_dir: Spec directory
        qa_session: QA iteration number
        max_iterations: Maximum number of QA iterations
        verbose: Whether to show detailed output
        previous_error: Error context from previous iteration for self-correction

    Returns:
        (status, response_text) where status is:
        - "approved" if QA approves
        - "rejected" if QA finds issues
        - "error" if an error occurred
    """
    debug_section("qa_reviewer", f"QA Reviewer Session {qa_session}")
    debug(
        "qa_reviewer",
        "Starting QA reviewer session",
        spec_dir=str(spec_dir),
        qa_session=qa_session,
        max_iterations=max_iterations,
    )

    print(f"\n{'=' * 70}")
    print(f"  QA REVIEWER SESSION {qa_session}")
    print("  Validating all acceptance criteria...")
    print(f"{'=' * 70}\n")

    # Get task logger for streaming markers
    task_logger = get_task_logger(spec_dir)
    current_tool = None
    message_count = 0
    tool_count = 0

    # Load QA prompt with dynamically-injected project-specific MCP tools
    # This includes Electron validation for Electron apps, Puppeteer for web, etc.
    prompt = get_qa_reviewer_prompt(spec_dir, project_dir)
    debug_detailed(
        "qa_reviewer",
        "Loaded QA reviewer prompt with project-specific tools",
        prompt_length=len(prompt),
        project_dir=str(project_dir),
    )

    # Retrieve memory context for QA (past patterns, gotchas, validation insights)
    qa_memory_context = await get_graphiti_context(
        spec_dir,
        project_dir,
        {
            "description": "QA validation and acceptance criteria review",
            "id": f"qa_reviewer_{qa_session}",
        },
    )
    if qa_memory_context:
        prompt += "\n\n" + qa_memory_context
        print("✓ Memory context loaded for QA reviewer")
        debug_success("qa_reviewer", "Graphiti memory context loaded for QA")

    # Add session context
    prompt += f"\n\n---\n\n**QA Session**: {qa_session}\n"
    prompt += f"**Max Iterations**: {max_iterations}\n"

    # Add error context for self-correction if previous iteration failed
    if previous_error:
        debug(
            "qa_reviewer",
            "Adding error context for self-correction",
            error_type=previous_error.get("error_type"),
            consecutive_errors=previous_error.get("consecutive_errors"),
        )
        prompt += f"""

---

## ⚠️ CRITICAL: PREVIOUS ITERATION FAILED - SELF-CORRECTION REQUIRED

The previous QA session failed with the following error:

**Error**: {previous_error.get("error_message", "Unknown error")}
**Consecutive Failures**: {previous_error.get("consecutive_errors", 1)}

### What Went Wrong

You did NOT update the `implementation_plan.json` file with the required `qa_signoff` object.

### Required Action

After completing your QA review, you MUST:

1. **Read the current implementation_plan.json**:
   ```bash
   cat {spec_dir}/implementation_plan.json
   ```

2. **Update it with your qa_signoff** by editing the JSON file to add/update the `qa_signoff` field:

   If APPROVED:
   ```json
   {{
     "qa_signoff": {{
       "status": "approved",
       "timestamp": "[current ISO timestamp]",
       "qa_session": {qa_session},
       "report_file": "qa_report.md",
       "tests_passed": {{"unit": "X/Y", "integration": "X/Y", "e2e": "X/Y"}},
       "verified_by": "qa_agent"
     }}
   }}
   ```

   If REJECTED:
   ```json
   {{
     "qa_signoff": {{
       "status": "rejected",
       "timestamp": "[current ISO timestamp]",
       "qa_session": {qa_session},
       "issues_found": [
         {{"type": "critical", "title": "[issue]", "location": "[file:line]", "fix_required": "[description]"}}
       ],
       "fix_request_file": "QA_FIX_REQUEST.md"
     }}
   }}
   ```

3. **Use the Edit tool or Write tool** to update the file. The file path is:
   `{spec_dir}/implementation_plan.json`

### FAILURE TO DO THIS WILL CAUSE ANOTHER ERROR

This is attempt {previous_error.get("consecutive_errors", 1) + 1}. If you fail to update implementation_plan.json again, the QA process will be escalated to human review.

---

"""
        print(
            f"\n⚠️  Retry with self-correction context (attempt {previous_error.get('consecutive_errors', 1) + 1})"
        )

    try:
        debug("qa_reviewer", "Sending query to Claude SDK...")
        await client.query(prompt)
        debug_success("qa_reviewer", "Query sent successfully")

        response_text = ""
        result_error: str | None = None
        debug("qa_reviewer", "Starting to receive response stream...")
        async for msg in client.receive_response():
            msg_type = type(msg).__name__
            message_count += 1
            debug_detailed(
                "qa_reviewer",
                f"Received message #{message_count}",
                msg_type=msg_type,
            )

            # Capture ResultMessage errors (e.g. rate limit, auth failure, crash)
            if isinstance(msg, ResultMessage):
                if msg.is_error:
                    result_error = msg.result or f"SDK error (subtype={msg.subtype})"
                    debug_error(
                        "qa_reviewer",
                        f"ResultMessage error: {result_error}",
                        num_turns=msg.num_turns,
                        duration_ms=msg.duration_ms,
                    )
                    print(f"\n❌ Claude session error: {result_error}")
                else:
                    debug(
                        "qa_reviewer",
                        "ResultMessage received (session complete)",
                        num_turns=msg.num_turns,
                        cost_usd=msg.total_cost_usd,
                        duration_ms=msg.duration_ms,
                    )
                continue

            if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                for block in msg.content:
                    block_type = type(block).__name__

                    if block_type == "TextBlock" and hasattr(block, "text"):
                        response_text += block.text
                        print(block.text, end="", flush=True)
                        # Log text to task logger (persist without double-printing)
                        if task_logger and block.text.strip():
                            task_logger.log(
                                block.text,
                                LogEntryType.TEXT,
                                LogPhase.VALIDATION,
                                print_to_console=False,
                            )
                    elif block_type == "ToolUseBlock" and hasattr(block, "name"):
                        tool_name = block.name
                        tool_input_display = None
                        tool_count += 1

                        # Safely extract tool input (handles None, non-dict, etc.)
                        inp = get_safe_tool_input(block)

                        # Extract tool input for display
                        if inp:
                            if "file_path" in inp:
                                fp = inp["file_path"]
                                if len(fp) > 50:
                                    fp = "..." + fp[-47:]
                                tool_input_display = fp
                            elif "pattern" in inp:
                                tool_input_display = f"pattern: {inp['pattern']}"

                        debug(
                            "qa_reviewer",
                            f"Tool call #{tool_count}: {tool_name}",
                            tool_input=tool_input_display,
                        )

                        # Log tool start (handles printing)
                        if task_logger:
                            task_logger.tool_start(
                                tool_name,
                                tool_input_display,
                                LogPhase.VALIDATION,
                                print_to_console=True,
                            )
                        else:
                            print(f"\n[QA Tool: {tool_name}]", flush=True)

                        if verbose and hasattr(block, "input"):
                            input_str = str(block.input)
                            if len(input_str) > 300:
                                print(f"   Input: {input_str[:300]}...", flush=True)
                            else:
                                print(f"   Input: {input_str}", flush=True)
                        current_tool = tool_name

            elif msg_type == "UserMessage" and hasattr(msg, "content"):
                for block in msg.content:
                    block_type = type(block).__name__

                    if block_type == "ToolResultBlock":
                        is_error = getattr(block, "is_error", False)
                        result_content = getattr(block, "content", "")

                        if is_error:
                            debug_error(
                                "qa_reviewer",
                                f"Tool error: {current_tool}",
                                error=str(result_content)[:200],
                            )
                            error_str = str(result_content)[:500]
                            print(f"   [Error] {error_str}", flush=True)
                            if task_logger and current_tool:
                                # Store full error in detail for expandable view
                                task_logger.tool_end(
                                    current_tool,
                                    success=False,
                                    result=error_str[:100],
                                    detail=str(result_content),
                                    phase=LogPhase.VALIDATION,
                                )
                        else:
                            debug_detailed(
                                "qa_reviewer",
                                f"Tool success: {current_tool}",
                                result_length=len(str(result_content)),
                            )
                            if verbose:
                                result_str = str(result_content)[:200]
                                print(f"   [Done] {result_str}", flush=True)
                            else:
                                print("   [Done]", flush=True)
                            if task_logger and current_tool:
                                # Store full result in detail for expandable view
                                detail_content = None
                                if current_tool in (
                                    "Read",
                                    "Grep",
                                    "Bash",
                                    "Edit",
                                    "Write",
                                ):
                                    result_str = str(result_content)
                                    if len(result_str) < 50000:
                                        detail_content = result_str
                                task_logger.tool_end(
                                    current_tool,
                                    success=True,
                                    detail=detail_content,
                                    phase=LogPhase.VALIDATION,
                                )

                        current_tool = None

        print("\n" + "-" * 70 + "\n")

        # Check the QA result from implementation_plan.json
        status = get_qa_signoff_status(spec_dir)
        debug(
            "qa_reviewer",
            "QA session completed",
            message_count=message_count,
            tool_count=tool_count,
            response_length=len(response_text),
            qa_status=status.get("status") if status else "unknown",
        )

        # Save QA session insights to memory
        qa_discoveries = {
            "files_understood": {},
            "patterns_found": [],
            "gotchas_encountered": [],
        }

        if status and status.get("status") == "approved":
            debug_success("qa_reviewer", "QA APPROVED")
            if _ut_record_qa is not None:
                try:
                    _ut_record_qa(project_dir, spec_dir.name, passed=True, score=100.0)
                except Exception:
                    pass
            qa_discoveries["patterns_found"].append(
                f"QA session {qa_session}: All acceptance criteria validated successfully"
            )
            # Save successful QA session to memory
            await save_session_memory(
                spec_dir=spec_dir,
                project_dir=project_dir,
                subtask_id=f"qa_reviewer_{qa_session}",
                session_num=qa_session,
                success=True,
                subtasks_completed=[f"qa_reviewer_{qa_session}"],
                discoveries=qa_discoveries,
            )
            return "approved", response_text
        elif status and status.get("status") == "rejected":
            debug_error("qa_reviewer", "QA REJECTED")
            if _ut_record_qa is not None:
                try:
                    _ut_record_qa(project_dir, spec_dir.name, passed=False, score=0.0)
                except Exception:
                    pass
            # Extract issues found for memory
            issues = status.get("issues_found", [])
            for issue in issues:
                qa_discoveries["gotchas_encountered"].append(
                    f"QA Issue ({issue.get('type', 'unknown')}): {issue.get('title', 'No title')} at {issue.get('location', 'unknown')}"
                )
            # Save rejected QA session to memory (learning from failures)
            await save_session_memory(
                spec_dir=spec_dir,
                project_dir=project_dir,
                subtask_id=f"qa_reviewer_{qa_session}",
                session_num=qa_session,
                success=False,
                subtasks_completed=[],
                discoveries=qa_discoveries,
            )
            return "rejected", response_text
        elif status and status.get("status") not in ("approved", "rejected"):
            # Non-standard status (e.g. "awaiting_manual_verification") — treat as human escalation
            non_standard = status.get("status", "unknown")
            debug_warning(
                "qa_reviewer",
                f"QA agent wrote non-standard status: {non_standard} — treating as human escalation",
            )
            print(f"\n⚠️  QA agent set non-standard status: {non_standard}")
            print("Treating as human escalation (manual verification required).")
            return "human_escalation", response_text
        else:
            # Agent didn't update the file - try to extract verdict from response
            extracted_verdict = _extract_verdict_from_response(response_text)

            if extracted_verdict:
                debug(
                    "qa_reviewer",
                    f"Extracted verdict from response: {extracted_verdict}",
                    message_count=message_count,
                    tool_count=tool_count,
                )
                print(
                    f"\n⚠️  Agent didn't update implementation_plan.json, "
                    f"but verdict detected: {extracted_verdict.upper()}"
                )

                # Programmatically write the qa_signoff
                if _programmatic_qa_signoff(spec_dir, extracted_verdict, qa_session):
                    debug_success(
                        "qa_reviewer",
                        f"Programmatically wrote qa_signoff: {extracted_verdict}",
                    )
                    print(
                        f"✅ Programmatically updated implementation_plan.json "
                        f"with status: {extracted_verdict}"
                    )
                    return extracted_verdict, response_text
                else:
                    debug_error(
                        "qa_reviewer",
                        "Failed to programmatically write qa_signoff",
                    )

            # Agent didn't update the status and no clear verdict in response
            debug_error(
                "qa_reviewer",
                "QA agent did not update implementation_plan.json",
                message_count=message_count,
                tool_count=tool_count,
                response_preview=response_text[:500] if response_text else "empty",
            )

            # Build informative error message for feedback loop
            error_details = []
            if result_error:
                # SDK-level error (rate limit, auth failure, subprocess crash)
                return "error", f"Claude session error: {result_error}"
            if message_count == 0:
                error_details.append("No messages received from agent")
            if tool_count == 0:
                error_details.append("No tools were used by agent")
            if not response_text:
                error_details.append("Agent produced no output")

            error_msg = "QA agent did not update implementation_plan.json"
            if error_details:
                error_msg += f" ({'; '.join(error_details)})"

            return "error", error_msg

    except Exception as e:
        debug_error(
            "qa_reviewer",
            f"QA session exception: {e}",
            exception_type=type(e).__name__,
        )
        print(f"Error during QA session: {e}")
        if task_logger:
            task_logger.log_error(f"QA session error: {e}", LogPhase.VALIDATION)
        return "error", str(e)
