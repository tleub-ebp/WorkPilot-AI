#!/usr/bin/env python3
"""
WorkPilot AI Framework
=====================

A multi-session autonomous coding framework for building features and applications.
Uses subtask-based implementation plans with phase dependencies.

Key Features:
- Safe workspace isolation (builds in separate workspace by default)
- Parallel execution with Git worktrees
- Smart recovery from interruptions
- Linear integration for project management

Usage:
    python auto-claude/run.py --spec 001-initial-app
    python auto-claude/run.py --spec 001
    python auto-claude/run.py --list

    # Workspace management
    python auto-claude/run.py --spec 001 --merge     # Add completed build to project
    python auto-claude/run.py --spec 001 --review    # See what was built
    python auto-claude/run.py --spec 001 --discard   # Delete build (requires confirmation)

Prerequisites:
    - CLAUDE_CODE_OAUTH_TOKEN environment variable set (run: claude setup-token)
    - Spec created via: claude /spec
    - Claude Code CLI installed
"""

import importlib.util
import io
import os
import socket
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

# Charger les variables d'environnement à partir du fichier .env
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Ensure apps/backend is in path for core/cli/agents imports
_BACKEND_DIR = Path(__file__).parent.resolve()
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# Ensure project root is in path for src.connectors imports (e.g. src.connectors.llm_config)
_PROJECT_ROOT = _BACKEND_DIR.parent.parent.resolve()
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Python version check - must be before any imports using 3.10+ syntax
if sys.version_info < (3, 10):  # noqa: UP036
    sys.exit(
        f"Error: WorkPilot AI requires Python 3.10 or higher.\n"
        f"You are running Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}\n"
        f"\n"
        f"Please upgrade Python: https://www.python.org/downloads/"
    )

# Configure safe encoding on Windows BEFORE any imports that might print
# This handles both TTY and piped output (e.g., from Electron)
if sys.platform == "win32":
    for _stream_name in ("stdout", "stderr"):
        _stream = getattr(sys, _stream_name)
        # Method 1: Try reconfigure (works for TTY)
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
                continue
            except (AttributeError, io.UnsupportedOperation, OSError):
                pass
        # Method 2: Wrap with TextIOWrapper for piped output
        try:
            if hasattr(_stream, "buffer"):
                _new_stream = io.TextIOWrapper(
                    _stream.buffer,
                    encoding="utf-8",
                    errors="replace",
                    line_buffering=True,
                )
                setattr(sys, _stream_name, _new_stream)
        except (AttributeError, io.UnsupportedOperation, OSError):
            pass
    # Clean up temporary variables
    del _stream_name, _stream
    if "_new_stream" in dir():
        del _new_stream

# Validate platform-specific dependencies BEFORE any imports that might
# trigger graphiti_core -> real_ladybug -> pywintypes import chain (ACS-253)
from core.dependency_validator import validate_platform_dependencies

validate_platform_dependencies()

from cli import main


def is_uvicorn_running(host="127.0.0.1", port=9000):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        try:
            sock.connect((host, port))
            return True
        except (ConnectionRefusedError, OSError):
            return False


def is_uvicorn_installed():
    return importlib.util.find_spec("uvicorn") is not None


if not is_uvicorn_running():
    if is_uvicorn_installed():
        try:
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "provider_api:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "9000",
                    "--reload",
                ],
                cwd=os.path.dirname(__file__),
                env=os.environ.copy(),
            )
            print("[INFO] Lancement automatique du backend FastAPI (uvicorn)...")
        except Exception as e:
            print(f"[ERREUR] Impossible de lancer uvicorn automatiquement: {e}")
    else:
        print(
            "[ERREUR] uvicorn n'est pas installé dans l'environnement Python courant. Veuillez exécuter 'pip install -r requirements.txt' dans apps/backend ou activer le bon venv."
        )

if __name__ == "__main__":
    main()
