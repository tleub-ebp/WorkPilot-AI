import sys
from pathlib import Path

import pytest

# Add the apps/backend directory to the Python path
backend_path = Path(__file__).parent.parent / "apps" / "backend"
sys.path.insert(0, str(backend_path))

from core.runtimes import create_agent_runtime


def test_runtime_factory_litellm():
    # Simule un ProviderConfig non-claude
    class DummyConfig:
        is_claude_sdk = False
        provider = "openai"
        model = "gpt-3.5-turbo"
        api_key = "test-key"
        base_url = None
    runtime = create_agent_runtime(
        spec_dir=None,
        phase="test",
        project_dir="C:\\test\\project",  # Provide a valid path
        agent_type="test",
        cli_provider=None,
        cli_model=None,
        cli_thinking=None,
        config=DummyConfig(),
    )
    assert runtime is not None
    assert hasattr(runtime, 'run_session')

def test_runtime_factory_claude():
    """Claude SDK runtime is now a real runtime (not NotImplementedError)."""
    from core.runtimes.claude_sdk_runtime import ClaudeSDKRuntime

    class DummyConfig:
        is_claude_sdk = True
    # The factory now returns a ClaudeSDKRuntime instead of raising NotImplementedError
    runtime = create_agent_runtime(
        spec_dir=None,
        phase="test",
        project_dir=None,
        agent_type="test",
        cli_provider=None,
        cli_model=None,
        cli_thinking=None,
        config=DummyConfig(),
    )
    assert runtime is not None
    assert isinstance(runtime, ClaudeSDKRuntime)
