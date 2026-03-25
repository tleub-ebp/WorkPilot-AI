#!/usr/bin/env python3
"""
Tests for process_agent_stream() — Provider-Agnostic Stream Processor
======================================================================

Unit tests for the process_agent_stream() function in sdk_utils.py.
Covers:
- Delegation to process_sdk_stream() for non-AgentClient objects
- Processing normalized AgentMessage streams
- Callback invocations (on_thinking, on_tool_use, on_tool_result, on_text, on_structured_output)
- Sub-agent (Task tool) tracking
- Circuit breaker / max message limit
- Concurrency error detection
- Error handling in stream processing
"""

import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import importlib.util
import types
from pathlib import Path as _Path

# Mock claude_agent_sdk before any imports that transitively need it
_mock_sdk = MagicMock()
_mock_sdk.ClaudeSDKClient = MagicMock()
_mock_sdk.ClaudeAgentOptions = MagicMock()
_mock_sdk.AgentDefinition = MagicMock()
_mock_sdk.types = MagicMock()
_mock_sdk.types.HookMatcher = MagicMock()
sys.modules["claude_agent_sdk"] = _mock_sdk
sys.modules["claude_agent_sdk.types"] = _mock_sdk.types

# Create runners package hierarchy WITHOUT triggering runners/__init__.py
# (which eagerly imports ideation_runner → cli → qa → claude_agent_sdk chain)
_BACKEND = _Path(__file__).parent.parent / "apps" / "backend"
_runners_path = str(_BACKEND / "runners")

for _pkg, _subpath in [
    ("runners", "runners"),
    ("runners.github", "runners/github"),
    ("runners.github.services", "runners/github/services"),
]:
    if _pkg not in sys.modules:
        _mod = types.ModuleType(_pkg)
        _mod.__path__ = [str(_BACKEND / _subpath)]
        _mod.__package__ = _pkg
        sys.modules[_pkg] = _mod

# Now load sdk_utils directly
_sdk_utils_path = _BACKEND / "runners" / "github" / "services" / "sdk_utils.py"
_spec = importlib.util.spec_from_file_location(
    "runners.github.services.sdk_utils", _sdk_utils_path,
    submodule_search_locations=[],
)
_sdk_utils_mod = importlib.util.module_from_spec(_spec)
sys.modules["runners.github.services.sdk_utils"] = _sdk_utils_mod
_spec.loader.exec_module(_sdk_utils_mod)

process_agent_stream = _sdk_utils_mod.process_agent_stream

from core.agent_client import (
    AgentClient,
    AgentMessage,
    ClaudeAgentClient,
    ContentBlock,
    ContentBlockType,
    CopilotAgentClient,
    MessageRole,
)


# =============================================================================
# Helpers
# =============================================================================


class MockAgentClient(AgentClient):
    """Minimal AgentClient for testing stream processing."""

    def __init__(self, messages=None):
        self._messages = messages or []
        self._queried = False

    async def query(self, prompt):
        self._queried = True

    async def receive_response(self):
        for msg in self._messages:
            yield msg

    def supports_subagents(self):
        return False

    def provider_name(self):
        return "mock"

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Mock implementation - no cleanup needed for test client
        pass


def _text_msg(text):
    """Create a simple text AgentMessage."""
    return AgentMessage(
        role=MessageRole.ASSISTANT,
        content=[ContentBlock(type=ContentBlockType.TEXT, text=text)],
    )


def _tool_use_msg(name, tool_id, tool_input=None):
    """Create a tool use AgentMessage."""
    return AgentMessage(
        role=MessageRole.ASSISTANT,
        content=[
            ContentBlock(
                type=ContentBlockType.TOOL_USE,
                tool_name=name,
                tool_id=tool_id,
                tool_input=tool_input or {},
            )
        ],
    )


def _tool_result_msg(tool_id, content, is_error=False):
    """Create a tool result AgentMessage."""
    return AgentMessage(
        role=MessageRole.USER,
        content=[
            ContentBlock(
                type=ContentBlockType.TOOL_RESULT,
                tool_use_id=tool_id,
                is_error=is_error,
                result_content=content,
            )
        ],
    )


def _thinking_msg(text):
    return AgentMessage(
        role=MessageRole.SYSTEM,
        content=[ContentBlock(type=ContentBlockType.THINKING, text=text)],
    )


def _structured_output_msg(data):
    return AgentMessage(
        role=MessageRole.ASSISTANT,
        content=[
            ContentBlock(
                type=ContentBlockType.STRUCTURED_OUTPUT,
                structured_output=data,
            )
        ],
    )


def _result_msg(subtype=None, structured_output=None):
    return AgentMessage(
        role=MessageRole.SYSTEM,
        content=[
            ContentBlock(
                type=ContentBlockType.RESULT,
                subtype=subtype,
                structured_output=structured_output,
            )
        ],
    )


# =============================================================================
# Tests
# =============================================================================


class TestProcessAgentStream:
    """Tests for process_agent_stream()."""

    @pytest.mark.asyncio
    async def test_delegates_to_sdk_stream_for_non_agent_client(self):
        """Non-AgentClient objects should delegate to process_sdk_stream."""
        from runners.github.services.sdk_utils import process_agent_stream

        raw_sdk_client = MagicMock()  # Not an AgentClient instance

        with patch(
            "runners.github.services.sdk_utils.process_sdk_stream",
            new_callable=AsyncMock,
        ) as mock_sdk:
            mock_sdk.return_value = {
                "result_text": "ok",
                "structured_output": None,
                "agents_invoked": [],
                "msg_count": 1,
                "subagent_tool_ids": {},
                "error": None,
            }
            result = await process_agent_stream(client=raw_sdk_client)

            mock_sdk.assert_awaited_once()
            assert result["result_text"] == "ok"

    @pytest.mark.asyncio
    async def test_basic_text_stream(self):
        """Simple text messages should accumulate in result_text."""
        from runners.github.services.sdk_utils import process_agent_stream

        client = MockAgentClient(
            messages=[_text_msg("Hello "), _text_msg("World")]
        )

        result = await process_agent_stream(client=client)

        assert result["result_text"] == "Hello World"
        assert result["error"] is None
        assert result["msg_count"] == 2

    @pytest.mark.asyncio
    async def test_text_callback_invoked(self):
        """on_text callback should be called for text blocks."""
        from runners.github.services.sdk_utils import process_agent_stream

        texts = []
        client = MockAgentClient(messages=[_text_msg("abc")])

        await process_agent_stream(client=client, on_text=lambda t: texts.append(t))

        assert texts == ["abc"]

    @pytest.mark.asyncio
    async def test_thinking_callback(self):
        """on_thinking callback should be called for thinking blocks."""
        from runners.github.services.sdk_utils import process_agent_stream

        thoughts = []
        client = MockAgentClient(messages=[_thinking_msg("Let me think...")])

        await process_agent_stream(
            client=client, on_thinking=lambda t: thoughts.append(t)
        )

        assert thoughts == ["Let me think..."]

    @pytest.mark.asyncio
    async def test_tool_use_callback(self):
        """on_tool_use callback should be called for tool invocations."""
        from runners.github.services.sdk_utils import process_agent_stream

        tools = []
        client = MockAgentClient(
            messages=[_tool_use_msg("Read", "t1", {"file_path": "/f.py"})]
        )

        await process_agent_stream(
            client=client,
            on_tool_use=lambda name, tid, inp: tools.append((name, tid, inp)),
        )

        assert len(tools) == 1
        assert tools[0] == ("Read", "t1", {"file_path": "/f.py"})

    @pytest.mark.asyncio
    async def test_tool_result_callback(self):
        """on_tool_result callback should be called for tool results."""
        from runners.github.services.sdk_utils import process_agent_stream

        results = []
        client = MockAgentClient(
            messages=[_tool_result_msg("t1", "file content", is_error=False)]
        )

        await process_agent_stream(
            client=client,
            on_tool_result=lambda tid, err, content: results.append(
                (tid, err, content)
            ),
        )

        assert len(results) == 1
        assert results[0] == ("t1", False, "file content")

    @pytest.mark.asyncio
    async def test_structured_output_callback(self):
        """on_structured_output should be called and structured_output captured."""
        from runners.github.services.sdk_utils import process_agent_stream

        outputs = []
        data = {"findings": [{"severity": "high"}]}
        client = MockAgentClient(messages=[_structured_output_msg(data)])

        result = await process_agent_stream(
            client=client,
            on_structured_output=lambda d: outputs.append(d),
        )

        assert result["structured_output"] == data
        assert outputs == [data]

    @pytest.mark.asyncio
    async def test_subagent_task_tool_tracking(self):
        """Task tool calls should be tracked as sub-agent invocations."""
        from runners.github.services.sdk_utils import process_agent_stream

        client = MockAgentClient(
            messages=[
                _tool_use_msg(
                    "Task", "task_1", {"subagent_type": "security"}
                ),
                _tool_result_msg("task_1", "No issues found"),
            ]
        )

        result = await process_agent_stream(client=client)

        assert "security" in result["agents_invoked"]
        assert result["subagent_tool_ids"] == {"task_1": "security"}

    @pytest.mark.asyncio
    async def test_circuit_breaker_max_messages(self):
        """Message count exceeding limit should trigger circuit breaker."""
        from runners.github.services.sdk_utils import process_agent_stream

        # Create more messages than the limit
        msgs = [_text_msg(f"msg{i}") for i in range(10)]
        client = MockAgentClient(messages=msgs)

        result = await process_agent_stream(
            client=client, max_messages=5
        )

        assert result["error"] is not None
        assert "Circuit breaker" in result["error"]
        # msg_count should be 6 (the one that exceeded)
        assert result["msg_count"] <= 7

    @pytest.mark.asyncio
    async def test_concurrency_error_detection(self):
        """Tool concurrency error in text should be detected."""
        from runners.github.services.sdk_utils import process_agent_stream

        # The error pattern that _is_tool_concurrency_error checks for
        error_text = "Error: 400 tool use is not allowed"
        client = MockAgentClient(messages=[_text_msg(error_text)])

        result = await process_agent_stream(client=client)

        # Should detect concurrency error
        assert result["error"] == "tool_use_concurrency_error"

    @pytest.mark.asyncio
    async def test_result_block_structured_output(self):
        """ResultMessage with structured_output should be captured."""
        from runners.github.services.sdk_utils import process_agent_stream

        data = {"score": 95}
        client = MockAgentClient(messages=[_result_msg(structured_output=data)])

        result = await process_agent_stream(client=client)

        assert result["structured_output"] == data

    @pytest.mark.asyncio
    async def test_result_block_error_subtype(self):
        """ResultMessage with error subtype should set stream_error."""
        from runners.github.services.sdk_utils import process_agent_stream

        client = MockAgentClient(
            messages=[
                _result_msg(subtype="error_max_structured_output_retries")
            ]
        )

        result = await process_agent_stream(client=client)

        assert result["error"] == "structured_output_validation_failed"

    @pytest.mark.asyncio
    async def test_empty_stream(self):
        """Empty stream should return clean result."""
        from runners.github.services.sdk_utils import process_agent_stream

        client = MockAgentClient(messages=[])

        result = await process_agent_stream(client=client)

        assert result["result_text"] == ""
        assert result["msg_count"] == 0
        assert result["error"] is None
        assert result["agents_invoked"] == []

    @pytest.mark.asyncio
    async def test_mixed_message_stream(self):
        """Complex stream with thinking, tool use, results, and text."""
        from runners.github.services.sdk_utils import process_agent_stream

        client = MockAgentClient(
            messages=[
                _thinking_msg("Planning..."),
                _tool_use_msg("Read", "t1", {"file_path": "/main.py"}),
                _tool_result_msg("t1", "def main(): pass"),
                _text_msg("I read the file. "),
                _tool_use_msg("Edit", "t2", {"file_path": "/main.py"}),
                _tool_result_msg("t2", "File edited"),
                _text_msg("Done editing."),
            ]
        )

        thinking = []
        tools = []
        results_cb = []
        texts = []

        result = await process_agent_stream(
            client=client,
            on_thinking=lambda t: thinking.append(t),
            on_tool_use=lambda n, tid, i: tools.append(n),
            on_tool_result=lambda tid, err, c: results_cb.append(tid),
            on_text=lambda t: texts.append(t),
        )

        assert thinking == ["Planning..."]
        assert tools == ["Read", "Edit"]
        assert results_cb == ["t1", "t2"]
        assert texts == ["I read the file. ", "Done editing."]
        assert result["result_text"] == "I read the file. Done editing."
        assert result["msg_count"] == 7

    @pytest.mark.asyncio
    async def test_exception_in_stream(self):
        """Exception during stream processing should be caught and returned as error."""
        from runners.github.services.sdk_utils import process_agent_stream

        class FailingClient(MockAgentClient):
            async def receive_response(self):
                yield _text_msg("ok")
                raise RuntimeError("Connection lost")

        client = FailingClient()

        result = await process_agent_stream(client=client)

        assert result["error"] == "Connection lost"
        assert result["msg_count"] == 1
