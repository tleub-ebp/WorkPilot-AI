"""
Self-Healing CLI Commands
==========================

CLI command handlers for the Self-Healing Codebase + Incident Responder.
"""

import asyncio
import subprocess
import sys
from pathlib import Path


def handle_self_healing_command(
    project_dir: Path,
    mode: str,
    verbose: bool = False,
) -> None:
    """Handle self-healing CLI commands.

    Args:
        project_dir: The project directory.
        mode: One of 'cicd', 'proactive', 'dashboard'.
        verbose: Enable verbose output.
    """
    from runners.self_healing_runner import SelfHealingRunner

    runner = SelfHealingRunner(project_dir=project_dir)

    if mode == "cicd":
        # Get current commit and branch
        commit = _get_current_commit(project_dir)
        branch = _get_current_branch(project_dir)
        if not commit:
            print("❌ Could not determine current commit SHA")
            sys.exit(1)

        print(f"🔄 Running CI/CD healing for commit {commit[:7]} on {branch}...")
        success = asyncio.run(
            runner.run_cicd(
                commit_sha=commit,
                branch=branch,
            )
        )
        if not success:
            sys.exit(1)

    elif mode == "proactive":
        print("🔍 Running proactive fragility scan...")
        success = asyncio.run(runner.run_proactive())
        if not success:
            sys.exit(1)

    elif mode == "dashboard":
        asyncio.run(runner.run_dashboard())

    else:
        print(f"❌ Unknown self-healing mode: {mode}")
        print("   Valid modes: cicd, proactive, dashboard")
        sys.exit(1)


def _get_current_commit(project_dir: Path) -> str | None:
    """Get the current HEAD commit SHA."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def _get_current_branch(project_dir: Path) -> str:
    """Get the current branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip() if result.returncode == 0 else "main"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return "main"
