"""
Tests d'intégration pour les providers LLM concrets (OpenAI, Claude, Ollama, Google, Anthropic).
Utilise des clés factices et vérifie la robustesse de l'instanciation et de la validation.
"""
import pytest
from src.connectors.llm_openai import OpenAIProvider
from src.connectors.llm_claude import ClaudeProvider
from src.connectors.llm_ollama import OllamaProvider
from src.connectors.llm_google import GoogleLLMProvider
from src.connectors.llm_anthropic import AnthropicProvider

@pytest.mark.parametrize("provider_cls,kwargs,should_validate", [
    (OpenAIProvider, {"api_key": "sk-test", "model": "gpt-3.5-turbo"}, False),
    (ClaudeProvider, {"api_key": "sk-test", "model": "claude-3-sonnet-20240229"}, True),
    (OllamaProvider, {"model": "llama2"}, False),
    (GoogleLLMProvider, {"api_key": "test", "model": "gemini-2.0-flash"}, False),
    (AnthropicProvider, {"api_key": "sk-ant-test", "model": "claude-3-sonnet-20240229"}, True),
])
def test_provider_instantiation_and_validation(provider_cls, kwargs, should_validate):
    provider = provider_cls(**kwargs)
    assert hasattr(provider, "connect")
    assert hasattr(provider, "validate")
    assert hasattr(provider, "generate")
    assert hasattr(provider, "get_capabilities")
    assert hasattr(provider, "get_config_schema")
    assert hasattr(provider, "get_name")
    # New: get_name should be callable on the class
    assert isinstance(provider_cls.get_name(), str)
    assert provider.validate() == should_validate