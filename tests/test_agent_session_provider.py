#!/usr/bin/env python3
"""
Tests for Provider-Agnostic Agent Session Runner
==================================================

Unit tests for _run_agent_client_session() in agents/session.py.
Covers:
- Routing: run_agent_session() dispatches to _run_agent_client_session for AgentClient
- Text accumulation from AgentMessage stream
- Tool use / tool result logging
- Build-complete detection → "complete" status
- Continuing sessions → "continue" status
- Error handling (concurrency, rate limit, auth, generic)
"""

import importlib.util
import sys
import types as _types_mod
from pathlib import Path
from pathlib import Path as _Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add the apps/backend directory to the Python path
backend_path = Path(__file__).parent.parent / "apps" / "backend"
sys.path.insert(0, str(backend_path))

# Mock claude_agent_sdk before any imports
_mock_sdk = MagicMock()
_mock_sdk.ClaudeSDKClient = MagicMock()
_mock_sdk.ClaudeAgentOptions = MagicMock()
_mock_sdk.AgentDefinition = MagicMock()
_mock_sdk.types = MagicMock()
_mock_sdk.types.HookMatcher = MagicMock()
sys.modules["claude_agent_sdk"] = _mock_sdk
sys.modules["claude_agent_sdk.types"] = _mock_sdk.types

# Mock ALL top-level modules that agents.session imports (and their transitive
# deps) to avoid the deep import chain that requires core.provider_config.
# These are direct imports in session.py that trigger heavy chains.
for _mod_name in [
    "insight_extractor",
    "linear_updater",
    "recovery",
]:
    sys.modules[_mod_name] = MagicMock()

from core.agent_client import (
    AgentClient,
    AgentMessage,
    ContentBlock,
    ContentBlockType,
    MessageRole,
)

# =============================================================================
# Helpers — minimal AgentClient for testing session runner
# =============================================================================


class FakeAgentClient(AgentClient):
    """Fake AgentClient that yields pre-configured messages."""

    def __init__(self, messages=None, provider="fake"):
        self._messages = messages or []
        self._provider = provider
        self._queried = False

    async def query(self, prompt):
        self._queried = True

    async def receive_response(self):
        for msg in self._messages:
            yield msg

    def supports_subagents(self):
        return False

    def provider_name(self):
        return self._provider

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class ErrorAgentClient(AgentClient):
    """AgentClient that raises an exception during query or receive."""

    def __init__(self, error_on="receive", exception=None):
        self._error_on = error_on
        self._exception = exception or RuntimeError("test error")

    async def query(self, prompt):
        if self._error_on == "query":
            raise self._exception

    async def receive_response(self):
        if self._error_on == "receive":
            raise self._exception
        yield AgentMessage(role=MessageRole.ASSISTANT, content=[])  # pragma: no cover

    def supports_subagents(self):
        return False

    def provider_name(self):
        return "error"

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


# =============================================================================
# Tests
# =============================================================================


class TestRunAgentSessionRouting:
    """Test that run_agent_session routes correctly based on client type."""

    @pytest.mark.asyncio
    async def test_agent_client_routes_to_provider_agnostic(self, tmp_path):
        """AgentClient instance should be routed to _run_agent_client_session."""
        from agents.session import run_agent_session

        client = FakeAgentClient(
            messages=[
                AgentMessage(
                    role=MessageRole.ASSISTANT,
                    content=[
                        ContentBlock(type=ContentBlockType.TEXT, text="Done")
                    ],
                )
            ]
        )

        # Mock is_build_complete to return False → "continue"
        with patch("agents.session.is_build_complete", return_value=False), \
             patch("agents.session.get_task_logger", return_value=None):
            status, text, error_info = await run_agent_session(
                client=client,
                message="test prompt",
                spec_dir=tmp_path,
            )

        assert status == "continue"
        assert "Done" in text
        assert error_info == {}


class TestRunAgentClientSession:
    """Tests for _run_agent_client_session (the provider-agnostic session)."""

    @pytest.mark.asyncio
    async def test_text_accumulation(self, tmp_path):
        """Text blocks should accumulate into response_text."""
        from agents.session import _run_agent_client_session

        client = FakeAgentClient(
            messages=[
                AgentMessage(
                    role=MessageRole.ASSISTANT,
                    content=[ContentBlock(type=ContentBlockType.TEXT, text="Hello ")],
                ),
                AgentMessage(
                    role=MessageRole.ASSISTANT,
                    content=[ContentBlock(type=ContentBlockType.TEXT, text="World")],
                ),
            ]
        )

        with patch("agents.session.is_build_complete", return_value=False), \
             patch("agents.session.get_task_logger", return_value=None):
            status, text, error_info = await _run_agent_client_session(
                client=client,
                message="test",
                spec_dir=tmp_path,
            )

        assert status == "continue"
        assert text == "Hello World"
        assert error_info == {}

    @pytest.mark.asyncio
    async def test_build_complete_returns_complete(self, tmp_path):
        """When build is complete, status should be 'complete'."""
        from agents.session import _run_agent_client_session

        client = FakeAgentClient(
            messages=[
                AgentMessage(
                    role=MessageRole.ASSISTANT,
                    content=[ContentBlock(type=ContentBlockType.TEXT, text="All done")],
                ),
            ]
        )

        with patch("agents.session.is_build_complete", return_value=True), \
             patch("agents.session.get_task_logger", return_value=None):
            status, text, error_info = await _run_agent_client_session(
                client=client,
                message="test",
                spec_dir=tmp_path,
            )

        assert status == "complete"
        assert "All done" in text

    @pytest.mark.asyncio
    async def test_tool_use_tracking(self, tmp_path):
        """Tool use blocks should be processed without error."""
        from agents.session import _run_agent_client_session

        client = FakeAgentClient(
            messages=[
                AgentMessage(
                    role=MessageRole.ASSISTANT,
                    content=[
                        ContentBlock(
                            type=ContentBlockType.TOOL_USE,
                            tool_name="Read",
                            tool_id="t1",
                            tool_input={"file_path": "/foo.py"},
                        )
                    ],
                ),
                AgentMessage(
                    role=MessageRole.USER,
                    content=[
                        ContentBlock(
                            type=ContentBlockType.TOOL_RESULT,
                            tool_use_id="t1",
                            is_error=False,
                            result_content="def foo(): pass",
                        )
                    ],
                ),
                AgentMessage(
                    role=MessageRole.ASSISTANT,
                    content=[
                        ContentBlock(type=ContentBlockType.TEXT, text="Read the file.")
                    ],
                ),
            ]
        )

        with patch("agents.session.is_build_complete", return_value=False), \
             patch("agents.session.get_task_logger", return_value=None):
            status, text, error_info = await _run_agent_client_session(
                client=client,
                message="test",
                spec_dir=tmp_path,
            )

        assert status == "continue"
        assert "Read the file." in text

    @pytest.mark.asyncio
    async def test_tool_error_handling(self, tmp_path):
        """Tool errors should be logged but not crash the session."""
        from agents.session import _run_agent_client_session

        client = FakeAgentClient(
            messages=[
                AgentMessage(
                    role=MessageRole.ASSISTANT,
                    content=[
                        ContentBlock(
                            type=ContentBlockType.TOOL_USE,
                            tool_name="Bash",
                            tool_id="t2",
                            tool_input={"command": "rm -rf /"},
                        )
                    ],
                ),
                AgentMessage(
                    role=MessageRole.USER,
                    content=[
                        ContentBlock(
                            type=ContentBlockType.TOOL_RESULT,
                            tool_use_id="t2",
                            is_error=True,
                            result_content="Command blocked by security policy",
                        )
                    ],
                ),
            ]
        )

        with patch("agents.session.is_build_complete", return_value=False), \
             patch("agents.session.get_task_logger", return_value=None):
            status, text, error_info = await _run_agent_client_session(
                client=client,
                message="test",
                spec_dir=tmp_path,
            )

        assert status == "continue"

    @pytest.mark.asyncio
    async def test_exception_returns_error(self, tmp_path):
        """Exception during session should return error status."""
        from agents.session import _run_agent_client_session

        client = ErrorAgentClient(error_on="receive")

        with patch("agents.session.get_task_logger", return_value=None):
            status, text, error_info = await _run_agent_client_session(
                client=client,
                message="test",
                spec_dir=tmp_path,
            )

        assert status == "error"
        assert error_info["type"] in ("other", "tool_concurrency", "rate_limit", "authentication")
        assert "test error" in error_info["message"]

    @pytest.mark.asyncio
    async def test_exception_on_query_returns_error(self, tmp_path):
        """Exception during query() should return error status."""
        from agents.session import _run_agent_client_session

        client = ErrorAgentClient(error_on="query")

        with patch("agents.session.get_task_logger", return_value=None):
            status, text, error_info = await _run_agent_client_session(
                client=client,
                message="test",
                spec_dir=tmp_path,
            )

        assert status == "error"

    @pytest.mark.asyncio
    async def test_empty_stream_returns_continue(self, tmp_path):
        """Empty response stream should return 'continue'."""
        from agents.session import _run_agent_client_session

        client = FakeAgentClient(messages=[])

        with patch("agents.session.is_build_complete", return_value=False), \
             patch("agents.session.get_task_logger", return_value=None):
            status, text, error_info = await _run_agent_client_session(
                client=client,
                message="test",
                spec_dir=tmp_path,
            )

        assert status == "continue"
        assert text == ""

    @pytest.mark.asyncio
    async def test_provider_name_in_logging(self, tmp_path, capsys):
        """Session should print the provider name."""
        from agents.session import _run_agent_client_session

        client = FakeAgentClient(messages=[], provider="copilot")

        with patch("agents.session.is_build_complete", return_value=False), \
             patch("agents.session.get_task_logger", return_value=None):
            await _run_agent_client_session(
                client=client,
                message="test",
                spec_dir=tmp_path,
            )

        captured = capsys.readouterr()
        assert "copilot" in captured.out.lower()
