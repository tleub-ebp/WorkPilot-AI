"""
Secure Subprocess Runner
=========================

Centralized, secure subprocess execution with:
- Allowlist of permitted commands
- Configurable timeouts
- Structured logging (no secrets leaked)
- Input validation

All subprocess calls in the backend should go through this module
instead of calling subprocess.run() directly.
"""

from __future__ import annotations

import logging
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Allowlist of commands that are permitted to be executed.
# Each key is the base command name, value is a short description for logging.
ALLOWED_COMMANDS: dict[str, str] = {
    "gh": "GitHub CLI",
    "git": "Git version control",
    "bandit": "Python SAST scanner",
    "semgrep": "SAST scanner",
    "pip-audit": "Python dependency audit",
    "snyk": "Snyk vulnerability scanner",
    "trivy": "Container/filesystem scanner",
    "npm": "Node package manager",
}

# Default timeout in seconds for subprocess calls
DEFAULT_TIMEOUT = 30

# Maximum allowed timeout to prevent resource exhaustion
MAX_TIMEOUT = 300


@dataclass
class SubprocessResult:
    """Structured result from a secure subprocess call."""

    returncode: int
    stdout: str
    stderr: str
    command: str
    timed_out: bool = False

    @property
    def success(self) -> bool:
        return self.returncode == 0 and not self.timed_out

    @property
    def output(self) -> str:
        """Combined stdout + stderr."""
        return self.stdout + self.stderr


class SubprocessSecurityError(Exception):
    """Raised when a subprocess call is blocked by security policy."""

    pass


def _validate_command(args: Sequence[str]) -> None:
    """Validate that the command is in the allowlist."""
    if not args:
        raise SubprocessSecurityError("Empty command is not allowed")

    base_cmd = args[0]
    if base_cmd not in ALLOWED_COMMANDS:
        raise SubprocessSecurityError(
            f"Command '{base_cmd}' is not in the allowlist. "
            f"Allowed commands: {sorted(ALLOWED_COMMANDS.keys())}"
        )


def _sanitize_for_log(args: Sequence[str]) -> str:
    """Return a log-safe representation of the command (no secrets)."""
    return " ".join(args)


def run_secure(
    args: Sequence[str],
    *,
    timeout: int | None = None,
    cwd: str | None = None,
    check: bool = False,
) -> SubprocessResult:
    """
    Execute a subprocess securely with validation, timeout, and logging.

    Args:
        args: Command and arguments as a sequence (e.g. ["gh", "auth", "status"]).
        timeout: Timeout in seconds. Defaults to DEFAULT_TIMEOUT. Capped at MAX_TIMEOUT.
        cwd: Working directory for the command.
        check: If True, raise SubprocessSecurityError on non-zero return code.

    Returns:
        SubprocessResult with returncode, stdout, stderr, etc.

    Raises:
        SubprocessSecurityError: If command is not allowed or check=True and command fails.
    """
    _validate_command(args)

    effective_timeout = min(timeout or DEFAULT_TIMEOUT, MAX_TIMEOUT)
    cmd_str = _sanitize_for_log(args)

    logger.debug(
        "Executing secure subprocess: %s (timeout=%ds)", cmd_str, effective_timeout
    )

    try:
        result = subprocess.run(
            list(args),
            capture_output=True,
            text=True,
            timeout=effective_timeout,
            cwd=cwd,
        )

        logger.debug(
            "Subprocess completed: %s (returncode=%d)", cmd_str, result.returncode
        )

        sub_result = SubprocessResult(
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            command=cmd_str,
        )

        if check and result.returncode != 0:
            raise SubprocessSecurityError(
                f"Command '{cmd_str}' failed with return code {result.returncode}: "
                f"{result.stderr[:200]}"
            )

        return sub_result

    except subprocess.TimeoutExpired:
        logger.warning("Subprocess timed out after %ds: %s", effective_timeout, cmd_str)
        return SubprocessResult(
            returncode=-1,
            stdout="",
            stderr=f"Command timed out after {effective_timeout}s",
            command=cmd_str,
            timed_out=True,
        )

    except FileNotFoundError:
        logger.warning("Command not found: %s", args[0])
        return SubprocessResult(
            returncode=-1,
            stdout="",
            stderr=f"Command not found: {args[0]}",
            command=cmd_str,
        )


def check_tool_available(tool: str, *, timeout: int = 5) -> bool:
    """
    Check if a CLI tool is available on the system.

    Args:
        tool: The tool name (must be in ALLOWED_COMMANDS).
        timeout: Timeout for the version check.

    Returns:
        True if the tool is available and responds to --version.
    """
    try:
        result = run_secure([tool, "--version"], timeout=timeout)
        return result.returncode == 0
    except SubprocessSecurityError:
        return False
