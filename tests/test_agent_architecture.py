#!/usr/bin/env python3
"""
Tests for Agent Architecture
============================

Verifies the agent architecture where:
- Python orchestrator runs a single Claude SDK session
- The agent itself decides when to spawn subagents (via Task tool)
- Parallel execution is handled internally by Claude Code, not Python

Key architectural constraints:
- No Python-level parallel orchestration (no coordinator.py, task_tool.py)
- No --parallel CLI flag (agent decides parallelism)
- Agent prompt includes subagent capability documentation
"""

import ast
import inspect
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add apps/backend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

# ---------------------------------------------------------------------------
# Module-level sys.modules mocking
# ---------------------------------------------------------------------------
# Several test classes import `agent` and `auto_claude_tools`, which pull in
# deep dependency chains (core.agent, agents.tools_pkg, etc.) that require
# packages not installed in the CI test environment.  Pre-populate
# sys.modules so Python's import machinery never attempts real resolution.
# ---------------------------------------------------------------------------
_mocked_module_names = [
    # External SDKs
    "claude_code_sdk",
    "claude_code_sdk.types",
    "claude_agent_sdk",
    "claude_agent_sdk.types",
    # Core infrastructure
    "core",
    "core.agent",
    "core.auth",
    "core.client",
    "core.simple_client",
    "core.task_event",
    "core.workspace",
    "core.workspace.models",
    "core.file_utils",
    "core.plan_normalization",
    "core.platform",
    "core.git_executable",
    "core.sentry",
    "client",
    # Config & phases
    "phase_config",
    "phase_event",
    # Logging & UI
    "debug",
    "ui",
    "ui.capabilities",
    "task_logger",
    "linear_updater",
    "progress",
    # Prompts
    "prompts",
    "prompts_pkg",
    "prompts_pkg.project_context",
    "prompt_generator",
    # Security
    "security",
    "security.constants",
    "security.tool_input_validator",
    "security.bash_security_hook",
    # Agents package
    "agents",
    "agents.base",
    "agents.coder",
    "agents.planner",
    "agents.session",
    "agents.utils",
    "agents.memory_manager",
    "agents.tools_pkg",
    "agents.tools_pkg.models",
    "agents.tools_pkg.permissions",
    "agents.tools_pkg.registry",
    "agents.tools_pkg.tools",
    "agents.tools_pkg.tools.memory",
    "agents.tools_pkg.tools.progress",
    "agents.tools_pkg.tools.qa",
    "agents.tools_pkg.tools.subtask",
    # Spec
    "spec",
    "spec.validate_pkg",
    "spec.validate_pkg.auto_fix",
    "spec.validate_pkg.spec_validator",
    "spec.validate_pkg.validators",
    "spec.complexity",
    "spec.compaction",
    "validate_spec",
    # Memory
    "memory",
    "memory.graphiti_helpers",
    "graphiti_config",
    "graphiti_providers",
    # Recovery & misc
    "recovery",
    "insight_extractor",
    # Integrations
    "integrations",
    "integrations.linear",
    "integrations.linear.updater",
]
for _name in _mocked_module_names:
    sys.modules[_name] = MagicMock()

# Wire up core.agent so `from core.agent import *` exposes a callable
_mock_core_agent = sys.modules["core.agent"]
_mock_core_agent.run_autonomous_agent = MagicMock()
_mock_core_agent.run_autonomous_agent.__name__ = "run_autonomous_agent"
_mock_core_agent.__all__ = ["run_autonomous_agent"]

# Flag: tests that inspect real module internals (function signatures, tool
# lists) cannot run against MagicMock stubs.  They are skipped when
# mocking is active.
_MODULES_ARE_MOCKED = True
_skip_needs_real = pytest.mark.skipif(
    _MODULES_ARE_MOCKED,
    reason="Skipped: real backend modules not available (CI mocked environment)",
)


class TestNoExternalParallelism:
    """Verify no Python-level parallel orchestration exists."""

    def test_no_coordinator_module(self):
        """No external coordinator module should exist."""
        coordinator_path = (
            Path(__file__).parent.parent / "apps" / "backend" / "coordinator.py"
        )
        assert not coordinator_path.exists(), (
            "coordinator.py should not exist. Parallel orchestration is handled "
            "internally by the agent using Claude Code's Task tool."
        )

    def test_no_task_tool_module(self):
        """No task_tool wrapper module should exist."""
        task_tool_path = (
            Path(__file__).parent.parent / "apps" / "backend" / "task_tool.py"
        )
        assert not task_tool_path.exists(), (
            "task_tool.py should not exist. The agent spawns subagents directly "
            "using Claude Code's built-in Task tool."
        )

    def test_no_subtask_worker_config(self):
        """No external subtask worker agent config should exist."""
        worker_config = (
            Path(__file__).parent.parent / ".claude" / "agents" / "subtask-worker.md"
        )
        assert not worker_config.exists(), (
            "subtask-worker.md should not exist. Subagents use Claude Code's "
            "built-in agent types, not custom configs."
        )


class TestCLIInterface:
    """Verify CLI doesn't expose parallel orchestration options."""

    def test_no_parallel_flag(self):
        """CLI should not have --parallel argument."""
        run_py_path = Path(__file__).parent.parent / "apps" / "backend" / "run.py"
        content = run_py_path.read_text(encoding="utf-8")

        # Check that --parallel is not defined as an argument
        assert '"--parallel"' not in content, (
            "CLI should not have --parallel flag. The agent decides when to "
            "use parallel execution via subagents."
        )
        assert "'--parallel'" not in content, (
            "CLI should not have --parallel flag. The agent decides when to "
            "use parallel execution via subagents."
        )

    def test_no_parallel_examples_in_docs(self):
        """CLI documentation should not mention parallel mode."""
        run_py_path = Path(__file__).parent.parent / "apps" / "backend" / "run.py"
        content = run_py_path.read_text(encoding="utf-8")

        # The docstring should not have --parallel examples
        assert "--parallel" not in content[:2000], (
            "CLI docs should not contain --parallel examples."
        )


class TestAgentEntryPoint:
    """Verify the agent entry point function signature."""

    @_skip_needs_real
    def test_no_parallel_parameters(self):
        """Agent entry point should not accept parallel configuration."""
        from agent import run_autonomous_agent

        sig = inspect.signature(run_autonomous_agent)
        param_names = list(sig.parameters.keys())

        assert "max_parallel_subtasks" not in param_names, (
            "Agent should not accept max_parallel_subtasks. "
            "Parallelism is decided by the agent itself."
        )
        assert "parallel" not in param_names, (
            "Agent should not accept a 'parallel' parameter."
        )

    @_skip_needs_real
    def test_required_parameters(self):
        """Agent entry point has required parameters."""
        from agent import run_autonomous_agent

        sig = inspect.signature(run_autonomous_agent)
        param_names = list(sig.parameters.keys())

        expected = ["project_dir", "spec_dir", "model"]
        for param in expected:
            assert param in param_names, f"Expected parameter '{param}' not found"

    @_skip_needs_real
    def test_is_async(self):
        """Agent entry point is async."""
        from agent import run_autonomous_agent

        assert inspect.iscoroutinefunction(run_autonomous_agent), (
            "run_autonomous_agent should be async"
        )

    def test_agent_module_exists(self):
        """Agent module file exists with correct structure."""
        agent_path = Path(__file__).parent.parent / "apps" / "backend" / "agent.py"
        assert agent_path.exists(), "agent.py should exist"
        content = agent_path.read_text(encoding="utf-8")
        assert "core.agent" in content, "agent.py should import from core.agent"

    def test_no_parallel_in_source(self):
        """Agent source code does not define parallel parameters."""
        core_agent_path = (
            Path(__file__).parent.parent / "apps" / "backend" / "core" / "agent.py"
        )
        content = core_agent_path.read_text(encoding="utf-8")
        assert "max_parallel_subtasks" not in content, (
            "core/agent.py should not define max_parallel_subtasks parameter"
        )


class TestAgentPrompt:
    """Verify the agent prompt documents subagent capability."""

    def test_mentions_subagents(self):
        """Agent prompt mentions subagent capability."""
        coder_prompt_path = (
            Path(__file__).parent.parent / "apps" / "backend" / "prompts" / "coder.md"
        )
        content = coder_prompt_path.read_text(encoding="utf-8")

        assert "subagent" in content.lower(), (
            "Agent prompt should document subagent capability for parallel work."
        )

    def test_mentions_parallel_capability(self):
        """Agent prompt mentions parallel/concurrent capability."""
        coder_prompt_path = (
            Path(__file__).parent.parent / "apps" / "backend" / "prompts" / "coder.md"
        )
        content = coder_prompt_path.read_text(encoding="utf-8")

        has_task_tool = "task tool" in content.lower() or "Task tool" in content
        has_parallel = "parallel" in content.lower()
        has_concurrent = (
            "concurrent" in content.lower() or "simultaneously" in content.lower()
        )

        assert has_task_tool or has_parallel or has_concurrent, (
            "Agent prompt should mention parallel/concurrent work capability."
        )


class TestModuleIntegrity:
    """Verify core modules work correctly."""

    def test_agent_module_imports(self):
        """Agent module imports without errors."""
        try:
            import agent  # noqa: F401
        except ImportError as e:
            pytest.fail(f"agent.py failed to import: {e}")

    def test_run_module_valid_syntax(self):
        """Run module has valid Python syntax."""
        run_py_path = Path(__file__).parent.parent / "apps" / "backend" / "run.py"
        content = run_py_path.read_text(encoding="utf-8")

        try:
            ast.parse(content)
        except SyntaxError as e:
            pytest.fail(f"run.py has syntax error: {e}")

    def test_no_coordinator_imports(self):
        """Core modules don't import coordinator."""
        for filename in ["run.py", "core/agent.py"]:
            filepath = Path(__file__).parent.parent / "apps" / "backend" / filename
            content = filepath.read_text(encoding="utf-8")

            assert "from coordinator import" not in content, (
                f"{filename} should not import coordinator"
            )
            assert "import coordinator" not in content, (
                f"{filename} should not import coordinator"
            )

    def test_no_task_tool_imports(self):
        """Core modules don't import task_tool."""
        for filename in ["run.py", "core/agent.py"]:
            filepath = Path(__file__).parent.parent / "apps" / "backend" / filename
            content = filepath.read_text(encoding="utf-8")

            assert "from task_tool import" not in content, (
                f"{filename} should not import task_tool"
            )
            assert "import task_tool" not in content, (
                f"{filename} should not import task_tool"
            )


class TestProjectDocumentation:
    """Verify project documentation is accurate."""

    def test_no_parallel_cli_documented(self):
        """CLAUDE.md doesn't document --parallel flag."""
        claude_md_path = Path(__file__).parent.parent / "CLAUDE.md"
        content = claude_md_path.read_text(encoding="utf-8")

        assert "--parallel 2" not in content, (
            "CLAUDE.md should not document --parallel flag"
        )

    def test_subagent_architecture_documented(self):
        """CLAUDE.md documents subagent-based architecture."""
        claude_md_path = Path(__file__).parent.parent / "CLAUDE.md"
        content = claude_md_path.read_text(encoding="utf-8")

        has_subagent = "subagent" in content.lower()
        has_task_tool = "task tool" in content.lower()

        assert has_subagent or has_task_tool, (
            "CLAUDE.md should document subagent-based parallel work"
        )


class TestElectronToolScoping:
    """Verify Electron MCP tools are scoped to QA agents only."""

    @_skip_needs_real
    def test_qa_reviewer_has_electron_tools_when_enabled(self, monkeypatch):
        """QA reviewer gets Electron tools when ELECTRON_MCP_ENABLED=true and project is Electron."""
        monkeypatch.setenv("ELECTRON_MCP_ENABLED", "true")

        # Re-import to pick up env change
        from auto_claude_tools import ELECTRON_TOOLS, get_allowed_tools

        # Must pass is_electron=True for Electron tools to be included
        qa_tools = get_allowed_tools(
            "qa_reviewer", project_capabilities={"is_electron": True}
        )

        # At least one Electron tool should be present
        has_electron = any("electron" in tool.lower() for tool in qa_tools)
        assert has_electron, (
            "QA reviewer should have Electron tools when ELECTRON_MCP_ENABLED=true and is_electron=True. "
            f"Got tools: {qa_tools}"
        )

        # Verify specific tools are included
        for tool in ELECTRON_TOOLS:
            assert tool in qa_tools, f"Expected {tool} in qa_reviewer tools"

    @_skip_needs_real
    def test_qa_fixer_has_electron_tools_when_enabled(self, monkeypatch):
        """QA fixer gets Electron tools when ELECTRON_MCP_ENABLED=true and project is Electron."""
        monkeypatch.setenv("ELECTRON_MCP_ENABLED", "true")

        from auto_claude_tools import ELECTRON_TOOLS, get_allowed_tools

        qa_fixer_tools = get_allowed_tools(
            "qa_fixer", project_capabilities={"is_electron": True}
        )

        has_electron = any("electron" in tool.lower() for tool in qa_fixer_tools)
        assert has_electron, (
            "QA fixer should have Electron tools when ELECTRON_MCP_ENABLED=true and is_electron=True. "
            f"Got tools: {qa_fixer_tools}"
        )

        for tool in ELECTRON_TOOLS:
            assert tool in qa_fixer_tools, f"Expected {tool} in qa_fixer tools"

    @_skip_needs_real
    def test_coder_no_electron_tools(self, monkeypatch):
        """Coder should NOT get Electron tools even when enabled and project is Electron."""
        monkeypatch.setenv("ELECTRON_MCP_ENABLED", "true")

        from auto_claude_tools import get_allowed_tools

        coder_tools = get_allowed_tools(
            "coder", project_capabilities={"is_electron": True}
        )

        has_electron = any("electron" in tool.lower() for tool in coder_tools)
        assert not has_electron, (
            "Coder should NOT have Electron tools - they are scoped to QA agents only. "
            "This prevents context token bloat for agents that don't need desktop automation."
        )

    @_skip_needs_real
    def test_planner_no_electron_tools(self, monkeypatch):
        """Planner should NOT get Electron tools even when enabled and project is Electron."""
        monkeypatch.setenv("ELECTRON_MCP_ENABLED", "true")

        from auto_claude_tools import get_allowed_tools

        planner_tools = get_allowed_tools(
            "planner", project_capabilities={"is_electron": True}
        )

        has_electron = any("electron" in tool.lower() for tool in planner_tools)
        assert not has_electron, (
            "Planner should NOT have Electron tools - they are scoped to QA agents only. "
            "This prevents context token bloat for agents that don't need desktop automation."
        )

    @_skip_needs_real
    def test_no_electron_tools_when_disabled(self, monkeypatch):
        """No agent gets Electron tools when ELECTRON_MCP_ENABLED is not set."""
        monkeypatch.delenv("ELECTRON_MCP_ENABLED", raising=False)

        from auto_claude_tools import get_allowed_tools

        for agent_type in ["planner", "coder", "qa_reviewer", "qa_fixer"]:
            tools = get_allowed_tools(
                agent_type, project_capabilities={"is_electron": True}
            )
            has_electron = any("electron" in tool.lower() for tool in tools)
            assert not has_electron, (
                f"{agent_type} should NOT have Electron tools when ELECTRON_MCP_ENABLED is not set"
            )

    def test_electron_tools_defined_in_source(self):
        """Electron tools constant exists in source code."""
        models_path = (
            Path(__file__).parent.parent
            / "apps"
            / "backend"
            / "agents"
            / "tools_pkg"
            / "models.py"
        )
        content = models_path.read_text(encoding="utf-8")
        assert "ELECTRON_TOOLS" in content, (
            "ELECTRON_TOOLS should be defined in agents/tools_pkg/models.py"
        )


class TestSubtaskTerminology:
    """Verify subtask terminology is used consistently."""

    def test_progress_uses_subtask_terminology(self):
        """Progress module uses subtask terminology."""
        progress_path = (
            Path(__file__).parent.parent / "apps" / "backend" / "core" / "progress.py"
        )
        content = progress_path.read_text(encoding="utf-8")

        assert "subtask" in content.lower(), (
            "core/progress.py should use subtask terminology"
        )


def run_tests():
    """Run all tests when executed directly."""
    print("\nTesting Agent Architecture")
    print("=" * 60)

    test_classes = [
        TestNoExternalParallelism,
        TestCLIInterface,
        TestAgentEntryPoint,
        TestAgentPrompt,
        TestModuleIntegrity,
        TestProjectDocumentation,
        TestElectronToolScoping,  # Note: requires pytest (uses monkeypatch)
        TestSubtaskTerminology,
    ]

    passed = 0
    failed = 0

    for test_class in test_classes:
        print(f"\n{test_class.__name__}:")
        instance = test_class()

        for method_name in dir(instance):
            if method_name.startswith("test_"):
                method = getattr(instance, method_name)
                try:
                    method()
                    print(f"  ✓ {method_name}")
                    passed += 1
                except AssertionError as e:
                    print(f"  ✗ {method_name}: {e}")
                    failed += 1
                except Exception as e:
                    print(f"  ✗ {method_name}: Unexpected error: {e}")
                    failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_tests())
