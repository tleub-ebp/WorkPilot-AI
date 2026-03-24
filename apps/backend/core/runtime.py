"""
Core Runtime Classes for Agent Execution
========================================

Base classes and types for agent runtime implementations.
"""

import asyncio
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class SessionStatus(Enum):
    """Status of an agent session."""

    STARTING = "starting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ERROR = "error"


class ErrorType(Enum):
    """Types of errors that can occur during agent execution."""

    TIMEOUT = "timeout"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    TOOL_ERROR = "tool_error"
    LLM_ERROR = "llm_error"
    UNKNOWN = "unknown"


class StreamEvent:
    """Event emitted during agent execution for streaming."""

    def __init__(self, event_type: str, data: dict[str, Any]):
        self.event_type = event_type
        self.data = data
        self.timestamp = asyncio.get_event_loop().time()


class SessionResult:
    """Result of an agent session."""

    def __init__(
        self,
        status: SessionStatus,
        output: str | None = None,
        error: str | None = None,
        error_type: ErrorType | None = None,
        usage: dict[str, Any] | None = None,
        events: list[StreamEvent] | None = None,
    ):
        self.status = status
        self.output = output
        self.error = error
        self.error_type = error_type
        self.usage = usage or {}
        self.events = events or []

    def is_success(self) -> bool:
        """Check if the session was successful."""
        return self.status == SessionStatus.COMPLETED

    def is_failure(self) -> bool:
        """Check if the session failed."""
        return self.status == SessionStatus.FAILED


class AgentRuntime(ABC):
    """Abstract base class for agent runtime implementations."""

    def __init__(
        self,
        spec_dir: str,
        phase: str,
        project_dir: str,
        agent_type: str,
        config: Any,
        cli_thinking: int | None = None,
    ):
        self.spec_dir = spec_dir
        self.phase = phase
        self.project_dir = project_dir
        self.agent_type = agent_type
        self.config = config
        self.cli_thinking = cli_thinking

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Cleanup if needed
        pass

    @abstractmethod
    async def run_session(
        self, prompt: str, tools: list[dict[str, Any]] | None = None, **kwargs
    ) -> SessionResult:
        """
        Run an agent session.

        Args:
            prompt: The prompt to send to the agent
            tools: Optional list of tools available to the agent
            **kwargs: Additional parameters

        Returns:
            SessionResult with the outcome of the session
        """
        pass

    @abstractmethod
    async def stream_session(
        self, prompt: str, tools: list[dict[str, Any]] | None = None, **kwargs
    ):
        """
        Run an agent session with streaming events.

        Args:
            prompt: The prompt to send to the agent
            tools: Optional list of tools available to the agent
            **kwargs: Additional parameters

        Yields:
            StreamEvent objects with real-time updates
        """
        pass
