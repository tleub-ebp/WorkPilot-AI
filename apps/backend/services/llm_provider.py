"""
LLM Provider Abstraction for Multi-Provider Support
"""
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate a response from the LLM given a prompt."""
        pass

# Example provider for Claude Opus (to be implemented)
class ClaudeOpusProvider(LLMProvider):
    def generate(self, prompt: str, **kwargs) -> str:
        # TODO: Implement call to Claude Opus API or local instance
        return f"[Claude Opus] {prompt}"

# Example provider for Claude Sonnet (to be implemented)
class ClaudeSonnetProvider(LLMProvider):
    def generate(self, prompt: str, **kwargs) -> str:
        # TODO: Implement call to Claude Sonnet API or local instance
        return f"[Claude Sonnet] {prompt}"

# Example provider for local LLM (to be implemented)
class LocalLLMProvider(LLMProvider):
    def generate(self, prompt: str, **kwargs) -> str:
        # TODO: Implement call to local LLM
        return f"[Local LLM] {prompt}"

# Factory for dynamic provider selection
import provider_api

def get_llm_provider() -> LLMProvider:
    provider_name = provider_api.get_selected_provider()
    if not provider_name:
        import os
        provider_name = os.getenv("LLM_PROVIDER", "anthropic").lower()
    else:
        provider_name = provider_name.lower()
    if provider_name in ["anthropic", "claude"]:
        return ClaudeOpusProvider()
    elif provider_name == "openai":
        return ClaudeSonnetProvider()
    elif provider_name == "local":
        return LocalLLMProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {provider_name}")