"""
Windsurf Credential Discovery
==============================

Automatically discovers credentials from the running Windsurf language server:
- CSRF token from process arguments
- Port from process listening sockets
- API key from VSCode state database or config files
- Version from process arguments

Ported from opencode-windsurf-auth/src/plugin/auth.ts
"""

import json
import logging
import os
import platform
import re
import sqlite3
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


# =============================================================================
# Types
# =============================================================================


class WindsurfErrorCode(str, Enum):
    NOT_RUNNING = "NOT_RUNNING"
    CSRF_MISSING = "CSRF_MISSING"
    API_KEY_MISSING = "API_KEY_MISSING"
    CONNECTION_FAILED = "CONNECTION_FAILED"
    AUTH_FAILED = "AUTH_FAILED"
    STREAM_ERROR = "STREAM_ERROR"


class WindsurfError(Exception):
    """Error raised when Windsurf credential discovery fails."""

    def __init__(self, message: str, code: WindsurfErrorCode, details: object = None):
        super().__init__(message)
        self.code = code
        self.details = details


@dataclass
class WindsurfCredentials:
    """Credentials needed to communicate with the Windsurf language server."""

    csrf_token: str
    port: int
    api_key: str
    version: str


# =============================================================================
# Platform-specific paths
# =============================================================================

_SYSTEM = platform.system()  # "Windows", "Darwin", "Linux"

VSCDB_FILENAME = "state.vscdb"

_VSCDB_PATHS = {
    "Windows": Path(os.environ.get("APPDATA", "")) / "Windsurf" / "User" / "globalStorage" / VSCDB_FILENAME,
    "Darwin": Path.home() / "Library" / "Application Support" / "Windsurf" / "User" / "globalStorage" / VSCDB_FILENAME,
    "Linux": Path.home() / ".config" / "Windsurf" / "User" / "globalStorage" / VSCDB_FILENAME,
}

_LEGACY_CONFIG_PATH = Path.home() / ".codeium" / "config.json"

_LANGUAGE_SERVER_PATTERNS = {
    "Darwin": "language_server_macos",
    "Linux": "language_server_linux",
    "Windows": "language_server_windows",
}


# =============================================================================
# Process Discovery
# =============================================================================


def _get_language_server_pattern() -> str:
    """Get the language server process pattern for the current platform."""
    return _LANGUAGE_SERVER_PATTERNS.get(_SYSTEM, "language_server")


_PROCESS_CACHE: tuple[str | None, float] | None = None
_PROCESS_CACHE_TTL = 10.0  # seconds


def invalidate_process_cache() -> None:
    """Force the next call to _get_language_server_process() to do a fresh discovery.

    Must be called before discover_credentials() when retrying after a Cascade
    session error — otherwise the 10-second TTL cache returns the same (potentially
    stale) CSRF token that triggered the failure in the first place.
    """
    global _PROCESS_CACHE
    _PROCESS_CACHE = None


def _get_language_server_process() -> str | None:
    """Get the language server process listing.

    Results are cached for 10 seconds to avoid spawning multiple wmic/ps
    subprocesses during a single credential discovery flow.
    """
    import time as _time

    global _PROCESS_CACHE

    now = _time.monotonic()
    if _PROCESS_CACHE is not None:
        cached_value, cached_at = _PROCESS_CACHE
        if now - cached_at < _PROCESS_CACHE_TTL:
            return cached_value

    result = _discover_language_server_process()
    _PROCESS_CACHE = (result, now)
    return result


def _discover_language_server_process() -> str | None:
    """Actually discover the language server process (uncached)."""
    pattern = _get_language_server_pattern()

    try:
        if _SYSTEM == "Windows":
            # Try PowerShell first (wmic is deprecated on Windows 11)
            output = _discover_via_powershell(pattern)
            if output:
                return output

            # Fallback: wmic (still works on many Windows versions)
            output = _discover_via_wmic(pattern)
            return output
        else:
            output = subprocess.check_output(
                ["ps", "aux"],
                encoding="utf-8",
                timeout=5,
                stderr=subprocess.DEVNULL,
            )
            # Filter lines containing the pattern
            lines = [line for line in output.splitlines() if pattern in line and "grep" not in line]
            return "\n".join(lines) if lines else None
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, UnicodeDecodeError):
        return None


def _discover_via_powershell(pattern: str) -> str | None:
    """Discover language server process via PowerShell (preferred on Windows 11+)."""
    try:
        # Use PowerShell to get both ProcessId and CommandLine.
        # The backtick-n in PowerShell is a newline escape; we pass it literally.
        ps_cmd = (
            "Get-CimInstance Win32_Process -Filter "
            f"\"name like '%{pattern}%'\" "
            "| ForEach-Object { "
            "'ProcessId=' + [string]$_.ProcessId + \"`n\" + "
            "'CommandLine=' + $_.CommandLine "
            "}"
        )
        output = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            encoding="utf-8",
            errors="replace",
            timeout=10,
            stderr=subprocess.DEVNULL,
        )
        return output if output.strip() else None
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, UnicodeDecodeError):
        return None


def _discover_via_wmic(pattern: str) -> str | None:
    """Discover language server process via wmic (legacy fallback)."""
    try:
        output = subprocess.check_output(
            ["wmic", "process", "where", f"name like '%{pattern}%'", "get", "CommandLine", "/format:list"],
            encoding="utf-8",
            errors="replace",
            timeout=5,
            stderr=subprocess.DEVNULL,
        )
        if not output.strip():
            # Try alternative with ProcessId
            output = subprocess.check_output(
                ["wmic", "process", "where", f"commandline like '%{pattern}%'", "get", "CommandLine,ProcessId", "/format:list"],
                encoding="utf-8",
                errors="replace",
                timeout=5,
                stderr=subprocess.DEVNULL,
            )
        return output if output.strip() else None
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, UnicodeDecodeError):
        return None


# =============================================================================
# CSRF Token Discovery
# =============================================================================


def _get_csrf_token_from_state_db() -> str | None:
    """Get CSRF token from state.vscdb (for newer Windsurf versions).

    Newer Windsurf versions (1.9500+) pass the CSRF token via
    --stdin_initial_metadata instead of --csrf_token CLI argument.
    The token is still stored in state.vscdb under the key
    'codeium.windsurf-windsurf_auth-'.
    """
    state_path = _VSCDB_PATHS.get(_SYSTEM)
    if not state_path or not state_path.exists():
        return None

    try:
        conn = sqlite3.connect(str(state_path))
        cursor = conn.execute(
            "SELECT value FROM ItemTable WHERE key = 'codeium.windsurf-windsurf_auth-'"
        )
        row = cursor.fetchone()
        conn.close()

        if row and row[0]:
            value = row[0].strip()
            # Validate it looks like a UUID/CSRF token (hex chars and dashes)
            if re.match(r"^[a-f0-9-]{8,}$", value):
                logger.debug("[WindsurfAuth] Found CSRF token from state.vscdb")
                return value
    except sqlite3.Error as e:
        logger.debug(f"[WindsurfAuth] Failed to read CSRF from state.vscdb: {e}")

    return None


def _get_csrf_token_from_process_env() -> str | None:
    """Read WINDSURF_CSRF_TOKEN from the running language server process env.

    Newer Windsurf versions (1.9500+) pass the CSRF token via
    --stdin_initial_metadata at startup.  The language server stores it
    as the environment variable ``WINDSURF_CSRF_TOKEN``.  Reading it via
    psutil is the most reliable approach because state.vscdb may contain
    a stale token from a previous session.
    """
    try:
        import psutil
    except ImportError:
        logger.debug("[WindsurfAuth] psutil not available for process env CSRF discovery")
        return None

    pattern = _get_language_server_pattern()

    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            name = proc.info.get("name", "") or ""
            cmdline = proc.info.get("cmdline") or []
            cmdline_str = " ".join(cmdline)

            # Match the language server process
            if pattern not in name.lower() and pattern not in cmdline_str.lower():
                continue
            if "windsurf" not in cmdline_str.lower() and "codeium" not in cmdline_str.lower():
                continue

            env = proc.environ()
            csrf = env.get("WINDSURF_CSRF_TOKEN")
            if csrf and re.match(r"^[a-f0-9-]{8,}$", csrf):
                logger.debug(
                    f"[WindsurfAuth] Found CSRF from process env (PID {proc.pid}): {csrf[:8]}..."
                )
                return csrf
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            continue
        except Exception as e:
            logger.debug(f"[WindsurfAuth] Error reading process env: {e}")
            continue

    return None


def get_csrf_token() -> str:
    """Extract CSRF token from running Windsurf language server process.

    Discovery order:
    1. --csrf_token CLI argument (older Windsurf versions)
    2. Process environment WINDSURF_CSRF_TOKEN (preferred for newer versions)
    3. state.vscdb 'codeium.windsurf-windsurf_auth-' key (fallback, may be stale)
    """
    process_info = _get_language_server_process()

    # 1. Try command-line argument (older Windsurf versions)
    if process_info:
        match = re.search(r"--csrf_token\s+([a-f0-9-]+)", process_info)
        if match:
            return match.group(1)

    # 2. Read from process environment (most reliable for newer versions)
    csrf = _get_csrf_token_from_process_env()
    if csrf:
        return csrf

    # 3. Fallback: read from state.vscdb (may be stale but still useful)
    csrf = _get_csrf_token_from_state_db()
    if csrf:
        logger.debug("[WindsurfAuth] Using state.vscdb CSRF (process env not available)")
        return csrf

    if not process_info:
        raise WindsurfError(
            "Windsurf language server not found. Is Windsurf running?",
            WindsurfErrorCode.NOT_RUNNING,
        )

    raise WindsurfError(
        "CSRF token not found in process arguments, process env, or state.vscdb.",
        WindsurfErrorCode.CSRF_MISSING,
    )


# =============================================================================
# Port Discovery
# =============================================================================


def _extract_pid_from_process_info(process_info: str) -> str | None:
    """Extract PID from process info based on platform."""
    if _SYSTEM == "Windows":
        pid_match = re.search(r"ProcessId=(\d+)", process_info)
        return pid_match.group(1) if pid_match else None
    else:
        # ps aux format: USER PID %CPU %MEM ...
        pid_match = re.search(r"^\s*\S+\s+(\d+)", process_info, re.MULTILINE)
        return pid_match.group(1) if pid_match else None


def _extract_extension_port(process_info: str) -> int | None:
    """Extract extension server port from process info."""
    ext_port_match = re.search(r"--extension_server_port\s+(\d+)", process_info)
    return int(ext_port_match.group(1)) if ext_port_match else None


def _get_listening_ports(pid: str) -> list[int]:
    """Get listening ports for the given PID using platform-specific tools."""
    if not pid:
        return []

    try:
        if _SYSTEM == "Windows":
            # Use errors='replace' to handle Windows locale-specific encodings
            output = subprocess.check_output(
                ["netstat", "-ano"],
                encoding="utf-8",
                errors="replace",
                timeout=15,
                stderr=subprocess.DEVNULL,
            )
            # Filter for PID and LISTENING
            port_matches = re.findall(
                rf":(\d+)\s+\S+\s+LISTENING\s+{pid}",
                output or "",
            )
        else:
            output = subprocess.check_output(
                ["lsof", "-p", pid, "-i", "-P", "-n"],
                encoding="utf-8",
                timeout=15,
                stderr=subprocess.DEVNULL,
            )
            port_matches = re.findall(r":(\d+)\s+\(LISTEN\)", output or "")

        return [int(p) for p in port_matches]
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, UnicodeDecodeError):
        return []


def _select_best_port(ports: list[int], ext_port: int | None) -> int | None:
    """Select the best port from available ports and extension port reference."""
    if not ports:
        return None
        
    if ext_port:
        # Prefer the first port after extension_server_port
        candidates = sorted(p for p in ports if p > ext_port)
        if candidates:
            logger.debug(f"[WindsurfAuth] Found ports {ports}, using {candidates[0]} (ext_port={ext_port})")
            return candidates[0]
    
    return ports[0]


def get_port() -> int:
    """Get the language server gRPC port dynamically.

    Uses lsof/netstat to find actual listening ports for the language server PID.
    Falls back to extension_server_port + 3 if dynamic discovery fails.
    """
    process_info = _get_language_server_process()

    if not process_info:
        raise WindsurfError(
            "Windsurf language server not found. Is Windsurf running?",
            WindsurfErrorCode.NOT_RUNNING,
        )

    pid = _extract_pid_from_process_info(process_info)
    ext_port = _extract_extension_port(process_info)

    # Try to find listening ports dynamically
    if pid:
        ports = _get_listening_ports(pid)
        best_port = _select_best_port(ports, ext_port)
        if best_port:
            return best_port

    # Fallback: try common offsets from extension_server_port
    if ext_port:
        logger.debug(f"[WindsurfAuth] Using fallback port: {ext_port + 3}")
        return ext_port + 3

    raise WindsurfError(
        "Windsurf language server port not found.",
        WindsurfErrorCode.NOT_RUNNING,
    )


# =============================================================================
# API Key Discovery
# =============================================================================


def _get_api_key_from_env() -> str | None:
    """Get API key from environment variables."""
    env_key = (
        os.environ.get("WINDSURF_API_KEY")
        or os.environ.get("WINDSURF_OAUTH_TOKEN")
        or os.environ.get("CODEIUM_API_KEY")
    )
    if env_key:
        logger.debug("[WindsurfAuth] Using API key from environment variable")
    return env_key


def _extract_api_key_from_auth_status(auth_data: dict) -> str | None:
    """Extract API key from windsurfAuthStatus data."""
    # Standard API key (sk-ws-... or sk-...)
    api_key = auth_data.get("apiKey")
    if api_key:
        logger.debug("[WindsurfAuth] Found API key in state.vscdb (windsurfAuthStatus.apiKey)")
        return api_key
    
    # SSO enterprise: token stored as accessToken or token (JWT format)
    api_key = auth_data.get("accessToken")
    if api_key:
        logger.debug("[WindsurfAuth] Found SSO accessToken in state.vscdb (windsurfAuthStatus.accessToken)")
        return api_key
    
    api_key = auth_data.get("token")
    if api_key:
        logger.debug("[WindsurfAuth] Found SSO token in state.vscdb (windsurfAuthStatus.token)")
        return api_key
    
    return None


def _get_api_key_from_main_db(state_path: Path) -> str | None:
    """Get API key from main windsurfAuthStatus entry."""
    try:
        conn = sqlite3.connect(str(state_path))
        cursor = conn.execute("SELECT value FROM ItemTable WHERE key = 'windsurfAuthStatus'")
        row = cursor.fetchone()
        conn.close()

        if row and row[0]:
            parsed = json.loads(row[0])
            return _extract_api_key_from_auth_status(parsed)
    except (sqlite3.Error, json.JSONDecodeError, KeyError) as e:
        logger.debug(f"[WindsurfAuth] Failed to read state.vscdb: {e}")
    
    return None


def _extract_api_key_from_value(value: str) -> str | None:
    """Extract API key from a database value (JSON or raw token)."""
    value = value.strip()
    
    # Try to parse as JSON
    try:
        parsed = json.loads(value)
        if isinstance(parsed, dict) and "apiKey" in parsed:
            return parsed["apiKey"]
    except json.JSONDecodeError:
        pass
    
    # Use raw value if it looks like a token
    if value.startswith(("sk-", "eyJ")):
        return value
    
    return None


def _get_api_key_from_alternative_db_keys(state_path: Path) -> str | None:
    """Get API key from alternative database keys."""
    try:
        conn = sqlite3.connect(str(state_path))
        try:
            for key_name in ("windsurf.authToken", "codeium.apiKey", "service-auth/windsurf"):
                cursor = conn.execute("SELECT value FROM ItemTable WHERE key = ?", (key_name,))
                row = cursor.fetchone()
                if row and row[0]:
                    api_key = _extract_api_key_from_value(row[0])
                    if api_key:
                        return api_key
        finally:
            conn.close()
    except sqlite3.Error as e:
        logger.debug(f"[WindsurfAuth] Failed to read alternative keys from state.vscdb: {e}")
    
    return None


def _get_api_key_from_state_db() -> str | None:
    """Get API key from Windsurf state database."""
    state_path = _VSCDB_PATHS.get(_SYSTEM)
    if not state_path or not state_path.exists():
        return None
    
    # Try main windsurfAuthStatus first
    api_key = _get_api_key_from_main_db(state_path)
    if api_key:
        return api_key
    
    # Try alternative keys
    return _get_api_key_from_alternative_db_keys(state_path)


def _get_api_key_from_legacy_config() -> str | None:
    """Get API key from legacy ~/.codeium/config.json."""
    if not _LEGACY_CONFIG_PATH.exists():
        return None
    
    try:
        config = json.loads(_LEGACY_CONFIG_PATH.read_text(encoding="utf-8"))
        api_key = config.get("apiKey") or config.get("api_key")
        if api_key:
            logger.debug("[WindsurfAuth] Found API key in ~/.codeium/config.json")
        return api_key
    except (json.JSONDecodeError, OSError):
        return None


def get_api_key() -> str:
    """Read API key from Windsurf's state database or config files.

    Priority:
    1. WINDSURF_API_KEY environment variable
    2. state.vscdb SQLite database (windsurfAuthStatus key)
    3. ~/.codeium/config.json (legacy fallback)
    """
    # 1. Environment variable override
    env_key = _get_api_key_from_env()
    if env_key:
        return env_key

    # 2. state.vscdb SQLite database
    db_key = _get_api_key_from_state_db()
    if db_key:
        return db_key

    # 3. Legacy config file
    legacy_key = _get_api_key_from_legacy_config()
    if legacy_key:
        return legacy_key

    raise WindsurfError(
        "API key not found. Please login to Windsurf first.",
        WindsurfErrorCode.API_KEY_MISSING,
    )


# =============================================================================
# Version Discovery
# =============================================================================


def get_windsurf_version() -> str:
    """Get Windsurf version from process arguments."""
    process_info = _get_language_server_process()

    if process_info:
        match = re.search(r"--windsurf_version\s+(\S+)", process_info)
        if match:
            version = match.group(1).split("+")[0]
            return version

    return "1.13.104"  # Default fallback version


# =============================================================================
# Public API
# =============================================================================


def discover_credentials() -> WindsurfCredentials:
    """Get all credentials needed to communicate with Windsurf.

    Returns:
        WindsurfCredentials with csrf_token, port, api_key, and version.

    Raises:
        WindsurfError: If Windsurf is not running or credentials cannot be found.
    """
    csrf = get_csrf_token()
    port = get_port()
    api_key = get_api_key()
    version = get_windsurf_version()

    logger.info(
        f"[WindsurfAuth] Discovered credentials: port={port}, "
        f"csrf={csrf[:8]}..., apiKey={api_key[:8]}..., version={version}"
    )

    return WindsurfCredentials(
        csrf_token=csrf,
        port=port,
        api_key=api_key,
        version=version,
    )


def is_windsurf_running() -> bool:
    """Check if Windsurf is running and accessible.

    Checks both the language server process and credential availability
    (CSRF token from CLI args or state.vscdb, plus a discoverable port).
    """
    try:
        get_csrf_token()
        get_port()
        return True
    except Exception:
        pass

    # Fallback: process exists even if CSRF/port discovery failed
    # (e.g. newer Windsurf versions with different argument format)
    try:
        process_info = _get_language_server_process()
        if process_info and _get_csrf_token_from_state_db():
            logger.debug("[WindsurfAuth] Windsurf detected via process + state.vscdb CSRF")
            return True
    except Exception:
        pass

    return False
