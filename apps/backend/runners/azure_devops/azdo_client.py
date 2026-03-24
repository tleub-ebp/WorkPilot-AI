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

    def get_pr_diff(self, pr_id: int) -> str:
        """
        Get the diff for a PR.

        Azure DevOps doesn't provide a unified diff endpoint like GitHub.
        We reconstruct a pseudo-diff from iteration changes.
        """
        repos = self._get_repos_client()
        files = repos.get_pull_request_files(
            project=self.project,
            repository_id=self.repository_id,
            pull_request_id=pr_id,
        )

        # Build pseudo-diff from file changes
        diff_parts = []
        for file in files:
            change_type = file.change_type or "edit"
            path = file.path or "unknown"
            diff_parts.append(f"--- a/{path}")
            diff_parts.append(f"+++ b/{path}")
            diff_parts.append(f"# Change type: {change_type}")
            if file.additions:
                diff_parts.append(f"# +{file.additions} additions")
            if file.deletions:
                diff_parts.append(f"# -{file.deletions} deletions")
            diff_parts.append("")

        return "\n".join(diff_parts)

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
