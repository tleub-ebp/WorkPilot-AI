import pytest
from services.provider_registry import list_available_providers, validate_provider, get_provider_status

def test_list_available_providers(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.delenv("CLAUDE_API_KEY", raising=False)
    providers = list_available_providers()
    assert "openai" in providers
    assert "claude_opus" not in providers

def test_validate_provider(monkeypatch):
    monkeypatch.setenv("CLAUDE_API_KEY", "test")
    assert validate_provider("claude_opus")
    assert not validate_provider("groq")

def test_get_provider_status(monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "test")
    status = get_provider_status()
    assert status["mistral"] is True
    assert status["groq"] is False
