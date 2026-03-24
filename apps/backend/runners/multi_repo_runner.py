"""
Multi-Repo Orchestration Runner
=================================
CLI entry point for running tasks across multiple repositories simultaneously.

Usage:
    python runners/multi_repo_runner.py --task "Add auth across services" \
        --repos "/path/to/frontend,/path/to/backend,/path/to/shared-lib" \
        --project-dir /path/to/workspace

    python runners/multi_repo_runner.py --task "Update API contracts" \
        --repos "owner/frontend::/local/frontend,owner/backend::/local/backend" \
        --model opus --fail-fast
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestration import MultiRepoOrchestrator

logger = logging.getLogger(__name__)


def parse_repos(repos_str: str) -> list[dict[str, str]]:
    """
    Parse comma-separated repo specifications.

    Formats supported:
    - /path/to/repo                     (local path only, repo name inferred)
    - owner/repo::/path/to/repo         (explicit name + local path)
    - owner/repo                        (remote, path must be resolved)
    """
    repos = []
    for entry in repos_str.split(","):
        entry = entry.strip()
        if not entry:
            continue

        if "::" in entry:
            # Explicit name::path format
            name, path = entry.split("::", 1)
            repos.append({"repo": name.strip(), "repo_path": path.strip()})
        elif "/" in entry and not Path(entry).exists():
            # Looks like owner/repo format without path
            # Try to find it relative to project dir
            repos.append({"repo": entry, "repo_path": entry})
        else:
            # Local path, infer repo name from directory
            path = Path(entry).resolve()
            name = path.name
            repos.append({"repo": name, "repo_path": str(path)})

    return repos


def create_master_spec_dir(project_dir: Path, task: str) -> Path:
    """Create and return the master spec directory for this orchestration."""
    specs_dir = project_dir / ".auto-claude" / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)

    # Find next available spec number
    existing = [d.name for d in specs_dir.iterdir() if d.is_dir()]
    max_num = 0
    for name in existing:
        try:
            num = int(name.split("-")[0])
            max_num = max(max_num, num)
        except (ValueError, IndexError):
            pass

    # Create a slug from the task description
    import re

    slug = re.sub(r"[^\w\s-]", "", task.lower())
    slug = re.sub(r"[\s]+", "-", slug)[:50].strip("-")

    spec_name = f"{max_num + 1:03d}-multi-repo-{slug}"
    spec_dir = specs_dir / spec_name
    spec_dir.mkdir(parents=True, exist_ok=True)

    return spec_dir


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Multi-Repo Orchestration Runner - coordinate changes across multiple repositories"
    )
    parser.add_argument(
        "--task",
        type=str,
        required=True,
        help="Task description for the cross-repo orchestration",
    )
    parser.add_argument(
        "--repos",
        type=str,
        required=True,
        help="Comma-separated repo paths or owner/repo::path specifications",
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path.cwd(),
        help="Base project directory (default: current directory)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="sonnet",
        help="Model to use for AI agents (default: sonnet)",
    )
    parser.add_argument(
        "--thinking-level",
        type=str,
        default="medium",
        choices=["none", "low", "medium", "high", "ultrathink"],
        help="Thinking budget level (default: medium)",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on first repo failure",
    )
    parser.add_argument(
        "--spec-dir",
        type=Path,
        default=None,
        help="Use existing master spec directory instead of creating a new one",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Parse repos
    repos = parse_repos(args.repos)
    if len(repos) < 2:
        print(
            '[MULTI_REPO] {"event": "error", "message": "At least 2 repositories are required for multi-repo orchestration"}',
            flush=True,
        )
        return 1

    # Validate repo paths exist
    for repo_info in repos:
        repo_path = Path(repo_info["repo_path"])
        if not repo_path.exists():
            print(
                f'[MULTI_REPO] {{"event": "error", "message": "Repository path not found: {repo_path}"}}',
                flush=True,
            )
            return 1

    # Create or use existing spec dir
    if args.spec_dir:
        master_spec_dir = args.spec_dir
    else:
        master_spec_dir = create_master_spec_dir(args.project_dir, args.task)

    logger.info(
        f"Multi-repo orchestration: {len(repos)} repos, spec dir: {master_spec_dir}"
    )
    for repo_info in repos:
        logger.info(f"  - {repo_info['repo']} @ {repo_info['repo_path']}")

    # Run orchestration
    orchestrator = MultiRepoOrchestrator(
        master_spec_dir=master_spec_dir,
        project_dir=args.project_dir,
        repos=repos,
        task_description=args.task,
        model=args.model,
        thinking_level=args.thinking_level,
        fail_fast=args.fail_fast,
    )

    success = asyncio.run(orchestrator.run())
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
