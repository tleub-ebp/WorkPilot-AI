"""
Breaking Change Detector
=========================
Detects breaking changes across repository boundaries by analyzing
git diffs, API contracts, shared types, and package versions.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .repo_graph import DependencyType, RepoDependencyGraph

logger = logging.getLogger(__name__)


@dataclass
class BreakingChange:
    """A detected breaking change across repository boundaries."""

    source_repo: str  # Repo where the change was made
    target_repo: str  # Repo that will be affected
    change_type: str  # "api_contract" | "type_definition" | "package_version" | "schema" | "export"
    description: str
    severity: str  # "warning" | "error"
    file_path: str = ""
    suggestion: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_repo": self.source_repo,
            "target_repo": self.target_repo,
            "change_type": self.change_type,
            "description": self.description,
            "severity": self.severity,
            "file_path": self.file_path,
            "suggestion": self.suggestion,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BreakingChange:
        return cls(
            source_repo=data["source_repo"],
            target_repo=data["target_repo"],
            change_type=data["change_type"],
            description=data["description"],
            severity=data["severity"],
            file_path=data.get("file_path", ""),
            suggestion=data.get("suggestion", ""),
        )


class BreakingChangeDetector:
    """
    Detects breaking changes across repo boundaries.

    After each repo completes its pipeline, the detector compares its
    diffs against downstream consumers to identify contract violations.
    """

    def __init__(self, repo_paths: dict[str, Path]):
        """
        Args:
            repo_paths: Dict mapping repo name to local filesystem path.
        """
        self.repo_paths = repo_paths

    def _get_git_diff(self, repo_path: Path, branch: str = "") -> str:
        """Get git diff for a repo (worktree changes vs base branch)."""
        try:
            cmd = ["git", "diff", "--stat"]
            if branch:
                cmd.append(branch)
            result = subprocess.run(
                cmd,
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.stdout
        except Exception as e:
            logger.warning(f"Failed to get git diff for {repo_path}: {e}")
            return ""

    def _get_changed_files(self, repo_path: Path, branch: str = "") -> list[str]:
        """Get list of changed files in a repo."""
        try:
            cmd = ["git", "diff", "--name-only"]
            if branch:
                cmd.append(branch)
            result = subprocess.run(
                cmd,
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                timeout=30,
            )
            return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
        except Exception:
            return []

    def _get_file_diff(self, repo_path: Path, file_path: str, branch: str = "") -> str:
        """Get detailed diff for a specific file."""
        try:
            cmd = ["git", "diff"]
            if branch:
                cmd.append(branch)
            cmd.append(file_path)
            result = subprocess.run(
                cmd,
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.stdout
        except Exception:
            return ""

    async def detect_breaking_changes(
        self,
        completed_repos: list[str],
        dependency_graph: RepoDependencyGraph,
        worktree_paths: dict[str, Path] | None = None,
    ) -> list[BreakingChange]:
        """
        Detect breaking changes across completed repos.

        Analyzes diffs from each repo and checks for contract violations
        at dependency boundaries.

        Args:
            completed_repos: Repos that have completed their pipelines
            dependency_graph: The cross-repo dependency graph
            worktree_paths: Optional override paths (worktrees instead of main repo)
        """
        breaking_changes: list[BreakingChange] = []
        paths = worktree_paths or self.repo_paths

        for repo in completed_repos:
            repo_path = paths.get(repo)
            if not repo_path or not repo_path.exists():
                continue

            changed_files = self._get_changed_files(repo_path)
            if not changed_files:
                continue

            # Get downstream repos (consumers of this repo)
            downstream = dependency_graph.get_downstream_repos(repo)
            if not downstream:
                continue

            # Check for breaking patterns in changed files
            for dep in dependency_graph.dependencies:
                if dep.target_repo != repo:
                    continue
                if (
                    dep.source_repo not in completed_repos
                    and dep.source_repo not in paths
                ):
                    continue

                # Analyze based on dependency type
                repo_breaks = self._analyze_changes_for_dependency(
                    provider_repo=repo,
                    consumer_repo=dep.source_repo,
                    dependency=dep,
                    changed_files=changed_files,
                    repo_path=repo_path,
                )
                breaking_changes.extend(repo_breaks)

        return breaking_changes

    def _analyze_changes_for_dependency(
        self,
        provider_repo: str,
        consumer_repo: str,
        dependency: Any,
        changed_files: list[str],
        repo_path: Path,
    ) -> list[BreakingChange]:
        """Analyze changes in a provider repo for potential breaks to a consumer."""
        changes: list[BreakingChange] = []

        if dependency.dependency_type == DependencyType.PACKAGE:
            changes.extend(
                self._check_package_changes(
                    provider_repo, consumer_repo, changed_files, repo_path
                )
            )
        elif dependency.dependency_type == DependencyType.API:
            changes.extend(
                self._check_api_changes(
                    provider_repo, consumer_repo, changed_files, repo_path
                )
            )
        elif dependency.dependency_type == DependencyType.SHARED_TYPES:
            changes.extend(
                self._check_type_changes(
                    provider_repo, consumer_repo, changed_files, repo_path
                )
            )

        return changes

    def _check_package_changes(
        self,
        provider: str,
        consumer: str,
        changed_files: list[str],
        repo_path: Path,
    ) -> list[BreakingChange]:
        """Check for breaking changes in package exports."""
        changes: list[BreakingChange] = []

        # Patterns indicating potential breaking changes
        export_patterns = [
            "index.ts",
            "index.js",
            "index.d.ts",  # TS/JS exports
            "__init__.py",  # Python exports
            "lib.rs",  # Rust exports
            "package.json",  # npm package config
            "setup.py",
            "pyproject.toml",  # Python package config
        ]

        for f in changed_files:
            filename = Path(f).name
            if filename in export_patterns:
                diff = self._get_file_diff(repo_path, f)
                # Check for removed exports (lines starting with -)
                removed_lines = [
                    line
                    for line in diff.split("\n")
                    if line.startswith("-")
                    and not line.startswith("---")
                    and ("export" in line.lower() or "def " in line or "class " in line)
                ]
                if removed_lines:
                    changes.append(
                        BreakingChange(
                            source_repo=provider,
                            target_repo=consumer,
                            change_type="export",
                            description=f"Potentially removed exports in {f}: {len(removed_lines)} removal(s) detected",
                            severity="warning",
                            file_path=f,
                            suggestion=f"Verify {consumer} does not import removed symbols from {provider}",
                        )
                    )

        return changes

    def _check_api_changes(
        self,
        provider: str,
        consumer: str,
        changed_files: list[str],
        repo_path: Path,
    ) -> list[BreakingChange]:
        """Check for breaking changes in API endpoints."""
        changes: list[BreakingChange] = []

        api_patterns = [
            "routes",
            "router",
            "controller",
            "endpoint",
            "api",
            "handler",
            "schema",
            "openapi",
            "swagger",
        ]

        for f in changed_files:
            f_lower = f.lower()
            if any(p in f_lower for p in api_patterns):
                diff = self._get_file_diff(repo_path, f)
                removed_endpoints = [
                    line
                    for line in diff.split("\n")
                    if line.startswith("-")
                    and not line.startswith("---")
                    and any(
                        m in line.lower()
                        for m in [
                            "get",
                            "post",
                            "put",
                            "delete",
                            "patch",
                            "@app.",
                            "@router.",
                        ]
                    )
                ]
                if removed_endpoints:
                    changes.append(
                        BreakingChange(
                            source_repo=provider,
                            target_repo=consumer,
                            change_type="api_contract",
                            description=f"API endpoint changes detected in {f}: {len(removed_endpoints)} potential removal(s)",
                            severity="error",
                            file_path=f,
                            suggestion=f"Update API consumers in {consumer} to match new endpoints in {provider}",
                        )
                    )

        return changes

    def _check_type_changes(
        self,
        provider: str,
        consumer: str,
        changed_files: list[str],
        repo_path: Path,
    ) -> list[BreakingChange]:
        """Check for breaking changes in shared type definitions."""
        changes: list[BreakingChange] = []

        type_patterns = [
            "types",
            "interfaces",
            "models",
            "dto",
            "schema",
            "proto",
            "graphql",
            ".d.ts",
        ]

        for f in changed_files:
            f_lower = f.lower()
            if any(p in f_lower for p in type_patterns):
                diff = self._get_file_diff(repo_path, f)
                removed_types = [
                    line
                    for line in diff.split("\n")
                    if line.startswith("-")
                    and not line.startswith("---")
                    and any(
                        t in line
                        for t in ["interface ", "type ", "class ", "enum ", "message "]
                    )
                ]
                if removed_types:
                    changes.append(
                        BreakingChange(
                            source_repo=provider,
                            target_repo=consumer,
                            change_type="type_definition",
                            description=f"Type definition changes in {f}: {len(removed_types)} type removal(s) or modification(s)",
                            severity="error",
                            file_path=f,
                            suggestion=f"Ensure {consumer} type imports are updated to match changes in {provider}",
                        )
                    )

        return changes

    def build_detection_summary(self, breaking_changes: list[BreakingChange]) -> str:
        """Build a human-readable summary of detected breaking changes."""
        if not breaking_changes:
            return "No breaking changes detected."

        errors = [bc for bc in breaking_changes if bc.severity == "error"]
        warnings = [bc for bc in breaking_changes if bc.severity == "warning"]

        lines = [f"## Breaking Changes Detected: {len(breaking_changes)} total"]
        if errors:
            lines.append(f"\n### Errors ({len(errors)})")
            for bc in errors:
                lines.append(
                    f"- **{bc.source_repo} → {bc.target_repo}**: {bc.description}"
                )
                if bc.suggestion:
                    lines.append(f"  - Suggestion: {bc.suggestion}")

        if warnings:
            lines.append(f"\n### Warnings ({len(warnings)})")
            for bc in warnings:
                lines.append(
                    f"- **{bc.source_repo} → {bc.target_repo}**: {bc.description}"
                )
                if bc.suggestion:
                    lines.append(f"  - Suggestion: {bc.suggestion}")

        return "\n".join(lines)
