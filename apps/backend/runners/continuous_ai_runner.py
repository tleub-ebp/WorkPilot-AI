"""
Continuous AI Runner — Background Daemon Entry Point
=====================================================

Long-lived process that runs the continuous AI daemon, polling
for CI/CD failures, dependency vulnerabilities, and new issues.

Usage (CLI):
    python continuous_ai_runner.py --project-dir /path/to/project --config '{"enabled": true, ...}'

Usage (from Electron):
    Spawned as subprocess via continuous-ai-handlers.ts

Events emitted (stdout):
    __DAEMON_EVENT__:{...}  — Daemon lifecycle and module events
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import signal
import sys
from pathlib import Path

# Add the backend directory to sys.path for imports
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from continuous_ai.daemon import ContinuousAIDaemon
from continuous_ai.types import ContinuousAIConfig

logger = logging.getLogger(__name__)


async def run_daemon(
    project_dir: Path,
    config: ContinuousAIConfig,
) -> None:
    """
    Run the continuous AI daemon until interrupted.
    """
    daemon = ContinuousAIDaemon(
        project_dir=project_dir,
        config=config,
    )

    # Handle graceful shutdown
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def signal_handler() -> None:
        logger.info("Received shutdown signal")
        stop_event.set()

    # Register signal handlers (Unix only — Windows uses different mechanism)
    try:
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, signal_handler)
    except NotImplementedError:
        # Windows: signal handlers not supported in asyncio, use alternative
        pass

    print(f"\n{'=' * 60}", flush=True)
    print("  CONTINUOUS AI — Daemon Starting", flush=True)
    print(f"{'=' * 60}", flush=True)
    print(f"  Project:   {project_dir}", flush=True)
    print(f"  Budget:    ${config.daily_budget_usd}/day", flush=True)
    print("  Modules:", flush=True)
    if config.cicd_watcher.enabled:
        print(
            f"    CI/CD Watcher:        ON (every {config.cicd_watcher.poll_interval_seconds}s)",
            flush=True,
        )
    if config.dependency_sentinel.enabled:
        print(
            f"    Dependency Sentinel:  ON (every {config.dependency_sentinel.poll_interval_seconds}s)",
            flush=True,
        )
    if config.issue_responder.enabled:
        print(
            f"    Issue Responder:      ON (every {config.issue_responder.poll_interval_seconds}s)",
            flush=True,
        )
    if config.pr_reviewer.enabled:
        print(
            f"    PR Reviewer:          ON (every {config.pr_reviewer.poll_interval_seconds}s)",
            flush=True,
        )
    print(f"{'=' * 60}\n", flush=True)

    # Run daemon with stop event
    daemon_task = asyncio.create_task(daemon.start())

    # Also listen for stdin close (Electron process exit)
    stdin_task = asyncio.create_task(_wait_for_stdin_close())

    done, pending = await asyncio.wait(
        [daemon_task, stop_event.wait(), stdin_task],
        return_when=asyncio.FIRST_COMPLETED,
    )

    # Shut down gracefully
    await daemon.stop()
    for task in pending:
        task.cancel()

    print(f"\n{'=' * 60}", flush=True)
    print("  CONTINUOUS AI — Daemon Stopped", flush=True)
    print(f"{'=' * 60}\n", flush=True)


async def _wait_for_stdin_close() -> None:
    """Wait for stdin to close (parent process exit)."""
    loop = asyncio.get_running_loop()
    try:
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)
        while True:
            data = await reader.read(1024)
            if not data:
                break
    except (OSError, ValueError):
        # stdin already closed or not a pipe
        pass


def get_status(project_dir: Path) -> dict:
    """Read the daemon's last persisted status."""
    status_file = project_dir / ".workpilot" / "continuous-ai" / "status.json"
    if status_file.exists():
        try:
            with open(status_file, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"running": False}


# ─── CLI entry-point ─────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Continuous AI — Background Daemon")
    parser.add_argument(
        "--project-dir",
        default=os.getcwd(),
        help="Project root directory",
    )
    parser.add_argument(
        "--config",
        default="{}",
        help="JSON config string or path to config file",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print daemon status and exit",
    )

    args = parser.parse_args()
    project_dir = Path(args.project_dir).resolve()

    if args.status:
        status = get_status(project_dir)
        print(json.dumps(status, indent=2))
        return

    # Parse config
    config_str = args.config
    if Path(config_str).is_file():
        with open(config_str, encoding="utf-8") as f:
            config_data = json.load(f)
    else:
        config_data = json.loads(config_str)

    config = ContinuousAIConfig.from_dict(config_data)

    if not config.enabled:
        print("Continuous AI is disabled in config. Enable it to start the daemon.")
        sys.exit(0)

    asyncio.run(run_daemon(project_dir, config))


if __name__ == "__main__":
    main()
