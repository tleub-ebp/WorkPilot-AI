"""
Abstract Agent Client Interface
================================

Provides a provider-agnostic abstraction layer over agent execution backends.
This enables transparent switching between Claude Agent SDK and GitHub Copilot
without altering the Kanban task processing pipeline.

Architecture:
    AgentClient (ABC)
    ├── ClaudeAgentClient  — wraps claude_agent_sdk.ClaudeSDKClient
    └── CopilotAgentClient — uses GitHub Copilot Models API (OpenAI-compatible)

Usage:
    from core.agent_client import create_agent_client

    client = create_agent_client(
        provider="claude",  # or "copilot"
        project_dir=project_dir,
        spec_dir=spec_dir,
        model=model,
        agent_type="coder",
    )

    async with client:
        await client.query("Implement the feature")
        async for msg in client.receive_response():
            ...
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

CONTENT_TYPE_JSON = "application/json"

# =============================================================================
# Message Types for provider-agnostic stream processing
# =============================================================================


class MessageRole(str, Enum):
    """Role of a message in the agent conversation."""

    ASSISTANT = "assistant"
    USER = "user"
    SYSTEM = "system"


class ContentBlockType(str, Enum):
    """Type of content block within a message."""

    TEXT = "text"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
    THINKING = "thinking"
    STRUCTURED_OUTPUT = "structured_output"
    RESULT = "result"


@dataclass
class ContentBlock:
    """A single content block within an agent message.

    This normalizes the various block types from different providers
    into a common structure.
    """

    type: ContentBlockType
    text: str | None = None
    # Tool use fields
    tool_name: str | None = None
    tool_id: str | None = None
    tool_input: dict[str, Any] | None = None
    # Tool result fields
    tool_use_id: str | None = None
    is_error: bool = False
    result_content: Any = None
    # Structured output
    structured_output: dict[str, Any] | None = None
    # Result message fields
    subtype: str | None = None


@dataclass
class AgentMessage:
    """A normalized message from the agent stream.

    Wraps messages from any provider (Claude SDK, Copilot API) into
    a common format that process_agent_stream() can handle uniformly.
    """

    role: MessageRole
    content: list[ContentBlock] = field(default_factory=list)
    # Pass through the raw provider message for backward compatibility
    raw: Any = None

    @property
    def type_name(self) -> str:
        """Return a type name compatible with existing SDK message type checks."""
        if self.raw is not None:
            return type(self.raw).__name__
        return f"{self.role.value.capitalize()}Message"


@dataclass
class SubagentDefinition:
    """Provider-agnostic definition of a sub-agent.

    For Claude SDK, this maps to claude_agent_sdk.AgentDefinition.
    For Copilot, this maps to a parallel API session configuration.
    """

    description: str
    prompt: str
    tools: list[str] = field(default_factory=list)
    model: str = "inherit"


# =============================================================================
# Abstract Agent Client
# =============================================================================


class AgentClient(ABC):
    """Abstract interface for an agent execution client.

    Implementations must support:
    - Sending queries to the agent
    - Receiving streamed responses as AgentMessage objects
    - Async context manager protocol for resource lifecycle
    - Declaring sub-agent support capability
    """

    @abstractmethod
    async def query(self, prompt: str) -> None:
        """Send a prompt/query to the agent.

        Args:
            prompt: The user message to send to the agent.
        """
        ...

    @abstractmethod
    async def receive_response(self) -> AsyncIterator[AgentMessage]:
        """Receive the agent's response as a stream of messages.

        Yields:
            AgentMessage instances normalized from the provider's native format.
        """
        ...

    @abstractmethod
    def supports_subagents(self) -> bool:
        """Whether this client supports native sub-agent execution.

        Returns:
            True if the provider supports parallel sub-agent execution
            (e.g., Claude SDK Task tool), False otherwise.
        """
        ...

    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider identifier (e.g., 'claude', 'copilot')."""
        ...

    # Async context manager protocol
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


# =============================================================================
# Claude Agent Client — wraps ClaudeSDKClient
# =============================================================================


class ClaudeAgentClient(AgentClient):
    """Agent client backed by Claude Agent SDK (ClaudeSDKClient).

    This is a thin wrapper that adapts ClaudeSDKClient messages into
    the AgentMessage format. For backward compatibility, the raw SDK
    messages are preserved in AgentMessage.raw so that existing
    stream processors (process_sdk_stream) can still inspect them
    with hasattr()/getattr() patterns.
    """

    def __init__(self, sdk_client: Any):
        """
        Args:
            sdk_client: A configured ClaudeSDKClient instance.
        """
        self._client = sdk_client

    async def query(self, prompt: str) -> None:
        await self._client.query(prompt)

    async def receive_response(self) -> AsyncIterator[AgentMessage]:
        """Yield AgentMessages wrapping raw SDK messages.

        The raw SDK message is preserved in AgentMessage.raw so that
        existing code using hasattr(msg, 'content') patterns continues
        to work during the migration period.
        """
        async for raw_msg in self._client.receive_response():
            yield self._wrap_sdk_message(raw_msg)

    def _wrap_sdk_message(self, raw_msg: Any) -> AgentMessage:
        """Convert a raw Claude SDK message to AgentMessage.

        For backward compatibility, the raw message is attached so that
        existing stream processing code can still access SDK-specific
        attributes (e.g., msg.raw.content, msg.raw.structured_output).
        """
        msg_type = type(raw_msg).__name__

        # Determine role from SDK message type
        if msg_type == "AssistantMessage":
            role = MessageRole.ASSISTANT
        elif msg_type == "UserMessage":
            role = MessageRole.USER
        elif msg_type == "SystemMessage":
            role = MessageRole.SYSTEM
        else:
            # ThinkingBlock, ToolUseBlock, ToolResultBlock, ResultMessage
            # are content-level objects, not message-level. Wrap them
            # as system messages with appropriate content blocks.
            role = MessageRole.SYSTEM

        blocks = self._extract_content_blocks(raw_msg, msg_type)
        return AgentMessage(role=role, content=blocks, raw=raw_msg)

    def _extract_content_blocks(
        self, raw_msg: Any, msg_type: str
    ) -> list[ContentBlock]:
        """Extract ContentBlocks from a raw SDK message."""
        blocks: list[ContentBlock] = []

        # ThinkingBlock
        if msg_type == "ThinkingBlock" or (
            hasattr(raw_msg, "type") and getattr(raw_msg, "type", "") == "thinking"
        ):
            thinking_text = getattr(raw_msg, "thinking", "") or getattr(
                raw_msg, "text", ""
            )
            if thinking_text:
                blocks.append(ContentBlock(type=ContentBlockType.THINKING, text=thinking_text))
            return blocks

        # ToolUseBlock (top-level)
        if msg_type == "ToolUseBlock" or (
            hasattr(raw_msg, "type") and getattr(raw_msg, "type", "") == "tool_use"
        ):
            blocks.append(
                ContentBlock(
                    type=ContentBlockType.TOOL_USE,
                    tool_name=getattr(raw_msg, "name", ""),
                    tool_id=getattr(raw_msg, "id", "unknown"),
                    tool_input=getattr(raw_msg, "input", {}),
                )
            )
            return blocks

        # ToolResultBlock (top-level)
        if msg_type == "ToolResultBlock" or (
            hasattr(raw_msg, "type") and getattr(raw_msg, "type", "") == "tool_result"
        ):
            blocks.append(
                ContentBlock(
                    type=ContentBlockType.TOOL_RESULT,
                    tool_use_id=getattr(raw_msg, "tool_use_id", "unknown"),
                    is_error=getattr(raw_msg, "is_error", False),
                    result_content=getattr(raw_msg, "content", ""),
                )
            )
            return blocks

        # ResultMessage
        if msg_type == "ResultMessage" or (
            hasattr(raw_msg, "type") and getattr(raw_msg, "type", "") == "result"
        ):
            block = ContentBlock(
                type=ContentBlockType.RESULT,
                subtype=getattr(raw_msg, "subtype", None),
            )
            if hasattr(raw_msg, "structured_output") and raw_msg.structured_output:
                block.structured_output = raw_msg.structured_output
            blocks.append(block)
            return blocks

        # AssistantMessage / UserMessage with .content list
        if hasattr(raw_msg, "content"):
            for item in raw_msg.content:
                item_type = type(item).__name__
                if item_type == "TextBlock" and hasattr(item, "text"):
                    blocks.append(ContentBlock(type=ContentBlockType.TEXT, text=item.text))
                elif item_type == "ToolUseBlock" or getattr(item, "type", "") == "tool_use":
                    blocks.append(
                        ContentBlock(
                            type=ContentBlockType.TOOL_USE,
                            tool_name=getattr(item, "name", ""),
                            tool_id=getattr(item, "id", "unknown"),
                            tool_input=getattr(item, "input", {}),
                        )
                    )
                elif item_type == "ToolResultBlock" or getattr(item, "type", "") == "tool_result":
                    result_content = getattr(item, "content", "")
                    if isinstance(result_content, list):
                        result_content = " ".join(
                            str(getattr(c, "text", c)) for c in result_content
                        )
                    blocks.append(
                        ContentBlock(
                            type=ContentBlockType.TOOL_RESULT,
                            tool_use_id=getattr(item, "tool_use_id", "unknown"),
                            is_error=getattr(item, "is_error", False),
                            result_content=result_content,
                        )
                    )

        # Structured output on any message
        if hasattr(raw_msg, "structured_output") and raw_msg.structured_output:
            blocks.append(
                ContentBlock(
                    type=ContentBlockType.STRUCTURED_OUTPUT,
                    structured_output=raw_msg.structured_output,
                )
            )

        return blocks

    def supports_subagents(self) -> bool:
        return True

    def provider_name(self) -> str:
        return "claude"

    async def __aenter__(self):
        if hasattr(self._client, "__aenter__"):
            await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self._client, "__aexit__"):
            await self._client.__aexit__(exc_type, exc_val, exc_tb)

    @property
    def inner(self) -> Any:
        """Access the underlying ClaudeSDKClient for backward-compatible code paths."""
        return self._client


# =============================================================================
# Copilot Agent Client — uses GitHub Copilot Models API
# =============================================================================


class CopilotAgentClient(AgentClient):
    """Agent client backed by GitHub Copilot Models API.

    Uses the OpenAI-compatible endpoint at:
        https://api.github.com/copilot/chat/completions

    This enables:
    - Tool-use loops (function calling)
    - Parallel sub-agent simulation via concurrent API sessions
    - Streaming responses

    Authentication:
    - Uses GITHUB_TOKEN environment variable
    - Token must have Copilot access scope

    Sub-agent Strategy:
    When sub-agents are defined, CopilotAgentClient spawns parallel
    asyncio tasks — each making its own chat/completions call with
    the sub-agent's specialized system prompt. Results are collected
    and injected back into the orchestrator's context as tool results.
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        system_prompt: str | None = None,
        allowed_tools: list[str] | None = None,
        agents: dict[str, SubagentDefinition] | None = None,
        cwd: str | None = None,
        max_turns: int = 50,
        github_token: str | None = None,
    ):
        import os

        self.model = model
        self.system_prompt = system_prompt
        self.allowed_tools = allowed_tools or []
        self.agents = agents or {}
        self.cwd = cwd
        self.max_turns = max_turns
        self.github_token = github_token or os.environ.get("GITHUB_TOKEN", "")
        self._api_base = "https://api.github.com/copilot/chat/completions"
        self._messages: list[dict[str, Any]] = []
        self._pending_query: str | None = None
        self._http_client: Any = None

    def _get_http_client(self):
        """Lazy-init an aiohttp ClientSession."""
        if self._http_client is None:
            try:
                import aiohttp

                self._http_client = aiohttp.ClientSession(
                    headers={
                        "Authorization": f"Bearer {self.github_token}",
                        "Content-Type": CONTENT_TYPE_JSON,
                        "Accept": CONTENT_TYPE_JSON,
                    }
                )
            except ImportError:
                raise ImportError(
                    "aiohttp is required for CopilotAgentClient. "
                    "Install it with: pip install aiohttp"
                )
        return self._http_client

    async def query(self, prompt: str) -> None:
        """Queue a prompt for the next receive_response() call."""
        self._pending_query = prompt

    async def receive_response(self) -> AsyncIterator[AgentMessage]:
        """Execute the queued prompt against the Copilot Models API.

        Implements a tool-use loop similar to LiteLLMRuntime:
        1. Send messages to API
        2. If response contains tool_calls, yield tool-use blocks
        3. Wait for tool results (not handled here — caller must inject)
        4. Repeat until no more tool calls or max_turns reached

        For the initial implementation, this performs a single API call
        and yields the response. Tool-use loops will be implemented
        in Step 13.
        """
        if not self._pending_query:
            return

        # Build messages
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": self._pending_query})
        self._pending_query = None

        try:
            session = self._get_http_client()
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
            }

            async with session.post(self._api_base, json=payload) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    yield AgentMessage(
                        role=MessageRole.SYSTEM,
                        content=[
                            ContentBlock(
                                type=ContentBlockType.TEXT,
                                text=f"Copilot API error ({resp.status}): {error_text}",
                            )
                        ],
                    )
                    return

                data = await resp.json()

            # Parse response
            choices = data.get("choices", [])
            if not choices:
                return

            choice = choices[0]
            message = choice.get("message", {})
            content = message.get("content", "")

            # Check for tool calls
            tool_calls = message.get("tool_calls", [])

            blocks: list[ContentBlock] = []

            if content:
                blocks.append(ContentBlock(type=ContentBlockType.TEXT, text=content))

            for tc in tool_calls:
                import json

                func = tc.get("function", {})
                try:
                    args = json.loads(func.get("arguments", "{}"))
                except (json.JSONDecodeError, TypeError):
                    args = {}

                blocks.append(
                    ContentBlock(
                        type=ContentBlockType.TOOL_USE,
                        tool_name=func.get("name", ""),
                        tool_id=tc.get("id", "unknown"),
                        tool_input=args,
                    )
                )

            yield AgentMessage(role=MessageRole.ASSISTANT, content=blocks)

            # If there were tool calls, the caller is expected to handle
            # tool execution and feed results back. For sub-agents,
            # see run_subagents().

        except Exception as e:
            logger.error(f"[CopilotAgentClient] API error: {e}")
            yield AgentMessage(
                role=MessageRole.SYSTEM,
                content=[
                    ContentBlock(
                        type=ContentBlockType.TEXT,
                        text=f"Copilot API error: {e}",
                    )
                ],
            )

    async def run_subagents(
        self,
        agents: dict[str, SubagentDefinition],
        context_prompt: str,
    ) -> dict[str, str]:
        """Run sub-agents in parallel using the Copilot Models API.

        Each sub-agent gets its own API call with its specialized
        system prompt and the shared context. Results are returned
        as a dict mapping agent_name -> response_text.

        Args:
            agents: Dict of agent_name -> SubagentDefinition
            context_prompt: Shared context/prompt for all agents

        Returns:
            Dict mapping agent_name -> agent response text
        """
        import asyncio

        async def _run_one(name: str, defn: SubagentDefinition) -> tuple[str, str]:
            """Run a single sub-agent API call."""
            messages = [
                {"role": "system", "content": defn.prompt},
                {"role": "user", "content": context_prompt},
            ]

            session = self._get_http_client()
            payload = {
                "model": defn.model if defn.model != "inherit" else self.model,
                "messages": messages,
                "stream": False,
            }

            try:
                async with session.post(self._api_base, json=payload) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        return (name, f"Error ({resp.status}): {error_text}")
                    data = await resp.json()

                choices = data.get("choices", [])
                if choices:
                    return (name, choices[0].get("message", {}).get("content", ""))
                return (name, "")
            except Exception as e:
                logger.error(f"[CopilotSubagent:{name}] Error: {e}")
                return (name, f"Error: {e}")

        # Run all sub-agents in parallel
        tasks = [_run_one(name, defn) for name, defn in agents.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output: dict[str, str] = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"[CopilotSubagent] Task failed: {result}")
                continue
            name, text = result
            output[name] = text

        return output

    def supports_subagents(self) -> bool:
        return True

    def provider_name(self) -> str:
        return "copilot"

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._http_client is not None:
            await self._http_client.close()
            self._http_client = None


# =============================================================================
# Windsurf Agent Client — dual-mode (gRPC proxy + REST fallback)
# =============================================================================


class WindsurfAgentClient(AgentClient):
    """Agent client backed by Windsurf/Codeium with dual-mode support.

    Mode 1 (preferred): gRPC to local Windsurf IDE language server.
        Requires Windsurf IDE to be running and authenticated.
        Uses the approach from opencode-windsurf-auth.

    Mode 2 (fallback): OpenAI-compatible REST API to server.codeium.com.
        Uses stored API key or OAuth token. Works without the IDE.

    Authentication:
    - Mode 1: CSRF token + API key from running language server process
    - Mode 2: WINDSURF_API_KEY or WINDSURF_OAUTH_TOKEN environment variable
    """

    def __init__(
        self,
        model: str = "claude-4-sonnet",
        system_prompt: str | None = None,
        max_turns: int = 50,
    ):
        import os as _os

        self.model = model
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self._credentials: Any = None  # WindsurfCredentials (Mode 1)
        self._use_local_grpc = False
        self._api_key: str | None = None  # For Mode 2
        self._pending_query: str | None = None
        self._http_client: Any = None
        self._rest_base_url = _os.environ.get(
            "WINDSURF_BASE_URL", "https://server.codeium.com/api/v1"
        )

    async def __aenter__(self):
        import os as _os

        from integrations.windsurf_proxy.auth import (
            discover_credentials,
            is_windsurf_running,
        )

        if is_windsurf_running():
            try:
                self._credentials = discover_credentials()
                self._use_local_grpc = True
                logger.info(
                    f"[WindsurfAgent] Mode 1: gRPC proxy to localhost:{self._credentials.port} "
                    f"(model={self.model})"
                )
                return self
            except Exception as e:
                logger.warning(f"[WindsurfAgent] gRPC discovery failed, trying REST fallback: {e}")

        # Mode 2: REST fallback
        self._api_key = (
            _os.environ.get("WINDSURF_API_KEY")
            or _os.environ.get("WINDSURF_OAUTH_TOKEN")
            or _os.environ.get("CODEIUM_API_KEY")
        )

        # Fallback: try reading API key / SSO token from Windsurf's local state.vscdb
        # This covers enterprise SSO users whose token isn't in env vars
        if not self._api_key:
            try:
                from integrations.windsurf_proxy.auth import get_api_key
                self._api_key = get_api_key()
                logger.debug("[WindsurfAgent] Found API key/SSO token from local state.vscdb")
            except Exception as e:
                logger.debug(f"[WindsurfAgent] Local state.vscdb key lookup failed: {e}")

        if self._api_key:
            self._use_local_grpc = False
            logger.info(
                f"[WindsurfAgent] Mode 2: REST API to {self._rest_base_url} "
                f"(model={self.model})"
            )
            return self

        raise RuntimeError(
            "Windsurf IDE not running and no WINDSURF_API_KEY available. "
            "Please either start Windsurf IDE (and log in via SSO) or set "
            "WINDSURF_API_KEY environment variable."
        )

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._http_client is not None:
            await self._http_client.close()
            self._http_client = None

    async def query(self, prompt: str) -> None:
        """Queue a prompt for the next receive_response() call."""
        self._pending_query = prompt

    async def receive_response(self) -> AsyncIterator[AgentMessage]:
        """Execute the queued prompt against Windsurf.

        Routes to gRPC (Mode 1) or REST (Mode 2) based on connection state.
        """
        if not self._pending_query:
            return

        prompt = self._pending_query
        self._pending_query = None

        if self._use_local_grpc:
            yield await self._grpc_response(prompt)
        else:
            yield await self._rest_response(prompt)

    async def _grpc_response(self, prompt: str) -> AgentMessage:
        """Send prompt via gRPC to local Windsurf language server."""
        from integrations.windsurf_proxy.grpc_client import stream_chat
        from integrations.windsurf_proxy.models import resolve_model

        model_enum, model_name = resolve_model(self.model)
        messages = []

        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": prompt})

        text_parts: list[str] = []
        try:
            async for chunk in stream_chat(
                credentials=self._credentials,
                messages=messages,
                model_enum=model_enum,
                model_name=model_name,
                system_prompt=self.system_prompt,
            ):
                text_parts.append(chunk)
        except Exception as e:
            logger.error(f"[WindsurfAgent] gRPC streaming error: {e}")
            return AgentMessage(
                role=MessageRole.SYSTEM,
                content=[
                    ContentBlock(
                        type=ContentBlockType.TEXT,
                        text=f"Windsurf gRPC error: {e}",
                    )
                ],
            )

        full_text = "".join(text_parts)
        if not full_text:
            full_text = "(Empty response from Windsurf)"

        return AgentMessage(
            role=MessageRole.ASSISTANT,
            content=[ContentBlock(type=ContentBlockType.TEXT, text=full_text)],
        )

    async def _rest_response(self, prompt: str) -> AgentMessage:
        """Send prompt via REST API to server.codeium.com (Mode 2 fallback)."""
        try:
            import aiohttp
        except ImportError:
            raise ImportError(
                "aiohttp is required for WindsurfAgentClient REST mode. "
                "Install with: pip install aiohttp"
            )

        if self._http_client is None:
            self._http_client = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": CONTENT_TYPE_JSON,
                    "Accept": CONTENT_TYPE_JSON,
                }
            )

        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }

        url = f"{self._rest_base_url}/chat/completions"
        try:
            async with self._http_client.post(url, json=payload) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    return AgentMessage(
                        role=MessageRole.SYSTEM,
                        content=[
                            ContentBlock(
                                type=ContentBlockType.TEXT,
                                text=f"Windsurf REST API error ({resp.status}): {error_text}",
                            )
                        ],
                    )

                data = await resp.json()
                choices = data.get("choices", [])
                if not choices:
                    return AgentMessage(
                        role=MessageRole.ASSISTANT,
                        content=[
                            ContentBlock(
                                type=ContentBlockType.TEXT,
                                text="(Empty response from Windsurf REST API)",
                            )
                        ],
                    )

                content = choices[0].get("message", {}).get("content", "")
                return AgentMessage(
                    role=MessageRole.ASSISTANT,
                    content=[ContentBlock(type=ContentBlockType.TEXT, text=content)],
                )
        except Exception as e:
            logger.error(f"[WindsurfAgent] REST API error: {e}")
            return AgentMessage(
                role=MessageRole.SYSTEM,
                content=[
                    ContentBlock(
                        type=ContentBlockType.TEXT,
                        text=f"Windsurf REST API error: {e}",
                    )
                ],
            )

    def supports_subagents(self) -> bool:
        return False

    def provider_name(self) -> str:
        return "windsurf"
