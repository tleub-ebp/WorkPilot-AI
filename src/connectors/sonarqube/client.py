"""SonarQube HTTP client with token authentication.

Provides the core HTTP client for interacting with SonarQube / SonarCloud
Web API. Handles token-based authentication, request building, response
parsing, and error mapping.

The client uses ``requests`` for HTTP communication and maps all API
errors to the appropriate exception types.

Example:
    >>> from src.connectors.sonarqube.client import SonarQubeClient
    >>> client = SonarQubeClient(base_url="http://localhost:9000", token="squ_xxx")
    >>> client.connect()
    >>> projects = client.get("/api/projects/search")
"""

import logging
import os
from typing import Any

import requests

from src.connectors.sonarqube.exceptions import (
    SonarQubeAPIError,
    SonarQubeAuthenticationError,
    SonarQubeConfigurationError,
    SonarQubeError,
    SonarQubeProjectNotFoundError,
)

logger = logging.getLogger(__name__)


class SonarQubeClient:
    """HTTP client for authenticated access to SonarQube Web API.

    Manages token-based authentication and provides low-level HTTP
    methods (GET) for querying the SonarQube API. All responses are
    returned as parsed JSON dictionaries.

    Attributes:
        base_url: The SonarQube server base URL.
        _token: The authentication token.
        _session: The ``requests.Session`` used for HTTP calls.
        _connected: Whether ``connect()`` has been called.

    Example:
        >>> client = SonarQubeClient(
        ...     base_url="http://localhost:9000",
        ...     token="squ_your_token",
        ... )
        >>> client.connect()
        >>> data = client.get("/api/system/status")
    """

    def __init__(self, base_url: str, token: str) -> None:
        """Initialize the SonarQube client.

        Args:
            base_url: The SonarQube server URL (e.g.,
                ``'http://localhost:9000'`` or
                ``'https://sonarcloud.io'``).
            token: A SonarQube user token or global analysis token.

        Raises:
            SonarQubeConfigurationError: If base_url or token is empty.
        """
        if not base_url:
            raise SonarQubeConfigurationError(
                "SonarQube base URL is required. "
                "Set the SONARQUBE_URL environment variable."
            )
        if not token:
            raise SonarQubeConfigurationError(
                "SonarQube token is required. "
                "Set the SONARQUBE_TOKEN environment variable."
            )

        self.base_url = base_url.rstrip("/")
        self._token = token
        self._session: requests.Session | None = None
        self._connected = False

    @classmethod
    def from_env(cls) -> "SonarQubeClient":
        """Create a SonarQubeClient from environment variables and connect.

        Reads ``SONARQUBE_URL`` and ``SONARQUBE_TOKEN`` from environment
        variables, creates the client, and connects.

        Returns:
            A connected SonarQubeClient instance.

        Raises:
            SonarQubeConfigurationError: If required env vars are missing.
            SonarQubeAuthenticationError: If authentication fails.
        """
        base_url = os.getenv("SONARQUBE_URL", "")
        token = os.getenv("SONARQUBE_TOKEN", "")

        missing = []
        if not base_url:
            missing.append("SONARQUBE_URL")
        if not token:
            missing.append("SONARQUBE_TOKEN")

        if missing:
            raise SonarQubeConfigurationError(
                f"Missing required environment variables: {', '.join(missing)}. "
                "See .env.example for configuration details."
            )

        client = cls(base_url=base_url, token=token)
        client.connect()
        return client

    def connect(self) -> None:
        """Establish an authenticated session with SonarQube.

        Creates a ``requests.Session`` with token authentication and
        verifies connectivity by calling ``/api/system/status``.

        Raises:
            SonarQubeAuthenticationError: If the token is invalid.
            SonarQubeAPIError: If the server is unreachable.
        """
        logger.info("Connecting to SonarQube at %s", self.base_url)

        self._session = requests.Session()
        self._session.auth = (self._token, "")
        self._session.headers.update({
            "Accept": "application/json",
        })

        try:
            response = self._session.get(
                f"{self.base_url}/api/system/status",
                timeout=10,
            )
            if response.status_code == 401:
                raise SonarQubeAuthenticationError(
                    "Authentication failed. Verify that your SonarQube "
                    "token is valid and has not expired."
                )
            response.raise_for_status()
        except SonarQubeError:
            raise
        except requests.exceptions.ConnectionError as exc:
            raise SonarQubeAPIError(
                f"Cannot connect to SonarQube at '{self.base_url}': {exc}"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise SonarQubeAPIError(
                f"Failed to connect to SonarQube: {exc}"
            ) from exc

        self._connected = True
        logger.info("Successfully connected to SonarQube.")

    @property
    def is_connected(self) -> bool:
        """Check whether the client has an active session."""
        return self._connected and self._session is not None

    def _ensure_connected(self) -> None:
        """Verify that a connection has been established.

        Raises:
            SonarQubeConfigurationError: If connect() has not been called.
        """
        if not self.is_connected:
            raise SonarQubeConfigurationError(
                "Not connected to SonarQube. Call connect() first."
            )

    def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        timeout: int = 30,
    ) -> dict[str, Any]:
        """Make an authenticated GET request to the SonarQube API.

        Args:
            endpoint: The API endpoint path (e.g., ``'/api/projects/search'``).
            params: Optional query parameters.
            timeout: Request timeout in seconds.

        Returns:
            The parsed JSON response as a dictionary.

        Raises:
            SonarQubeAuthenticationError: If the token is invalid (HTTP 401/403).
            SonarQubeProjectNotFoundError: If a project is not found (HTTP 404).
            SonarQubeAPIError: For other HTTP errors.
            SonarQubeConfigurationError: If not connected.
        """
        self._ensure_connected()

        url = f"{self.base_url}{endpoint}"
        logger.debug("GET %s params=%s", url, params)

        try:
            response = self._session.get(  # type: ignore[union-attr]
                url,
                params=params,
                timeout=timeout,
            )
        except requests.exceptions.RequestException as exc:
            raise SonarQubeAPIError(
                f"Request to {endpoint} failed: {exc}"
            ) from exc

        if response.status_code == 401 or response.status_code == 403:
            raise SonarQubeAuthenticationError(
                f"Authentication failed for {endpoint}. "
                "Verify your token has the required permissions."
            )

        if response.status_code == 404:
            # Extract project key from params if available
            project_key = (params or {}).get(
                "component", (params or {}).get("projectKey", "")
            )
            if project_key:
                raise SonarQubeProjectNotFoundError(project_key)
            raise SonarQubeAPIError(
                f"Resource not found: {endpoint}", status_code=404
            )

        if response.status_code >= 400:
            error_body = ""
            try:
                error_data = response.json()
                errors = error_data.get("errors", [])
                if errors:
                    error_body = "; ".join(e.get("msg", "") for e in errors)
            except Exception:
                error_body = response.text[:500]

            raise SonarQubeAPIError(
                f"{endpoint}: {error_body or response.reason}",
                status_code=response.status_code,
            )

        if not response.content:
            return {}

        return response.json()

    def disconnect(self) -> None:
        """Close the HTTP session.

        Resets the client to a disconnected state.
        """
        if self._session:
            self._session.close()
        self._session = None
        self._connected = False
        logger.info("Disconnected from SonarQube.")

    def get_connection_info(self) -> dict[str, str]:
        """Get information about the current connection.

        Returns:
            A dictionary with connection details.
        """
        return {
            "base_url": self.base_url,
            "connected": str(self.is_connected),
        }
