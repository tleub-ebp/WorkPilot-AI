#!/usr/bin/env python3
"""
GitHub CLI Executable Finder
============================

Utility to find the gh (GitHub CLI) executable, with platform-specific fallbacks.
"""

import os
import shutil
import subprocess

_cached_gh_path: str | None = None


def invalidate_gh_cache() -> None:
    """Invalidate the cached gh executable path.

    Useful when gh may have been uninstalled, updated, or when
    GITHUB_CLI_PATH environment variable has changed.
    """
    global _cached_gh_path
    _cached_gh_path = None


def _verify_gh_executable(path: str) -> bool:
    """Verify that a path is a valid gh executable by checking version.

    Args:
        path: Path to the potential gh executable

    Returns:
        True if the path points to a valid gh executable, False otherwise
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
    """Find gh executable using shutil.which() (cross-platform).

    Returns:
        Path to gh executable, or None if not found
    """
    found_path = shutil.which("gh")
    if found_path and os.path.isfile(found_path) and _verify_gh_executable(found_path):
        return found_path
    return None


def get_gh_executable() -> str | None:
    """Find the gh executable, with platform-specific fallbacks.

    Returns the path to gh executable, or None if not found.

    Priority order:
    1. GITHUB_CLI_PATH env var (user-configured path from frontend)
    2. shutil.which (if gh is in PATH)
    3. Homebrew paths on macOS
    4. Windows Program Files paths
    5. Windows 'where' command

    Caches the result after first successful find. Use invalidate_gh_cache()
    to force re-detection (e.g., after gh installation/uninstallation).
    """
    global _cached_gh_path

    # Return cached result if available AND still exists
    if _cached_gh_path is not None and os.path.isfile(_cached_gh_path):
        return _cached_gh_path

    _cached_gh_path = _find_gh_executable()
    return _cached_gh_path


def _find_gh_executable() -> str | None:
    """Internal function to find gh executable."""
    # 1. Check GITHUB_CLI_PATH env var (set by Electron frontend)
    env_path = _check_env_path()
    if env_path:
        return env_path

    # 2. Try shutil.which (works if gh is in PATH)
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
    """Check GITHUB_CLI_PATH environment variable."""
    env_path = os.environ.get("GITHUB_CLI_PATH")
    if env_path and os.path.isfile(env_path) and _verify_gh_executable(env_path):
        return env_path
    return None


def _check_system_path() -> str | None:
    """Check system PATH for gh executable."""
    gh_path = shutil.which("gh")
    if gh_path and _verify_gh_executable(gh_path):
        return gh_path
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
        "/opt/homebrew/bin/gh",  # Apple Silicon
        "/usr/local/bin/gh",  # Intel Mac
        "/home/linuxbrew/.linuxbrew/bin/gh",  # Linux Homebrew
    ]
    return _find_valid_path(homebrew_paths)


def _check_windows_paths() -> str | None:
    """Check Windows-specific installation paths."""
    windows_paths = [
        os.path.expandvars(r"%PROGRAMFILES%\GitHub CLI\gh.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\GitHub CLI\gh.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\GitHub CLI\gh.exe"),
    ]
    return _find_valid_path(windows_paths)


def _find_valid_path(paths: list[str]) -> str | None:
    """Find first valid path from a list of candidate paths."""
    for path in paths:
        if os.path.isfile(path) and _verify_gh_executable(path):
            return path
    return None


def run_gh(
    args: list[str],
    cwd: str | None = None,
    timeout: int = 60,
    input_data: str | None = None,
) -> subprocess.CompletedProcess:
    """Run a gh command with proper executable finding.

    Args:
        args: gh command arguments (without 'gh' prefix)
        cwd: Working directory for the command
        timeout: Command timeout in seconds (default: 60)
        input_data: Optional string data to pass to stdin

    Returns:
        CompletedProcess with command results.
    """
    gh = get_gh_executable()
    if not gh:
        return subprocess.CompletedProcess(
            args=["gh"] + args,
            returncode=-1,
            stdout="",
            stderr="GitHub CLI (gh) not found. Install from https://cli.github.com/",
        )
    try:
        return subprocess.run(
            [gh] + args,
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
            args=[gh] + args,
            returncode=-1,
            stdout="",
            stderr=f"Command timed out after {timeout} seconds",
        )
    except FileNotFoundError:
        return subprocess.CompletedProcess(
            args=[gh] + args,
            returncode=-1,
            stdout="",
            stderr="GitHub CLI (gh) executable not found. Install from https://cli.github.com/",
        )
