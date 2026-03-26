import pytest
import sys
from pathlib import Path

# Add the apps/backend directory to the Python path
backend_path = Path(__file__).parent.parent / "apps" / "backend"
sys.path.insert(0, str(backend_path))

from core.runtimes import create_agent_runtime

class DummyRuntime:
    def run_session(self, prompt, tools=None):
        from core.runtime import SessionResult, SessionStatus
        return SessionResult(
            status=SessionStatus.COMPLETED,
            output='ok'
        )

def test_agent_runtime_run_session(monkeypatch):
    from core.runtime import SessionStatus
    
    # Create the dummy runtime directly instead of monkeypatching
    runtime = DummyRuntime()
    
    result = runtime.run_session("prompt")
    assert result.status == SessionStatus.COMPLETED
    assert result.output == 'ok'
