"""
Agent Runner
============

Handles the execution of AI agents for the spec creation pipeline.
"""

from pathlib import Path
from typing import Optional

# Configure safe encoding before any output (fixes Windows encoding errors)
from ui.capabilities import configure_safe_encoding

configure_safe_encoding()

from debug import debug, debug_detailed, debug_error, debug_section, debug_success
from security.tool_input_validator import get_safe_tool_input
from task_logger import (
    LogEntryType,
    LogPhase,
    TaskLogger,
)

# Lazy import create_client to avoid circular import with core.client
# The import chain: spec.pipeline -> agent_runner -> core.client -> agents.tools_pkg -> spec.validate_pkg
# By deferring the import, we break the circular dependency.


class AgentRunner:
    """Manages agent execution with logging and error handling."""

    def __init__(
        self,
        project_dir: Path,
        spec_dir: Path,
        model: str,
        task_logger: Optional[TaskLogger] = None,
    ):
        """Initialize the agent runner.

        Args:
            project_dir: The project root directory
            spec_dir: The spec directory
            model: The model to use for agent execution
            task_logger: Optional task logger for tracking progress
        """
        self.project_dir = project_dir
        self.spec_dir = spec_dir
        self.model = model
        self.task_logger = task_logger

    async def run_agent(
        self,
        prompt_file: str,
        additional_context: str = "",
        interactive: bool = False,
        thinking_budget: Optional[int] = None,
        prior_phase_summaries: Optional[str] = None,
    ) -> tuple[bool, str]:
        """Run an agent with the given prompt.

        Args:
            prompt_file: The prompt file to use (relative to prompts directory)
            additional_context: Additional context to add to the prompt
            interactive: Whether to run in interactive mode
            thinking_budget: Token budget for extended thinking (None = disabled)
            prior_phase_summaries: Summaries from previous phases for context

        Returns:
            Tuple of (success, response_text)
        """
        debug_section("agent_runner", f"Spec Agent - {prompt_file}")
        debug(
            "agent_runner",
            "Running spec creation agent",
            prompt_file=prompt_file,
            spec_dir=str(self.spec_dir),
            model=self.model,
            interactive=interactive,
        )

        prompt_path = Path(__file__).parent.parent.parent / "prompts" / prompt_file

        if not prompt_path.exists():
            debug_error("agent_runner", f"Prompt file not found: {prompt_path}")
            return False, f"Prompt not found: {prompt_path}"

        # Load prompt
        prompt = prompt_path.read_text(encoding="utf-8")
        debug_detailed(
            "agent_runner",
            "Loaded prompt file",
            prompt_length=len(prompt),
        )

        # Add context
        prompt += f"\n\n---\n\n**Spec Directory**: {self.spec_dir}\n"
        prompt += f"**Project Directory**: {self.project_dir}\n"

        # Add summaries from previous phases (compaction)
        if prior_phase_summaries:
            prompt += f"\n{prior_phase_summaries}\n"
            debug_detailed(
                "agent_runner",
                "Added prior phase summaries",
                summaries_length=len(prior_phase_summaries),
            )

        if additional_context:
            prompt += f"\n{additional_context}\n"
            debug_detailed(
                "agent_runner",
                "Added additional context",
                context_length=len(additional_context),
            )

        # Create client with thinking budget
        # Log model/CWD prominently so issues are visible in task console
        debug(
            "agent_runner",
            "Creating agent client",
            model=self.model,
            thinking_budget=thinking_budget,
            project_dir=str(self.project_dir),
            project_dir_exists=self.project_dir.exists(),
            spec_dir=str(self.spec_dir),
            spec_dir_exists=self.spec_dir.exists(),
        )
        if self.task_logger:
            self.task_logger.log(
                f"Agent config: model={self.model}, thinking={thinking_budget}, "
                f"CWD exists={self.project_dir.exists()}",
                LogEntryType.TEXT,
                LogPhase.PLANNING,
                print_to_console=True,
            )

        # Lazy import to avoid circular import with core.client
        from core.client import create_agent_client

        client = create_agent_client(
            project_dir=self.project_dir,
            spec_dir=self.spec_dir,
            model=self.model,
            agent_type="spec_writer",  # Use spec_writer type for spec creation
            max_thinking_tokens=thinking_budget,
        )

        # Debug: Log which provider is being used
        try:
            from provider_api import get_selected_provider
            selected_provider = get_selected_provider()
            debug("agent_runner", f"Selected provider from IPC: {selected_provider}")
        except Exception as e:
            debug("agent_runner", f"Could not get selected provider: {e}")
        
        # Debug: Check if input files exist for spec_writer
        if prompt_file == "spec_writer.md":
            input_files = ["project_index.json", "requirements.json", "context.json"]
            for file_name in input_files:
                file_path = self.spec_dir / file_name
                exists = file_path.exists()
                debug("agent_runner", f"Input file {file_name} exists: {exists}")
                if exists:
                    size = file_path.stat().st_size
                    debug("agent_runner", f"Input file {file_name} size: {size} bytes")

        current_tool = None
        message_count = 0
        tool_count = 0
        hit_usage_cap = False  # Track if we received a rate/usage limit event from SDK

        try:
            async with client:
                debug("agent_runner", "Sending query to Claude SDK...")
                await client.query(prompt)
                debug_success("agent_runner", "Query sent successfully")

                response_text = ""
                debug("agent_runner", "Starting to receive response stream...")
                async for msg in client.receive_response():
                    msg_type = type(msg).__name__
                    message_count += 1
                    debug_detailed(
                        "agent_runner",
                        f"Received message #{message_count}",
                        msg_type=msg_type,
                    )

                    if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                        for block in msg.content:
                            block_type = type(block).__name__
                            if block_type == "TextBlock" and hasattr(block, "text"):
                                response_text += block.text
                                print(block.text, end="", flush=True)
                                if self.task_logger and block.text.strip():
                                    self.task_logger.log(
                                        block.text,
                                        LogEntryType.TEXT,
                                        LogPhase.PLANNING,
                                        print_to_console=False,
                                    )
                            elif block_type == "ToolUseBlock" and hasattr(
                                block, "name"
                            ):
                                tool_name = block.name
                                tool_count += 1

                                # Safely extract tool input (handles None, non-dict, etc.)
                                inp = get_safe_tool_input(block)
                                tool_input_display = self._extract_tool_input_display(
                                    inp
                                )

                                debug(
                                    "agent_runner",
                                    f"Tool call #{tool_count}: {tool_name}",
                                    tool_input=tool_input_display,
                                )

                                if self.task_logger:
                                    self.task_logger.tool_start(
                                        tool_name,
                                        tool_input_display,
                                        LogPhase.PLANNING,
                                        print_to_console=True,
                                    )
                                else:
                                    print(f"\n[Tool: {tool_name}]", flush=True)
                                current_tool = tool_name

                    elif msg_type == "UserMessage" and hasattr(msg, "content"):
                        for block in msg.content:
                            block_type = type(block).__name__
                            if block_type == "ToolResultBlock":
                                is_error = getattr(block, "is_error", False)
                                result_content = getattr(block, "content", "")
                                if is_error:
                                    debug_error(
                                        "agent_runner",
                                        f"Tool error: {current_tool}",
                                        error=str(result_content)[:200],
                                    )
                                else:
                                    debug_detailed(
                                        "agent_runner",
                                        f"Tool success: {current_tool}",
                                        result_length=len(str(result_content)),
                                    )
                                if self.task_logger and current_tool:
                                    detail_content = self._get_tool_detail_content(
                                        current_tool, result_content
                                    )
                                    self.task_logger.tool_end(
                                        current_tool,
                                        success=not is_error,
                                        detail=detail_content,
                                        phase=LogPhase.PLANNING,
                                    )
                                current_tool = None

                    else:
                        # Handle unknown/special message types from the SDK.
                        # The Claude SDK may send rate_limit_event, error, or other
                        # non-standard message types that we need to detect.
                        debug(
                            "agent_runner",
                            f"Received non-standard message type: {msg_type}",
                            msg_attrs=str(dir(msg))[:200],
                        )

                        # Detect rate/usage limit events from SDK
                        # The SDK sends a message with type name containing "rate_limit"
                        # when the account has hit its usage cap.
                        if "rate_limit" in msg_type.lower() or "limit" in msg_type.lower():
                            hit_usage_cap = True
                            # Extract any details from the message for logging
                            limit_detail = ""
                            for attr in ("message", "error", "detail", "retry_after", "reset_at"):
                                val = getattr(msg, attr, None)
                                if val is not None:
                                    limit_detail += f" {attr}={val}"

                            # Use "hit your limit" phrasing so frontend rate-limit-detector
                            # catches it via the /hit your limit/i pattern.
                            cap_msg = f"You've hit your limit — Claude SDK returned {msg_type}.{limit_detail}"
                            debug_error("agent_runner", cap_msg)
                            print(f"\n⚠️  {cap_msg}", flush=True)
                            if self.task_logger:
                                self.task_logger.log_error(cap_msg, LogPhase.PLANNING)

                print()

                # If we received a usage cap event, fail immediately with a clear message
                if hit_usage_cap:
                    cap_error = (
                        f"You've hit your limit — the Claude SDK returned a usage cap event. "
                        f"Please wait for the limit to reset or switch to a different Claude profile."
                    )
                    debug_error("agent_runner", cap_error)
                    if self.task_logger:
                        self.task_logger.log_error(cap_error, LogPhase.PLANNING)
                    return False, cap_error

                # Detect empty sessions: if the agent didn't call any tools
                # and produced no meaningful output, something went wrong
                # (e.g., auth failure, invalid CWD, prompt too long).
                if tool_count == 0 and len(response_text.strip()) < 50:
                    debug_error(
                        "agent_runner",
                        "Agent session completed but produced no tool calls and minimal output",
                        message_count=message_count,
                        tool_count=tool_count,
                        response_length=len(response_text),
                    )
                    # IMPORTANT: Do NOT include the words "rate limit" in the error message!
                    # The frontend rate-limit-detector.ts pattern-matches on /rate\s*limit/i
                    # in the process output, which causes a false positive detection.
                    if self.task_logger:
                        self.task_logger.log_error(
                            f"Agent session empty: 0 tool calls, {len(response_text)}b output "
                            f"— possible causes: usage cap reached, auth failure, invalid working directory, "
                            f"or model unavailable. Check Claude profile settings.",
                            LogPhase.PLANNING,
                        )
                    return False, (
                        f"Agent session empty (0 tools, {len(response_text)}b output). "
                        f"Possible causes: usage cap, auth failure, invalid CWD, model unavailable. "
                        f"Response: {response_text[:200]}"
                    )

                debug_success(
                    "agent_runner",
                    "Agent session completed successfully",
                    message_count=message_count,
                    tool_count=tool_count,
                    response_length=len(response_text),
                )
                return True, response_text

        except Exception as e:
            error_str = str(e).lower()
            debug_error(
                "agent_runner",
                f"Agent session error: {e}",
                exception_type=type(e).__name__,
            )

            # Detect rate/usage limit exceptions from the SDK.
            # The Claude Agent SDK may raise exceptions like:
            #   "Unknown message type: rate_limit_event"
            # when the account has hit its usage cap. We need to surface
            # this clearly so the frontend rate-limit-detector picks it up.
            if "rate_limit" in error_str or "limit_event" in error_str:
                # Use "hit your limit" phrasing so frontend rate-limit-detector.ts
                # matches via /hit your limit/i pattern and triggers proper UI.
                cap_msg = (
                    f"You've hit your limit — Claude SDK error: {e}. "
                    f"Please wait for the limit to reset or switch to a different Claude profile."
                )
                debug_error("agent_runner", cap_msg)
                print(f"\n⚠️  {cap_msg}", flush=True)
                if self.task_logger:
                    self.task_logger.log_error(cap_msg, LogPhase.PLANNING)
                return False, cap_msg

            if self.task_logger:
                self.task_logger.log_error(f"Agent error: {e}", LogPhase.PLANNING)
            return False, str(e)

    @staticmethod
    def _extract_tool_input_display(inp: dict) -> Optional[str]:
        """Extract meaningful tool input for display.

        Args:
            inp: The tool input dictionary

        Returns:
            A formatted string for display, or None
        """
        if not isinstance(inp, dict):
            return None

        if "pattern" in inp:
            return f"pattern: {inp['pattern']}"
        elif "file_path" in inp:
            fp = inp["file_path"]
            if len(fp) > 50:
                fp = "..." + fp[-47:]
            return fp
        elif "command" in inp:
            cmd = inp["command"]
            if len(cmd) > 50:
                cmd = cmd[:47] + "..."
            return cmd
        elif "path" in inp:
            return inp["path"]

        return None

    @staticmethod
    def _get_tool_detail_content(tool_name: str, result_content: str) -> Optional[str]:
        """Get detail content for specific tools.

        Args:
            tool_name: The name of the tool
            result_content: The result content from the tool

        Returns:
            Detail content if relevant, otherwise None
        """
        if tool_name not in ("Read", "Grep", "Bash", "Edit", "Write"):
            return None

        result_str = str(result_content)
        if len(result_str) < 50000:
            return result_str

        return None