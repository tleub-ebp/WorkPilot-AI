"""
Azure DevOps Client Wrapper
============================

Lightweight wrapper around the existing Azure DevOps connector
for PR review operations.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Import safe_print
try:
    from core.io_utils import safe_print
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from core.io_utils import safe_print


class AzDOClient:
    """
    Client for Azure DevOps PR review operations.

    Wraps the existing AzureDevOps connector from src/connectors/azure_devops/.
    """

    def __init__(
        self,
        project_dir: Path,
        pat: str,
        organization_url: str,
        project: str,
        repository_id: str = "",
    ):
        self.project_dir = Path(project_dir).resolve()
        self.pat = pat
        self.organization_url = organization_url
        self.project = project
        self.repository_id = repository_id
        self._repos_client = None

    def _get_repos_client(self):
        """Lazily initialize the repos client."""
        if self._repos_client is None:
            # Add connector paths
            project_root = self.project_dir
            src_path = project_root / "src"
            if src_path.exists():
                sys.path.insert(0, str(project_root))

            from src.config.settings import Settings
            from src.connectors.azure_devops.client import AzureDevOpsClient
            from src.connectors.azure_devops.repos import AzureReposClient

            settings = Settings(
                pat=self.pat,
                organization_url=self.organization_url,
                project=self.project,
            )
            client = AzureDevOpsClient.from_settings(settings)
            self._repos_client = AzureReposClient(client)

        return self._repos_client

    def get_pull_request(self, pr_id: int) -> dict:
        """Get PR details."""
        repos = self._get_repos_client()
        return repos.get_pull_request_details(
            project=self.project,
            repository_id=self.repository_id,
            pull_request_id=pr_id,
        )

    def get_pr_diff(
        self,
        pr_id: int,
        max_files: int = 50,
        max_file_bytes: int = 200_000,
    ) -> str:
        """
        Get the unified diff for a PR.

        Azure DevOps doesn't provide a single unified-diff endpoint like
        GitHub does. We reconstruct one with `difflib`:

        1. Fetch PR metadata (source + target branches).
        2. Fetch the list of changed files.
        3. For each file, fetch the source-branch and target-branch
           contents and run `difflib.unified_diff`.

        On any failure (network, 404, decode error) we fall back to the
        old pseudo-diff for that file so the LLM at least sees the
        change footprint. We never crash the whole call.

        Args:
            pr_id: pull request id.
            max_files: cap to keep diffs reasonable for downstream LLMs.
                Files past this cap get a pseudo-diff entry only.
            max_file_bytes: per-file cap on each side. Files larger than
                this fall back to pseudo-diff (binary-ish content).
        """
        import difflib

        repos = self._get_repos_client()
        files = repos.get_pull_request_files(
            project=self.project,
            repository_id=self.repository_id,
            pull_request_id=pr_id,
        )

        # Source / target branch refs from the PR metadata.
        try:
            pr_details = repos.get_pull_request_details(
                project=self.project,
                repository_id=self.repository_id,
                pull_request_id=pr_id,
            )
            source_branch = self._strip_ref(
                self._read_attr(pr_details, "source_ref_name")
            )
            target_branch = self._strip_ref(
                self._read_attr(pr_details, "target_ref_name")
            )
        except Exception as e:
            safe_print(
                f"[AzDO] Could not load PR refs, falling back to pseudo-diff: {e}"
            )
            return self._pseudo_diff(files)

        if not source_branch or not target_branch:
            safe_print("[AzDO] PR refs missing, falling back to pseudo-diff")
            return self._pseudo_diff(files)

        diff_parts: list[str] = []
        for idx, file in enumerate(files):
            path = file.path or "unknown"
            change_type = (file.change_type or "edit").lower()

            if idx >= max_files:
                # Past the cap → pseudo-diff entry only.
                diff_parts.append(self._pseudo_diff_for(file))
                continue

            try:
                target_content = self._safe_get_content(
                    repos,
                    project=self.project,
                    repository_id=self.repository_id,
                    path=path,
                    branch=target_branch,
                    change_type=change_type,
                    side="target",
                )
                source_content = self._safe_get_content(
                    repos,
                    project=self.project,
                    repository_id=self.repository_id,
                    path=path,
                    branch=source_branch,
                    change_type=change_type,
                    side="source",
                )

                if (
                    target_content is None
                    or source_content is None
                    or len(target_content) > max_file_bytes
                    or len(source_content) > max_file_bytes
                ):
                    diff_parts.append(self._pseudo_diff_for(file))
                    continue

                udiff = difflib.unified_diff(
                    target_content.splitlines(keepends=True),
                    source_content.splitlines(keepends=True),
                    fromfile=f"a/{path}",
                    tofile=f"b/{path}",
                    n=3,
                )
                diff_parts.append("".join(udiff))
            except Exception as e:
                safe_print(f"[AzDO] diff failed for {path}: {e}")
                diff_parts.append(self._pseudo_diff_for(file))

        return "\n".join(p for p in diff_parts if p)

    @staticmethod
    def _strip_ref(ref_name: str | None) -> str | None:
        """`refs/heads/feature-x` → `feature-x`."""
        if not ref_name:
            return None
        for prefix in ("refs/heads/", "refs/tags/"):
            if ref_name.startswith(prefix):
                return ref_name[len(prefix) :]
        return ref_name

    @staticmethod
    def _read_attr(obj, attr: str):
        """Read `attr` from obj whether it's a dataclass-like object or a dict."""
        if obj is None:
            return None
        if hasattr(obj, attr):
            return getattr(obj, attr)
        if isinstance(obj, dict):
            return obj.get(attr)
        return None

    @staticmethod
    def _safe_get_content(
        repos,
        *,
        project: str,
        repository_id: str,
        path: str,
        branch: str,
        change_type: str,
        side: str,
    ) -> str | None:
        """Fetch file content, returning None on miss / failure.

        For an `add` change the file doesn't exist on the target branch
        and we return an empty string so the diff still works. Same for
        a `delete` on the source branch.
        """
        if change_type == "add" and side == "target":
            return ""
        if change_type == "delete" and side == "source":
            return ""
        try:
            return repos.get_file_content(
                project=project,
                repository_id=repository_id,
                file_path=path if path.startswith("/") else f"/{path}",
                branch=branch,
            )
        except Exception:
            return None

    @staticmethod
    def _pseudo_diff_for(file) -> str:
        """Old per-file pseudo-diff for the fallback path."""
        path = file.path or "unknown"
        change_type = file.change_type or "edit"
        parts = [
            f"--- a/{path}",
            f"+++ b/{path}",
            f"# Change type: {change_type}",
        ]
        if getattr(file, "additions", None):
            parts.append(f"# +{file.additions} additions")
        if getattr(file, "deletions", None):
            parts.append(f"# -{file.deletions} deletions")
        return "\n".join(parts) + "\n"

    def _pseudo_diff(self, files) -> str:
        return "\n".join(self._pseudo_diff_for(f) for f in files)

    def post_pr_comment(self, pr_id: int, content: str) -> bool:
        """Post a comment thread on a PR."""
        try:
            repos = self._get_repos_client()
            git_client = repos._get_git_client()

            from azure.devops.v7_0.git.models import (
                Comment,
                GitPullRequestCommentThread,
            )

            thread = GitPullRequestCommentThread(
                comments=[Comment(content=content)],
                status="active",
            )

            git_client.create_thread(
                comment_thread=thread,
                repository_id=self.repository_id,
                pull_request_id=pr_id,
                project=self.project,
            )
            return True
        except Exception as e:
            safe_print(f"[AzDO] Failed to post comment: {e}")
            return False
