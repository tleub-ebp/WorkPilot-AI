"""Unit tests for AzureDevOpsClient authentication, connection, and config.

Tests the core client lifecycle including:
- Configuration validation (missing PAT, missing URL, non-HTTPS URL)
- PAT-based authentication and connection establishment
- Connection error mapping (401 → AuthenticationError, 404 → ConfigurationError)
- Factory methods (from_settings, from_env)
- Git and WIT client accessor caching and error handling
- Connection state management (connect, disconnect, is_connected)
- Connection info retrieval
"""

from unittest.mock import MagicMock, patch

import pytest

from src.config.settings import Settings
from src.connectors.azure_devops.client import AzureDevOpsClient
from src.connectors.azure_devops.exceptions import (
    AuthenticationError,
    ConfigurationError,
)

# ── Configuration validation tests ─────────────────────────────────


class TestClientValidation:
    """Tests for _validate_settings and constructor validation."""

    def test_missing_pat_raises_configuration_error(self):
        """Constructor rejects settings with an empty PAT."""
        settings = Settings(
            pat="",
            organization_url="https://dev.azure.com/org",
            project="Project",
        )
        with pytest.raises(ConfigurationError, match="PAT is required"):
            AzureDevOpsClient(settings)

    def test_missing_organization_url_raises_configuration_error(self):
        """Constructor rejects settings with an empty organization URL."""
        settings = Settings(
            pat="valid-pat-token",
            organization_url="",
            project="Project",
        )
        with pytest.raises(ConfigurationError, match="organization URL is required"):
            AzureDevOpsClient(settings)

    def test_non_https_url_raises_configuration_error(self):
        """Constructor rejects an organization URL that is not HTTPS."""
        settings = Settings(
            pat="valid-pat-token",
            organization_url="http://dev.azure.com/org",
            project="Project",
        )
        with pytest.raises(ConfigurationError, match="must use HTTPS"):
            AzureDevOpsClient(settings)

    def test_valid_settings_accepted(self, sample_settings):
        """Constructor accepts valid settings without raising."""
        client = AzureDevOpsClient(sample_settings)
        assert client.settings is sample_settings

    def test_valid_settings_without_project(self, settings_no_project):
        """Constructor accepts settings without a default project."""
        client = AzureDevOpsClient(settings_no_project)
        assert client.settings.project is None

    def test_client_starts_disconnected(self, sample_settings):
        """Newly created client has no active connection."""
        client = AzureDevOpsClient(sample_settings)
        assert client.is_connected is False
        assert client._connection is None
        assert client._git_client is None
        assert client._wit_client is None


# ── Connection tests ───────────────────────────────────────────────


class TestClientConnection:
    """Tests for connect(), disconnect(), and is_connected."""

    @patch("src.connectors.azure_devops.client.Connection")
    @patch("src.connectors.azure_devops.client.BasicAuthentication")
    def test_connect_creates_connection(
        self, mock_basic_auth, mock_connection_cls, sample_settings
    ):
        """connect() creates a Connection with PAT credentials."""
        mock_creds = MagicMock()
        mock_basic_auth.return_value = mock_creds
        mock_conn_instance = MagicMock()
        mock_connection_cls.return_value = mock_conn_instance

        client = AzureDevOpsClient(sample_settings)
        client.connect()

        mock_basic_auth.assert_called_once_with("", sample_settings.pat)
        mock_connection_cls.assert_called_once_with(
            base_url=sample_settings.organization_url,
            creds=mock_creds,
        )
        assert client.is_connected is True

    @patch("src.connectors.azure_devops.client.Connection")
    @patch("src.connectors.azure_devops.client.BasicAuthentication")
    def test_connect_resets_cached_clients(
        self, mock_basic_auth, mock_connection_cls, sample_settings
    ):
        """Reconnecting clears previously cached Git and WIT clients."""
        mock_connection_cls.return_value = MagicMock()

        client = AzureDevOpsClient(sample_settings)
        client._git_client = MagicMock()
        client._wit_client = MagicMock()

        client.connect()

        assert client._git_client is None
        assert client._wit_client is None

    def test_connect_401_raises_authentication_error(self, sample_settings):
        """connect() maps 401/unauthorized errors to AuthenticationError."""
        with (
            patch(
                "src.connectors.azure_devops.client.Connection",
                side_effect=Exception("HTTP 401 Unauthorized"),
            ),
            patch("src.connectors.azure_devops.client.BasicAuthentication"),
        ):
            client = AzureDevOpsClient(sample_settings)
            with pytest.raises(AuthenticationError, match="Authentication failed"):
                client.connect()

    def test_connect_unauthorized_raises_authentication_error(self, sample_settings):
        """connect() maps 'unauthorized' keyword to AuthenticationError."""
        with (
            patch(
                "src.connectors.azure_devops.client.Connection",
                side_effect=Exception("Request unauthorized by server"),
            ),
            patch("src.connectors.azure_devops.client.BasicAuthentication"),
        ):
            client = AzureDevOpsClient(sample_settings)
            with pytest.raises(AuthenticationError, match="Authentication failed"):
                client.connect()

    def test_connect_404_raises_configuration_error(self, sample_settings):
        """connect() maps 404/not found errors to ConfigurationError."""
        with (
            patch(
                "src.connectors.azure_devops.client.Connection",
                side_effect=Exception("HTTP 404 Not Found"),
            ),
            patch("src.connectors.azure_devops.client.BasicAuthentication"),
        ):
            client = AzureDevOpsClient(sample_settings)
            with pytest.raises(ConfigurationError, match="Organization URL not found"):
                client.connect()

    def test_connect_not_found_raises_configuration_error(self, sample_settings):
        """connect() maps 'not found' keyword to ConfigurationError."""
        with (
            patch(
                "src.connectors.azure_devops.client.Connection",
                side_effect=Exception("Resource not found on server"),
            ),
            patch("src.connectors.azure_devops.client.BasicAuthentication"),
        ):
            client = AzureDevOpsClient(sample_settings)
            with pytest.raises(ConfigurationError, match="Organization URL not found"):
                client.connect()

    def test_connect_generic_error_raises_authentication_error(self, sample_settings):
        """connect() wraps unknown errors as AuthenticationError."""
        with (
            patch(
                "src.connectors.azure_devops.client.Connection",
                side_effect=Exception("Network timeout"),
            ),
            patch("src.connectors.azure_devops.client.BasicAuthentication"),
        ):
            client = AzureDevOpsClient(sample_settings)
            with pytest.raises(AuthenticationError, match="Failed to connect"):
                client.connect()

    def test_disconnect_clears_state(self, azure_client):
        """disconnect() resets the connection and cached clients."""
        assert azure_client.is_connected is True

        azure_client.disconnect()

        assert azure_client.is_connected is False
        assert azure_client._connection is None
        assert azure_client._git_client is None
        assert azure_client._wit_client is None

    def test_is_connected_reflects_connection_state(self, sample_settings):
        """is_connected returns True only when a connection exists."""
        client = AzureDevOpsClient(sample_settings)
        assert client.is_connected is False

        client._connection = MagicMock()
        assert client.is_connected is True

        client._connection = None
        assert client.is_connected is False


# ── _ensure_connected tests ────────────────────────────────────────


class TestEnsureConnected:
    """Tests for the _ensure_connected guard method."""

    def test_raises_when_not_connected(self, sample_settings):
        """_ensure_connected raises ConfigurationError if not connected."""
        client = AzureDevOpsClient(sample_settings)
        with pytest.raises(ConfigurationError, match="Not connected.*Call connect"):
            client._ensure_connected()

    def test_passes_when_connected(self, azure_client):
        """_ensure_connected does not raise when a connection exists."""
        azure_client._ensure_connected()


# ── Git client accessor tests ──────────────────────────────────────


class TestGetGitClient:
    """Tests for get_git_client() accessor and caching."""

    def test_returns_git_client(self, azure_client, mock_git_client):
        """get_git_client() returns the Git API client from the connection."""
        result = azure_client.get_git_client()
        assert result is mock_git_client

    def test_caches_git_client(self, azure_client):
        """get_git_client() caches and returns the same client instance."""
        first = azure_client.get_git_client()
        second = azure_client.get_git_client()
        assert first is second

        # The underlying factory should only be called once
        azure_client._connection.clients.get_git_client.assert_called_once()

    def test_raises_when_not_connected(self, sample_settings):
        """get_git_client() raises ConfigurationError if not connected."""
        client = AzureDevOpsClient(sample_settings)
        with pytest.raises(ConfigurationError, match="Not connected"):
            client.get_git_client()

    def test_client_creation_failure_raises_auth_error(self, azure_client):
        """get_git_client() wraps client creation errors as AuthenticationError."""
        azure_client._connection.clients.get_git_client.side_effect = Exception(
            "Token expired"
        )
        with pytest.raises(
            AuthenticationError, match="Failed to initialize Git client"
        ):
            azure_client.get_git_client()


# ── WIT client accessor tests ─────────────────────────────────────


class TestGetWitClient:
    """Tests for get_wit_client() accessor and caching."""

    def test_returns_wit_client(self, azure_client, mock_wit_client):
        """get_wit_client() returns the WIT API client from the connection."""
        result = azure_client.get_wit_client()
        assert result is mock_wit_client

    def test_caches_wit_client(self, azure_client):
        """get_wit_client() caches and returns the same client instance."""
        first = azure_client.get_wit_client()
        second = azure_client.get_wit_client()
        assert first is second

        azure_client._connection.clients.get_work_item_tracking_client.assert_called_once()

    def test_raises_when_not_connected(self, sample_settings):
        """get_wit_client() raises ConfigurationError if not connected."""
        client = AzureDevOpsClient(sample_settings)
        with pytest.raises(ConfigurationError, match="Not connected"):
            client.get_wit_client()

    def test_client_creation_failure_raises_auth_error(self, azure_client):
        """get_wit_client() wraps client creation errors as AuthenticationError."""
        azure_client._connection.clients.get_work_item_tracking_client.side_effect = (
            Exception("Insufficient permissions")
        )
        with pytest.raises(
            AuthenticationError,
            match="Failed to initialize Work Item Tracking client",
        ):
            azure_client.get_wit_client()


# ── Factory method tests ───────────────────────────────────────────


class TestFactoryMethods:
    """Tests for from_settings() and from_env() class methods."""

    @patch("src.connectors.azure_devops.client.Connection")
    @patch("src.connectors.azure_devops.client.BasicAuthentication")
    def test_from_settings_creates_and_connects(
        self, mock_basic_auth, mock_connection_cls, sample_settings
    ):
        """from_settings() creates a client and calls connect()."""
        mock_connection_cls.return_value = MagicMock()

        client = AzureDevOpsClient.from_settings(sample_settings)

        assert client.is_connected is True
        assert client.settings is sample_settings

    @patch("src.connectors.azure_devops.client.Connection")
    @patch("src.connectors.azure_devops.client.BasicAuthentication")
    @patch("src.config.settings.Settings.from_env")
    def test_from_env_loads_settings_and_connects(
        self,
        mock_from_env,
        mock_basic_auth,
        mock_connection_cls,
        sample_settings,
    ):
        """from_env() loads settings from environment and connects."""
        mock_from_env.return_value = sample_settings
        mock_connection_cls.return_value = MagicMock()

        client = AzureDevOpsClient.from_env()

        mock_from_env.assert_called_once()
        assert client.is_connected is True

    @patch("src.config.settings.Settings.from_env")
    def test_from_env_wraps_value_error_as_config_error(self, mock_from_env):
        """from_env() wraps ValueError from Settings into ConfigurationError."""
        mock_from_env.side_effect = ValueError(
            "Missing required environment variables: AZURE_DEVOPS_PAT"
        )

        with pytest.raises(
            ConfigurationError, match="Missing required environment variables"
        ):
            AzureDevOpsClient.from_env()


# ── Connection info tests ─────────────────────────────────────────


class TestGetConnectionInfo:
    """Tests for get_connection_info() method."""

    def test_returns_connection_details(self, azure_client):
        """get_connection_info() returns organization URL, project, status."""
        info = azure_client.get_connection_info()

        assert info["organization_url"] == azure_client.settings.organization_url
        assert info["project"] == azure_client.settings.project
        assert info["connected"] == "True"

    def test_returns_empty_project_when_none(self, settings_no_project):
        """get_connection_info() returns empty string for missing project."""
        client = AzureDevOpsClient(settings_no_project)
        info = client.get_connection_info()

        assert info["project"] == ""
        assert info["connected"] == "False"

    def test_connected_status_reflects_state(self, sample_settings):
        """get_connection_info() shows correct connected status."""
        client = AzureDevOpsClient(sample_settings)
        assert client.get_connection_info()["connected"] == "False"

        client._connection = MagicMock()
        assert client.get_connection_info()["connected"] == "True"
