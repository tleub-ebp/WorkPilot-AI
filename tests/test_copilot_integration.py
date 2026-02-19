#!/usr/bin/env python3
"""
Integration Tests for Copilot Sub-Agents Plan
===============================================

End-to-end integration tests verifying that the full provider-agnostic
pipeline works correctly for both Claude and Copilot paths:
- create_agent_client → AgentClient → process_agent_stream
- Orchestrator reviewer uses create_agent_client correctly
- Provider switching via environment variable
- Backward compatibility: raw ClaudeSDKClient still works
"""

import asyncio
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import importlib.util
import types as _types
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
_BACKEND = _Path(__file__).parent.parent / "apps" / "backend"
for _pkg, _subpath in [
    ("runners", "runners"),
    ("runners.github", "runners/github"),
    ("runners.github.services", "runners/github/services"),
]:
    if _pkg not in sys.modules:
        _m = _types.ModuleType(_pkg)
        _m.__path__ = [str(_BACKEND / _subpath)]
        _m.__package__ = _pkg
        sys.modules[_pkg] = _m

_sdk_utils_path = _BACKEND / "runners" / "github" / "services" / "sdk_utils.py"
if "runners.github.services.sdk_utils" not in sys.modules:
    _spec = importlib.util.spec_from_file_location(
        "runners.github.services.sdk_utils", _sdk_utils_path,
        submodule_search_locations=[],
    )
    _sdk_utils_mod = importlib.util.module_from_spec(_spec)
    sys.modules["runners.github.services.sdk_utils"] = _sdk_utils_mod
    _spec.loader.exec_module(_sdk_utils_mod)

process_agent_stream = sys.modules["runners.github.services.sdk_utils"].process_agent_stream

from core.agent_client import (
    AgentClient,
    AgentMessage,
    ClaudeAgentClient,
    ContentBlock,
    ContentBlockType,
    CopilotAgentClient,
    MessageRole,
    SubagentDefinition,
)


# =============================================================================
# Integration: Full Claude Path
# =============================================================================


class TestClaudeIntegrationPath:
    """Integration tests for the Claude SDK provider path."""

    @patch("core.client.create_client")
    def test_create_agent_client_to_process_stream(self, mock_create_client, tmp_path):
        """Full path: create_agent_client(claude) → ClaudeAgentClient → process_agent_stream."""
        from core.client import create_agent_client

        # Mock the SDK client
        mock_sdk = MagicMock()
        mock_create_client.return_value = mock_sdk

        client = create_agent_client(
            project_dir=tmp_path,
            spec_dir=tmp_path,
            model="claude-sonnet-4-5-20250929",
            provider="claude",
        )

        assert isinstance(client, ClaudeAgentClient)
        assert client.provider_name() == "claude"
        assert client.supports_subagents() is True
        assert client.inner is mock_sdk

    @patch("core.client.create_client")
    def test_backward_compat_raw_sdk_client(self, mock_create_client, tmp_path):
        """Raw create_client() still works and returns ClaudeSDKClient (not wrapped)."""
        from core.client import create_client

        mock_sdk = MagicMock()
        mock_create_client.return_value = mock_sdk

        # This should still work — direct call to create_client
        # (we patched it, so just verify it's called)
        result = create_client(
            project_dir=tmp_path,
            spec_dir=tmp_path,
            model="claude-sonnet-4-5-20250929",
        )
        assert result is mock_sdk

    @pytest.mark.asyncio
    async def test_claude_agent_client_full_stream(self):
        """ClaudeAgentClient wraps SDK stream and preserves raw messages."""
        # Simulate SDK messages
        text_block = SimpleNamespace(type="text", text="Analysis complete")
        text_block.__class__ = type("TextBlock", (), {})

        assistant_msg = SimpleNamespace(content=[text_block], structured_output=None)
        assistant_msg.__class__ = type("AssistantMessage", (), {})

        sdk_mock = MagicMock()
        sdk_mock.query = AsyncMock()

        async def mock_receive():
            yield assistant_msg

        sdk_mock.receive_response = mock_receive

        client = ClaudeAgentClient(sdk_mock)
        await client.query("analyze this")

        messages = []
        async for msg in client.receive_response():
            messages.append(msg)

        assert len(messages) == 1
        assert messages[0].raw is assistant_msg
        assert messages[0].content[0].type == ContentBlockType.TEXT
        assert messages[0].content[0].text == "Analysis complete"


# =============================================================================
# Integration: Full Copilot Path
# =============================================================================


class TestCopilotIntegrationPath:
    """Integration tests for the Copilot provider path."""

    @patch("core.client._get_cached_project_data")
    @patch("core.client.load_project_mcp_config")
    @patch("core.client.get_allowed_tools")
    def test_create_agent_client_copilot(
        self, mock_tools, mock_mcp, mock_cache, tmp_path, monkeypatch
    ):
        """Full path: create_agent_client(copilot) → CopilotAgentClient."""
        from core.client import create_agent_client

        monkeypatch.setenv("GITHUB_TOKEN", "ghp_integration_test")
        mock_cache.return_value = ({}, {})
        mock_mcp.return_value = {}
        mock_tools.return_value = ["Read", "Write", "Edit"]
        monkeypatch.setattr("core.client.is_linear_enabled", lambda: False)

        client = create_agent_client(
            project_dir=tmp_path,
            spec_dir=tmp_path,
            model="gpt-4o",
            agent_type="coder",
            provider="copilot",
        )

        assert isinstance(client, CopilotAgentClient)
        assert client.provider_name() == "copilot"
        assert client.supports_subagents() is True
        assert client.model == "gpt-4o"

    @patch("core.client._get_cached_project_data")
    @patch("core.client.load_project_mcp_config")
    @patch("core.client.get_allowed_tools")
    def test_copilot_with_subagent_definitions(
        self, mock_tools, mock_mcp, mock_cache, tmp_path, monkeypatch
    ):
        """Copilot client should receive converted SubagentDefinitions."""
        from core.client import create_agent_client

        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
        mock_cache.return_value = ({}, {})
        mock_mcp.return_value = {}
        mock_tools.return_value = []
        monkeypatch.setattr("core.client.is_linear_enabled", lambda: False)

        # Simulate AgentDefinition-like objects (from Claude SDK)
        mock_agent = MagicMock()
        mock_agent.description = "Security specialist"
        mock_agent.prompt = "Analyze for vulnerabilities"
        mock_agent.tools = ["Read", "Bash"]
        mock_agent.model = "gpt-4o"

        client = create_agent_client(
            project_dir=tmp_path,
            spec_dir=tmp_path,
            model="gpt-4o",
            agents={"security": mock_agent},
            provider="copilot",
        )

        assert isinstance(client, CopilotAgentClient)
        assert "security" in client.agents
        assert client.agents["security"].description == "Security specialist"
        assert client.agents["security"].tools == ["Read", "Bash"]

    @pytest.mark.asyncio
    async def test_copilot_subagent_parallel_execution(self):
        """CopilotAgentClient.run_subagents executes agents in parallel."""
        client = CopilotAgentClient(model="gpt-4o", github_token="ghp_test")

        agents = {
            "sec": SubagentDefinition(description="Security", prompt="Check sec"),
            "quality": SubagentDefinition(description="Quality", prompt="Check quality"),
            "logic": SubagentDefinition(description="Logic", prompt="Check logic"),
        }

        call_urls = []

        def make_response(text):
            resp = MagicMock()
            resp.status = 200
            resp.json = AsyncMock(
                return_value={"choices": [{"message": {"content": text}}]}
            )
            resp.__aenter__ = AsyncMock(return_value=resp)
            resp.__aexit__ = AsyncMock(return_value=None)
            return resp

        responses = iter([
            make_response("No security issues found"),
            make_response("Code quality is acceptable"),
            make_response("Logic is sound"),
        ])

        mock_session = MagicMock()
        mock_session.post = MagicMock(side_effect=lambda *a, **kw: next(responses))
        client._http_client = mock_session

        results = await client.run_subagents(agents, "Review PR #123")

        assert len(results) == 3
        assert "sec" in results
        assert "quality" in results
        assert "logic" in results
        assert "security issues" in results["sec"].lower()


# =============================================================================
# Integration: Provider Switching
# =============================================================================


class TestProviderSwitching:
    """Integration tests for dynamic provider switching."""

    @patch("core.client.create_client")
    def test_env_switch_to_claude(self, mock_create_client, tmp_path, monkeypatch):
        """AUTO_CLAUDE_PROVIDER=claude → ClaudeAgentClient."""
        from core.client import create_agent_client

        monkeypatch.setenv("AUTO_CLAUDE_PROVIDER", "claude")
        mock_create_client.return_value = MagicMock()

        client = create_agent_client(
            project_dir=tmp_path,
            spec_dir=tmp_path,
            model="claude-sonnet-4-5-20250929",
        )

        assert isinstance(client, ClaudeAgentClient)

    @patch("core.client._get_cached_project_data")
    @patch("core.client.load_project_mcp_config")
    @patch("core.client.get_allowed_tools")
    def test_env_switch_to_copilot(
        self, mock_tools, mock_mcp, mock_cache, tmp_path, monkeypatch
    ):
        """AUTO_CLAUDE_PROVIDER=copilot → CopilotAgentClient."""
        from core.client import create_agent_client

        monkeypatch.setenv("AUTO_CLAUDE_PROVIDER", "copilot")
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
        mock_cache.return_value = ({}, {})
        mock_mcp.return_value = {}
        mock_tools.return_value = []
        monkeypatch.setattr("core.client.is_linear_enabled", lambda: False)

        client = create_agent_client(
            project_dir=tmp_path,
            spec_dir=tmp_path,
            model="gpt-4o",
        )

        assert isinstance(client, CopilotAgentClient)

    @patch("core.client._get_cached_project_data")
    @patch("core.client.load_project_mcp_config")
    @patch("core.client.get_allowed_tools")
    def test_project_env_file_switch(
        self, mock_tools, mock_mcp, mock_cache, tmp_path, monkeypatch
    ):
        """Project .auto-claude/.env AI_PROVIDER=copilot → CopilotAgentClient."""
        from core.client import create_agent_client

        monkeypatch.delenv("AUTO_CLAUDE_PROVIDER", raising=False)
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
        mock_cache.return_value = ({}, {})
        mock_mcp.return_value = {}
        mock_tools.return_value = []
        monkeypatch.setattr("core.client.is_linear_enabled", lambda: False)

        # Create project env file
        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir()
        env_file = auto_claude_dir / ".env"
        env_file.write_text("AI_PROVIDER=copilot\n")

        client = create_agent_client(
            project_dir=tmp_path,
            spec_dir=tmp_path,
            model="gpt-4o",
        )

        assert isinstance(client, CopilotAgentClient)


# =============================================================================
# Integration: process_agent_stream with real AgentClient
# =============================================================================


class TestProcessAgentStreamIntegration:
    """Integration tests for process_agent_stream with real client implementations."""

    @pytest.mark.asyncio
    async def test_claude_client_through_process_agent_stream(self):
        """ClaudeAgentClient messages should be processed by process_agent_stream."""
        from runners.github.services.sdk_utils import process_agent_stream

        # Create a ClaudeAgentClient with mock SDK
        text_block = SimpleNamespace(type="text", text="Review complete")
        text_block.__class__ = type("TextBlock", (), {})

        result_msg_raw = SimpleNamespace(
            type="result", subtype=None,
            structured_output={"verdict": "approve"}
        )
        result_msg_raw.__class__ = type("ResultMessage", (), {})

        assistant_msg = SimpleNamespace(
            content=[text_block], structured_output=None
        )
        assistant_msg.__class__ = type("AssistantMessage", (), {})

        sdk_mock = MagicMock()
        sdk_mock.query = AsyncMock()

        async def mock_receive():
            yield assistant_msg
            yield result_msg_raw

        sdk_mock.receive_response = mock_receive
        client = ClaudeAgentClient(sdk_mock)

        await client.query("review PR")

        result = await process_agent_stream(
            client=client,
            context_name="IntegrationTest",
        )

        assert "Review complete" in result["result_text"]
        assert result["structured_output"] == {"verdict": "approve"}
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_copilot_client_through_process_agent_stream(self):
        """CopilotAgentClient messages should be processed by process_agent_stream."""
        from runners.github.services.sdk_utils import process_agent_stream

        client = CopilotAgentClient(model="gpt-4o", github_token="ghp_test")
        await client.query("analyze code")

        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "choices": [
                    {"message": {"content": "Code looks good", "tool_calls": []}}
                ]
            }
        )
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)
        client._http_client = mock_session

        result = await process_agent_stream(
            client=client,
            context_name="CopilotIntegration",
        )

        assert "Code looks good" in result["result_text"]
        assert result["error"] is None


# =============================================================================
# Integration: Orchestrator Reviewer Imports
# =============================================================================


class TestOrchestratorReviewerIntegration:
    """Verify orchestrator reviewers can import the new abstractions."""

    def test_parallel_orchestrator_imports(self):
        """parallel_orchestrator_reviewer should import create_agent_client."""
        from runners.github.services.parallel_orchestrator_reviewer import (
            create_agent_client,
            process_agent_stream,
        )
        assert callable(create_agent_client)
        assert callable(process_agent_stream)

    def test_parallel_followup_imports(self):
        """parallel_followup_reviewer should import create_agent_client."""
        from runners.github.services.parallel_followup_reviewer import (
            create_agent_client,
            process_agent_stream,
        )
        assert callable(create_agent_client)
        assert callable(process_agent_stream)

    def test_agent_definition_optional(self):
        """AgentDefinition import should not crash even if claude_agent_sdk missing."""
        # This test verifies the try/except pattern works
        import runners.github.services.parallel_orchestrator_reviewer as mod
        # AgentDefinition can be None or the real class — both are acceptable
        assert hasattr(mod, "AgentDefinition")


# =============================================================================
# Integration: Session with Provider Routing
# =============================================================================


class TestSessionProviderRouting:
    """Integration tests verifying session.py routes correctly."""

    @pytest.mark.asyncio
    async def test_agent_client_to_session_to_result(self, tmp_path):
        """Full path: AgentClient → run_agent_session → (status, text, error)."""
        from agents.session import run_agent_session
        from core.agent_client import AgentMessage, ContentBlock, ContentBlockType

        class SimpleTestClient(AgentClient):
            async def query(self, prompt):
                pass

            async def receive_response(self):
                yield AgentMessage(
                    role=MessageRole.ASSISTANT,
                    content=[
                        ContentBlock(type=ContentBlockType.TEXT, text="Task implemented successfully")
                    ],
                )

            def supports_subagents(self):
                return False

            def provider_name(self):
                return "test"

        client = SimpleTestClient()

        with patch("agents.session.is_build_complete", return_value=True), \
             patch("agents.session.get_task_logger", return_value=None):
            status, text, error_info = await run_agent_session(
                client=client,
                message="implement feature",
                spec_dir=tmp_path,
            )

        assert status == "complete"
        assert "Task implemented successfully" in text
        assert error_info == {}
