import pytest
from core.runtimes import create_agent_runtime

def test_runtime_factory_litellm():
    # Simule un ProviderConfig non-claude
    class DummyConfig:
        is_claude_sdk = False
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
    assert hasattr(runtime, 'run_session')

def test_runtime_factory_claude():
    class DummyConfig:
        is_claude_sdk = True
    with pytest.raises(NotImplementedError):
        create_agent_runtime(
            spec_dir=None,
            phase="test",
            project_dir=None,
            agent_type="test",
            cli_provider=None,
            cli_model=None,
            cli_thinking=None,
            config=DummyConfig(),
        )
