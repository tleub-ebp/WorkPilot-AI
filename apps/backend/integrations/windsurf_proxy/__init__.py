"""
Windsurf Proxy Module
=====================

**Experimental** — the Connect/gRPC protocol used here is brittle and
evolves quickly. Opt in with the ``WORKPILOT_ENABLE_WINDSURF=1`` env var;
otherwise callers of :func:`check_windsurf_enabled` will be told to enable
it explicitly.

Provides dual-mode access to Windsurf/Codeium AI models:

Mode 1 (Local gRPC): Communicates with a running Windsurf IDE's language server
    via HTTP/2 gRPC on localhost. Requires Windsurf IDE to be running and
    authenticated (e.g., via SSO). Ported from opencode-windsurf-auth.

Mode 2 (REST Fallback): Uses the OpenAI-compatible REST API at
    server.codeium.com/api/v1 with a stored API key or OAuth token.
    Works without the IDE running.
"""

import logging
import os

from integrations.windsurf_proxy.auth import (
    WindsurfCredentials,
    WindsurfError,
    WindsurfErrorCode,
    discover_credentials,
    is_windsurf_running,
)

logger = logging.getLogger(__name__)

_ENABLE_ENV = "WORKPILOT_ENABLE_WINDSURF"


def is_windsurf_enabled() -> bool:
    """Return True when the Windsurf integration is explicitly enabled."""
    return os.environ.get(_ENABLE_ENV, "").lower() in ("1", "true", "yes")


def check_windsurf_enabled() -> None:
    """Raise if the Windsurf integration is not explicitly enabled.

    Call this at the entry point of any feature that relies on the Windsurf
    integration so users don't hit obscure gRPC errors before realizing the
    feature is experimental.
    """
    if not is_windsurf_enabled():
        raise RuntimeError(
            "Windsurf integration is experimental and disabled by default. "
            f"Set {_ENABLE_ENV}=1 to enable it."
        )


__all__ = [
    "WindsurfCredentials",
    "WindsurfError",
    "WindsurfErrorCode",
    "check_windsurf_enabled",
    "discover_credentials",
    "is_windsurf_enabled",
    "is_windsurf_running",
]
