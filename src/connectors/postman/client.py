"""Postman HTTP client with API key authentication.

Provides the core HTTP client for interacting with the Postman API v10.
Handles API key authentication, request building, response parsing,
and error mapping.

The client uses ``requests`` for HTTP communication and maps all API
errors to the appropriate exception types.

Example:
    >>> from src.connectors.postman.client import PostmanClient
    >>> client = PostmanClient(api_key="PMAK-xxx")
    >>> client.connect()
    >>> collections = client.get("/collections")
"""

import logging
import os
from typing import Any

import requests

from src.connectors.postman.exceptions import (
    PostmanAPIError,
    PostmanAuthenticationError,
    PostmanCollectionNotFoundError,
    PostmanConfigurationError,
    PostmanEnvironmentNotFoundError,
    PostmanError,
)

logger = logging.getLogger(__name__)

POSTMAN_API_BASE_URL = "https://api.getpostman.com"


class PostmanClient:
    """HTTP client for authenticated access to the Postman API.

    Manages API key authentication and provides low-level HTTP methods
    (GET, POST, PUT, DELETE) for querying the Postman API. All responses
    are returned as parsed JSON dictionaries.

    Attributes:
        _api_key: The Postman API key.
        _base_url: The Postman API base URL.
        _session: The ``requests.Session`` used for HTTP calls.
        _connected: Whether ``connect()`` has been called.

    Example:
        >>> client = PostmanClient(api_key="PMAK-xxx")
        >>> client.connect()
        >>> data = client.get("/me")
    """

    def __init__(self, api_key: str, base_url: str | None = None) -> None:
        """Initialize the Postman client.

        Args:
            api_key: A Postman API key.
            base_url: Override for the Postman API base URL. Defaults
                to ``https://api.getpostman.com``.

        Raises:
            PostmanConfigurationError: If api_key is empty.
        """
        if not api_key:
            raise PostmanConfigurationError(
                "Postman API key is required. "
                "Set the POSTMAN_API_KEY environment variable."
            )

        self._api_key = api_key
        self._base_url = (base_url or POSTMAN_API_BASE_URL).rstrip("/")
        self._session: requests.Session | None = None
        self._connected = False

    @classmethod
    def from_env(cls) -> "PostmanClient":
        """Create a PostmanClient from environment variables and connect.

        Reads ``POSTMAN_API_KEY`` from environment variables, creates
        the client, and connects.

        Returns:
            A connected PostmanClient instance.

        Raises:
            PostmanConfigurationError: If required env vars are missing.
            PostmanAuthenticationError: If authentication fails.
        """
        api_key = os.getenv("POSTMAN_API_KEY", "")

        if not api_key:
            raise PostmanConfigurationError(
                "Missing required environment variable: POSTMAN_API_KEY. "
                "See .env.example for configuration details."
            )

        client = cls(api_key=api_key)
        client.connect()
        return client

    def connect(self) -> None:
        """Establish an authenticated session with Postman.

        Creates a ``requests.Session`` with API key header and
        verifies connectivity by calling ``/me``.

        Raises:
            PostmanAuthenticationError: If the API key is invalid.
            PostmanAPIError: If the server is unreachable.
        """
        logger.info("Connecting to Postman API.")

        self._session = requests.Session()
        self._session.headers.update({
            "X-Api-Key": self._api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

        try:
            response = self._session.get(
                f"{self._base_url}/me",
                timeout=10,
            )
            if response.status_code == 401:
                raise PostmanAuthenticationError(
                    "Authentication failed. Verify that your Postman "
                    "API key is valid and has not expired."
                )
            response.raise_for_status()
        except PostmanError:
            raise
        except requests.exceptions.ConnectionError as exc:
            raise PostmanAPIError(
                f"Cannot connect to Postman API: {exc}"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise PostmanAPIError(
                f"Failed to connect to Postman API: {exc}"
            ) from exc

        self._connected = True
        logger.info("Successfully connected to Postman API.")

    @property
    def is_connected(self) -> bool:
        """Check whether the client has an active session."""
        return self._connected and self._session is not None

    def _ensure_connected(self) -> None:
        """Verify that a connection has been established.

        Raises:
            PostmanConfigurationError: If connect() has not been called.
        """
        if not self.is_connected:
            raise PostmanConfigurationError(
                "Not connected to Postman. Call connect() first."
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
            PostmanAuthenticationError: For HTTP 401/403.
            PostmanCollectionNotFoundError: For HTTP 404 on collection endpoints.
            PostmanEnvironmentNotFoundError: For HTTP 404 on environment endpoints.
            PostmanAPIError: For other HTTP errors.
        """
        if response.status_code in (401, 403):
            raise PostmanAuthenticationError(
                f"Authentication failed for {endpoint}. "
                "Verify your API key has the required permissions."
            )

        if response.status_code == 404:
            if "/collections/" in endpoint:
                cid = endpoint.split("/collections/")[-1].split("/")[0].split("?")[0]
                raise PostmanCollectionNotFoundError(cid)
            if "/environments/" in endpoint:
                eid = endpoint.split("/environments/")[-1].split("/")[0].split("?")[0]
                raise PostmanEnvironmentNotFoundError(eid)
            raise PostmanAPIError(
                f"Resource not found: {endpoint}", status_code=404
            )

        if response.status_code >= 400:
            error_body = ""
            try:
                error_data = response.json()
                error_body = error_data.get("error", {}).get(
                    "message", str(error_data)
                )
            except Exception:
                error_body = response.text[:500]

            raise PostmanAPIError(
                f"{endpoint}: {error_body or response.reason}",
                status_code=response.status_code,
            )

    def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        timeout: int = 30,
    ) -> dict[str, Any]:
        """Make an authenticated GET request to the Postman API.

        Args:
            endpoint: The API endpoint path (e.g., ``'/collections'``).
            params: Optional query parameters.
            timeout: Request timeout in seconds.

        Returns:
            The parsed JSON response as a dictionary.

        Raises:
            PostmanAuthenticationError: If API key is invalid.
            PostmanAPIError: For HTTP errors.
            PostmanConfigurationError: If not connected.
        """
        self._ensure_connected()

        url = f"{self._base_url}{endpoint}"
        logger.debug("GET %s params=%s", url, params)

        try:
            response = self._session.get(  # type: ignore[union-attr]
                url,
                params=params,
                timeout=timeout,
            )
        except requests.exceptions.RequestException as exc:
            raise PostmanAPIError(
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
        """Make an authenticated POST request to the Postman API.

        Args:
            endpoint: The API endpoint path.
            json_data: Request body as a dictionary.
            timeout: Request timeout in seconds.

        Returns:
            The parsed JSON response as a dictionary.

        Raises:
            PostmanAuthenticationError: If API key is invalid.
            PostmanAPIError: For HTTP errors.
            PostmanConfigurationError: If not connected.
        """
        self._ensure_connected()

        url = f"{self._base_url}{endpoint}"
        logger.debug("POST %s", url)

        try:
            response = self._session.post(  # type: ignore[union-attr]
                url,
                json=json_data,
                timeout=timeout,
            )
        except requests.exceptions.RequestException as exc:
            raise PostmanAPIError(
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
        """Make an authenticated PUT request to the Postman API.

        Args:
            endpoint: The API endpoint path.
            json_data: Request body as a dictionary.
            timeout: Request timeout in seconds.

        Returns:
            The parsed JSON response as a dictionary.

        Raises:
            PostmanAuthenticationError: If API key is invalid.
            PostmanAPIError: For HTTP errors.
            PostmanConfigurationError: If not connected.
        """
        self._ensure_connected()

        url = f"{self._base_url}{endpoint}"
        logger.debug("PUT %s", url)

        try:
            response = self._session.put(  # type: ignore[union-attr]
                url,
                json=json_data,
                timeout=timeout,
            )
        except requests.exceptions.RequestException as exc:
            raise PostmanAPIError(
                f"Request to {endpoint} failed: {exc}"
            ) from exc

        self._handle_error_response(response, endpoint)

        if not response.content:
            return {}

        return response.json()

    def delete(
        self,
        endpoint: str,
        timeout: int = 30,
    ) -> dict[str, Any]:
        """Make an authenticated DELETE request to the Postman API.

        Args:
            endpoint: The API endpoint path.
            timeout: Request timeout in seconds.

        Returns:
            The parsed JSON response as a dictionary.

        Raises:
            PostmanAuthenticationError: If API key is invalid.
            PostmanAPIError: For HTTP errors.
            PostmanConfigurationError: If not connected.
        """
        self._ensure_connected()

        url = f"{self._base_url}{endpoint}"
        logger.debug("DELETE %s", url)

        try:
            response = self._session.delete(  # type: ignore[union-attr]
                url,
                timeout=timeout,
            )
        except requests.exceptions.RequestException as exc:
            raise PostmanAPIError(
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
        logger.info("Disconnected from Postman API.")

    def get_connection_info(self) -> dict[str, str]:
        """Get information about the current connection.

        Returns:
            A dictionary with connection details.
        """
        return {
            "base_url": self._base_url,
            "connected": str(self.is_connected),
        }
