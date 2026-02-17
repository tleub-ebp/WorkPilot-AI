"""Base connector abstract classes for future extensibility.

Defines abstract interfaces that all connector implementations must follow.
This enables a consistent API across different source control and work item
tracking providers (e.g., Azure DevOps, GitHub, GitLab).
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseConnector(ABC):
    """Abstract base class for source control connectors.

    All source control connector implementations (Azure DevOps, GitHub, etc.)
    must inherit from this class and implement all abstract methods to ensure
    a consistent interface across providers.
    """

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the source control service.

        Should validate credentials and create an authenticated client.

        Raises:
            AuthenticationError: If credentials are invalid.
            ConfigurationError: If required configuration is missing.
            ConnectionError: If the service is unreachable.
        """

    @abstractmethod
    def list_repositories(self, project: str) -> list[Any]:
        """List all repositories in a project.

        Args:
            project: The project name or identifier.

        Returns:
            A list of repository objects.

        Raises:
            ConnectionError: If not connected to the service.
        """

    @abstractmethod
    def get_repository(self, project: str, repository_id: str) -> Any:
        """Get a single repository by its identifier.

        Args:
            project: The project name or identifier.
            repository_id: The repository name or ID.

        Returns:
            A repository object.

        Raises:
            RepositoryNotFoundError: If the repository does not exist.
        """

    @abstractmethod
    def list_files(
        self,
        project: str,
        repository_id: str,
        path: str = "/",
        branch: str | None = None,
    ) -> list[Any]:
        """List files and directories at a given path in a repository.

        Args:
            project: The project name or identifier.
            repository_id: The repository name or ID.
            path: The path within the repository to list. Defaults to root.
            branch: The branch to list from. Defaults to the repository
                default branch.

        Returns:
            A list of file/directory objects.

        Raises:
            RepositoryNotFoundError: If the repository does not exist.
        """

    @abstractmethod
    def get_file_content(
        self,
        project: str,
        repository_id: str,
        file_path: str,
        branch: str | None = None,
    ) -> str:
        """Get the content of a file from a repository.

        Args:
            project: The project name or identifier.
            repository_id: The repository name or ID.
            file_path: The path to the file within the repository.
            branch: The branch to read from. Defaults to the repository
                default branch.

        Returns:
            The file content as a string.

        Raises:
            FileNotFoundError: If the file does not exist.
            RepositoryNotFoundError: If the repository does not exist.
        """


class BaseWorkItemTracker(ABC):
    """Abstract base class for work item tracking connectors.

    All work item tracking implementations (Azure Boards, GitHub Issues, etc.)
    must inherit from this class and implement all abstract methods to ensure
    a consistent interface across providers.
    """

    @abstractmethod
    def query(
        self,
        project: str,
        query: str,
        max_items: int = 100,
    ) -> list[Any]:
        """Query work items using a provider-specific query language.

        Args:
            project: The project name or identifier.
            query: The query string (e.g., WIQL for Azure DevOps).
            max_items: Maximum number of items to return.

        Returns:
            A list of work item objects matching the query.
        """

    @abstractmethod
    def get_item(self, project: str, item_id: int) -> Any:
        """Get a single work item by its identifier.

        Args:
            project: The project name or identifier.
            item_id: The work item ID.

        Returns:
            A work item object with all fields populated.

        Raises:
            WorkItemNotFoundError: If the work item does not exist.
        """

    @abstractmethod
    def list_backlog_items(
        self,
        project: str,
        item_types: list[str] | None = None,
        max_items: int = 100,
    ) -> list[Any]:
        """List work items from the project backlog.

        Args:
            project: The project name or identifier.
            item_types: Filter by work item types (e.g., Bug, User Story,
                Task). If None, returns all backlog item types.
            max_items: Maximum number of items to return.

        Returns:
            A list of work item objects from the backlog.
        """


class BaseIntegratedConnector(BaseConnector, BaseWorkItemTracker):
    """Abstract base for connectors that support both source control and
    work item tracking.

    Combines BaseConnector and BaseWorkItemTracker interfaces for services
    that provide both capabilities (e.g., Azure DevOps, GitHub).
    Implementations must implement all abstract methods from both base classes.
    """

    @abstractmethod
    def get_connection_info(self) -> dict[str, str]:
        """Get information about the current connection.

        Returns:
            A dictionary with connection details such as organization URL,
            authenticated user, and service version.
        """


class GrepaiConnector:
    """Connector pour effectuer des recherches avancées via Grepai."""
    def __init__(self, base_url="http://localhost:9000"):
        from src.connectors.grepai.client import GrepaiClient
        self.client = GrepaiClient(base_url=base_url)

    def search_code(self, query, top_k=5):
        """Recherche du code ou des fonctions via Grepai."""
        return self.client.search(query=query, top_k=top_k)

    def enrich_item(self, item: Any) -> Any:
        """Enrichit un item (repository, fichier, etc.) via Grepai."""
        result = self.search_code(f"item:{str(item)}")
        if result and 'error' not in result:
            item['grepai'] = result
        return item