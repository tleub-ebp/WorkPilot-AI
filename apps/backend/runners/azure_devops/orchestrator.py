"""
Azure DevOps PR Review Orchestrator
=====================================

Main coordinator for Azure DevOps PR review workflows.
Integrates deep codebase context from the shared DeepContextProvider.
"""

from __future__ import annotations

import traceback
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

try:
    from ..github.services.deep_context_provider import (
        DeepContextProvider,
        store_review_learnings,
    )
    from .azdo_client import AzDOClient
    from .models import (
        AzDOPRContext,
        AzureDevOpsRunnerConfig,
        MergeVerdict,
        PRReviewResult,
    )
    from .services import PRReviewEngine
except ImportError:
    from azdo_client import AzDOClient
    from models import (
        AzDOPRContext,
        AzureDevOpsRunnerConfig,
        MergeVerdict,
        PRReviewResult,
    )
    from services import PRReviewEngine

    try:
        from services.deep_context_provider import (
            DeepContextProvider,
            store_review_learnings,
        )
    except ImportError:
        DeepContextProvider = None
        store_review_learnings = None

# Import safe_print
try:
    from core.io_utils import safe_print
except ImportError:
    import sys
    from pathlib import Path as PathLib

    sys.path.insert(0, str(PathLib(__file__).parent.parent.parent))
    from core.io_utils import safe_print


@dataclass
class ProgressCallback:
    """Callback for progress updates."""

    phase: str
    progress: int
    message: str
    pr_id: int | None = None


class AzureDevOpsOrchestrator:
    """
    Orchestrates Azure DevOps PR review workflows.

    Usage:
        orchestrator = AzureDevOpsOrchestrator(
            project_dir=Path("/path/to/project"),
            config=config,
        )

        result = await orchestrator.review_pr(pr_id=123)
    """

    def __init__(
        self,
        project_dir: Path,
        config: AzureDevOpsRunnerConfig,
        progress_callback: Callable[[ProgressCallback], None] | None = None,
    ):
        self.project_dir = Path(project_dir)
        self.config = config
        self.progress_callback = progress_callback

        # Azure DevOps directory for storing state
        self.azdo_dir = self.project_dir / ".auto-claude" / "azure-devops"
        self.azdo_dir.mkdir(parents=True, exist_ok=True)

        # Initialize client
        self.client = AzDOClient(
            project_dir=self.project_dir,
            pat=config.pat,
            organization_url=config.organization_url,
            project=config.project,
            repository_id=config.repository_id,
        )

        # Initialize deep context provider (shared with GitHub/GitLab)
        self.deep_context_provider = (
            DeepContextProvider(project_dir=self.project_dir)
            if DeepContextProvider
            else None
        )

        # Initialize review engine
        self.review_engine = PRReviewEngine(
            project_dir=self.project_dir,
            azdo_dir=self.azdo_dir,
            config=self.config,
            progress_callback=self._forward_progress,
        )

    def _report_progress(
        self,
        phase: str,
        progress: int,
        message: str,
        pr_id: int | None = None,
    ) -> None:
        if self.progress_callback:
            self.progress_callback(
                ProgressCallback(
                    phase=phase, progress=progress, message=message, pr_id=pr_id
                )
            )

    def _forward_progress(self, callback) -> None:
        if self.progress_callback:
            self.progress_callback(callback)

    async def _gather_pr_context(self, pr_id: int) -> AzDOPRContext:
        """Gather context for a PR review."""
        safe_print(f"[AzDO] Fetching PR #{pr_id} data...")

        pr_data = self.client.get_pull_request(pr_id)

        # Extract info
        changed_files = pr_data.get("files", [])
        total_additions = pr_data.get("additions", 0)
        total_deletions = pr_data.get("deletions", 0)

        # Get diff
        diff = self.client.get_pr_diff(pr_id)

        # Get author
        created_by = pr_data.get("createdBy", {})
        author = (
            created_by.get("displayName", "unknown")
            if isinstance(created_by, dict)
            else "unknown"
        )

        return AzDOPRContext(
            pr_id=pr_id,
            title=pr_data.get("title", ""),
            description=pr_data.get("description", ""),
            author=author,
            source_branch=pr_data.get("sourceRefName", "").replace("refs/heads/", ""),
            target_branch=pr_data.get("targetRefName", "").replace("refs/heads/", ""),
            status=pr_data.get("status", "active"),
            changed_files=changed_files,
            diff=diff,
            total_additions=total_additions,
            total_deletions=total_deletions,
        )

    async def review_pr(self, pr_id: int) -> PRReviewResult:
        """
        Perform AI-powered review of a pull request.

        Args:
            pr_id: The PR ID to review

        Returns:
            PRReviewResult with findings and overall assessment
        """
        safe_print(f"[AzDO] Starting review for PR #{pr_id}")

        self._report_progress(
            "gathering_context",
            10,
            f"Gathering context for PR #{pr_id}...",
            pr_id=pr_id,
        )

        try:
            # Gather PR context
            context = await self._gather_pr_context(pr_id)
            safe_print(
                f"[AzDO] Context gathered: {context.title} "
                f"({len(context.changed_files)} files, {context.total_additions}+/{context.total_deletions}-)"
            )

            # Gather deep codebase context (non-blocking)
            if self.deep_context_provider:
                try:
                    changed_paths = [
                        f.get("path", "")
                        for f in context.changed_files
                        if f.get("path")
                    ]
                    deep_ctx = await self.deep_context_provider.gather_deep_context(
                        pr_title=context.title,
                        pr_description=context.description or "",
                        changed_file_paths=changed_paths,
                        timeout=20.0,
                    )
                    context.deep_context = deep_ctx.to_dict()
                    safe_print(
                        f"[AzDO] Deep context: patterns={len(deep_ctx.project_patterns)}, "
                        f"insights={len(deep_ctx.historical_insights)}, "
                        f"arch_violations={len(deep_ctx.architecture_violations)}"
                    )
                except Exception as e:
                    safe_print(
                        f"[AzDO] Deep context gathering failed (non-blocking): {e}"
                    )

            self._report_progress("analyzing", 30, "Running AI review...", pr_id=pr_id)

            # Run review
            findings, verdict, summary, blockers = await self.review_engine.run_review(
                context
            )
            safe_print(f"[AzDO] Review complete: {len(findings)} findings")

            # Map verdict to overall_status
            if verdict == MergeVerdict.BLOCKED:
                overall_status = "request_changes"
            elif verdict == MergeVerdict.NEEDS_REVISION:
                overall_status = "request_changes"
            elif verdict == MergeVerdict.MERGE_WITH_CHANGES:
                overall_status = "comment"
            else:
                overall_status = "approve"

            # Generate summary
            full_summary = self.review_engine.generate_summary(
                findings=findings,
                verdict=verdict,
                verdict_reasoning=summary,
                blockers=blockers,
            )

            # Create result
            result = PRReviewResult(
                pr_id=pr_id,
                project=self.config.project,
                repository_id=self.config.repository_id,
                success=True,
                findings=findings,
                summary=full_summary,
                overall_status=overall_status,
                verdict=verdict,
                verdict_reasoning=summary,
                blockers=blockers,
                deep_context=context.deep_context,
            )

            # Save result
            result.save(self.azdo_dir)

            # Store review learnings to Graphiti memory (non-blocking)
            if store_review_learnings and findings:
                try:
                    changed_paths = [
                        f.get("path", "")
                        for f in context.changed_files
                        if f.get("path")
                    ]
                    await store_review_learnings(
                        project_dir=self.project_dir,
                        pr_number=pr_id,
                        findings=[f.to_dict() for f in findings],
                        pr_title=context.title,
                        changed_files=changed_paths,
                    )
                except Exception as e:
                    safe_print(
                        f"[AzDO] Failed to store review learnings (non-blocking): {e}"
                    )

            self._report_progress("complete", 100, "Review complete!", pr_id=pr_id)

            return result

        except Exception as e:
            error_details = f"{type(e).__name__}: {e}"
            full_traceback = traceback.format_exc()
            safe_print(f"[AzDO] Review failed for #{pr_id}: {error_details}")
            safe_print(f"[AzDO] Traceback:\n{full_traceback}")

            result = PRReviewResult(
                pr_id=pr_id,
                project=self.config.project,
                repository_id=self.config.repository_id,
                success=False,
                error=error_details,
            )
            result.save(self.azdo_dir)
            return result
