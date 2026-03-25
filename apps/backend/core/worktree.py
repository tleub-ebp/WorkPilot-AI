#!/usr/bin/env python3
"""
Git Worktree Manager - Per-Spec Architecture
=============================================

Each spec gets its own worktree:
- Worktree path: .workpilot/worktrees/tasks/{spec-name}/
- Branch name: workpilot/{spec-name}

This allows:
1. Multiple specs to be worked on simultaneously
2. Each spec's changes are isolated
3. Branches persist until explicitly merged
4. Clear 1:1:1 mapping: spec → worktree → branch
"""

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TypedDict, TypeVar

from core.gh_executable import get_gh_executable, invalidate_gh_cache
from core.git_executable import get_git_executable, get_isolated_git_env, run_git
from core.git_provider import (
    detect_git_provider,
    extract_azure_devops_org,
    extract_azure_devops_project,
    extract_azure_devops_repository,
)
from core.glab_executable import get_glab_executable, invalidate_glab_cache
from core.model_config import get_utility_model_config
from debug import debug_warning

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ── i18n helpers for PR / MR body fallback ────────────────────────────────


def _get_app_language() -> str:
    """Return the UI language configured by the frontend (``APP_LANGUAGE`` env var)."""
    return os.environ.get("APP_LANGUAGE", "en")


_WORKTREE_PR_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "fallback_footer": "Auto-generated PR from WorkPilot AI build.",
        "summary_section": "Summary",
        "checklist_section": "Review checklist",
        "check_standards": "Code follows project standards",
        "check_tests": "Tests pass (if applicable)",
        "check_docs": "Documentation is up to date",
        "check_coherent": "Changes are consistent with the task",
        "check_regression": "No regression detected",
        "warning": "This PR requires human validation before merge.",
        "footer": "PR created automatically by WorkPilot AI",
    },
    "fr": {
        "fallback_footer": "PR générée automatiquement par WorkPilot AI.",
        "summary_section": "Résumé",
        "checklist_section": "Checklist de vérification",
        "check_standards": "Le code respecte les standards du projet",
        "check_tests": "Les tests passent (si applicables)",
        "check_docs": "La documentation est à jour",
        "check_coherent": "Les changements sont cohérents avec la tâche",
        "check_regression": "Aucune régression détectée",
        "warning": "Cette PR nécessite une validation humaine avant merge.",
        "footer": "PR créée automatiquement par WorkPilot AI",
    },
}


def _wt(key: str) -> str:
    """Return a translated worktree PR string for the current app language."""
    lang = _get_app_language()
    strings = _WORKTREE_PR_STRINGS.get(lang, _WORKTREE_PR_STRINGS["en"])
    return strings.get(key, _WORKTREE_PR_STRINGS["en"].get(key, key))


def _is_retryable_network_error(stderr: str) -> bool:
    """Check if an error is a retryable network/connection issue."""
    stderr_lower = stderr.lower()
    return any(
        term in stderr_lower
        for term in ["connection", "network", "timeout", "reset", "refused"]
    )


def _is_retryable_http_error(stderr: str) -> bool:
    """
    Check if an HTTP error is retryable (5xx errors, timeouts).
    Excludes auth errors (401, 403) and client errors (404, 422).
    """
    stderr_lower = stderr.lower()
    # Check for HTTP 5xx errors (server errors are retryable)
    if re.search(r"http[s]?\s*5\d{2}", stderr_lower):
        return True
    # Check for HTTP timeout patterns
    if "http" in stderr_lower and "timeout" in stderr_lower:
        return True
    return False


def _with_retry(
    operation: Callable[[], tuple[bool, T | None, str]],
    max_retries: int = 3,
    is_retryable: Callable[[str], bool] | None = None,
    on_retry: Callable[[int, str], None] | None = None,
) -> tuple[T | None, str]:
    """
    Execute an operation with retry logic.

    Args:
        operation: Function that returns a tuple of (success: bool, result: T | None, error: str).
                   On success (success=True), result contains the value and error is empty.
                   On failure (success=False), result is None and error contains the message.
        max_retries: Maximum number of retry attempts
        is_retryable: Function to check if error is retryable based on error message
        on_retry: Optional callback called before each retry with (attempt, error)

    Returns:
        Tuple of (result, last_error) where result is T on success, None on failure
    """
    last_error = ""

    for attempt in range(1, max_retries + 1):
        try:
            success, result, error = operation()
            if success:
                return result, ""

            last_error = error

            # Check if error is retryable
            if is_retryable and attempt < max_retries and is_retryable(error):
                if on_retry:
                    on_retry(attempt, error)
                backoff = 2 ** (attempt - 1)
                time.sleep(backoff)
                continue

            break

        except subprocess.TimeoutExpired:
            last_error = "Operation timed out"
            if attempt < max_retries:
                if on_retry:
                    on_retry(attempt, last_error)
                backoff = 2 ** (attempt - 1)
                time.sleep(backoff)
                continue
            break

    return None, last_error


class PushBranchResult(TypedDict, total=False):
    """Result of pushing a branch to remote."""

    success: bool
    branch: str
    remote: str
    error: str


class PullRequestResult(TypedDict, total=False):
    """Result of creating a pull request."""

    success: bool
    pr_url: str | None  # None when PR was created but URL couldn't be extracted
    already_exists: bool
    error: str
    message: str


class PushAndCreatePRResult(TypedDict, total=False):
    """Result of push_and_create_pr operation."""

    success: bool
    pushed: bool
    remote: str
    branch: str
    provider: str  # 'github', 'gitlab', or 'unknown'
    pr_url: str | None  # None when PR was created but URL couldn't be extracted
    already_exists: bool
    error: str
    message: str


class WorktreeError(Exception):
    """Error during worktree operations."""

    pass


@dataclass
class WorktreeInfo:
    """Information about a spec's worktree."""

    path: Path
    branch: str
    spec_name: str
    base_branch: str
    is_active: bool = True
    commit_count: int = 0
    files_changed: int = 0
    additions: int = 0
    deletions: int = 0
    last_commit_date: datetime | None = None
    days_since_last_commit: int | None = None


class WorktreeManager:
    """
    Manages per-spec Git worktrees.

    Each spec gets its own worktree in .workpilot/worktrees/tasks/{spec-name}/ with
    a corresponding branch workpilot/{spec-name}.
    """

    # Timeout constants for subprocess operations
    GIT_PUSH_TIMEOUT = 120  # 2 minutes for git push (network operations)
    CLI_TIMEOUT = 60  # 1 minute for CLI commands (gh/glab)
    CLI_QUERY_TIMEOUT = 30  # 30 seconds for CLI queries (gh/glab)

    def __init__(
        self,
        project_dir: Path,
        base_branch: str | None = None,
        use_local_branch: bool = False,
    ):
        self.project_dir = project_dir
        self.base_branch = base_branch or self._detect_base_branch()
        self.use_local_branch = use_local_branch
        self.worktrees_dir = project_dir / ".workpilot" / "worktrees" / "tasks"
        self._merge_lock = asyncio.Lock()

    def _detect_base_branch(self) -> str:
        """
        Detect the base branch for worktree creation.

        Priority order:
        1. DEFAULT_BRANCH environment variable
        2. Auto-detect main/master (if they exist)
        3. Fall back to current branch (with warning)

        Returns:
            The detected base branch name
        """
        # 1. Check for DEFAULT_BRANCH env var
        env_branch = os.getenv("DEFAULT_BRANCH")
        if env_branch:
            # Verify the branch exists
            result = run_git(
                ["rev-parse", "--verify", env_branch],
                cwd=self.project_dir,
            )
            if result.returncode == 0:
                return env_branch
            else:
                print(
                    f"Warning: DEFAULT_BRANCH '{env_branch}' not found, auto-detecting..."
                )

        # 2. Auto-detect main/master
        for branch in ["main", "master"]:
            result = run_git(
                ["rev-parse", "--verify", branch],
                cwd=self.project_dir,
            )
            if result.returncode == 0:
                return branch

        # 3. Fall back to current branch with warning
        current = self._get_current_branch()
        print("Warning: Could not find 'main' or 'master' branch.")
        print(f"Warning: Using current branch '{current}' as base for worktree.")
        print("Tip: Set DEFAULT_BRANCH=your-branch in .env to avoid this.")
        return current

    def _get_current_branch(self) -> str:
        """Get the current git branch."""
        result = run_git(
            ["rev-parse", "--abbrev-ref", "HEAD"],
            cwd=self.project_dir,
        )
        if result.returncode != 0:
            raise WorktreeError(f"Failed to get current branch: {result.stderr}")
        return result.stdout.strip()

    def _run_git(
        self, args: list[str], cwd: Path | None = None, timeout: int = 60
    ) -> subprocess.CompletedProcess:
        """Run a git command and return the result.

        Args:
            args: Git command arguments (without 'git' prefix)
            cwd: Working directory for the command
            timeout: Command timeout in seconds (default: 60)

        Returns:
            CompletedProcess with command results. On timeout, returns a
            CompletedProcess with returncode=-1 and timeout error in stderr.
        """
        return run_git(args, cwd=cwd or self.project_dir, timeout=timeout)

    def _unstage_gitignored_files(self) -> None:
        """
        Unstage any staged files that are gitignored in the current branch,
        plus any files in the .workpilot directory which should never be merged.

        This is needed after a --no-commit merge because files that exist in the
        source branch (like spec files in .workpilot/specs/) get staged even if
        they're gitignored in the target branch.
        """
        # Get list of staged files
        result = self._run_git(["diff", "--cached", "--name-only"])
        if result.returncode != 0 or not result.stdout.strip():
            return

        staged_files = result.stdout.strip().split("\n")

        # Files to unstage: gitignored files + .workpilot directory files
        files_to_unstage = set()

        # 1. Check which staged files are gitignored
        # git check-ignore returns the files that ARE ignored
        result = run_git(
            ["check-ignore", "--stdin"],
            cwd=self.project_dir,
            input_data="\n".join(staged_files),
        )

        if result.stdout.strip():
            for file in result.stdout.strip().split("\n"):
                if file.strip():
                    files_to_unstage.add(file.strip())

        # 2. Always unstage .workpilot directory files - these are project-specific
        # and should never be merged from the worktree branch
        workpilot_patterns = [".workpilot/", "workpilot/specs/"]
        for file in staged_files:
            file = file.strip()
            if not file:
                continue
            # Normalize path separators for cross-platform (Windows backslash support)
            normalized = file.replace("\\", "/")
            for pattern in workpilot_patterns:
                if normalized.startswith(pattern) or f"/{pattern}" in normalized:
                    files_to_unstage.add(file)
                    break

        if files_to_unstage:
            print(f"Unstaging {len(files_to_unstage)} workpilot/gitignored file(s)...")
            # Unstage each file
            for file in files_to_unstage:
                self._run_git(["reset", "HEAD", "--", file])

    def setup(self) -> None:
        """Create worktrees directory if needed."""
        self.worktrees_dir.mkdir(parents=True, exist_ok=True)

    # ==================== Per-Spec Worktree Methods ====================

    def get_worktree_path(self, spec_name: str) -> Path:
        """Get the worktree path for a spec (checks new and legacy locations)."""
        # New path first (.workpilot/worktrees/tasks/)
        new_path = self.worktrees_dir / spec_name
        if new_path.exists():
            return new_path

        # Legacy fallback (.worktrees/ instead of .workpilot/worktrees/tasks/)
        legacy_path = self.project_dir / ".worktrees" / spec_name
        if legacy_path.exists():
            return legacy_path

        # Return new path as default for creation
        return new_path

    def get_branch_name(self, spec_name: str) -> str:
        """Get the branch name for a spec."""
        return f"workpilot/{spec_name}"

    def worktree_exists(self, spec_name: str) -> bool:
        """Check if a worktree exists for a spec."""
        return self.get_worktree_path(spec_name).exists()

    def get_worktree_info(self, spec_name: str) -> WorktreeInfo | None:
        """Get info about a spec's worktree."""
        worktree_path = self.get_worktree_path(spec_name)
        if not worktree_path.exists():
            return None

        # Verify the branch exists in the worktree
        result = self._run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=worktree_path)
        if result.returncode != 0:
            return None

        actual_branch = result.stdout.strip()

        # Handle detached HEAD state: rev-parse --abbrev-ref returns literal "HEAD"
        # when the worktree is in detached HEAD (e.g. after rebase, merge conflict, etc.)
        # First try to resolve the branch from git's worktree registry, then fall back
        # to the expected branch name derived from the spec name.
        if actual_branch == "HEAD":
            registered_branch = self._get_worktree_registered_branch(worktree_path)
            if registered_branch:
                debug_warning(
                    "worktree",
                    f"Worktree '{spec_name}' is in detached HEAD state. "
                    f"Resolved branch from git worktree registry: {registered_branch}",
                )
                actual_branch = registered_branch
            else:
                expected_branch = self.get_branch_name(spec_name)
                debug_warning(
                    "worktree",
                    f"Worktree '{spec_name}' is in detached HEAD state. "
                    f"Using expected branch name: {expected_branch}",
                )
                actual_branch = expected_branch

        # Get statistics
        stats = self._get_worktree_stats(spec_name)

        return WorktreeInfo(
            path=worktree_path,
            branch=actual_branch,
            spec_name=spec_name,
            base_branch=self.base_branch,
            is_active=True,
            **stats,
        )

    def _get_worktree_registered_branch(self, worktree_path: Path) -> str | None:
        """
        Get the branch name for a worktree from git's worktree registry.

        Uses `git worktree list --porcelain` to find the branch associated with
        a worktree path. This works even when the worktree is in detached HEAD state,
        as git tracks the original branch association in its registry.

        Args:
            worktree_path: The path to the worktree directory.

        Returns:
            The branch name (without refs/heads/ prefix) if found, None otherwise.
        """
        result = self._run_git(["worktree", "list", "--porcelain"])
        if result.returncode != 0:
            return None

        resolved_path = worktree_path.resolve()

        # Parse porcelain output: entries are separated by blank lines,
        # each entry has "worktree <path>", "HEAD <sha>", "branch refs/heads/<name>"
        # (or "detached" instead of "branch" if truly detached in registry too)
        current_path = None
        for line in result.stdout.split("\n"):
            if line.startswith("worktree "):
                current_path = Path(line.split(" ", 1)[1])
            elif line.startswith("branch refs/heads/") and current_path is not None:
                try:
                    if current_path.exists() and resolved_path.exists():
                        if os.path.samefile(resolved_path, current_path):
                            return line[len("branch refs/heads/") :]
                except OSError:
                    pass
                # Fallback to normalized case comparison
                if os.path.normcase(str(resolved_path)) == os.path.normcase(
                    str(current_path)
                ):
                    return line[len("branch refs/heads/") :]
            elif line == "":
                current_path = None

        return None

    def _check_branch_namespace_conflict(self) -> str | None:
        """
        Check if a branch named 'workpilot' exists, which would block creating
        branches in the 'workpilot/*' namespace.

        Git stores branch refs as files under .git/refs/heads/, so a branch named
        'workpilot' creates a file that prevents creating the 'workpilot/'
        directory needed for 'workpilot/{spec-name}' branches.

        Returns:
            The conflicting branch name if found, None otherwise.
        """
        result = self._run_git(["rev-parse", "--verify", "workpilot"])
        if result.returncode == 0:
            return "workpilot"
        return None

    def _branch_exists(self, branch_name: str) -> bool:
        """
        Check if a local branch exists in the repository.

        Uses git show-ref to specifically check for local branches, avoiding
        false positives from tags or other refs with the same name.

        Args:
            branch_name: The name of the branch to check (e.g., 'workpilot/my-spec')

        Returns:
            True if the local branch exists, False otherwise.
        """
        result = self._run_git(["show-ref", "--verify", f"refs/heads/{branch_name}"])
        return result.returncode == 0

    def _worktree_is_registered(self, worktree_path: Path) -> bool:
        """
        Check if a worktree path is registered with git.

        This determines if git tracks the worktree even if the directory exists.
        Useful for detecting orphaned worktree directories that need cleanup.

        Args:
            worktree_path: The path to the worktree directory to check.

        Returns:
            True if the worktree is registered with git, False otherwise.
        """
        result = self._run_git(["worktree", "list", "--porcelain"])
        if result.returncode != 0:
            return False

        # Parse porcelain output to get registered worktree paths
        # Format: "worktree /path/to/worktree" for each worktree
        registered_paths = set()
        for line in result.stdout.split("\n"):
            if line.startswith("worktree "):
                parts = line.split(" ", 1)
                if len(parts) == 2:
                    registered_paths.add(Path(parts[1]))

        # Check if worktree_path matches any registered path
        # Use samefile() for accurate comparison on case-insensitive filesystems
        resolved_path = worktree_path.resolve()
        for registered_path in registered_paths:
            # Try samefile first (handles case-insensitivity and symlinks)
            try:
                if resolved_path.exists() and registered_path.exists():
                    if os.path.samefile(resolved_path, registered_path):
                        return True
            except OSError:
                pass
            # Fallback to normalized case comparison for non-existent paths
            if os.path.normcase(str(resolved_path)) == os.path.normcase(
                str(registered_path)
            ):
                return True
        return False

    def _get_worktree_stats(self, spec_name: str) -> dict:
        """Get diff statistics for a worktree."""
        worktree_path = self.get_worktree_path(spec_name)

        stats = {
            "commit_count": 0,
            "files_changed": 0,
            "additions": 0,
            "deletions": 0,
            "last_commit_date": None,
            "days_since_last_commit": None,
        }

        if not worktree_path.exists():
            return stats

        # Commit count
        result = self._run_git(
            ["rev-list", "--count", f"{self.base_branch}..HEAD"], cwd=worktree_path
        )
        if result.returncode == 0:
            stats["commit_count"] = int(result.stdout.strip() or "0")

        # Last commit date (most recent commit in this worktree)
        result = self._run_git(
            ["log", "-1", "--format=%cd", "--date=iso"], cwd=worktree_path
        )
        if result.returncode == 0 and result.stdout.strip():
            try:
                # Parse ISO date format: "2026-01-04 00:25:25 +0100"
                date_str = result.stdout.strip()
                # Convert git format to ISO format for fromisoformat()
                # "2026-01-04 00:25:25 +0100" -> "2026-01-04T00:25:25+01:00"
                parts = date_str.rsplit(" ", 1)
                if len(parts) == 2:
                    date_part, tz_part = parts
                    # Convert timezone format: "+0100" -> "+01:00"
                    if len(tz_part) == 5 and (
                        tz_part.startswith("+") or tz_part.startswith("-")
                    ):
                        tz_formatted = f"{tz_part[:3]}:{tz_part[3:]}"
                        iso_str = f"{date_part.replace(' ', 'T')}{tz_formatted}"
                        last_commit_date = datetime.fromisoformat(iso_str)
                        stats["last_commit_date"] = last_commit_date
                        # Use timezone-aware now() for accurate comparison
                        now_aware = datetime.now(last_commit_date.tzinfo)
                        stats["days_since_last_commit"] = (
                            now_aware - last_commit_date
                        ).days
                    else:
                        # Fallback for unexpected timezone format
                        last_commit_date = datetime.strptime(
                            parts[0], "%Y-%m-%d %H:%M:%S"
                        )
                        stats["last_commit_date"] = last_commit_date
                        stats["days_since_last_commit"] = (
                            datetime.now() - last_commit_date
                        ).days
                else:
                    # No timezone in output
                    last_commit_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                    stats["last_commit_date"] = last_commit_date
                    stats["days_since_last_commit"] = (
                        datetime.now() - last_commit_date
                    ).days
            except (ValueError, TypeError) as e:
                # If parsing fails, silently continue without date info
                pass

        # Diff stats
        result = self._run_git(
            ["diff", "--shortstat", f"{self.base_branch}...HEAD"], cwd=worktree_path
        )
        if result.returncode == 0 and result.stdout.strip():
            # Parse: "3 files changed, 50 insertions(+), 10 deletions(-)"
            match = re.search(r"(\d+) files? changed", result.stdout)
            if match:
                stats["files_changed"] = int(match.group(1))
            match = re.search(r"(\d+) insertions?", result.stdout)
            if match:
                stats["additions"] = int(match.group(1))
            match = re.search(r"(\d+) deletions?", result.stdout)
            if match:
                stats["deletions"] = int(match.group(1))

        return stats

    def create_worktree(self, spec_name: str) -> WorktreeInfo:
        """
        Create a worktree for a spec (idempotent).

        This method is idempotent - calling it multiple times with the same spec_name
        will succeed regardless of prior state. It handles:
        - Existing valid worktrees (returns existing)
        - Corrupted worktrees (force removes and recreates)
        - Orphaned worktree references (prunes them)
        - Stale worktree directories (cleans them up)
        - Existing branches without worktrees (reuses the branch)

        Note:
            This method is NOT thread-safe for concurrent calls with the same spec_name.
            If concurrent access is needed, implement external locking.

        Args:
            spec_name: The spec folder name (e.g., "002-implement-memory")

        Returns:
            WorktreeInfo for the created or existing worktree

        Raises:
            WorktreeError: If a branch namespace conflict exists or worktree creation fails
        """
        worktree_path = self.get_worktree_path(spec_name)
        branch_name = self.get_branch_name(spec_name)

        # Step 1: Prune orphaned worktree references first
        # This cleans up any stale references that might block operations
        self._run_git(["worktree", "prune"])

        # Step 2: Check for branch namespace conflict (e.g., 'workpilot' blocking 'workpilot/*')
        conflicting_branch = self._check_branch_namespace_conflict()
        if conflicting_branch:
            raise WorktreeError(
                f"Branch '{conflicting_branch}' exists and blocks creating '{branch_name}'.\n"
                f"\n"
                f"Git branch names work like file paths - a branch named 'workpilot' prevents\n"
                f"creating branches under 'workpilot/' (like 'workpilot/{spec_name}').\n"
                f"\n"
                f"Fix: Rename the conflicting branch:\n"
                f"  git branch -m {conflicting_branch} {conflicting_branch}-backup"
            )

        # Step 3: Check if worktree already exists and is valid
        if worktree_path.exists() and self._worktree_is_registered(worktree_path):
            # Worktree exists and is tracked by git - return existing (idempotent)
            existing = self.get_worktree_info(spec_name)
            if existing:
                print(
                    f"Using existing worktree: {worktree_path.name} on branch {existing.branch}"
                )
                return existing
            else:
                # Worktree is registered but corrupted (e.g., unreadable HEAD)
                # Force remove the registration and let it be recreated
                print(f"Removing corrupted worktree registration: {worktree_path.name}")
                remove_result = self._run_git(
                    ["worktree", "remove", "--force", str(worktree_path)]
                )
                if remove_result.returncode != 0:
                    raise WorktreeError(
                        f"Failed to remove corrupted worktree: {remove_result.stderr}"
                    )

        # Step 4: Handle stale worktree directory (exists but not registered with git)
        if worktree_path.exists() and not self._worktree_is_registered(worktree_path):
            print(f"Removing stale worktree directory: {worktree_path.name}")
            shutil.rmtree(worktree_path, ignore_errors=True)
            if worktree_path.exists():
                raise WorktreeError(
                    f"Failed to remove stale worktree directory: {worktree_path}\n"
                    f"This may be due to permission issues or file locks."
                )

        # Step 5: Check if branch already exists
        branch_exists = self._branch_exists(branch_name)

        # Step 6: Fetch latest from remote to ensure we have the most up-to-date code
        # GitHub/remote is the source of truth, not the local branch
        fetch_result = self._run_git(["fetch", "origin", self.base_branch])
        if fetch_result.returncode != 0:
            print(
                f"Warning: Could not fetch {self.base_branch} from origin: {fetch_result.stderr}"
            )
            print("Falling back to local branch...")

        # Step 7: Create the worktree
        if branch_exists:
            # Branch exists - attach worktree to existing branch (no -b flag)
            print(f"Reusing existing branch: {branch_name}")
            result = self._run_git(["worktree", "add", str(worktree_path), branch_name])
        else:
            # Branch doesn't exist - create new branch from remote or local base
            # Determine the start point for the worktree
            start_point = self.base_branch  # Default to local branch

            if self.use_local_branch:
                # User explicitly requested local branch - skip auto-switch to remote
                # This preserves gitignored files (.env, configs) that may not exist on remote
                print(f"Creating worktree from local branch: {self.base_branch}")
            else:
                # Check if remote ref exists and use it as the source of truth
                remote_ref = f"origin/{self.base_branch}"
                check_remote = self._run_git(["rev-parse", "--verify", remote_ref])
                if check_remote.returncode == 0:
                    start_point = remote_ref
                    print(f"Creating worktree from remote: {remote_ref}")
                else:
                    print(
                        f"Remote ref {remote_ref} not found, using local branch: {self.base_branch}"
                    )

            # Create worktree with new branch from the start point
            result = self._run_git(
                ["worktree", "add", "-b", branch_name, str(worktree_path), start_point]
            )

        if result.returncode != 0:
            raise WorktreeError(
                f"Failed to create worktree for {spec_name}: {result.stderr}"
            )

        print(f"Created worktree: {worktree_path.name} on branch {branch_name}")

        return WorktreeInfo(
            path=worktree_path,
            branch=branch_name,
            spec_name=spec_name,
            base_branch=self.base_branch,
            is_active=True,
        )

    def get_or_create_worktree(self, spec_name: str) -> WorktreeInfo:
        """
        Get existing worktree or create a new one for a spec.

        Args:
            spec_name: The spec folder name

        Returns:
            WorktreeInfo for the worktree
        """
        existing = self.get_worktree_info(spec_name)
        if existing:
            print(f"Using existing worktree: {existing.path}")
            return existing

        return self.create_worktree(spec_name)

    def remove_worktree(self, spec_name: str, delete_branch: bool = False) -> None:
        """
        Remove a spec's worktree.

        Args:
            spec_name: The spec folder name
            delete_branch: Whether to also delete the branch
        """
        worktree_path = self.get_worktree_path(spec_name)
        branch_name = self.get_branch_name(spec_name)

        if worktree_path.exists():
            result = self._run_git(
                ["worktree", "remove", "--force", str(worktree_path)]
            )
            if result.returncode == 0:
                print(f"Removed worktree: {worktree_path.name}")
            else:
                print(f"Warning: Could not remove worktree: {result.stderr}")
                shutil.rmtree(worktree_path, ignore_errors=True)

        if delete_branch:
            self._run_git(["branch", "-D", branch_name])
            print(f"Deleted branch: {branch_name}")

        self._run_git(["worktree", "prune"])

    def merge_worktree(
        self, spec_name: str, delete_after: bool = False, no_commit: bool = False
    ) -> bool:
        """
        Merge a spec's worktree branch back to base branch.

        Args:
            spec_name: The spec folder name
            delete_after: Whether to remove worktree and branch after merge
            no_commit: If True, merge changes but don't commit (stage only for review)

        Returns:
            True if merge succeeded
        """
        info = self.get_worktree_info(spec_name)
        if not info:
            print(f"No worktree found for spec: {spec_name}")
            return False

        if no_commit:
            print(
                f"Merging {info.branch} into {self.base_branch} (staged, not committed)..."
            )
        else:
            print(f"Merging {info.branch} into {self.base_branch}...")

        # Switch to base branch in main project, but skip if already on it
        # This avoids triggering git hooks unnecessarily
        current_branch = self._get_current_branch()
        if current_branch != self.base_branch:
            result = self._run_git(["checkout", self.base_branch])
            if result.returncode != 0:
                # Check if this is a hook failure vs actual checkout failure
                # Hook failures still change the branch but return non-zero
                new_branch = self._get_current_branch()
                if new_branch == self.base_branch:
                    # Branch did change - likely a hook failure, continue with merge
                    stderr_msg = result.stderr[:100] if result.stderr else "<no stderr>"
                    debug_warning(
                        "worktree",
                        f"Checkout succeeded but hook returned non-zero: {stderr_msg}",
                    )
                else:
                    # Actual checkout failure
                    stderr_msg = result.stderr[:100] if result.stderr else "<no stderr>"
                    print(f"Error: Could not checkout base branch: {stderr_msg}")
                    return False

        # Merge the spec branch
        merge_args = ["merge", "--no-ff", info.branch]
        if no_commit:
            # --no-commit stages the merge but doesn't create the commit
            merge_args.append("--no-commit")
        else:
            merge_args.extend(["-m", f"workpilot: Merge {info.branch}"])

        result = self._run_git(merge_args)

        if result.returncode != 0:
            # Check if it's "already up to date" - not an error
            output = (result.stdout + result.stderr).lower()
            if "already up to date" in output or "already up-to-date" in output:
                print(f"Branch {info.branch} is already up to date.")
                if no_commit:
                    print("No changes to stage.")
                if delete_after:
                    self.remove_worktree(spec_name, delete_branch=True)
                return True
            # Check for actual conflicts
            if "conflict" in output:
                print("Merge conflict! Aborting merge...")
                self._run_git(["merge", "--abort"])
                return False
            # Other error - show details
            stderr_msg = (
                result.stderr[:200]
                if result.stderr
                else result.stdout[:200]
                if result.stdout
                else "<no output>"
            )
            print(f"Merge failed: {stderr_msg}")
            self._run_git(["merge", "--abort"])
            return False

        if no_commit:
            # Unstage any files that are gitignored in the main branch
            # These get staged during merge because they exist in the worktree branch
            self._unstage_gitignored_files()
            print(
                f"Changes from {info.branch} are now staged in your working directory."
            )
            print("Review the changes, then commit when ready:")
            print("  git commit -m 'your commit message'")
        else:
            print(f"Successfully merged {info.branch}")

        if delete_after:
            self.remove_worktree(spec_name, delete_branch=True)

        return True

    def commit_in_worktree(self, spec_name: str, message: str) -> bool:
        """Commit all changes in a spec's worktree."""
        worktree_path = self.get_worktree_path(spec_name)
        if not worktree_path.exists():
            return False

        self._run_git(["add", "."], cwd=worktree_path)
        result = self._run_git(["commit", "-m", message], cwd=worktree_path)

        if result.returncode == 0:
            return True
        elif "nothing to commit" in result.stdout + result.stderr:
            return True
        else:
            print(f"Commit failed: {result.stderr}")
            return False

    # ==================== Listing & Discovery ====================

    def list_all_worktrees(self) -> list[WorktreeInfo]:
        """List all spec worktrees (includes legacy .worktrees/ location)."""
        worktrees = []
        seen_specs = set()

        # Check new location first
        if self.worktrees_dir.exists():
            for item in self.worktrees_dir.iterdir():
                if item.is_dir():
                    info = self.get_worktree_info(item.name)
                    if info:
                        worktrees.append(info)
                        seen_specs.add(item.name)

        # Check legacy location (.worktrees/)
        legacy_dir = self.project_dir / ".worktrees"
        if legacy_dir.exists():
            for item in legacy_dir.iterdir():
                if item.is_dir() and item.name not in seen_specs:
                    info = self.get_worktree_info(item.name)
                    if info:
                        worktrees.append(info)

        return worktrees

    def list_all_spec_branches(self) -> list[str]:
        """List all workpilot branches (even if worktree removed)."""
        result = self._run_git(["branch", "--list", "workpilot/*"])
        if result.returncode != 0:
            return []

        branches = []
        for line in result.stdout.strip().split("\n"):
            branch = line.strip().lstrip("* ")
            if branch:
                branches.append(branch)

        return branches

    def get_changed_files(self, spec_name: str) -> list[tuple[str, str]]:
        """Get list of changed files in a spec's worktree."""
        worktree_path = self.get_worktree_path(spec_name)
        if not worktree_path.exists():
            return []

        result = self._run_git(
            ["diff", "--name-status", f"{self.base_branch}...HEAD"], cwd=worktree_path
        )

        files = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2:
                files.append((parts[0], parts[1]))

        return files

    def get_change_summary(self, spec_name: str) -> dict:
        """Get a summary of changes in a worktree."""
        files = self.get_changed_files(spec_name)

        new_files = sum(1 for status, _ in files if status == "A")
        modified_files = sum(1 for status, _ in files if status == "M")
        deleted_files = sum(1 for status, _ in files if status == "D")

        return {
            "new_files": new_files,
            "modified_files": modified_files,
            "deleted_files": deleted_files,
        }

    def cleanup_all(self) -> None:
        """Remove all worktrees and their branches."""
        for worktree in self.list_all_worktrees():
            self.remove_worktree(worktree.spec_name, delete_branch=True)

    def cleanup_stale_worktrees(self) -> None:
        """Remove worktrees that aren't registered with git."""
        if not self.worktrees_dir.exists():
            return

        # Get list of registered worktrees
        result = self._run_git(["worktree", "list", "--porcelain"])
        registered_paths = set()
        for line in result.stdout.split("\n"):
            if line.startswith("worktree "):
                registered_paths.add(Path(line.split(" ", 1)[1]))

        # Remove unregistered directories
        for item in self.worktrees_dir.iterdir():
            if item.is_dir() and item not in registered_paths:
                print(f"Removing stale worktree directory: {item.name}")
                shutil.rmtree(item, ignore_errors=True)

        self._run_git(["worktree", "prune"])

    def get_test_commands(self, spec_name: str) -> list[str]:
        """Detect likely test/run commands for the project."""
        worktree_path = self.get_worktree_path(spec_name)
        commands = []

        if (worktree_path / "package.json").exists():
            commands.append("npm install && npm run dev")
            commands.append("npm test")

        if (worktree_path / "requirements.txt").exists():
            commands.append("pip install -r requirements.txt")

        if (worktree_path / "Cargo.toml").exists():
            commands.append("cargo run")
            commands.append("cargo test")

        if (worktree_path / "go.mod").exists():
            commands.append("go run .")
            commands.append("go test ./...")

        if not commands:
            commands.append("# Check the project's README for run instructions")

        return commands

    def has_uncommitted_changes(self, spec_name: str | None = None) -> bool:
        """Check if there are uncommitted changes."""
        cwd = None
        if spec_name:
            worktree_path = self.get_worktree_path(spec_name)
            if worktree_path.exists():
                cwd = worktree_path
        result = self._run_git(["status", "--porcelain"], cwd=cwd)
        return bool(result.stdout.strip())

    # ==================== PR Creation Methods ====================

    def push_branch(self, spec_name: str, force: bool = False) -> PushBranchResult:
        """
        Push a spec's branch to the remote origin with retry logic.

        Args:
            spec_name: The spec folder name
            force: Whether to force push (use with caution)

        Returns:
            PushBranchResult with keys:
                - success: bool
                - branch: str (branch name)
                - remote: str (if successful)
                - error: str (if failed)
        """
        info = self.get_worktree_info(spec_name)
        if not info:
            return PushBranchResult(
                success=False,
                error=f"No worktree found for spec: {spec_name}",
            )

        # Verify we have an actual branch name (not detached HEAD)
        # get_worktree_info already falls back to expected branch name for detached HEAD,
        # but we also need to re-attach HEAD to the branch in the worktree so git push works.
        head_check = self._run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=info.path)
        if head_check.returncode == 0 and head_check.stdout.strip() == "HEAD":
            # Resolve the target branch: first check git's worktree registry (which
            # tracks the original branch even when detached), then fall back to the
            # expected branch name derived from the spec name.
            target_branch = self._get_worktree_registered_branch(info.path)
            if not target_branch:
                target_branch = self.get_branch_name(spec_name)
            debug_warning(
                "worktree",
                f"Re-attaching detached HEAD to branch '{target_branch}' before push",
            )
            # Check if the target branch exists locally
            if self._branch_exists(target_branch):
                # Move the branch ref to current commit and switch to it
                current_commit = self._run_git(["rev-parse", "HEAD"], cwd=info.path)
                if current_commit.returncode != 0:
                    return PushBranchResult(
                        success=False,
                        branch=target_branch,
                        error=f"Failed to resolve HEAD commit: {current_commit.stderr}",
                    )
                commit_sha = current_commit.stdout.strip()
                # Update the branch to point to current commit
                branch_update = self._run_git(
                    ["branch", "-f", target_branch, commit_sha],
                    cwd=info.path,
                )
                if branch_update.returncode != 0:
                    return PushBranchResult(
                        success=False,
                        branch=target_branch,
                        error=f"Failed to update branch '{target_branch}' to commit {commit_sha}: {branch_update.stderr}",
                    )
                # Switch to the branch
                switch_result = self._run_git(
                    ["checkout", target_branch], cwd=info.path
                )
                if switch_result.returncode != 0:
                    return PushBranchResult(
                        success=False,
                        branch=target_branch,
                        error=f"Failed to re-attach to branch '{target_branch}': {switch_result.stderr}",
                    )
            else:
                # Branch doesn't exist locally - create it at current HEAD
                checkout_result = self._run_git(
                    ["checkout", "-b", target_branch], cwd=info.path
                )
                if checkout_result.returncode != 0:
                    return PushBranchResult(
                        success=False,
                        branch=target_branch,
                        error=f"Failed to create branch '{target_branch}': {checkout_result.stderr}",
                    )

        # Push the branch to origin
        push_args = ["push", "-u", "origin", info.branch]
        if force:
            push_args.insert(1, "--force")

        def do_push() -> tuple[bool, PushBranchResult | None, str]:
            """Execute push operation for retry wrapper."""
            try:
                git_executable = get_git_executable()
                result = subprocess.run(
                    [git_executable] + push_args,
                    cwd=info.path,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=self.GIT_PUSH_TIMEOUT,
                    env=get_isolated_git_env(),
                )

                if result.returncode == 0:
                    return (
                        True,
                        PushBranchResult(
                            success=True,
                            branch=info.branch,
                            remote="origin",
                        ),
                        "",
                    )
                return (False, None, result.stderr)
            except FileNotFoundError:
                return (False, None, "git executable not found")

        max_retries = 3
        result, last_error = _with_retry(
            operation=do_push,
            max_retries=max_retries,
            is_retryable=_is_retryable_network_error,
        )

        if result:
            return result

        # Handle timeout error message
        if last_error == "Operation timed out":
            return PushBranchResult(
                success=False,
                branch=info.branch,
                error=f"Push timed out after {max_retries} attempts.",
            )

        return PushBranchResult(
            success=False,
            branch=info.branch,
            error=f"Failed to push branch: {last_error}",
        )

    def _get_azure_devops_credentials(self) -> tuple[str, str] | None:
        """Get Azure DevOps credentials from git credential manager or environment.

        Tries in order:
        1. AZURE_DEVOPS_PAT environment variable
        2. Git credential manager (same credentials used for git push)

        Returns:
            Tuple of (username, password/PAT) or None if no credentials found.
        """
        # 1. Check for PAT in environment
        pat = os.environ.get("AZURE_DEVOPS_PAT") or os.environ.get(
            "AZURE_DEVOPS_EXT_PAT"
        )
        if pat:
            return ("", pat)

        # 2. Try git credential manager
        try:
            remote_result = self._run_git(
                ["remote", "get-url", "origin"], cwd=self.project_dir
            )
            if remote_result.returncode != 0 or not remote_result.stdout.strip():
                return None

            remote_url = remote_result.stdout.strip()

            # Parse the remote URL to extract protocol, host, and path
            from urllib.parse import urlparse

            parsed = urlparse(remote_url)
            if not parsed.hostname:
                return None

            # Build credential fill input
            cred_input = f"protocol={parsed.scheme}\nhost={parsed.hostname}\npath={parsed.path.lstrip('/')}\n\n"

            git_executable = get_git_executable()
            result = subprocess.run(
                [git_executable, "credential", "fill"],
                input=cred_input,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
                cwd=self.project_dir,
                env=get_isolated_git_env(),
            )

            if result.returncode == 0 and result.stdout:
                username = ""
                password = ""
                for line in result.stdout.strip().split("\n"):
                    if line.startswith("username="):
                        username = line[len("username=") :]
                    elif line.startswith("password="):
                        password = line[len("password=") :]
                if password:
                    return (username, password)

        except Exception as e:
            logger.debug(f"Failed to get credentials from git credential manager: {e}")

        return None

    def create_azure_pull_request(
        self,
        spec_name: str,
        target_branch: str | None = None,
        title: str | None = None,
        draft: bool = False,
    ) -> PullRequestResult:
        """
        Create an Azure DevOps pull request using the REST API.

        Uses git credential manager or AZURE_DEVOPS_PAT environment variable
        for authentication (same credentials that git push uses).

        Args:
            spec_name: The spec folder name
            target_branch: Target branch for PR (defaults to base_branch)
            title: PR title (defaults to spec name)
            draft: Whether to create as draft PR

        Returns:
            PullRequestResult with keys:
                - success: bool
                - pr_url: str (if created)
                - already_exists: bool (if PR already exists)
                - error: str (if failed)
        """
        import requests

        info = self.get_worktree_info(spec_name)
        if not info:
            return PullRequestResult(
                success=False,
                error=f"No worktree found for spec: {spec_name}",
            )

        target = target_branch or self.base_branch
        pr_title = title or f"feat: {spec_name}"

        # Try AI-powered PR body from project's PR template, fall back to spec summary
        pr_body: str | None = None
        try:
            diff_summary, commit_log = self._gather_pr_context(spec_name, target)
            pr_body = self._try_ai_pr_body(
                spec_name=spec_name,
                target_branch=target,
                branch_name=info.branch,
                diff_summary=diff_summary,
                commit_log=commit_log,
            )
        except Exception as e:
            logger.warning(f"AI PR body generation encountered an error: {e}")

        if not pr_body:
            pr_body = self._extract_spec_summary(spec_name)

        # Extract Azure DevOps coordinates from git remote
        org = extract_azure_devops_org(self.project_dir)
        project = extract_azure_devops_project(self.project_dir)
        repository = extract_azure_devops_repository(self.project_dir)

        if not org:
            return PullRequestResult(
                success=False,
                error="Could not extract Azure DevOps organization from git remote URL",
            )
        if not project:
            return PullRequestResult(
                success=False,
                error="Could not extract Azure DevOps project from git remote URL",
            )
        if not repository:
            return PullRequestResult(
                success=False,
                error="Could not extract Azure DevOps repository from git remote URL",
            )

        # Get credentials
        credentials = self._get_azure_devops_credentials()
        if not credentials:
            return PullRequestResult(
                success=False,
                error=(
                    "No Azure DevOps credentials found. "
                    "Set AZURE_DEVOPS_PAT environment variable or configure git credential manager."
                ),
            )

        username, password = credentials
        auth = (username, password)

        # URL-encode project and repository for API calls
        from urllib.parse import quote

        project_encoded = quote(project, safe="")
        repository_encoded = quote(repository, safe="")
        base_url = f"https://dev.azure.com/{quote(org, safe='')}/{project_encoded}/_apis/git/repositories/{repository_encoded}"
        api_version = "api-version=7.1"

        def is_pr_retryable(stderr: str) -> bool:
            """Check if PR creation error is retryable (network or HTTP 5xx)."""
            return _is_retryable_network_error(stderr) or _is_retryable_http_error(
                stderr
            )

        def do_create_pr() -> tuple[bool, PullRequestResult | None, str]:
            """Execute PR creation for retry wrapper."""
            try:
                # Check if PR already exists
                try:
                    search_url = (
                        f"{base_url}/pullrequests?{api_version}"
                        f"&searchCriteria.sourceRefName=refs/heads/{info.branch}"
                        f"&searchCriteria.targetRefName=refs/heads/{target}"
                        f"&searchCriteria.status=active"
                    )
                    resp = requests.get(search_url, auth=auth, timeout=30)
                    if resp.status_code == 200:
                        data = resp.json()
                        prs = data.get("value", [])
                        if prs:
                            # PR already exists — build the web URL
                            pr_id = prs[0].get("pullRequestId")
                            pr_url = (
                                f"https://dev.azure.com/{quote(org, safe='')}"
                                f"/{project_encoded}/_git/{repository_encoded}"
                                f"/pullrequest/{pr_id}"
                            )
                            return (
                                True,
                                PullRequestResult(
                                    success=True,
                                    pr_url=pr_url,
                                    already_exists=True,
                                ),
                                "",
                            )
                except Exception:
                    # Continue with creation if check fails
                    pass

                # Create pull request via REST API
                create_url = f"{base_url}/pullrequests?{api_version}"
                payload: dict = {
                    "sourceRefName": f"refs/heads/{info.branch}",
                    "targetRefName": f"refs/heads/{target}",
                    "title": pr_title,
                    "description": pr_body or "",
                }
                if draft:
                    payload["isDraft"] = True

                resp = requests.post(
                    create_url,
                    json=payload,
                    auth=auth,
                    timeout=30,
                )

                if resp.status_code in (200, 201):
                    data = resp.json()
                    pr_id = data.get("pullRequestId")
                    pr_url = (
                        f"https://dev.azure.com/{quote(org, safe='')}"
                        f"/{project_encoded}/_git/{repository_encoded}"
                        f"/pullrequest/{pr_id}"
                    )
                    return (
                        True,
                        PullRequestResult(
                            success=True,
                            pr_url=pr_url,
                            already_exists=False,
                        ),
                        "",
                    )

                # Handle specific error cases
                error_body = resp.text
                if resp.status_code == 409 or "already exists" in error_body.lower():
                    # PR already exists — try to find it
                    try:
                        search_url = (
                            f"{base_url}/pullrequests?{api_version}"
                            f"&searchCriteria.sourceRefName=refs/heads/{info.branch}"
                            f"&searchCriteria.targetRefName=refs/heads/{target}"
                            f"&searchCriteria.status=active"
                        )
                        search_resp = requests.get(search_url, auth=auth, timeout=30)
                        if search_resp.status_code == 200:
                            prs = search_resp.json().get("value", [])
                            if prs:
                                pr_id = prs[0].get("pullRequestId")
                                pr_url = (
                                    f"https://dev.azure.com/{quote(org, safe='')}"
                                    f"/{project_encoded}/_git/{repository_encoded}"
                                    f"/pullrequest/{pr_id}"
                                )
                                return (
                                    True,
                                    PullRequestResult(
                                        success=True,
                                        pr_url=pr_url,
                                        already_exists=True,
                                    ),
                                    "",
                                )
                    except Exception:
                        pass

                if resp.status_code == 401:
                    return (
                        False,
                        None,
                        "Azure DevOps authentication failed. Check your PAT or credentials.",
                    )
                if resp.status_code == 403:
                    return (
                        False,
                        None,
                        "Azure DevOps access denied. Ensure your PAT has 'Code (Read & Write)' scope.",
                    )

                # Try to parse error message from response
                try:
                    err_data = resp.json()
                    err_msg = err_data.get("message", error_body)
                except Exception:
                    err_msg = error_body

                return (
                    False,
                    None,
                    f"Azure DevOps API error (HTTP {resp.status_code}): {err_msg}",
                )

            except requests.exceptions.Timeout:
                return (False, None, "timeout")
            except requests.exceptions.ConnectionError as e:
                return (False, None, f"connection error: {e}")
            except Exception as e:
                return (
                    False,
                    None,
                    f"Failed to create Azure DevOps pull request: {e}",
                )

        # Execute with retry logic
        result, last_error = _with_retry(
            operation=do_create_pr,
            max_retries=3,
            is_retryable=is_pr_retryable,
        )

        if result is None:
            return PullRequestResult(
                success=False,
                error=last_error or "Unknown error creating Azure DevOps pull request",
            )

        return result

    def create_pull_request(
        self,
        spec_name: str,
        target_branch: str | None = None,
        title: str | None = None,
        draft: bool = False,
    ) -> PullRequestResult:
        """
        Create a GitHub pull request for a spec's branch using gh CLI with retry logic.

        Args:
            spec_name: The spec folder name
            target_branch: Target branch for PR (defaults to base_branch)
            title: PR title (defaults to spec name)
            draft: Whether to create as draft PR

        Returns:
            PullRequestResult with keys:
                - success: bool
                - pr_url: str (if created)
                - already_exists: bool (if PR already exists)
                - error: str (if failed)
        """
        info = self.get_worktree_info(spec_name)
        if not info:
            return PullRequestResult(
                success=False,
                error=f"No worktree found for spec: {spec_name}",
            )

        target = target_branch or self.base_branch
        pr_title = title or f"feat: {spec_name}"

        # Try AI-powered PR body from project's PR template, fall back to spec summary
        pr_body: str | None = None
        try:
            diff_summary, commit_log = self._gather_pr_context(spec_name, target)
            pr_body = self._try_ai_pr_body(
                spec_name=spec_name,
                target_branch=target,
                branch_name=info.branch,
                diff_summary=diff_summary,
                commit_log=commit_log,
            )
        except Exception as e:
            logger.warning(f"AI PR body generation encountered an error: {e}")

        if not pr_body:
            pr_body = self._extract_spec_summary(spec_name)

        # Find gh executable before attempting PR creation
        gh_executable = get_gh_executable()
        if not gh_executable:
            return PullRequestResult(
                success=False,
                error="GitHub CLI (gh) not found. Install from https://cli.github.com/",
            )

        # Build gh pr create command
        gh_args = [
            gh_executable,
            "pr",
            "create",
            "--base",
            target,
            "--head",
            info.branch,
            "--title",
            pr_title,
            "--body",
            pr_body,
        ]
        if draft:
            gh_args.append("--draft")

        def is_pr_retryable(stderr: str) -> bool:
            """Check if PR creation error is retryable (network or HTTP 5xx)."""
            return _is_retryable_network_error(stderr) or _is_retryable_http_error(
                stderr
            )

        def do_create_pr() -> tuple[bool, PullRequestResult | None, str]:
            """Execute PR creation for retry wrapper."""
            try:
                result = subprocess.run(
                    gh_args,
                    cwd=info.path,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=self.CLI_TIMEOUT,
                    env=get_isolated_git_env(),
                )

                # Check for "already exists" case (success, no retry needed)
                if result.returncode != 0 and "already exists" in result.stderr.lower():
                    existing_url = self._get_existing_pr_url(spec_name, target)
                    result_dict = PullRequestResult(
                        success=True,
                        pr_url=existing_url,
                        already_exists=True,
                    )
                    if existing_url is None:
                        result_dict["message"] = (
                            "PR already exists but URL could not be retrieved"
                        )
                    return (True, result_dict, "")

                if result.returncode == 0:
                    # Extract PR URL from output
                    pr_url: str | None = result.stdout.strip()
                    if not pr_url.startswith("http"):
                        # Try to find URL in output
                        # Use general pattern to support GitHub Enterprise instances
                        # Matches any HTTPS URL with /pull/<number> path
                        match = re.search(r"https://[^\s]+/pull/\d+", result.stdout)
                        if match:
                            pr_url = match.group(0)
                        else:
                            # Invalid output - no valid URL found
                            pr_url = None

                    return (
                        True,
                        PullRequestResult(
                            success=True,
                            pr_url=pr_url,
                            already_exists=False,
                        ),
                        "",
                    )

                return (False, None, result.stderr)

            except FileNotFoundError:
                # gh CLI not installed - not retryable, raise to exit retry loop
                raise

        max_retries = 3
        try:
            result, last_error = _with_retry(
                operation=do_create_pr,
                max_retries=max_retries,
                is_retryable=is_pr_retryable,
            )

            if result:
                return result

            # Handle timeout error message
            if last_error == "Operation timed out":
                return PullRequestResult(
                    success=False,
                    error=f"PR creation timed out after {max_retries} attempts.",
                )

            return PullRequestResult(
                success=False,
                error=f"Failed to create PR: {last_error}",
            )

        except FileNotFoundError:
            # Cached gh path became invalid - clear cache so next call re-discovers
            invalidate_gh_cache()
            return PullRequestResult(
                success=False,
                error="GitHub CLI (gh) not found. Install from https://cli.github.com/",
            )

    def create_merge_request(
        self,
        spec_name: str,
        target_branch: str | None = None,
        title: str | None = None,
        draft: bool = False,
    ) -> PullRequestResult:
        """
        Create a GitLab merge request for a spec's branch using glab CLI with retry logic.

        Args:
            spec_name: The spec folder name
            target_branch: Target branch for MR (defaults to base_branch)
            title: MR title (defaults to spec name)
            draft: Whether to create as draft MR

        Returns:
            PullRequestResult with keys:
                - success: bool
                - pr_url: str (if created)
                - already_exists: bool (if MR already exists)
                - error: str (if failed)
        """
        info = self.get_worktree_info(spec_name)
        if not info:
            return PullRequestResult(
                success=False,
                error=f"No worktree found for spec: {spec_name}",
            )

        target = target_branch or self.base_branch
        mr_title = title or f"feat: {spec_name}"

        # Get MR body from spec.md if available
        mr_body = self._extract_spec_summary(spec_name)

        # Find glab executable before attempting MR creation
        glab_executable = get_glab_executable()
        if not glab_executable:
            return PullRequestResult(
                success=False,
                error="GitLab CLI (glab) not found. Install from https://gitlab.com/gitlab-org/cli",
            )

        # Build glab mr create command
        glab_args = [
            glab_executable,
            "mr",
            "create",
            "--target-branch",
            target,
            "--source-branch",
            info.branch,
            "--title",
            mr_title,
            "--description",
            mr_body,
        ]
        if draft:
            glab_args.append("--draft")

        def is_mr_retryable(stderr: str) -> bool:
            """Check if MR creation error is retryable (network or HTTP 5xx)."""
            return _is_retryable_network_error(stderr) or _is_retryable_http_error(
                stderr
            )

        def do_create_mr() -> tuple[bool, PullRequestResult | None, str]:
            """Execute MR creation for retry wrapper."""
            try:
                result = subprocess.run(
                    glab_args,
                    cwd=info.path,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=self.CLI_TIMEOUT,
                    env=get_isolated_git_env(),
                )

                # Check for "already exists" case (success, no retry needed)
                if result.returncode != 0 and "already exists" in result.stderr.lower():
                    existing_url = self._get_existing_mr_url(spec_name, target)
                    result_dict = PullRequestResult(
                        success=True,
                        pr_url=existing_url,
                        already_exists=True,
                    )
                    if existing_url is None:
                        result_dict["message"] = (
                            "MR already exists but URL could not be retrieved"
                        )
                    return (True, result_dict, "")

                if result.returncode == 0:
                    # Extract MR URL from output
                    mr_url: str | None = result.stdout.strip()
                    if not mr_url.startswith("http"):
                        # Try to find URL in output
                        # GitLab URL pattern: matches any HTTPS URL with /merge_requests/<number> or /-/merge_requests/<number> path
                        match = re.search(
                            r"https://[^\s]+(?:/merge_requests/|/-/merge_requests/)\d+",
                            result.stdout,
                        )
                        if match:
                            mr_url = match.group(0)
                        else:
                            # Invalid output - no valid URL found
                            mr_url = None

                    return (
                        True,
                        PullRequestResult(
                            success=True,
                            pr_url=mr_url,
                            already_exists=False,
                        ),
                        "",
                    )

                return (False, None, result.stderr)

            except FileNotFoundError:
                # glab CLI not installed - not retryable, raise to exit retry loop
                raise

        max_retries = 3
        try:
            result, last_error = _with_retry(
                operation=do_create_mr,
                max_retries=max_retries,
                is_retryable=is_mr_retryable,
            )

            if result:
                return result

            # Handle timeout error message
            if last_error == "Operation timed out":
                return PullRequestResult(
                    success=False,
                    error=f"MR creation timed out after {max_retries} attempts.",
                )

            return PullRequestResult(
                success=False,
                error=f"Failed to create MR: {last_error}",
            )

        except FileNotFoundError:
            # Cached glab path became invalid - clear cache so next call re-discovers
            invalidate_glab_cache()
            return PullRequestResult(
                success=False,
                error="GitLab CLI (glab) not found. Install from https://gitlab.com/gitlab-org/cli",
            )

    def _gather_pr_context(self, spec_name: str, target_branch: str) -> tuple[str, str]:
        """
        Gather diff summary and commit log for PR template filling.

        Args:
            spec_name: The spec folder name
            target_branch: The target branch for the PR

        Returns:
            Tuple of (diff_summary, commit_log)
        """
        worktree_path = self.get_worktree_path(spec_name)
        info = self.get_worktree_info(spec_name)
        branch = info.branch if info else self.get_branch_name(spec_name)

        # Get diff summary (stat for overview)
        diff_result = self._run_git(
            ["diff", "--stat", f"{target_branch}...{branch}"],
            cwd=worktree_path,
            timeout=30,
        )
        diff_summary = diff_result.stdout.strip() if diff_result.returncode == 0 else ""

        # Get shortstat for quick summary
        shortstat_result = self._run_git(
            ["diff", "--shortstat", f"{target_branch}...{branch}"],
            cwd=worktree_path,
            timeout=30,
        )
        if shortstat_result.returncode == 0 and shortstat_result.stdout.strip():
            diff_summary += "\n\n" + shortstat_result.stdout.strip()

        # Get actual code changes (patch format) for better AI context
        # Truncate to 30k chars to avoid token limits while still providing meaningful context
        patch_result = self._run_git(
            ["diff", "-p", "--stat-width=999", f"{target_branch}...{branch}"],
            cwd=worktree_path,
            timeout=30,
        )
        if patch_result.returncode == 0 and patch_result.stdout.strip():
            patch_content = patch_result.stdout.strip()
            MAX_DIFF_CHARS = 30_000

            if len(patch_content) > MAX_DIFF_CHARS:
                # Truncate patch and add notice
                truncated_patch = patch_content[:MAX_DIFF_CHARS]
                diff_summary += (
                    "\n\n" + truncated_patch + "\n\n(... diff truncated due to size)"
                )
            else:
                diff_summary += "\n\n" + patch_content

        # Get commit log
        log_result = self._run_git(
            [
                "log",
                "--oneline",
                "--no-merges",
                f"{target_branch}..{branch}",
            ],
            cwd=worktree_path,
            timeout=30,
        )
        commit_log = log_result.stdout.strip() if log_result.returncode == 0 else ""

        return diff_summary, commit_log

    def _try_ai_pr_body(
        self,
        spec_name: str,
        target_branch: str,
        branch_name: str,
        diff_summary: str,
        commit_log: str,
    ) -> str | None:
        """
        Attempt to generate a PR body using the AI template filler agent.

        Runs the async agent synchronously with a 30-second timeout.
        Returns None on any failure so the caller can fall back gracefully.

        Args:
            spec_name: The spec folder name
            target_branch: The target branch for the PR
            branch_name: The source branch name
            diff_summary: Git diff summary of changes
            commit_log: Git log of commits

        Returns:
            The AI-generated PR body string, or None if unavailable.
        """
        try:
            from agents.pr_template_filler import (
                detect_pr_template,
                run_pr_template_filler,
            )
        except ImportError:
            logger.warning(
                "PR template filler module not available, skipping AI PR body"
            )
            return None

        # Check if a PR template exists before doing any heavy lifting
        template = detect_pr_template(self.project_dir)
        if template is None:
            return None

        # Resolve spec directory
        spec_dir = self.project_dir / ".workpilot" / "specs" / spec_name
        if not spec_dir.is_dir():
            # Try worktree-local spec path
            worktree_path = self.get_worktree_path(spec_name)
            spec_dir = worktree_path / ".workpilot" / "specs" / spec_name
            if not spec_dir.is_dir():
                logger.warning("Spec directory not found for AI PR body generation")
                return None

        # Get model configuration from environment (respects user settings)
        model, thinking_budget = get_utility_model_config()

        async def _run_with_timeout() -> str | None:
            try:
                return await asyncio.wait_for(
                    run_pr_template_filler(
                        project_dir=self.project_dir,
                        spec_dir=spec_dir,
                        model=model,
                        thinking_budget=thinking_budget,
                        branch_name=branch_name,
                        target_branch=target_branch,
                        diff_summary=diff_summary,
                        commit_log=commit_log,
                        verbose=False,
                    ),
                    timeout=30.0,
                )
            except asyncio.TimeoutError:
                logger.warning("PR template filler timed out after 30s")
                return None

        try:
            # Check if there's already a running event loop
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # We're already inside an async context — run in a new thread
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(asyncio.run, _run_with_timeout())
                    return future.result(timeout=35)
            else:
                return asyncio.run(_run_with_timeout())

        except Exception as e:
            logger.warning(f"AI PR body generation failed: {e}")
            return None

    def _extract_spec_summary(self, spec_name: str) -> str:
        """
        Build a rich Markdown PR/MR body from the spec summary.

        Extracts the first paragraphs of ``spec.md`` and wraps them in a
        localised template that includes a review checklist and footer.
        When no spec is available the method returns a minimal fallback body.

        Args:
            spec_name: The spec folder name (e.g. ``001-my-feature``).

        Returns:
            Formatted Markdown string ready to be used as a PR/MR body.
        """
        # ── locate spec.md ────────────────────────────────────────────
        worktree_path = self.get_worktree_path(spec_name)
        spec_path = worktree_path / ".workpilot" / "specs" / spec_name / "spec.md"

        if not spec_path.exists():
            # Try project spec path
            spec_path = (
                self.project_dir / ".workpilot" / "specs" / spec_name / "spec.md"
            )

        # ── extract raw summary text ──────────────────────────────────
        raw_summary: str | None = None
        if spec_path.exists():
            try:
                content = spec_path.read_text(encoding="utf-8")
                lines = content.split("\n")
                summary_lines: list[str] = []
                in_content = False

                for line in lines:
                    if line.startswith("# "):
                        continue
                    if line.strip() and not line.startswith("#"):
                        in_content = True
                    if in_content:
                        if line.startswith("## ") and summary_lines:
                            break
                        summary_lines.append(line)
                        if len(summary_lines) >= 10:
                            break

                text = "\n".join(summary_lines).strip()
                if text:
                    raw_summary = text
            except (OSError, UnicodeDecodeError) as e:
                debug_warning(
                    "worktree",
                    f"Could not extract spec summary for PR body: {e}",
                )

        # ── build rich markdown body ──────────────────────────────────
        summary_text = raw_summary or _wt("fallback_footer")

        parts = [
            f"## 🤖 {_wt('summary_section')}",
            "",
            summary_text,
            "",
            f"### ✅ {_wt('checklist_section')}",
            f"- [ ] {_wt('check_standards')}",
            f"- [ ] {_wt('check_tests')}",
            f"- [ ] {_wt('check_docs')}",
            f"- [ ] {_wt('check_coherent')}",
            f"- [ ] {_wt('check_regression')}",
            "",
            "---",
            f"⚠️ **{_wt('warning')}**",
            "",
            f"_{_wt('footer')}_",
        ]

        return "\n".join(parts)

    def _get_existing_pr_url(self, spec_name: str, target_branch: str) -> str | None:
        """Get the URL of an existing PR for this branch."""
        info = self.get_worktree_info(spec_name)
        if not info:
            return None

        gh_executable = get_gh_executable()
        if not gh_executable:
            # gh CLI not found - return None and let caller handle it
            return None

        try:
            result = subprocess.run(
                [
                    gh_executable,
                    "pr",
                    "view",
                    info.branch,
                    "--json",
                    "url",
                    "--jq",
                    ".url",
                ],
                cwd=info.path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.CLI_QUERY_TIMEOUT,
                env=get_isolated_git_env(),
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (
            subprocess.TimeoutExpired,
            FileNotFoundError,
            subprocess.SubprocessError,
        ) as e:
            # Silently ignore errors when fetching existing PR URL - this is a best-effort
            # lookup that may fail due to network issues, missing gh CLI, or auth problems.
            # Returning None allows the caller to handle missing URLs gracefully.
            if isinstance(e, FileNotFoundError):
                invalidate_gh_cache()
            debug_warning("worktree", f"Could not get existing PR URL: {e}")

        return None

    def _get_existing_mr_url(self, spec_name: str, target_branch: str) -> str | None:
        """Get the URL of an existing MR for this branch."""
        info = self.get_worktree_info(spec_name)
        if not info:
            return None

        glab_executable = get_glab_executable()
        if not glab_executable:
            # glab CLI not found - return None and let caller handle it
            return None

        try:
            result = subprocess.run(
                [
                    glab_executable,
                    "mr",
                    "view",
                    info.branch,
                    "--output",
                    "json",
                ],
                cwd=info.path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.CLI_QUERY_TIMEOUT,
                env=get_isolated_git_env(),
            )
            if result.returncode == 0 and result.stdout.strip():
                # Parse JSON output to extract web_url (glab uses snake_case)
                try:
                    data = json.loads(result.stdout)
                    return data.get("web_url")
                except json.JSONDecodeError:
                    # If JSON parsing fails, return None
                    pass
        except (
            subprocess.TimeoutExpired,
            FileNotFoundError,
            subprocess.SubprocessError,
        ) as e:
            # Silently ignore errors when fetching existing MR URL - this is a best-effort
            # lookup that may fail due to network issues, missing glab CLI, or auth problems.
            # Returning None allows the caller to handle missing URLs gracefully.
            if isinstance(e, FileNotFoundError):
                invalidate_glab_cache()
            debug_warning("worktree", f"Could not get existing MR URL: {e}")

        return None

    def push_and_create_pr(
        self,
        spec_name: str,
        target_branch: str | None = None,
        title: str | None = None,
        draft: bool = False,
        force_push: bool = False,
    ) -> PushAndCreatePRResult:
        """
        Push branch and create a pull request/merge request in one operation.
        Automatically detects git provider (GitHub or GitLab) and routes to the appropriate CLI.

        Args:
            spec_name: The spec folder name
            target_branch: Target branch for PR/MR (defaults to base_branch)
            title: PR/MR title (defaults to spec name)
            draft: Whether to create as draft PR/MR
            force_push: Whether to force push the branch

        Returns:
            PushAndCreatePRResult with keys:
                - success: bool
                - pr_url: str (if created)
                - pushed: bool (if push succeeded)
                - provider: str ('github', 'gitlab', or 'unknown')
                - already_exists: bool (if PR/MR already exists)
                - error: str (if failed)
        """
        # Step 1: Push the branch
        push_result = self.push_branch(spec_name, force=force_push)
        if not push_result.get("success"):
            return PushAndCreatePRResult(
                success=False,
                pushed=False,
                branch=push_result.get("branch", ""),
                remote=push_result.get("remote", ""),
                error=push_result.get("error", "Push failed"),
            )

        # Step 2: Detect git provider (use the remote that was pushed to)
        provider = detect_git_provider(
            self.project_dir, remote_name=push_result.get("remote")
        )

        # Step 3: Create the PR/MR based on provider
        if provider == "azure_devops":
            pr_result = self.create_azure_pull_request(
                spec_name=spec_name,
                target_branch=target_branch,
                title=title,
                draft=draft,
            )
        elif provider == "github":
            pr_result = self.create_pull_request(
                spec_name=spec_name,
                target_branch=target_branch,
                title=title,
                draft=draft,
            )
        elif provider == "gitlab":
            pr_result = self.create_merge_request(
                spec_name=spec_name,
                target_branch=target_branch,
                title=title,
                draft=draft,
            )
        else:
            # Unknown provider
            return PushAndCreatePRResult(
                success=False,
                pushed=True,
                remote=push_result.get("remote"),
                branch=push_result.get("branch"),
                provider=provider,
                error="Unable to determine git hosting provider. Supported: GitHub, GitLab, Azure DevOps.",
            )

        # Combine results
        return PushAndCreatePRResult(
            success=pr_result.get("success", False),
            pushed=True,
            remote=push_result.get("remote"),
            branch=push_result.get("branch"),
            provider=provider,
            pr_url=pr_result.get("pr_url"),
            already_exists=pr_result.get("already_exists", False),
            error=pr_result.get("error"),
        )

    # ==================== Worktree Cleanup Methods ====================

    def get_old_worktrees(
        self, days_threshold: int = 30, include_stats: bool = False
    ) -> list[WorktreeInfo] | list[str]:
        """
        Find worktrees that haven't been modified in the specified number of days.

        Args:
            days_threshold: Number of days without activity to consider a worktree old (default: 30)
            include_stats: If True, return full WorktreeInfo objects; if False, return just spec names

        Returns:
            List of old worktrees (either WorktreeInfo objects or spec names based on include_stats)
        """
        old_worktrees = []

        for worktree_info in self.list_all_worktrees():
            # Skip if we can't determine age
            if worktree_info.days_since_last_commit is None:
                continue

            if worktree_info.days_since_last_commit >= days_threshold:
                if include_stats:
                    old_worktrees.append(worktree_info)
                else:
                    old_worktrees.append(worktree_info.spec_name)

        return old_worktrees

    def cleanup_old_worktrees(
        self, days_threshold: int = 30, dry_run: bool = False
    ) -> tuple[list[str], list[str]]:
        """
        Remove worktrees that haven't been modified in the specified number of days.

        Args:
            days_threshold: Number of days without activity to consider a worktree old (default: 30)
            dry_run: If True, only report what would be removed without actually removing

        Returns:
            Tuple of (removed_specs, failed_specs) containing spec names
        """
        old_worktrees = self.get_old_worktrees(
            days_threshold=days_threshold, include_stats=True
        )

        if not old_worktrees:
            print(f"No worktrees found older than {days_threshold} days.")
            return ([], [])

        removed = []
        failed = []

        if dry_run:
            print(f"\n[DRY RUN] Would remove {len(old_worktrees)} old worktrees:")
            for info in old_worktrees:
                print(
                    f"  - {info.spec_name} (last activity: {info.days_since_last_commit} days ago)"
                )
            return ([], [])

        print(f"\nRemoving {len(old_worktrees)} old worktrees...")
        for info in old_worktrees:
            try:
                self.remove_worktree(info.spec_name, delete_branch=True)
                removed.append(info.spec_name)
                print(
                    f"  ✓ Removed {info.spec_name} (last activity: {info.days_since_last_commit} days ago)"
                )
            except Exception as e:
                failed.append(info.spec_name)
                print(f"  ✗ Failed to remove {info.spec_name}: {e}")

        if removed:
            print(f"\nSuccessfully removed {len(removed)} worktree(s).")
        if failed:
            print(f"Failed to remove {len(failed)} worktree(s).")

        return (removed, failed)

    def get_worktree_count_warning(
        self, warning_threshold: int = 10, critical_threshold: int = 20
    ) -> str | None:
        """
        Check worktree count and return a warning message if threshold is exceeded.

        Args:
            warning_threshold: Number of worktrees to trigger a warning (default: 10)
            critical_threshold: Number of worktrees to trigger a critical warning (default: 20)

        Returns:
            Warning message string if threshold exceeded, None otherwise
        """
        worktrees = self.list_all_worktrees()
        count = len(worktrees)

        if count >= critical_threshold:
            old_worktrees = self.get_old_worktrees(days_threshold=30)
            old_count = len(old_worktrees)
            return (
                f"CRITICAL: {count} worktrees detected! "
                f"Consider cleaning up old worktrees ({old_count} are 30+ days old). "
                f"Run cleanup to remove stale worktrees."
            )
        elif count >= warning_threshold:
            old_worktrees = self.get_old_worktrees(days_threshold=30)
            old_count = len(old_worktrees)
            return (
                f"WARNING: {count} worktrees detected. "
                f"{old_count} are 30+ days old and may be safe to clean up."
            )

        return None

    def print_worktree_summary(self) -> None:
        """Print a summary of all worktrees with age information."""
        worktrees = self.list_all_worktrees()

        if not worktrees:
            print("No worktrees found.")
            return

        print(f"\n{'=' * 80}")
        print(f"Worktree Summary ({len(worktrees)} total)")
        print(f"{'=' * 80}\n")

        # Group by age
        recent = []  # < 7 days
        week_old = []  # 7-30 days
        month_old = []  # 30-90 days
        very_old = []  # > 90 days
        unknown_age = []

        for info in worktrees:
            if info.days_since_last_commit is None:
                unknown_age.append(info)
            elif info.days_since_last_commit < 7:
                recent.append(info)
            elif info.days_since_last_commit < 30:
                week_old.append(info)
            elif info.days_since_last_commit < 90:
                month_old.append(info)
            else:
                very_old.append(info)

        def print_group(title: str, items: list[WorktreeInfo]):
            if not items:
                return
            print(f"{title} ({len(items)}):")
            for info in sorted(items, key=lambda x: x.spec_name):
                age_str = (
                    f"{info.days_since_last_commit}d ago"
                    if info.days_since_last_commit is not None
                    else "unknown"
                )
                print(f"  - {info.spec_name} (last activity: {age_str})")
            print()

        print_group("Recent (< 7 days)", recent)
        print_group("Week Old (7-30 days)", week_old)
        print_group("Month Old (30-90 days)", month_old)
        print_group("Very Old (> 90 days)", very_old)
        print_group("Unknown Age", unknown_age)

        # Print cleanup suggestions
        if month_old or very_old:
            total_old = len(month_old) + len(very_old)
            print(f"{'=' * 80}")
            print(
                f"💡 Suggestion: {total_old} worktree(s) are 30+ days old and may be safe to clean up."
            )
            print("   Review these worktrees and run cleanup if no longer needed.")
            print(f"{'=' * 80}\n")
