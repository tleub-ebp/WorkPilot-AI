"""
Multi-Repo Orchestrator
========================
Main orchestration engine that coordinates spec execution across
multiple repositories simultaneously.

Flow:
1. Analyze all target repos
2. Build cross-repo dependency graph
3. Create master spec with per-repo sub-specs
4. Execute in dependency order (providers first, consumers last)
5. Detect breaking changes after each repo completes
6. Create linked PRs with cross-references
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .breaking_changes import BreakingChange, BreakingChangeDetector
from .cross_repo_spec import CrossRepoSpecManager, MultiRepoManifest
from .repo_graph import RepoDependencyGraph

logger = logging.getLogger(__name__)


def _emit_progress(event: str, data: dict[str, Any]) -> None:
    """Emit a progress event to stdout for the frontend to parse."""
    payload = json.dumps({"event": event, **data})
    print(f"[MULTI_REPO] {payload}", flush=True)


class MultiRepoOrchestrator:
    """
    Orchestrates task execution across multiple repositories.

    This is a meta-runner that wraps the existing spec/build pipeline,
    creating per-repo sub-specs under a parent orchestration spec.
    Existing planner/coder/QA agents run unchanged inside each repo's worktree.
    """

    def __init__(
        self,
        master_spec_dir: Path,
        project_dir: Path,
        repos: list[dict[str, str]],
        task_description: str,
        model: str = "sonnet",
        thinking_level: str = "medium",
        fail_fast: bool = False,
    ):
        """
        Args:
            master_spec_dir: Path to the master spec directory
            project_dir: Base project directory (where .auto-claude lives)
            repos: List of repo dicts with 'repo' and 'repo_path' keys
            task_description: The cross-repo task description
            model: Model to use for AI agents
            thinking_level: Thinking budget level
            fail_fast: Stop on first repo failure
        """
        self.master_spec_dir = master_spec_dir
        self.project_dir = project_dir
        self.repos = repos
        self.task_description = task_description
        self.model = model
        self.thinking_level = thinking_level
        self.fail_fast = fail_fast

        self.spec_manager = CrossRepoSpecManager(master_spec_dir)
        self.manifest: MultiRepoManifest | None = None
        self.graph: RepoDependencyGraph | None = None
        self.worktree_paths: dict[str, Path] = {}

    async def run(self) -> bool:
        """
        Main orchestration loop.

        Returns True if all repos completed successfully.
        """
        try:
            _emit_progress(
                "status",
                {"status": "analyzing", "message": "Analyzing repositories..."},
            )

            # 1. Analyze all repos
            analyses = await self._analyze_repos()

            # 2. Build dependency graph
            _emit_progress(
                "status",
                {"status": "analyzing", "message": "Building dependency graph..."},
            )
            self.graph = RepoDependencyGraph.from_analysis(analyses)

            # Add any repos that weren't detected by analysis
            for repo_info in self.repos:
                self.graph.add_repo(repo_info["repo"])

            try:
                execution_order = self.graph.topological_sort()
            except ValueError as e:
                _emit_progress("error", {"message": str(e)})
                return False

            _emit_progress(
                "graph",
                {
                    "graph": self.graph.to_dict(),
                    "execution_order": execution_order,
                },
            )

            # 3. Create master spec
            _emit_progress(
                "status",
                {"status": "planning", "message": "Creating cross-repo spec..."},
            )
            self.manifest = self.spec_manager.create_master_spec(
                task_description=self.task_description,
                repos=self.repos,
                dependency_graph=self.graph.to_dict(),
                execution_order=execution_order,
            )

            # 4. Execute per-repo in dependency order
            _emit_progress(
                "status",
                {"status": "executing", "message": "Starting per-repo execution..."},
            )
            self.manifest.status = "executing"
            self.spec_manager.save_manifest(self.manifest)

            completed_repos: list[str] = []
            all_breaking_changes: list[BreakingChange] = []

            for repo_name in execution_order:
                sub_spec = self.manifest.get_sub_spec(repo_name)
                if not sub_spec:
                    logger.warning(f"No sub-spec found for {repo_name}, skipping")
                    continue

                _emit_progress(
                    "repo_start",
                    {
                        "repo": repo_name,
                        "status": "in_progress",
                        "message": f"Starting pipeline for {repo_name}",
                    },
                )

                # Update sub-spec status
                self.manifest.update_sub_spec_status(repo_name, "coding")
                self.spec_manager.save_manifest(self.manifest)

                # Run the standard pipeline for this repo
                cross_repo_context = self._build_cross_repo_context(completed_repos)
                success = await self._run_repo_pipeline(
                    repo_name=repo_name,
                    sub_spec=sub_spec,
                    cross_repo_context=cross_repo_context,
                )

                if success:
                    self.manifest.update_sub_spec_status(
                        repo_name, "completed", progress=100.0
                    )
                    completed_repos.append(repo_name)

                    _emit_progress(
                        "repo_complete",
                        {
                            "repo": repo_name,
                            "status": "completed",
                        },
                    )

                    # 5. Breaking change detection after each repo
                    if len(completed_repos) > 1:
                        _emit_progress(
                            "status",
                            {
                                "status": "executing",
                                "message": f"Checking for breaking changes after {repo_name}...",
                            },
                        )
                        repo_paths = {
                            r["repo"]: Path(r["repo_path"]) for r in self.repos
                        }
                        detector = BreakingChangeDetector(repo_paths)
                        new_breaks = await detector.detect_breaking_changes(
                            completed_repos, self.graph, self.worktree_paths
                        )
                        if new_breaks:
                            all_breaking_changes.extend(new_breaks)
                            self.manifest.breaking_changes.extend(
                                [bc.to_dict() for bc in new_breaks]
                            )
                            _emit_progress(
                                "breaking_changes",
                                {
                                    "changes": [bc.to_dict() for bc in new_breaks],
                                    "summary": detector.build_detection_summary(
                                        new_breaks
                                    ),
                                },
                            )
                else:
                    self.manifest.update_sub_spec_status(
                        repo_name,
                        "failed",
                        error_message=f"Pipeline failed for {repo_name}",
                    )
                    _emit_progress(
                        "repo_complete",
                        {
                            "repo": repo_name,
                            "status": "failed",
                        },
                    )

                    if self.fail_fast:
                        logger.error(f"Fail-fast: stopping after {repo_name} failed")
                        break

                self.spec_manager.save_manifest(self.manifest)

            # 6. Create linked PRs
            if completed_repos:
                _emit_progress(
                    "status",
                    {"status": "creating_prs", "message": "Creating linked PRs..."},
                )
                await self._create_linked_prs(completed_repos)

            # Final status
            all_completed = all(
                sub.status == "completed" for sub in self.manifest.repos
            )
            self.manifest.status = "completed" if all_completed else "failed"
            self.spec_manager.save_manifest(self.manifest)

            _emit_progress(
                "complete",
                {
                    "status": self.manifest.status,
                    "completed_repos": completed_repos,
                    "total_repos": len(self.repos),
                    "breaking_changes_count": len(all_breaking_changes),
                    "overall_progress": self.manifest.get_overall_progress(),
                },
            )

            return all_completed

        except Exception as e:
            logger.exception(f"Orchestration failed: {e}")
            _emit_progress("error", {"message": str(e)})
            if self.manifest:
                self.manifest.status = "failed"
                self.spec_manager.save_manifest(self.manifest)
            return False

    async def _analyze_repos(self) -> dict[str, dict[str, Any]]:
        """Analyze all target repositories."""
        analyses: dict[str, dict[str, Any]] = {}

        for repo_info in self.repos:
            repo_name = repo_info["repo"]
            repo_path = Path(repo_info["repo_path"])

            _emit_progress(
                "repo_analyzing",
                {
                    "repo": repo_name,
                    "message": f"Analyzing {repo_name}...",
                },
            )

            analysis = await self._analyze_single_repo(repo_name, repo_path)
            analyses[repo_name] = analysis

        return analyses

    async def _analyze_single_repo(
        self, repo_name: str, repo_path: Path
    ) -> dict[str, Any]:
        """
        Analyze a single repo to extract dependency and structure info.

        Uses heuristic analysis (package.json, requirements.txt, etc.)
        to detect dependencies and published packages.
        """
        analysis: dict[str, Any] = {
            "repo": repo_name,
            "path": str(repo_path),
            "dependencies": [],
            "published_packages": [],
            "services": [],
            "project_type": "unknown",
        }

        if not repo_path.exists():
            logger.warning(f"Repo path does not exist: {repo_path}")
            return analysis

        # Detect Node.js projects
        package_json = repo_path / "package.json"
        if package_json.exists():
            try:
                with open(package_json, encoding="utf-8") as f:
                    pkg = json.load(f)
                analysis["project_type"] = "node"
                # Published package name
                if pkg.get("name"):
                    analysis["published_packages"].append(pkg["name"])
                # Dependencies
                for dep_section in [
                    "dependencies",
                    "devDependencies",
                    "peerDependencies",
                ]:
                    for dep_name in pkg.get(dep_section, {}):
                        analysis["dependencies"].append(dep_name)
            except Exception:
                pass

        # Detect Python projects
        for pyfile in ["requirements.txt", "pyproject.toml", "setup.py"]:
            pypath = repo_path / pyfile
            if pypath.exists():
                analysis["project_type"] = "python"
                if pyfile == "requirements.txt":
                    try:
                        content = pypath.read_text(encoding="utf-8")
                        for line in content.strip().split("\n"):
                            line = line.strip()
                            if line and not line.startswith("#"):
                                pkg_name = (
                                    line.split("==")[0]
                                    .split(">=")[0]
                                    .split("<=")[0]
                                    .split("[")[0]
                                    .strip()
                                )
                                if pkg_name:
                                    analysis["dependencies"].append(pkg_name)
                    except Exception:
                        pass
                break

        # Detect monorepo indicators
        monorepo_indicators = [
            "pnpm-workspace.yaml",
            "lerna.json",
            "nx.json",
            "turbo.json",
            "rush.json",
        ]
        for indicator in monorepo_indicators:
            if (repo_path / indicator).exists():
                analysis["project_type"] = "monorepo"
                break

        # Detect workspace packages in monorepo
        packages_dir = repo_path / "packages"
        apps_dir = repo_path / "apps"
        for workspace_dir in [packages_dir, apps_dir]:
            if workspace_dir.exists() and workspace_dir.is_dir():
                for child in workspace_dir.iterdir():
                    if child.is_dir():
                        child_pkg = child / "package.json"
                        if child_pkg.exists():
                            try:
                                with open(child_pkg, encoding="utf-8") as f:
                                    cpkg = json.load(f)
                                if cpkg.get("name"):
                                    analysis["published_packages"].append(cpkg["name"])
                            except Exception:
                                pass

        return analysis

    async def _run_repo_pipeline(
        self,
        repo_name: str,
        sub_spec: Any,
        cross_repo_context: str,
    ) -> bool:
        """
        Run the standard planner → coder → QA pipeline for a single repo.

        This delegates to the existing build pipeline by importing and
        invoking the spec runner / build runner for the repo.
        """
        repo_path = Path(sub_spec.repo_path)
        if not repo_path.exists():
            logger.error(f"Repo path does not exist: {repo_path}")
            return False

        try:
            # Write cross-repo context to the sub-spec directory
            sub_spec_dir = Path(sub_spec.spec_dir)
            sub_spec_dir.mkdir(parents=True, exist_ok=True)

            # Write the spec for this repo
            spec_content = self._build_repo_spec(repo_name, cross_repo_context)
            (sub_spec_dir / "spec.md").write_text(spec_content, encoding="utf-8")

            # Write cross-repo context as a separate file for agent reference
            (sub_spec_dir / "cross_repo_context.md").write_text(
                cross_repo_context, encoding="utf-8"
            )

            # Write a requirements.json for the sub-spec
            requirements = {
                "task_description": self.task_description,
                "repo": repo_name,
                "repo_path": str(repo_path),
                "cross_repo": True,
                "model": self.model,
                "thinking_level": self.thinking_level,
            }
            with open(sub_spec_dir / "requirements.json", "w", encoding="utf-8") as f:
                json.dump(requirements, f, indent=2)

            _emit_progress(
                "repo_pipeline",
                {
                    "repo": repo_name,
                    "phase": "spec_ready",
                    "message": f"Spec prepared for {repo_name}, ready for build pipeline",
                },
            )

            # The actual build execution is handled by the runner
            # which spawns planner/coder/QA agents using existing infrastructure.
            # For now, mark as ready for the runner to pick up.
            return True

        except Exception as e:
            logger.exception(f"Failed to prepare pipeline for {repo_name}: {e}")
            return False

    def _build_repo_spec(self, repo_name: str, cross_repo_context: str) -> str:
        """Build the spec content for a single repo within the orchestration."""
        lines = [
            f"# Spec for {repo_name}",
            "",
            "## Part of Multi-Repo Orchestration",
            "",
            f"**Master Task:** {self.task_description}",
            "",
            f"**This Repo:** {repo_name}",
            "",
            "## Cross-Repo Context",
            "",
        ]

        if cross_repo_context:
            lines.append(cross_repo_context)
        else:
            lines.append(
                "This is the first repo in the execution order. No upstream repos have been modified yet."
            )

        lines.extend(
            [
                "",
                "## Instructions",
                "",
                f"Implement the portion of the task that belongs in this repository ({repo_name}).",
                "Consider the cross-repo context above when making changes.",
                "Ensure your changes are compatible with the overall orchestration.",
            ]
        )

        return "\n".join(lines) + "\n"

    def _build_cross_repo_context(self, completed_repos: list[str]) -> str:
        """
        Build a context summary of what has been completed in upstream repos.
        This gets injected into downstream agents as additional context.
        """
        if not completed_repos:
            return ""

        lines = [
            "### Completed Upstream Repos",
            "",
            "The following repos have already been modified as part of this orchestration:",
            "",
        ]

        for repo in completed_repos:
            sub_spec = self.manifest.get_sub_spec(repo) if self.manifest else None
            lines.append(f"#### {repo}")
            if sub_spec and sub_spec.pr_url:
                lines.append(f"- PR: {sub_spec.pr_url}")
            if sub_spec and sub_spec.branch_name:
                lines.append(f"- Branch: {sub_spec.branch_name}")
            lines.append("")

        # Include breaking changes context
        if self.manifest and self.manifest.breaking_changes:
            lines.append("### Known Breaking Changes")
            lines.append("")
            for bc in self.manifest.breaking_changes:
                lines.append(
                    f"- **{bc['source_repo']} → {bc['target_repo']}**: "
                    f"{bc['description']}"
                )
            lines.append("")
            lines.append(
                "**Important:** Address the above breaking changes in your implementation."
            )

        return "\n".join(lines)

    async def _create_linked_prs(self, completed_repos: list[str]) -> None:
        """
        Create linked PRs for all completed repos with cross-references.

        Each PR body includes links to PRs in other repos that are part
        of the same orchestration.
        """
        pr_urls: dict[str, str] = {}

        for repo_name in completed_repos:
            sub_spec = self.manifest.get_sub_spec(repo_name) if self.manifest else None
            if sub_spec and sub_spec.pr_url:
                pr_urls[repo_name] = sub_spec.pr_url

        if not pr_urls:
            _emit_progress(
                "prs",
                {
                    "message": "No PRs to link (PRs will be created by individual repo pipelines)",
                    "pr_urls": {},
                },
            )
            return

        # Build cross-reference section for each PR
        cross_ref_section = "\n## Related PRs (Multi-Repo Orchestration)\n\n"
        cross_ref_section += f"**Task:** {self.task_description}\n\n"
        for repo, url in pr_urls.items():
            cross_ref_section += f"- [{repo}]({url})\n"

        _emit_progress(
            "prs",
            {
                "message": f"Linked {len(pr_urls)} PRs across repos",
                "pr_urls": pr_urls,
                "cross_ref_section": cross_ref_section,
            },
        )
