"""Reusable middleware to scan prompts before they reach an LLM.

Wraps any callable that takes a prompt string and returns a string. If
the scanner says BLOCK, we raise `PromptInjectionBlocked` instead of
calling through. SUSPECT is logged but allowed through (unless the
caller passed `strict=True`).

Usage from a runner:

    from injection_guard import guarded_prompt
    safe_prompt = guarded_prompt(user_prompt, source="github_pr_review")
    response = await llm_client.chat(safe_prompt)
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from .scanner import InjectionScanner, ScanResult, ThreatLevel

logger = logging.getLogger(__name__)


class PromptInjectionBlocked(Exception):
    """Raised when the scanner determines a prompt is hostile."""

    def __init__(self, scan: ScanResult) -> None:
        self.scan = scan
        descriptions = "; ".join(f.description for f in scan.findings) or "no findings"
        super().__init__(
            f"Prompt blocked by injection guard ({scan.threat_level.value}): "
            f"{descriptions}"
        )


# Module-level singleton — cheap to construct but no need to recreate
# the regex table on every call.
_DEFAULT_SCANNER: InjectionScanner | None = None


def get_default_scanner() -> InjectionScanner:
    global _DEFAULT_SCANNER
    if _DEFAULT_SCANNER is None:
        _DEFAULT_SCANNER = InjectionScanner()
    return _DEFAULT_SCANNER


def guarded_prompt(
    text: str,
    source: str = "unknown",
    strict: bool = False,
    scanner: InjectionScanner | None = None,
) -> str:
    """Validate a prompt before forwarding it to an LLM.

    Args:
        text: the prompt about to be sent.
        source: free-form label propagated to the scan result for telemetry
            (e.g. "github_pr_review", "spec_writer", "user_chat").
        strict: when True, SUSPECT also blocks. Default: only BLOCK blocks.
        scanner: optional scanner override (defaults to a process singleton).

    Returns:
        The same `text` unmodified — we only validate, we don't rewrite.
    """
    if not text:
        return text
    sc = scanner or get_default_scanner()
    result = sc.scan(text, source=source)

    if result.threat_level == ThreatLevel.BLOCKED:
        logger.warning(
            "Injection guard BLOCKED prompt from %s: %s",
            source,
            "; ".join(f.description for f in result.findings),
        )
        raise PromptInjectionBlocked(result)

    if result.threat_level == ThreatLevel.SUSPECT:
        logger.info(
            "Injection guard SUSPECT prompt from %s (allowing): %s",
            source,
            "; ".join(f.description for f in result.findings),
        )
        if strict:
            raise PromptInjectionBlocked(result)

    return text


# ---------------------------------------------------------------------------
# Decorator helper for runners that take a prompt as their first arg

P = ParamSpec("P")
R = TypeVar("R")


def guard_runner(
    source: str, strict: bool = False
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator that auto-scans the first positional argument as a prompt.

    Synchronous variant. For async runners use `guard_async_runner`.
    """

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        @wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            if args and isinstance(args[0], str):
                guarded_prompt(args[0], source=source, strict=strict)
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def guard_async_runner(
    source: str, strict: bool = False
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Async variant of `guard_runner`."""

    def decorator(fn: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            if args and isinstance(args[0], str):
                guarded_prompt(args[0], source=source, strict=strict)
            return await fn(*args, **kwargs)

        return wrapper

    return decorator


def reset_default_scanner_for_tests() -> None:
    """Test hook — drop the singleton so a fresh one is built next call."""
    global _DEFAULT_SCANNER
    _DEFAULT_SCANNER = None


# Re-export the type for convenience
__all__ = [
    "PromptInjectionBlocked",
    "guard_async_runner",
    "guard_runner",
    "guarded_prompt",
    "get_default_scanner",
    "reset_default_scanner_for_tests",
]
