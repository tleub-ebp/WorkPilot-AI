"""BaseAgent abstraction.

Common skeleton for the per-task LLM agents (Coder, Planner, QA Reviewer,
QA Fixer, Documenter, Migration, Refactorer…). Captures what every agent
does identically so concrete subclasses only have to implement
`_execute()`:

* lifecycle logging (start / end / error) with workflow_logger
* trace IDs propagated to the workflow_logger
* timing
* uniform `AgentResult` shape so callers don't have to special-case
* injection-guard pass on the input prompt (when one is provided)
* one retry-on-transient-error layer (configurable)

This does NOT replace `scanner_base.BaseScanner`, which is for static
scanners (TechDebt, Flaky tests, etc.) that produce structured reports.
This is for the **interactive LLM agents**.

Adoption is opt-in: existing agents in `agents/` keep working unchanged
until their author migrates them. New agents should subclass
`BaseAgent` directly.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar

logger = logging.getLogger(__name__)

# Generic type for whatever payload the agent returns.
T = TypeVar("T")


class AgentStatus(str, Enum):
    OK = "ok"
    FAILED = "failed"
    BLOCKED = "blocked"  # injection guard or guardrail tripped
    TIMEOUT = "timeout"


@dataclass
class AgentResult(Generic[T]):
    """Uniform return shape across every BaseAgent subclass."""

    status: AgentStatus
    data: T | None = None
    error: str | None = None
    trace_id: str = ""
    duration_seconds: float = 0.0
    retries: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @property
    def ok(self) -> bool:
        return self.status == AgentStatus.OK


@dataclass
class AgentContext:
    """Loose context bag passed to every agent.

    Subclasses are free to subclass this if they need more structure;
    the BaseAgent only cares about the fields it touches for logging.
    """

    project_path: str = ""
    spec_id: str = ""
    correlation_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC, Generic[T]):
    """Common skeleton for interactive LLM agents.

    Subclass and implement `_execute()`. Optionally override
    `_should_retry()` to tweak the retry rule.
    """

    #: Human-readable name used in logs and metrics. Override per subclass.
    name: str = "BaseAgent"

    #: How many times to retry on transient errors. Set to 0 to disable.
    max_retries: int = 0

    #: Hard wall-clock cap for `run()`. None disables.
    timeout_seconds: float | None = None

    #: When True, route the prompt through `injection_guard.guarded_prompt`.
    use_injection_guard: bool = True

    #: When True, SUSPECT prompts also block (in addition to BLOCKED).
    injection_guard_strict: bool = False

    def __init__(self, context: AgentContext | None = None) -> None:
        self.context = context or AgentContext()

    # ------------------------------------------------------------------
    # Public entry points

    async def run(self, prompt: str | None = None, **kwargs: Any) -> AgentResult[T]:
        """Async run with full lifecycle (logging, timing, retry)."""
        trace_id = uuid.uuid4().hex[:12]
        start = time.monotonic()
        self._log_start(trace_id, prompt)

        try:
            self._maybe_guard_prompt(prompt)
        except Exception as e:
            duration = time.monotonic() - start
            self._log_end(trace_id, AgentStatus.BLOCKED, duration, error=str(e))
            return AgentResult(
                status=AgentStatus.BLOCKED,
                error=str(e),
                trace_id=trace_id,
                duration_seconds=duration,
            )

        attempts = 0
        last_error: Exception | None = None
        while attempts <= self.max_retries:
            try:
                if self.timeout_seconds is not None:
                    data = await asyncio.wait_for(
                        self._execute(prompt=prompt, **kwargs),
                        timeout=self.timeout_seconds,
                    )
                else:
                    data = await self._execute(prompt=prompt, **kwargs)
                duration = time.monotonic() - start
                self._log_end(trace_id, AgentStatus.OK, duration, retries=attempts)
                return AgentResult(
                    status=AgentStatus.OK,
                    data=data,
                    trace_id=trace_id,
                    duration_seconds=duration,
                    retries=attempts,
                )
            except asyncio.TimeoutError:
                duration = time.monotonic() - start
                self._log_end(
                    trace_id,
                    AgentStatus.TIMEOUT,
                    duration,
                    retries=attempts,
                    error="timeout",
                )
                return AgentResult(
                    status=AgentStatus.TIMEOUT,
                    error=f"Exceeded timeout of {self.timeout_seconds}s",
                    trace_id=trace_id,
                    duration_seconds=duration,
                    retries=attempts,
                )
            except Exception as e:
                last_error = e
                if attempts >= self.max_retries or not self._should_retry(e):
                    duration = time.monotonic() - start
                    self._log_end(
                        trace_id,
                        AgentStatus.FAILED,
                        duration,
                        retries=attempts,
                        error=str(e),
                    )
                    return AgentResult(
                        status=AgentStatus.FAILED,
                        error=str(e),
                        trace_id=trace_id,
                        duration_seconds=duration,
                        retries=attempts,
                    )
                attempts += 1
                logger.info(
                    "[%s] retry %d/%d after %s: %s",
                    self.name,
                    attempts,
                    self.max_retries,
                    type(e).__name__,
                    e,
                )

        # Unreachable but keeps type-checkers happy.
        duration = time.monotonic() - start
        return AgentResult(
            status=AgentStatus.FAILED,
            error=str(last_error) if last_error else "exhausted retries",
            trace_id=trace_id,
            duration_seconds=duration,
            retries=attempts,
        )

    def run_sync(self, prompt: str | None = None, **kwargs: Any) -> AgentResult[T]:
        """Convenience sync wrapper for callers not in an event loop."""
        return asyncio.run(self.run(prompt=prompt, **kwargs))

    # ------------------------------------------------------------------
    # Hooks for subclasses

    @abstractmethod
    async def _execute(self, prompt: str | None = None, **kwargs: Any) -> T:
        """Do the actual work. Subclasses MUST implement.

        Raise on failure — the base wrapper handles logging + retry.
        """

    def _should_retry(self, exc: Exception) -> bool:
        """Return True if `exc` is worth retrying. Default: never.

        Override in subclasses to whitelist transient errors (rate limits,
        network blips, etc.). Don't retry programming errors.
        """
        _ = exc
        return False

    # ------------------------------------------------------------------
    # Internals

    def _maybe_guard_prompt(self, prompt: str | None) -> None:
        if not self.use_injection_guard or not prompt:
            return
        # Lazy import so test environments without injection_guard wired
        # up still load the BaseAgent module.
        from injection_guard import guarded_prompt

        guarded_prompt(
            prompt,
            source=self.name,
            strict=self.injection_guard_strict,
        )

    def _log_start(self, trace_id: str, prompt: str | None) -> None:
        prompt_preview = (prompt or "")[:80].replace("\n", " ")
        logger.info(
            "[%s] start trace=%s spec=%s prompt=%r",
            self.name,
            trace_id,
            self.context.spec_id or "-",
            prompt_preview,
        )

    def _log_end(
        self,
        trace_id: str,
        status: AgentStatus,
        duration: float,
        retries: int = 0,
        error: str | None = None,
    ) -> None:
        if status == AgentStatus.OK:
            logger.info(
                "[%s] end trace=%s status=%s dur=%.3fs retries=%d",
                self.name,
                trace_id,
                status.value,
                duration,
                retries,
            )
        else:
            logger.warning(
                "[%s] end trace=%s status=%s dur=%.3fs retries=%d error=%s",
                self.name,
                trace_id,
                status.value,
                duration,
                retries,
                error or "?",
            )
