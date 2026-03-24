"""
LLM Client Classes
==================

Client classes for interacting with various LLM providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolCall:
    """Represents a tool call request from an LLM."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ToolResult:
    """Represents the result of a tool execution."""

    tool_call_id: str
    result: Any
    error: str | None = None


@dataclass
class Usage:
    """Token usage information."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LLMResponse:
    """Base response from an LLM."""

    content: str
    usage: Usage | None = None
    finish_reason: str | None = None


@dataclass
class LLMToolResponse(LLMResponse):
    """Response from an LLM that includes tool calls."""

    tool_calls: list[ToolCall] = None

    def has_tool_calls(self) -> bool:
        """Check if the response includes tool calls."""
        return bool(self.tool_calls)


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    def __init__(
        self,
        provider: str,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
        **kwargs,
    ):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    def from_provider_config(cls, config: Any) -> "LLMClient":
        """Create an LLM client from a provider configuration."""
        return cls(
            provider=config.provider,
            model=config.model,
            api_key=getattr(config, "api_key", None),
            base_url=getattr(config, "base_url", None),
        )

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate a completion from the LLM.

        Args:
            prompt: The prompt to send
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters

        Returns:
            LLMResponse with the generated content
        """
        pass

    @abstractmethod
    async def complete_with_tools(
        self,
        prompt: str,
        tools: list[dict[str, Any]],
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs,
    ) -> LLMToolResponse:
        """
        Generate a completion with tool calling support.

        Args:
            prompt: The prompt to send
            tools: List of available tools
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters

        Returns:
            LLMToolResponse with content and optional tool calls
        """
        pass

    async def stream_complete(
        self,
        prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs,
    ):
        """
        Stream a completion from the LLM.

        Args:
            prompt: The prompt to send
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters

        Yields:
            Chunks of the generated content
        """
        # Default implementation - just return the complete response
        response = await self.complete(prompt, max_tokens, temperature, **kwargs)
        yield response.content


class ConcreteLLMClient(LLMClient):
    """Concrete implementation of LLMClient for testing."""

    async def complete(
        self,
        prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate a completion from the LLM."""
        # Simple mock implementation
        return LLMResponse(
            content=f"Mock response for {self.provider} model {self.model}: {prompt[:100]}...",
            usage=Usage(
                prompt_tokens=len(prompt) // 4, completion_tokens=len(prompt) // 4
            ),
        )

    async def complete_with_tools(
        self,
        prompt: str,
        tools: list[dict[str, Any]],
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs,
    ) -> LLMToolResponse:
        """Generate a completion with tool calling support."""
        # Simple mock implementation
        return LLMToolResponse(
            content=f"Mock response for {self.provider} model {self.model}: {prompt[:100]}...",
            tool_calls=[],
        )

    async def stream_complete(
        self,
        prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs,
    ):
        """Stream a completion from the LLM."""
        response = await self.complete(prompt, max_tokens, temperature, **kwargs)
        yield response.content
