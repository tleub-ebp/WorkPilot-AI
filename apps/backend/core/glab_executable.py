#!/usr/bin/env python3
"""
GitLab CLI Executable Finder
============================

Utility to find the glab (GitLab CLI) executable, with platform-specific fallbacks.
"""

import os
import shutil
import subprocess

_cached_glab_path: str | None = None


def invalidate_glab_cache() -> None:
    """Invalidate the cached glab executable path.

    Useful when glab may have been uninstalled, updated, or when
    GITLAB_CLI_PATH environment variable has changed.
    """
    global _cached_glab_path
    _cached_glab_path = None


def _verify_glab_executable(path: str) -> bool:
    """Verify that a path is a valid glab executable by checking version.

    Args:
        path: Path to the potential glab executable

    Returns:
        True if the path points to a valid glab executable, False otherwise
    """
    try:
        result = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def _run_where_command() -> str | None:
    """Find glab executable using shutil.which() (cross-platform).

    Returns:
        Path to glab executable, or None if not found
    """
    found_path = shutil.which("glab")
    if (
        found_path
        and os.path.isfile(found_path)
        and _verify_glab_executable(found_path)
    ):
        return found_path
    return None


def get_glab_executable() -> str | None:
    """Find the glab executable, with platform-specific fallbacks.

    Returns the path to glab executable, or None if not found.

    Priority order:
    1. GITLAB_CLI_PATH env var (user-configured path from frontend)
    2. shutil.which (if glab is in PATH)
    3. Homebrew paths on macOS
    4. Windows Program Files paths
    5. Windows 'where' command

    Caches the result after first successful find. Use invalidate_glab_cache()
    to force re-detection (e.g., after glab installation/uninstallation).
    """
    global _cached_glab_path

    # Return cached result if available AND still exists
    if _cached_glab_path is not None and os.path.isfile(_cached_glab_path):
        return _cached_glab_path

    _cached_glab_path = _find_glab_executable()
    return _cached_glab_path


def _find_glab_executable() -> str | None:
    """Internal function to find glab executable."""
    # 1. Check GITLAB_CLI_PATH env var (set by Electron frontend)
    env_path = _check_env_path()
    if env_path:
        return env_path

    # 2. Try shutil.which (works if glab is in PATH)
    system_path = _check_system_path()
    if system_path:
        return system_path

    # 3-4. Platform-specific paths
    platform_path = _check_platform_paths()
    if platform_path:
        return platform_path

    # 5. Windows-specific: Try 'where' command
    return _run_where_command() if os.name == "nt" else None


def _check_env_path() -> str | None:
    """Check GITLAB_CLI_PATH environment variable."""
    env_path = os.environ.get("GITLAB_CLI_PATH")
    if env_path and os.path.isfile(env_path) and _verify_glab_executable(env_path):
        return env_path
    return None


def _check_system_path() -> str | None:
    """Check system PATH for glab executable."""
    glab_path = shutil.which("glab")
    if glab_path and _verify_glab_executable(glab_path):
        return glab_path
    return None


def _check_platform_paths() -> str | None:
    """Check platform-specific installation paths."""
    if os.name != "nt":  # Unix-like systems (macOS, Linux)
        return _check_unix_paths()
    else:  # Windows
        return _check_windows_paths()


def _check_unix_paths() -> str | None:
    """Check Unix-like system paths (macOS/Linux Homebrew)."""
    homebrew_paths = [
        "/opt/homebrew/bin/glab",  # Apple Silicon
        "/usr/local/bin/glab",  # Intel Mac
        "/home/linuxbrew/.linuxbrew/bin/glab",  # Linux Homebrew
    ]
    return _find_valid_path(homebrew_paths)


def _check_windows_paths() -> str | None:
    """Check Windows-specific installation paths."""
    windows_paths = [
        os.path.expandvars(r"%PROGRAMFILES%\glab\glab.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\glab\glab.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\glab\glab.exe"),
    ]
    return _find_valid_path(windows_paths)


def _find_valid_path(paths: list[str]) -> str | None:
    """Find first valid path from a list of candidate paths."""
    for path in paths:
        if os.path.isfile(path) and _verify_glab_executable(path):
            return path
    return None


def run_glab(
    args: list[str],
    cwd: str | None = None,
    timeout: int = 60,
    input_data: str | None = None,
) -> subprocess.CompletedProcess:
    """Run a glab command with proper executable finding.

    Args:
        args: glab command arguments (without 'glab' prefix)
        cwd: Working directory for the command
        timeout: Command timeout in seconds (default: 60)
        input_data: Optional string data to pass to stdin

    Returns:
        CompletedProcess with command results.
    """
    glab = get_glab_executable()
    if not glab:
        return subprocess.CompletedProcess(
            args=["glab"] + args,
            returncode=-1,
            stdout="",
            stderr="GitLab CLI (glab) not found. Install from https://gitlab.com/gitlab-org/cli",
        )
    try:
        return subprocess.run(
            [glab] + args,
            cwd=cwd,
            input=input_data,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args=[glab] + args,
            returncode=-1,
            stdout="",
            stderr=f"Command timed out after {timeout} seconds",
        )
    except FileNotFoundError:
        return subprocess.CompletedProcess(
            args=[glab] + args,
            returncode=-1,
            stdout="",
            stderr="GitLab CLI (glab) executable not found. Install from https://gitlab.com/gitlab-org/cli",
        )
