"""Jira HTTP client with API token authentication.

Provides the core HTTP client for interacting with Jira Cloud REST API v3.
Handles email+token-based authentication, request building, response
parsing, and error mapping.

The client uses ``requests`` for HTTP communication and maps all API
errors to the appropriate exception types.

Example:
    >>> from src.connectors.jira.client import JiraClient
    >>> client = JiraClient(base_url="https://your-org.atlassian.net", email="user@example.com", token="xxx")
    >>> client.connect()
    >>> projects = client.get("/rest/api/3/project")
"""

import logging
import os
from typing import Any

import requests

from src.connectors.jira.exceptions import (
    JiraAPIError,
    JiraAuthenticationError,
    JiraConfigurationError,
    JiraError,
    JiraIssueNotFoundError,
    JiraProjectNotFoundError,
)

logger = logging.getLogger(__name__)


class JiraClient:
    """HTTP client for authenticated access to Jira Cloud REST API v3.

    Manages email+token-based authentication and provides low-level HTTP
    methods (GET, POST, PUT) for querying the Jira API. All responses are
    returned as parsed JSON dictionaries.

    Attributes:
        base_url: The Jira instance base URL.
        _email: The authentication email.
        _token: The API token.
        _session: The ``requests.Session`` used for HTTP calls.
        _connected: Whether ``connect()`` has been called.

    Example:
        >>> client = JiraClient(
        ...     base_url="https://your-org.atlassian.net",
        ...     email="user@example.com",
        ...     token="your_api_token",
        ... )
        >>> client.connect()
        >>> data = client.get("/rest/api/3/myself")
    """

    def __init__(self, base_url: str, email: str, token: str) -> None:
        """Initialize the Jira client.

        Args:
            base_url: The Jira instance URL (e.g.,
                ``'https://your-org.atlassian.net'``).
            email: The Jira account email for authentication.
            token: A Jira API token.

        Raises:
            JiraConfigurationError: If base_url, email, or token is empty.
        """
        if not base_url:
            raise JiraConfigurationError(
                "Jira base URL is required. "
                "Set the JIRA_URL environment variable."
            )
        if not email:
            raise JiraConfigurationError(
                "Jira email is required. "
                "Set the JIRA_EMAIL environment variable."
            )
        if not token:
            raise JiraConfigurationError(
                "Jira API token is required. "
                "Set the JIRA_API_TOKEN environment variable."
            )

        self.base_url = base_url.rstrip("/")
        self._email = email
        self._token = token
        self._session: requests.Session | None = None
        self._connected = False

    @classmethod
    def from_env(cls) -> "JiraClient":
        """Create a JiraClient from environment variables and connect.

        Reads ``JIRA_URL``, ``JIRA_EMAIL``, and ``JIRA_API_TOKEN`` from
        environment variables, creates the client, and connects.

        Returns:
            A connected JiraClient instance.

        Raises:
            JiraConfigurationError: If required env vars are missing.
            JiraAuthenticationError: If authentication fails.
        """
        base_url = os.getenv("JIRA_URL", "")
        email = os.getenv("JIRA_EMAIL", "")
        token = os.getenv("JIRA_API_TOKEN", "")

        missing = []
        if not base_url:
            missing.append("JIRA_URL")
        if not email:
            missing.append("JIRA_EMAIL")
        if not token:
            missing.append("JIRA_API_TOKEN")

        if missing:
            raise JiraConfigurationError(
                f"Missing required environment variables: {', '.join(missing)}. "
                "See .env.example for configuration details."
            )

        client = cls(base_url=base_url, email=email, token=token)
        client.connect()
        return client

    def connect(self) -> None:
        """Establish an authenticated session with Jira.

        Creates a ``requests.Session`` with Basic Auth (email + API token)
        and verifies connectivity by calling ``/rest/api/3/myself``.

        Raises:
            JiraAuthenticationError: If the credentials are invalid.
            JiraAPIError: If the server is unreachable.
        """
        logger.info("Connecting to Jira at %s", self.base_url)

        self._session = requests.Session()
        self._session.auth = (self._email, self._token)
        self._session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

        try:
            response = self._session.get(
                f"{self.base_url}/rest/api/3/myself",
                timeout=10,
            )
            if response.status_code == 401:
                raise JiraAuthenticationError(
                    "Authentication failed. Verify that your Jira email "
                    "and API token are valid."
                )
            if response.status_code == 403:
                raise JiraAuthenticationError(
                    "Authorization failed. Your Jira API token lacks "
                    "the required permissions."
                )
            response.raise_for_status()
        except JiraError:
            raise
        except requests.exceptions.ConnectionError as exc:
            raise JiraAPIError(
                f"Cannot connect to Jira at '{self.base_url}': {exc}"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise JiraAPIError(
                f"Failed to connect to Jira: {exc}"
            ) from exc

        self._connected = True
        logger.info("Successfully connected to Jira.")

    @property
    def is_connected(self) -> bool:
        """Check whether the client has an active session."""
        return self._connected and self._session is not None

    def _ensure_connected(self) -> None:
        """Verify that a connection has been established.

        Raises:
            JiraConfigurationError: If connect() has not been called.
        """
        if not self.is_connected:
            raise JiraConfigurationError(
                "Not connected to Jira. Call connect() first."
            )

    def _handle_error_response(
        self,
        response: requests.Response,
        endpoint: str,
    ) -> None:
        """Map HTTP error responses to appropriate exceptions.

        Args:
            response: The HTTP response object.
            endpoint: The API endpoint for context.

        Raises:
            JiraAuthenticationError: For HTTP 401/403.
            JiraProjectNotFoundError: For HTTP 404 on project endpoints.
            JiraIssueNotFoundError: For HTTP 404 on issue endpoints.
            JiraAPIError: For other HTTP errors.
        """
        if response.status_code in (401, 403):
            raise JiraAuthenticationError(
                f"Authentication failed for {endpoint}. "
                "Verify your credentials have the required permissions."
            )

        if response.status_code == 404:
            if "/project/" in endpoint:
                key = endpoint.split("/project/")[-1].split("/")[0]
                raise JiraProjectNotFoundError(key)
            if "/issue/" in endpoint:
                key = endpoint.split("/issue/")[-1].split("/")[0]
                raise JiraIssueNotFoundError(key)
            raise JiraAPIError(
                f"Resource not found: {endpoint}", status_code=404
            )

        if response.status_code >= 400:
            error_body = ""
            try:
                error_data = response.json()
                messages = error_data.get("errorMessages", [])
                errors = error_data.get("errors", {})
                parts = list(messages)
                parts.extend(f"{k}: {v}" for k, v in errors.items())
                error_body = "; ".join(parts)
            except Exception:
                error_body = response.text[:500]

            raise JiraAPIError(
                f"{endpoint}: {error_body or response.reason}",
                status_code=response.status_code,
            )

    def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        timeout: int = 30,
    ) -> dict[str, Any]:
        """Make an authenticated GET request to the Jira API.

        Args:
            endpoint: The API endpoint path (e.g., ``'/rest/api/3/project'``).
            params: Optional query parameters.
            timeout: Request timeout in seconds.

        Returns:
            The parsed JSON response as a dictionary or list.

        Raises:
            JiraAuthenticationError: If credentials are invalid.
            JiraAPIError: For HTTP errors.
            JiraConfigurationError: If not connected.
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
            raise JiraAPIError(
                f"Request to {endpoint} failed: {exc}"
            ) from exc

        self._handle_error_response(response, endpoint)

        if not response.content:
            return {}

        return response.json()

    def post(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
        timeout: int = 30,
    ) -> dict[str, Any]:
        """Make an authenticated POST request to the Jira API.

        Args:
            endpoint: The API endpoint path.
            json_data: Request body as a dictionary.
            timeout: Request timeout in seconds.

        Returns:
            The parsed JSON response as a dictionary.

        Raises:
            JiraAuthenticationError: If credentials are invalid.
            JiraAPIError: For HTTP errors.
            JiraConfigurationError: If not connected.
        """
        self._ensure_connected()

        url = f"{self.base_url}{endpoint}"
        logger.debug("POST %s", url)

        try:
            response = self._session.post(  # type: ignore[union-attr]
                url,
                json=json_data,
                timeout=timeout,
            )
        except requests.exceptions.RequestException as exc:
            raise JiraAPIError(
                f"Request to {endpoint} failed: {exc}"
            ) from exc

        self._handle_error_response(response, endpoint)

        if not response.content:
            return {}

        return response.json()

    def put(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
        timeout: int = 30,
    ) -> dict[str, Any]:
        """Make an authenticated PUT request to the Jira API.

        Args:
            endpoint: The API endpoint path.
            json_data: Request body as a dictionary.
            timeout: Request timeout in seconds.

        Returns:
            The parsed JSON response as a dictionary.

        Raises:
            JiraAuthenticationError: If credentials are invalid.
            JiraAPIError: For HTTP errors.
            JiraConfigurationError: If not connected.
        """
        self._ensure_connected()

        url = f"{self.base_url}{endpoint}"
        logger.debug("PUT %s", url)

        try:
            response = self._session.put(  # type: ignore[union-attr]
                url,
                json=json_data,
                timeout=timeout,
            )
        except requests.exceptions.RequestException as exc:
            raise JiraAPIError(
                f"Request to {endpoint} failed: {exc}"
            ) from exc

        self._handle_error_response(response, endpoint)

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
        logger.info("Disconnected from Jira.")

    def get_connection_info(self) -> dict[str, str]:
        """Get information about the current connection.

        Returns:
            A dictionary with connection details.
        """
        return {
            "base_url": self.base_url,
            "email": self._email,
            "connected": str(self.is_connected),
        }
