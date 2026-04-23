"""
Claude client module facade — **deprecated**.

Prefer ``from core.client import create_client``. This shim stays in
place for any legacy caller that still imports from the root, but
emits a ``DeprecationWarning`` on first access so the migration can
eventually land.

Uses lazy imports to avoid circular dependencies with
``auto_claude_tools``.
"""

import warnings

_DEPRECATION_MESSAGE = (
    "apps.backend.client is deprecated; import from apps.backend.core.client instead."
)


def _warn_once() -> None:
    warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=3)


def __getattr__(name):
    """Lazy import to avoid circular imports with auto_claude_tools."""
    _warn_once()
    from core import client as _client

    return getattr(_client, name)


def create_client(*args, **kwargs):
    """Create a Claude client instance."""
    _warn_once()
    from core.client import create_client as _create_client

    return _create_client(*args, **kwargs)


__all__ = [
    "create_client",
]
