"""
Cross-Repo Spec Manager
========================
Manages the parent (master) spec and per-repo sub-specs for multi-repo orchestration.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class RepoSubSpec:
    """Spec for a single repository within a multi-repo orchestration."""

    repo: str  # owner/repo or local path
    repo_path: str  # Local filesystem path to the repo
    spec_dir: str = ""  # Path to sub-spec directory (set after creation)
    worktree_path: str = ""  # Worktree path once created
    status: str = "pending"  # pending | analyzing | planning | coding | qa | completed | failed
    pr_url: str = ""
    branch_name: str = ""
    progress: float = 0.0  # 0-100
    current_phase: str = ""
    error_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo": self.repo,
            "repo_path": self.repo_path,
            "spec_dir": self.spec_dir,
            "worktree_path": self.worktree_path,
            "status": self.status,
            "pr_url": self.pr_url,
            "branch_name": self.branch_name,
            "progress": self.progress,
            "current_phase": self.current_phase,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RepoSubSpec:
        return cls(
            repo=data["repo"],
            repo_path=data.get("repo_path", ""),
            spec_dir=data.get("spec_dir", ""),
            worktree_path=data.get("worktree_path", ""),
            status=data.get("status", "pending"),
            pr_url=data.get("pr_url", ""),
            branch_name=data.get("branch_name", ""),
            progress=data.get("progress", 0.0),
            current_phase=data.get("current_phase", ""),
            error_message=data.get("error_message", ""),
        )


@dataclass
class MultiRepoManifest:
    """
    Master manifest for a multi-repo orchestration.

    Stored as multi_repo_manifest.json in the master spec directory.
    """

    task_description: str
    repos: list[RepoSubSpec] = field(default_factory=list)
    dependency_graph: dict[str, Any] = field(default_factory=dict)
    execution_order: list[str] = field(default_factory=list)
    status: str = "pending"  # pending | analyzing | planning | executing | creating_prs | completed | failed
    created_at: str = ""
    updated_at: str = ""
    cross_repo_context: str = ""  # Summary of completed repos for downstream agents
    breaking_changes: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def get_sub_spec(self, repo: str) -> RepoSubSpec | None:
        """Get sub-spec for a repository."""
        for sub in self.repos:
            if sub.repo == repo:
                return sub
        return None

    def update_sub_spec_status(
        self, repo: str, status: str, **kwargs: Any
    ) -> None:
        """Update status and optional fields for a repo sub-spec."""
        sub = self.get_sub_spec(repo)
        if sub:
            sub.status = status
            for key, value in kwargs.items():
                if hasattr(sub, key):
                    setattr(sub, key, value)
            self.updated_at = datetime.now(timezone.utc).isoformat()

    def get_completed_repos(self) -> list[str]:
        """Get list of repos that have completed successfully."""
        return [sub.repo for sub in self.repos if sub.status == "completed"]

    def get_overall_progress(self) -> float:
        """Calculate overall orchestration progress (0-100)."""
        if not self.repos:
            return 0.0
        total = sum(sub.progress for sub in self.repos)
        return total / len(self.repos)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_description": self.task_description,
            "repos": [sub.to_dict() for sub in self.repos],
            "dependency_graph": self.dependency_graph,
            "execution_order": self.execution_order,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "cross_repo_context": self.cross_repo_context,
            "breaking_changes": self.breaking_changes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MultiRepoManifest:
        manifest = cls(
            task_description=data.get("task_description", ""),
            dependency_graph=data.get("dependency_graph", {}),
            execution_order=data.get("execution_order", []),
            status=data.get("status", "pending"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            cross_repo_context=data.get("cross_repo_context", ""),
            breaking_changes=data.get("breaking_changes", []),
        )
        manifest.repos = [
            RepoSubSpec.from_dict(r) for r in data.get("repos", [])
        ]
        return manifest


class CrossRepoSpecManager:
    """
    Manages master spec directory and per-repo sub-specs.

    Directory structure:
        .auto-claude/specs/XXX-multi-repo-task/
            spec.md                      # Master spec
            multi_repo_manifest.json     # Orchestration state
            requirements.json
            repos/
                owner_frontend/          # Sub-spec per repo
                    spec.md
                    implementation_plan.json
                    context.json
                owner_backend/
                    ...
    """

    MANIFEST_FILE = "multi_repo_manifest.json"

    def __init__(self, master_spec_dir: Path):
        self.master_spec_dir = master_spec_dir
        self.repos_dir = master_spec_dir / "repos"

    def _repo_slug(self, repo: str) -> str:
        """Convert repo identifier to filesystem-safe directory name."""
        return re.sub(r"[^\w-]", "_", repo)

    def create_master_spec(
        self,
        task_description: str,
        repos: list[dict[str, str]],
        dependency_graph: dict[str, Any],
        execution_order: list[str],
    ) -> MultiRepoManifest:
        """
        Create master spec directory with manifest and sub-spec directories.

        Args:
            task_description: The cross-repo task description
            repos: List of repo dicts with 'repo' and 'repo_path' keys
            dependency_graph: Serialized RepoDependencyGraph
            execution_order: Topological order for execution
        """
        self.master_spec_dir.mkdir(parents=True, exist_ok=True)
        self.repos_dir.mkdir(parents=True, exist_ok=True)

        # Create sub-spec directories
        sub_specs = []
        for repo_info in repos:
            repo_name = repo_info["repo"]
            slug = self._repo_slug(repo_name)
            sub_dir = self.repos_dir / slug
            sub_dir.mkdir(parents=True, exist_ok=True)

            sub_specs.append(
                RepoSubSpec(
                    repo=repo_name,
                    repo_path=repo_info.get("repo_path", ""),
                    spec_dir=str(sub_dir),
                )
            )

        manifest = MultiRepoManifest(
            task_description=task_description,
            repos=sub_specs,
            dependency_graph=dependency_graph,
            execution_order=execution_order,
        )

        # Write master spec.md
        spec_content = self._generate_master_spec_md(
            task_description, repos, execution_order
        )
        (self.master_spec_dir / "spec.md").write_text(
            spec_content, encoding="utf-8"
        )

        # Save manifest
        self.save_manifest(manifest)

        return manifest

    def _generate_master_spec_md(
        self,
        task_description: str,
        repos: list[dict[str, str]],
        execution_order: list[str],
    ) -> str:
        """Generate the master spec markdown document."""
        lines = [
            "# Multi-Repo Orchestration Spec",
            "",
            "## Task Description",
            "",
            task_description,
            "",
            "## Target Repositories",
            "",
        ]
        for repo_info in repos:
            repo = repo_info["repo"]
            path = repo_info.get("repo_path", "N/A")
            lines.append(f"- **{repo}** — `{path}`")

        lines.extend(
            [
                "",
                "## Execution Order",
                "",
            ]
        )
        for i, repo in enumerate(execution_order, 1):
            lines.append(f"{i}. {repo}")

        lines.extend(
            [
                "",
                "## Cross-Repo Coordination Notes",
                "",
                "- Shared libraries and providers are executed first",
                "- Consumer repos receive cross-repo context from completed upstream repos",
                "- Breaking changes are detected after each repo completes",
                "- Linked PRs are created with cross-references",
            ]
        )

        return "\n".join(lines) + "\n"

    def create_sub_spec(
        self,
        repo: str,
        spec_content: str,
        implementation_plan: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> Path:
        """
        Write spec files for a specific repo's sub-spec.

        Returns the sub-spec directory path.
        """
        slug = self._repo_slug(repo)
        sub_dir = self.repos_dir / slug
        sub_dir.mkdir(parents=True, exist_ok=True)

        (sub_dir / "spec.md").write_text(spec_content, encoding="utf-8")

        if implementation_plan:
            with open(sub_dir / "implementation_plan.json", "w", encoding="utf-8") as f:
                json.dump(implementation_plan, f, indent=2)

        if context:
            with open(sub_dir / "context.json", "w", encoding="utf-8") as f:
                json.dump(context, f, indent=2)

        return sub_dir

    def save_manifest(self, manifest: MultiRepoManifest) -> None:
        """Save manifest to disk."""
        manifest.updated_at = datetime.now(timezone.utc).isoformat()
        manifest_path = self.master_spec_dir / self.MANIFEST_FILE
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, indent=2)

    def load_manifest(self) -> MultiRepoManifest | None:
        """Load manifest from disk. Returns None if not found."""
        manifest_path = self.master_spec_dir / self.MANIFEST_FILE
        if not manifest_path.exists():
            return None
        with open(manifest_path, encoding="utf-8") as f:
            return MultiRepoManifest.from_dict(json.load(f))
