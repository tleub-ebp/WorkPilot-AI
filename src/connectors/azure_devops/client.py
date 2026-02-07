"""Azure DevOps client with PAT authentication and connection management.

Provides the core client for interacting with Azure DevOps services.
Handles Personal Access Token (PAT) authentication, connection lifecycle,
and exposes Git and Work Item Tracking API clients for downstream use.

The client caches the connection object and service clients to avoid
expensive re-creation on every call.

Example:
    >>> from src.config.settings import Settings
    >>> settings = Settings.from_env()
    >>> client = AzureDevOpsClient(settings)
    >>> client.connect()
    >>> git_client = client.get_git_client()
"""

import logging
from typing import Any

from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication

from src.config.settings import Settings
from src.connectors.azure_devops.exceptions import (
    AuthenticationError,
    ConfigurationError,
)

logger = logging.getLogger(__name__)


class AzureDevOpsClient:
    """Client for authenticated access to Azure DevOps services.

    Manages PAT-based authentication and provides access to the Git
    and Work Item Tracking API clients. The connection and individual
    service clients are cached after first initialization.

    Attributes:
        settings: The configuration settings containing credentials
            and organization URL.

    Example:
        >>> settings = Settings(
        ...     pat="your-pat-token",
        ...     organization_url="https://dev.azure.com/your-org",
        ...     project="MyProject",
        ... )
        >>> client = AzureDevOpsClient(settings)
        >>> client.connect()
        >>> repos = client.get_git_client()
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize the Azure DevOps client with configuration settings.

        Does not establish a connection immediately. Call connect() to
        authenticate and create the connection.

        Args:
            settings: A Settings instance with PAT, organization URL,
                and optional default project.

        Raises:
            ConfigurationError: If settings are invalid or incomplete.
        """
        self._validate_settings(settings)
        self.settings = settings
        self._connection: Connection | None = None
        self._git_client: Any | None = None
        self._wit_client: Any | None = None

    @staticmethod
    def _validate_settings(settings: Settings) -> None:
        """Validate that settings contain all required values.

        Args:
            settings: The Settings instance to validate.

        Raises:
            ConfigurationError: If required settings are missing or invalid.
        """
        if not settings.pat:
            raise ConfigurationError(
                "Azure DevOps PAT is required. "
                "Set the AZURE_DEVOPS_PAT environment variable."
            )

        if not settings.organization_url:
            raise ConfigurationError(
                "Azure DevOps organization URL is required. "
                "Set the AZURE_DEVOPS_ORG_URL environment variable."
            )

        if not settings.organization_url.startswith("https://"):
            raise ConfigurationError(
                "Azure DevOps organization URL must use HTTPS. "
                f"Got: '{settings.organization_url}'"
            )

    @classmethod
    def from_settings(cls, settings: Settings) -> "AzureDevOpsClient":
        """Create an AzureDevOpsClient from Settings and immediately connect.

        Convenience factory method that creates the client and establishes
        the connection in a single step.

        Args:
            settings: A Settings instance with credentials and configuration.

        Returns:
            A connected AzureDevOpsClient instance.

        Raises:
            ConfigurationError: If settings are invalid or incomplete.
            AuthenticationError: If authentication fails.
        """
        client = cls(settings)
        client.connect()
        return client

    @classmethod
    def from_env(cls) -> "AzureDevOpsClient":
        """Create an AzureDevOpsClient from environment variables and connect.

        Loads settings from environment variables using Settings.from_env(),
        then creates and connects the client.

        Returns:
            A connected AzureDevOpsClient instance.

        Raises:
            ConfigurationError: If required environment variables are missing.
            AuthenticationError: If authentication fails.
        """
        try:
            settings = Settings.from_env()
        except ValueError as exc:
            raise ConfigurationError(str(exc)) from exc

        return cls.from_settings(settings)

    def connect(self) -> None:
        """Establish an authenticated connection to Azure DevOps.

        Creates a connection using PAT authentication. The connection
        is cached for subsequent calls. Calling connect() again will
        re-establish the connection.

        Raises:
            AuthenticationError: If the PAT is invalid or expired.
            ConfigurationError: If the organization URL is unreachable.
        """
        logger.info(
            "Connecting to Azure DevOps at %s",
            self.settings.organization_url,
        )

        try:
            # CRITICAL: Empty string for username with PAT authentication
            credentials = BasicAuthentication("", self.settings.pat)
            self._connection = Connection(
                base_url=self.settings.organization_url,
                creds=credentials,
            )

            # Reset cached clients to force re-creation with new connection
            self._git_client = None
            self._wit_client = None

            logger.info("Successfully connected to Azure DevOps.")
        except Exception as exc:
            error_msg = str(exc).lower()
            if "401" in error_msg or "unauthorized" in error_msg:
                raise AuthenticationError(
                    "Authentication failed. Verify that your Personal Access "
                    "Token (PAT) is valid and has not expired."
                ) from exc
            if "404" in error_msg or "not found" in error_msg:
                raise ConfigurationError(
                    f"Organization URL not found: "
                    f"'{self.settings.organization_url}'. "
                    "Verify the URL format: "
                    "https://dev.azure.com/your-organization"
                ) from exc
            raise AuthenticationError(
                f"Failed to connect to Azure DevOps: {exc}"
            ) from exc

    @property
    def is_connected(self) -> bool:
        """Check whether the client has an active connection.

        Returns:
            True if a connection has been established, False otherwise.
        """
        return self._connection is not None

    def _ensure_connected(self) -> None:
        """Verify that a connection has been established.

        Raises:
            ConfigurationError: If connect() has not been called.
        """
        if not self.is_connected:
            raise ConfigurationError(
                "Not connected to Azure DevOps. Call connect() first."
            )

    def get_git_client(self) -> Any:
        """Get the Git API client for repository operations.

        Returns the cached Git client if available, otherwise creates
        one from the current connection.

        Returns:
            An Azure DevOps GitClient instance.

        Raises:
            ConfigurationError: If not connected.
            AuthenticationError: If the connection's credentials
                are invalid when creating the client.
        """
        self._ensure_connected()

        if self._git_client is None:
            try:
                self._git_client = self._connection.clients.get_git_client()
                logger.debug("Git client initialized successfully.")
            except Exception as exc:
                raise AuthenticationError(
                    f"Failed to initialize Git client: {exc}. "
                    "Verify your PAT has the 'Code (Read)' scope."
                ) from exc

        return self._git_client

    def get_wit_client(self) -> Any:
        """Get the Work Item Tracking API client.

        Returns the cached WIT client if available, otherwise creates
        one from the current connection.

        Returns:
            An Azure DevOps WorkItemTrackingClient instance.

        Raises:
            ConfigurationError: If not connected.
            AuthenticationError: If the connection's credentials
                are invalid when creating the client.
        """
        self._ensure_connected()

        if self._wit_client is None:
            try:
                self._wit_client = (
                    self._connection.clients.get_work_item_tracking_client()
                )
                logger.debug("Work Item Tracking client initialized successfully.")
            except Exception as exc:
                raise AuthenticationError(
                    f"Failed to initialize Work Item Tracking client: {exc}. "
                    "Verify your PAT has the 'Work Items (Read)' scope."
                ) from exc

        return self._wit_client

    def get_connection_info(self) -> dict:
        """Get information about the current connection.

        Returns:
            A dictionary with connection details including the
            organization URL, default project, and connection status.
        """
        return {
            "organization_url": self.settings.organization_url,
            "project": self.settings.project or "",
            "connected": str(self.is_connected),
        }

    def disconnect(self) -> None:
        """Clear the connection and cached clients.

        Resets the client to a disconnected state. A new call to
        connect() is required before further API operations.
        """
        self._connection = None
        self._git_client = None
        self._wit_client = None
        logger.info("Disconnected from Azure DevOps.")
