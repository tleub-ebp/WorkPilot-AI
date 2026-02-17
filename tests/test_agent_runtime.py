import pytest
from core.runtimes import create_agent_runtime

class DummyRuntime:
    async def run_session(self, prompt, tools=None):
        return type('Result', (), {'status': 'complete', 'response': 'ok', 'error_info': None})()

def test_agent_runtime_run_session(monkeypatch):
    class DummyConfig:
        is_claude_sdk = False
    # Monkeypatch LiteLLMRuntime to DummyRuntime
    import core.runtimes.litellm_runtime
    core.runtimes.litellm_runtime.LiteLLMRuntime = lambda *a, **kw: DummyRuntime()
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
    import asyncio
    result = asyncio.run(runtime.run_session("prompt"))
    assert result.status == 'complete'
    assert result.response == 'ok'
    assert result.error_info is None
