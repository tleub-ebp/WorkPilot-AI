"""
Worktree Manager — Manage isolated Git worktrees for sandbox simulation.

Creates temporary Git worktrees (or overlay copies) so that agents
can operate on a snapshot of the repository without affecting the
real working tree.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class WorktreeInfo:
    """Metadata about a managed sandbox worktree."""

    path: Path
    branch: str
    commit_sha: str
    is_temporary: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class WorktreeManager:
    """Create and manage Git worktrees for sandbox dry-runs.

    Usage::

        mgr = WorktreeManager(repo_root=Path("/my/repo"))
        wt = mgr.create_snapshot()
        # ... run agent actions on wt.path ...
        mgr.cleanup(wt)
    """

    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root
        self._active: list[WorktreeInfo] = []

    @property
    def repo_root(self) -> Path:
        return self._repo_root

    @property
    def active_worktrees(self) -> list[WorktreeInfo]:
        return list(self._active)

    def create_snapshot(self, ref: str = "HEAD") -> WorktreeInfo:
        """Create an isolated worktree snapshot from *ref*.

        Falls back to a plain directory copy if git worktree is
        unavailable (e.g. not a Git repo).
        """
        commit_sha = self._resolve_ref(ref)
        tmp_dir = Path(tempfile.mkdtemp(prefix="workpilot_sandbox_"))

        try:
            self._create_git_worktree(tmp_dir, ref)
            branch = ref
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            logger.warning(
                "Git worktree creation failed – falling back to directory copy"
            )
            self._copy_directory(tmp_dir)
            branch = "copy"

        info = WorktreeInfo(
            path=tmp_dir,
            branch=branch,
            commit_sha=commit_sha,
        )
        self._active.append(info)
        logger.info("Sandbox worktree created at %s (ref=%s)", tmp_dir, ref)
        return info

    def cleanup(self, worktree: WorktreeInfo) -> None:
        """Remove a sandbox worktree and clean up resources."""
        if worktree in self._active:
            self._active.remove(worktree)

        if worktree.path.exists():
            # Try git worktree remove first
            try:
                subprocess.run(
                    ["git", "worktree", "remove", "--force", str(worktree.path)],
                    cwd=str(self._repo_root),
                    capture_output=True,
                    timeout=30,
                )
            except (subprocess.CalledProcessError, FileNotFoundError, OSError):
                pass

            # Fallback: just remove the directory
            if worktree.path.exists():
                shutil.rmtree(worktree.path, ignore_errors=True)

        logger.info("Sandbox worktree cleaned up: %s", worktree.path)

    def cleanup_all(self) -> None:
        """Remove all active sandbox worktrees."""
        for wt in list(self._active):
            self.cleanup(wt)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_ref(self, ref: str) -> str:
        try:
            result = subprocess.run(
                ["git", "rev-parse", ref],
                cwd=str(self._repo_root),
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except (FileNotFoundError, OSError):
            return "unknown"

    def _create_git_worktree(self, dest: Path, ref: str) -> None:
        # Remove the temp dir first — git worktree add needs a non-existing target
        if dest.exists():
            shutil.rmtree(dest)

        subprocess.run(
            ["git", "worktree", "add", "--detach", str(dest), ref],
            cwd=str(self._repo_root),
            capture_output=True,
            check=True,
            timeout=60,
        )

    def _copy_directory(self, dest: Path) -> None:
        """Plain directory copy fallback, excluding heavy dirs."""
        exclude = {".git", "node_modules", "__pycache__", ".venv", "venv", ".tox"}
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(
            self._repo_root,
            dest,
            ignore=shutil.ignore_patterns(*exclude),
        )
