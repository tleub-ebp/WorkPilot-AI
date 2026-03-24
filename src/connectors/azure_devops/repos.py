"""Repository operations for the Azure DevOps connector.

Provides methods for listing repositories, retrieving repository details,
browsing file structures, and fetching file content from Azure DevOps
Git repositories via the Azure DevOps SDK.

Example:
    >>> from src.connectors.azure_devops.client import AzureDevOpsClient
    >>> from src.connectors.azure_devops.repos import AzureReposClient
    >>> client = AzureDevOpsClient.from_env()
    >>> repos = AzureReposClient(client)
    >>> repositories = repos.list_repositories("MyProject")
"""

import logging
from typing import Any

from azure.devops.v7_0.git.models import GitVersionDescriptor

from src.connectors.azure_devops.client import AzureDevOpsClient
from src.connectors.azure_devops.exceptions import (
    APIError,
    AzureDevOpsError,
    RepositoryNotFoundError,
)
from src.connectors.azure_devops.models import (
    FileItem,
    PullRequest,
    PullRequestFileChange,
    Repository,
)

logger = logging.getLogger(__name__)


class AzureReposClient:
    """Client for Azure DevOps Git repository operations.

    Wraps the Azure DevOps Git API client to provide high-level methods
    for listing repositories, browsing file structures, and retrieving
    file content. All API responses are mapped to clean data models.

    Attributes:
        _client: The underlying AzureDevOpsClient providing authenticated
            access to the Git API.

    Example:
        >>> client = AzureDevOpsClient.from_env()
        >>> repos_client = AzureReposClient(client)
        >>> for repo in repos_client.list_repositories("MyProject"):
        ...     print(repo.name)
    """

    def __init__(self, client: AzureDevOpsClient) -> None:
        """Initialize the repository operations client.

        Args:
            client: An authenticated AzureDevOpsClient instance.
                Must have an active connection (connect() must have
                been called).
        """
        self._client = client

    def _get_git_client(self) -> Any:
        """Get the Git API client from the underlying connection.

        Returns:
            An Azure DevOps GitClient instance for making API calls.

        Raises:
            ConfigurationError: If the client is not connected.
            AuthenticationError: If credentials are invalid.
        """
        return self._client.get_git_client()

    def list_repositories(self, project: str) -> list[Repository]:
        """List all Git repositories in an Azure DevOps project.

        Args:
            project: The project name or identifier.

        Returns:
            A list of Repository objects representing all repositories
            in the specified project. Returns an empty list if the
            project has no repositories.

        Raises:
            APIError: If the API call fails unexpectedly.
        """
        logger.info("Listing repositories for project '%s'.", project)

        try:
            git_client = self._get_git_client()
            api_repos = git_client.get_repositories(project=project)
        except AzureDevOpsError:
            raise
        except Exception as exc:
            raise APIError(
                f"Failed to list repositories for project '{project}': {exc}"
            ) from exc

        if not api_repos:
            logger.info("No repositories found in project '%s'.", project)
            return []

        repositories = [Repository.from_api_response(repo) for repo in api_repos]

        logger.info(
            "Found %d repositories in project '%s'.",
            len(repositories),
            project,
        )
        return repositories

    def get_repository(self, project: str, repository_id: str) -> Repository:
        """Get a single repository by its name or ID.

        Args:
            project: The project name or identifier.
            repository_id: The repository name or unique ID.

        Returns:
            A Repository object for the requested repository.

        Raises:
            RepositoryNotFoundError: If the repository does not exist
                in the specified project.
            APIError: If the API call fails unexpectedly.
        """
        logger.info(
            "Getting repository '%s' in project '%s'.",
            repository_id,
            project,
        )

        try:
            git_client = self._get_git_client()
            api_repo = git_client.get_repository(
                repository_id=repository_id,
                project=project,
            )
        except AzureDevOpsError:
            raise
        except Exception as exc:
            error_msg = str(exc).lower()
            if "404" in error_msg or "not found" in error_msg:
                raise RepositoryNotFoundError(
                    repository_id=repository_id, project=project
                ) from exc
            raise APIError(
                f"Failed to get repository '{repository_id}' "
                f"in project '{project}': {exc}"
            ) from exc

        return Repository.from_api_response(api_repo)

    def list_files(
        self,
        project: str,
        repository_id: str,
        path: str = "/",
        branch: str | None = None,
    ) -> list[FileItem]:
        """List files and directories at a given path in a repository.

        Retrieves the tree structure at the specified path, with one level
        of recursion to list immediate children.

        Args:
            project: The project name or identifier.
            repository_id: The repository name or unique ID.
            path: The path within the repository to list. Defaults to
                the root ("/").
            branch: The branch to list from. If None, uses the
                repository's default branch.

        Returns:
            A list of FileItem objects representing files and directories
            at the specified path. Returns an empty list for empty
            repositories or paths with no items.

        Raises:
            RepositoryNotFoundError: If the repository does not exist.
            APIError: If the API call fails unexpectedly.
        """
        logger.info(
            "Listing files in '%s/%s' (path='%s', branch=%s).",
            project,
            repository_id,
            path,
            branch or "default",
        )

        version_descriptor = None
        if branch:
            version_descriptor = GitVersionDescriptor(
                version=branch,
                version_type="branch",
            )

        try:
            git_client = self._get_git_client()
            api_items = git_client.get_items(
                repository_id=repository_id,
                project=project,
                scope_path=path,
                recursion_level="oneLevel",
                version_descriptor=version_descriptor,
            )
        except AzureDevOpsError:
            raise
        except Exception as exc:
            error_msg = str(exc).lower()
            if "404" in error_msg or "not found" in error_msg:
                raise RepositoryNotFoundError(
                    repository_id=repository_id, project=project
                ) from exc
            raise APIError(
                f"Failed to list files in repository '{repository_id}': {exc}"
            ) from exc

        if not api_items:
            logger.info(
                "No items found at path '%s' in repository '%s'.",
                path,
                repository_id,
            )
            return []

        # Filter out the scope path itself (first item is the directory)
        file_items = []
        for item in api_items:
            item_path = getattr(item, "path", "")
            # Skip the root/scope path entry itself
            if item_path == path:
                continue
            file_items.append(FileItem.from_api_response(item))

        logger.info(
            "Found %d items at path '%s' in repository '%s'.",
            len(file_items),
            path,
            repository_id,
        )
        return file_items

    def get_file_content(
        self,
        project: str,
        repository_id: str,
        file_path: str,
        branch: str | None = None,
    ) -> str:
        """Get the content of a file from a repository.

        Retrieves the raw content of a file at the specified path and
        branch. Uses include_content=True to fetch the actual file data
        rather than just metadata.

        Args:
            project: The project name or identifier.
            repository_id: The repository name or unique ID.
            file_path: The full path to the file within the repository
                (e.g., '/src/main.py').
            branch: The branch to read from. If None, uses the
                repository's default branch.

        Returns:
            The file content as a string.

        Raises:
            FileNotFoundError: If the file does not exist at the
                specified path.
            RepositoryNotFoundError: If the repository does not exist.
            APIError: If the API call fails unexpectedly.
        """
        logger.info(
            "Getting file content for '%s' in '%s/%s' (branch=%s).",
            file_path,
            project,
            repository_id,
            branch or "default",
        )

        version_descriptor = None
        if branch:
            version_descriptor = GitVersionDescriptor(
                version=branch,
                version_type="branch",
            )

        try:
            git_client = self._get_git_client()
            # CRITICAL: include_content=True is required to get actual
            # file content; the default returns metadata only.
            item = git_client.get_item(
                repository_id=repository_id,
                path=file_path,
                project=project,
                version_descriptor=version_descriptor,
                include_content=True,
            )
        except AzureDevOpsError:
            raise
        except Exception as exc:
            error_msg = str(exc).lower()
            if "404" in error_msg or "not found" in error_msg:
                # Distinguish between repo not found and file not found
                if "repository" in error_msg:
                    raise RepositoryNotFoundError(
                        repository_id=repository_id, project=project
                    ) from exc
                raise FileNotFoundError(
                    f"File '{file_path}' not found in repository "
                    f"'{repository_id}' (project '{project}', "
                    f"branch='{branch or 'default'}')."
                ) from exc
            raise APIError(
                f"Failed to get file content for '{file_path}' "
                f"in repository '{repository_id}': {exc}"
            ) from exc

        content = getattr(item, "content", None)
        if content is None:
            raise FileNotFoundError(
                f"File '{file_path}' exists but returned no content "
                f"in repository '{repository_id}' (project '{project}')."
            )

        # Ensure content is typed as str for mypy
        content_str: str = str(content)

        logger.info(
            "Retrieved file content for '%s' (%d characters).",
            file_path,
            len(content_str),
        )
        return content_str

    # ── Pull Request operations (Feature 4.2 — enriched Boards) ─────

    def create_pull_request(
        self,
        project: str,
        repository_id: str,
        source_branch: str,
        target_branch: str,
        title: str,
        description: str | None = None,
        reviewers: list[str] | None = None,
        work_item_ids: list[int] | None = None,
        is_draft: bool = False,
    ) -> "PullRequest":
        """Create a pull request in an Azure DevOps Git repository.

        Creates a new PR from a source branch to a target branch,
        optionally linking work items and adding reviewers.

        Args:
            project: The project name or identifier.
            repository_id: The repository name or unique ID.
            source_branch: The source branch ref (e.g., ``'refs/heads/feature'``).
                If no ``refs/heads/`` prefix is given, it is added automatically.
            target_branch: The target branch ref (e.g., ``'refs/heads/main'``).
                If no ``refs/heads/`` prefix is given, it is added automatically.
            title: The PR title.
            description: Optional PR description in Markdown.
            reviewers: Optional list of reviewer unique names or IDs.
            work_item_ids: Optional list of work item IDs to link.
            is_draft: If True, creates the PR as a draft.

        Returns:
            A PullRequest dataclass with the created PR details.

        Raises:
            RepositoryNotFoundError: If the repository does not exist.
            APIError: If the API call fails.
        """
        logger.info(
            "Creating PR '%s' (%s → %s) in '%s/%s'.",
            title,
            source_branch,
            target_branch,
            project,
            repository_id,
        )

        from azure.devops.v7_0.git.models import (
            GitPullRequest,
            IdentityRefWithVote,
            ResourceRef,
        )

        # Normalise branch refs
        if not source_branch.startswith("refs/"):
            source_branch = f"refs/heads/{source_branch}"
        if not target_branch.startswith("refs/"):
            target_branch = f"refs/heads/{target_branch}"

        pr_reviewers = None
        if reviewers:
            pr_reviewers = [
                IdentityRefWithVote(unique_name=name) for name in reviewers
            ]

        pr_work_items = None
        if work_item_ids:
            pr_work_items = [
                ResourceRef(id=str(wid)) for wid in work_item_ids
            ]

        pr_to_create = GitPullRequest(
            source_ref_name=source_branch,
            target_ref_name=target_branch,
            title=title,
            description=description or "",
            reviewers=pr_reviewers,
            work_item_refs=pr_work_items,
            is_draft=is_draft,
        )

        try:
            git_client = self._get_git_client()
            api_pr = git_client.create_pull_request(
                git_pull_request_to_create=pr_to_create,
                repository_id=repository_id,
                project=project,
            )
        except AzureDevOpsError:
            raise
        except Exception as exc:
            error_msg = str(exc).lower()
            if "404" in error_msg or "not found" in error_msg:
                raise RepositoryNotFoundError(
                    repository_id=repository_id, project=project
                ) from exc
            raise APIError(
                f"Failed to create pull request in repository "
                f"'{repository_id}': {exc}"
            ) from exc

        pull_request = PullRequest.from_api_response(api_pr)
        logger.info(
            "Created PR #%d: '%s' in repository '%s'.",
            pull_request.pull_request_id,
            pull_request.title,
            repository_id,
        )
        return pull_request

    def get_pull_request(
        self,
        project: str,
        repository_id: str,
        pull_request_id: int,
    ) -> PullRequest:
        """Get a pull request by its ID.

        Args:
            project: The project name or identifier.
            repository_id: The repository name or unique ID.
            pull_request_id: The pull request ID.

        Returns:
            A PullRequest object for the requested PR.

        Raises:
            RepositoryNotFoundError: If the repository does not exist.
            APIError: If the API call fails unexpectedly.
        """
        logger.info(
            "Getting PR #%d in '%s/%s'.",
            pull_request_id,
            project,
            repository_id,
        )

        try:
            git_client = self._get_git_client()
            api_pr = git_client.get_pull_request(
                repository_id=repository_id,
                project=project,
                pull_request_id=pull_request_id,
                include_commits=True,
                include_work_item_refs=True,
            )
        except AzureDevOpsError:
            raise
        except Exception as exc:
            error_msg = str(exc).lower()
            if "404" in error_msg or "not found" in error_msg:
                raise RepositoryNotFoundError(
                    repository_id=repository_id, project=project
                ) from exc
            raise APIError(
                f"Failed to get pull request #{pull_request_id} "
                f"in repository '{repository_id}': {exc}"
            ) from exc

        pull_request = PullRequest.from_api_response(api_pr)
        logger.info(
            "Retrieved PR #%d: '%s' from repository '%s'.",
            pull_request.pull_request_id,
            pull_request.title,
            repository_id,
        )
        return pull_request

    def get_pull_request_files(
        self,
        project: str,
        repository_id: str,
        pull_request_id: int,
    ) -> list["PullRequestFileChange"]:
        """Get the file changes for a pull request.

        Args:
            project: The project name or identifier.
            repository_id: The repository name or unique ID.
            pull_request_id: The pull request ID.

        Returns:
            A list of PullRequestFileChange objects representing all
            files changed in the PR.

        Raises:
            RepositoryNotFoundError: If the repository does not exist.
            APIError: If the API call fails unexpectedly.
        """
        logger.info(
            "Getting file changes for PR #%d in '%s/%s'.",
            pull_request_id,
            project,
            repository_id,
        )

        try:
            git_client = self._get_git_client()
            api_changes = git_client.get_pull_request_commits(
                repository_id=repository_id,
                project=project,
                pull_request_id=pull_request_id,
            )
            
            # Get the iteration changes to see file differences
            api_iterations = git_client.get_pull_request_iterations(
                repository_id=repository_id,
                project=project,
                pull_request_id=pull_request_id,
            )
            
            # Get the latest iteration's changes
            latest_iteration = api_iterations[-1] if api_iterations else None
            if not latest_iteration:
                return []
                
            api_changes = git_client.get_pull_request_iteration_changes(
                repository_id=repository_id,
                project=project,
                pull_request_id=pull_request_id,
                iteration_id=latest_iteration.id,
            )
            
        except AzureDevOpsError:
            raise
        except Exception as exc:
            error_msg = str(exc).lower()
            if "404" in error_msg or "not found" in error_msg:
                raise RepositoryNotFoundError(
                    repository_id=repository_id, project=project
                ) from exc
            raise APIError(
                f"Failed to get pull request files for PR #{pull_request_id} "
                f"in repository '{repository_id}': {exc}"
            ) from exc

        file_changes = [
            PullRequestFileChange.from_api_response(change)
            for change in api_changes.change_entries
        ]

        logger.info(
            "Retrieved %d file changes for PR #%d in repository '%s'.",
            len(file_changes),
            pull_request_id,
            repository_id,
        )
        return file_changes

    def get_pull_request_details(
        self,
        project: str,
        repository_id: str,
        pull_request_id: int,
    ) -> dict:
        """Get comprehensive pull request details including files.

        Args:
            project: The project name or identifier.
            repository_id: The repository name or unique ID.
            pull_request_id: The pull request ID.

        Returns:
            A dictionary containing PR details and file changes.

        Raises:
            RepositoryNotFoundError: If the repository does not exist.
            APIError: If the API call fails unexpectedly.
        """
        logger.info(
            "Getting comprehensive details for PR #%d in '%s/%s'.",
            pull_request_id,
            project,
            repository_id,
        )

        # Get PR details
        pr = self.get_pull_request(project, repository_id, pull_request_id)
        
        # Get file changes
        files = self.get_pull_request_files(project, repository_id, pull_request_id)
        
        # Calculate statistics
        additions = sum(file.additions for file in files)
        deletions = sum(file.deletions for file in files)
        changes = sum(file.changes for file in files)
        
        return {
            "id": pr.pull_request_id,
            "title": pr.title,
            "description": pr.description,
            "status": pr.status,
            "sourceRefName": pr.source_branch,
            "targetRefName": pr.target_branch,
            "createdBy": {
                "displayName": pr.created_by
            } if pr.created_by else None,
            "creationDate": pr.creation_date.isoformat() if pr.creation_date else None,
            "isDraft": pr.is_draft,
            "mergeStatus": pr.merge_status,
            "url": pr.url,
            "repositoryId": pr.repository_id,
            "additions": additions,
            "deletions": deletions,
            "changed_files": len(files),
            "files": [
                {
                    "path": file.path,
                    "changeType": file.change_type,
                    "additions": file.additions,
                    "deletions": file.deletions,
                    "changes": file.changes,
                    "oldPath": file.old_path
                }
                for file in files
            ]
        }
