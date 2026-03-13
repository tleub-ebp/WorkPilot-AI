"""
Windsurf Proxy Module
=====================

Provides dual-mode access to Windsurf/Codeium AI models:

Mode 1 (Local gRPC): Communicates with a running Windsurf IDE's language server
    via HTTP/2 gRPC on localhost. Requires Windsurf IDE to be running and
    authenticated (e.g., via SSO). Ported from opencode-windsurf-auth.

Mode 2 (REST Fallback): Uses the OpenAI-compatible REST API at
    server.codeium.com/api/v1 with a stored API key or OAuth token.
    Works without the IDE running.
"""

from integrations.windsurf_proxy.auth import (
    WindsurfCredentials,
    WindsurfError,
    WindsurfErrorCode,
    discover_credentials,
    is_windsurf_running,
)

__all__ = [
    "WindsurfCredentials",
    "WindsurfError",
    "WindsurfErrorCode",
    "discover_credentials",
    "is_windsurf_running",
]
