"""Azure DevOps connector - Integration with Azure Repos and Azure Boards.

Provides a unified interface for interacting with Azure DevOps services,
including repository browsing, file content retrieval, and work item
tracking via a single ``AzureDevOpsConnector`` class.

Example:
    >>> from src.connectors.azure_devops import AzureDevOpsConnector
    >>> connector = AzureDevOpsConnector.from_env()
    >>> repos = connector.list_repositories("MyProject")
    >>> items = connector.list_backlog_items("MyProject")
"""

import logging
from typing import Dict, List, Optional

from src.config.settings import Settings
from src.connectors.azure_devops.client import AzureDevOpsClient
from src.connectors.azure_devops.exceptions import (
    APIError,
    AuthenticationError,
    AzureDevOpsError,
    ConfigurationError,
    RateLimitError,
    RepositoryNotFoundError,
    ResourceNotFoundError,
    WorkItemNotFoundError,
)
from src.connectors.azure_devops.models import FileItem, Repository, WorkItem
from src.connectors.azure_devops.repos import AzureReposClient
from src.connectors.azure_devops.work_items import AzureWorkItemsClient
from src.connectors.base import BaseIntegratedConnector

logger = logging.getLogger(__name__)


class AzureDevOpsConnector(BaseIntegratedConnector):
    """Unified connector for Azure DevOps source control and work items.

    Combines repository operations (Azure Repos) and work item tracking
    (Azure Boards) into a single interface that implements
    ``BaseIntegratedConnector``. Internally delegates to specialized
    ``AzureReposClient`` and ``AzureWorkItemsClient`` instances.

    Attributes:
        _client: The underlying Azure DevOps API client.
        _repos: Client for Git repository operations.
        _work_items: Client for work item tracking operations.

    Example:
        >>> from src.config.settings import Settings
        >>> settings = Settings(
        ...     pat="your-pat",
        ...     organization_url="https://dev.azure.com/your-org",
        ...     project="MyProject",
        ... )
        >>> connector = AzureDevOpsConnector(settings)
        >>> connector.connect()
        >>> for repo in connector.list_repositories("MyProject"):
        ...     print(repo.name)
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize the Azure DevOps connector.

        Creates the underlying client and specialized operation clients.
        Does not establish a connection immediately — call ``connect()``
        to authenticate.

        Args:
            settings: A Settings instance with PAT, organization URL,
                and optional default project.

        Raises:
            ConfigurationError: If settings are invalid or incomplete.
        """
        self._client = AzureDevOpsClient(settings)
        self._repos = AzureReposClient(self._client)
        self._work_items = AzureWorkItemsClient(self._client)

    @classmethod
    def from_settings(cls, settings: Settings) -> "AzureDevOpsConnector":
        """Create a connector from Settings and connect immediately.

        Convenience factory method that creates the connector and
        establishes the connection in a single step.

        Args:
            settings: A Settings instance with credentials and
                configuration.

        Returns:
            A connected AzureDevOpsConnector instance.

        Raises:
            ConfigurationError: If settings are invalid or incomplete.
            AuthenticationError: If authentication fails.
        """
        connector = cls(settings)
        connector.connect()
        return connector

    @classmethod
    def from_env(cls) -> "AzureDevOpsConnector":
        """Create a connector from environment variables and connect.

        Loads settings from environment variables using
        ``Settings.from_env()``, then creates and connects the
        connector.

        Returns:
            A connected AzureDevOpsConnector instance.

        Raises:
            ConfigurationError: If required environment variables
                are missing.
            AuthenticationError: If authentication fails.
        """
        try:
            settings = Settings.from_env()
        except ValueError as exc:
            raise ConfigurationError(str(exc)) from exc

        return cls.from_settings(settings)

    # ── BaseConnector interface ──────────────────────────────────────

    def connect(self) -> None:
        """Establish an authenticated connection to Azure DevOps.

        Delegates to the underlying ``AzureDevOpsClient.connect()``
        method. Must be called before any other operations.

        Raises:
            AuthenticationError: If the PAT is invalid or expired.
            ConfigurationError: If the organization URL is unreachable.
        """
        self._client.connect()

    def list_repositories(self, project: str) -> List[Repository]:
        """List all Git repositories in an Azure DevOps project.

        Args:
            project: The project name or identifier.

        Returns:
            A list of Repository objects. Returns an empty list if the
            project has no repositories.

        Raises:
            ConfigurationError: If not connected.
            APIError: If the API call fails.
        """
        return self._repos.list_repositories(project)

    def get_repository(
        self, project: str, repository_id: str
    ) -> Repository:
        """Get a single repository by its name or ID.

        Args:
            project: The project name or identifier.
            repository_id: The repository name or unique ID.

        Returns:
            A Repository object for the requested repository.

        Raises:
            RepositoryNotFoundError: If the repository does not exist.
            APIError: If the API call fails.
        """
        return self._repos.get_repository(project, repository_id)

    def list_files(
        self,
        project: str,
        repository_id: str,
        path: str = "/",
        branch: Optional[str] = None,
    ) -> List[FileItem]:
        """List files and directories at a given path in a repository.

        Args:
            project: The project name or identifier.
            repository_id: The repository name or unique ID.
            path: The path within the repository to list. Defaults to
                the root ("/").
            branch: The branch to list from. If None, uses the
                repository's default branch.

        Returns:
            A list of FileItem objects representing files and
            directories at the specified path.

        Raises:
            RepositoryNotFoundError: If the repository does not exist.
            APIError: If the API call fails.
        """
        return self._repos.list_files(project, repository_id, path, branch)

    def get_file_content(
        self,
        project: str,
        repository_id: str,
        file_path: str,
        branch: Optional[str] = None,
    ) -> str:
        """Get the content of a file from a repository.

        Args:
            project: The project name or identifier.
            repository_id: The repository name or unique ID.
            file_path: The full path to the file within the repository.
            branch: The branch to read from. If None, uses the
                repository's default branch.

        Returns:
            The file content as a string.

        Raises:
            FileNotFoundError: If the file does not exist.
            RepositoryNotFoundError: If the repository does not exist.
            APIError: If the API call fails.
        """
        return self._repos.get_file_content(
            project, repository_id, file_path, branch
        )

    # ── BaseWorkItemTracker interface ────────────────────────────────

    def query(
        self,
        project: str,
        query: str,
        max_items: int = 100,
    ) -> List[WorkItem]:
        """Query work items using WIQL (Work Item Query Language).

        Args:
            project: The project name or identifier.
            query: A WIQL query string.
            max_items: Maximum number of work items to return.

        Returns:
            A list of WorkItem objects matching the query.

        Raises:
            APIError: If the query is malformed or the API call fails.
        """
        return self._work_items.query_work_items(project, query, max_items)

    def get_item(self, project: str, item_id: int) -> WorkItem:
        """Get a single work item by its ID.

        Args:
            project: The project name or identifier.
            item_id: The unique integer ID of the work item.

        Returns:
            A WorkItem object with all fields populated.

        Raises:
            WorkItemNotFoundError: If the work item does not exist.
            APIError: If the API call fails.
        """
        return self._work_items.get_work_item(project, item_id)

    def list_backlog_items(
        self,
        project: str,
        item_types: Optional[List[str]] = None,
        max_items: int = 100,
    ) -> List[WorkItem]:
        """List work items from the project backlog.

        Retrieves backlog items filtered by work item type. By default
        queries for Bugs, User Stories, and Tasks that are not in a
        closed or done state.

        Args:
            project: The project name or identifier.
            item_types: Filter by work item types. If None, uses
                default backlog types (Bug, User Story, Task).
            max_items: Maximum number of items to return.

        Returns:
            A list of WorkItem objects from the backlog, ordered by
            priority.

        Raises:
            APIError: If the API call fails.
        """
        return self._work_items.list_backlog_items(
            project, item_types, max_items
        )

    # ── BaseIntegratedConnector interface ────────────────────────────

    def get_connection_info(self) -> Dict[str, str]:
        """Get information about the current connection.

        Returns:
            A dictionary with connection details including the
            organization URL, default project, and connection status.
        """
        return self._client.get_connection_info()

    # ── Additional convenience methods ───────────────────────────────

    @property
    def is_connected(self) -> bool:
        """Check whether the connector has an active connection.

        Returns:
            True if a connection has been established, False otherwise.
        """
        return self._client.is_connected

    def disconnect(self) -> None:
        """Clear the connection and cached clients.

        Resets the connector to a disconnected state. A new call to
        ``connect()`` is required before further API operations.
        """
        self._client.disconnect()


__all__ = [
    # Main connector
    "AzureDevOpsConnector",
    # Underlying clients
    "AzureDevOpsClient",
    "AzureReposClient",
    "AzureWorkItemsClient",
    # Data models
    "Repository",
    "WorkItem",
    "FileItem",
    # Exceptions
    "AzureDevOpsError",
    "AuthenticationError",
    "ConfigurationError",
    "ResourceNotFoundError",
    "RepositoryNotFoundError",
    "WorkItemNotFoundError",
    "APIError",
    "RateLimitError",
]
