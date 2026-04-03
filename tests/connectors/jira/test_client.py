"""Unit tests for JiraClient HTTP operations (Feature 4.1).

Tests the Jira HTTP client including:
- Initialization and configuration validation
- Connection and authentication
- GET, POST, PUT requests
- Error handling and exception mapping
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
import requests


# Helper function to import modules directly
def import_module_direct(module_name, file_path):
    """Import a module directly from file path, bypassing package __init__.py"""
    import importlib.util
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Import modules directly to avoid circular import issues in __init__.py
# First import exceptions, then client (which depends on exceptions)
project_root = Path(__file__).parent.parent.parent.parent

# Import exceptions first
exceptions_module = import_module_direct("jira_exceptions", project_root / "src" / "connectors" / "jira" / "exceptions.py")

# Make exceptions available in sys.modules so client can import them
sys.modules["src.connectors.jira.exceptions"] = exceptions_module
sys.modules["src.connectors.jira"] = type('Module', (), {'exceptions': exceptions_module})()

# Now import client
client_module = import_module_direct("jira_client", project_root / "src" / "connectors" / "jira" / "client.py")

JiraClient = client_module.JiraClient
JiraAPIError = exceptions_module.JiraAPIError
JiraAuthenticationError = exceptions_module.JiraAuthenticationError
JiraConfigurationError = exceptions_module.JiraConfigurationError
JiraIssueNotFoundError = exceptions_module.JiraIssueNotFoundError
JiraProjectNotFoundError = exceptions_module.JiraProjectNotFoundError


# ── Initialization tests ────────────────────────────────────────────


class TestJiraClientInit:
    """Tests for JiraClient initialization."""

    def test_init_valid_params(self):
        """JiraClient initializes with valid parameters."""
        client = JiraClient(
            base_url="https://test.atlassian.net",
            email="user@test.com",
            token="token123",
        )
        assert client.base_url == "https://test.atlassian.net"
        assert client.is_connected is False

    def test_init_strips_trailing_slash(self):
        """JiraClient strips trailing slash from base_url."""
        client = JiraClient(
            base_url="https://test.atlassian.net/",
            email="user@test.com",
            token="token123",
        )
        assert client.base_url == "https://test.atlassian.net"

    def test_init_missing_base_url_raises(self):
        """JiraClient raises JiraConfigurationError for empty base_url."""
        with pytest.raises(JiraConfigurationError, match="base URL"):
            JiraClient(base_url="", email="user@test.com", token="token123")

    def test_init_missing_email_raises(self):
        """JiraClient raises JiraConfigurationError for empty email."""
        with pytest.raises(JiraConfigurationError, match="email"):
            JiraClient(base_url="https://test.atlassian.net", email="", token="token123")

    def test_init_missing_token_raises(self):
        """JiraClient raises JiraConfigurationError for empty token."""
        with pytest.raises(JiraConfigurationError, match="token"):
            JiraClient(base_url="https://test.atlassian.net", email="user@test.com", token="")


# ── from_env tests ──────────────────────────────────────────────────


class TestJiraClientFromEnv:
    """Tests for JiraClient.from_env()."""

    @patch.dict("os.environ", {}, clear=True)
    def test_from_env_missing_vars_raises(self):
        """from_env() raises when environment variables are missing."""
        with pytest.raises(JiraConfigurationError, match="Missing required"):
            JiraClient.from_env()

    @patch.dict("os.environ", {"JIRA_URL": "https://test.atlassian.net"}, clear=True)
    def test_from_env_partial_vars_raises(self):
        """from_env() raises when some variables are missing."""
        with pytest.raises(JiraConfigurationError, match="JIRA_EMAIL"):
            JiraClient.from_env()


# ── Connect tests ───────────────────────────────────────────────────


class TestJiraClientConnect:
    """Tests for JiraClient.connect()."""

    def test_connect_success(self):
        """connect() sets connected state on success."""
        client = JiraClient(
            base_url="https://test.atlassian.net",
            email="user@test.com",
            token="token123",
        )
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("requests.Session") as MockSession:
            mock_session = MagicMock()
            mock_session.get.return_value = mock_response
            MockSession.return_value = mock_session

            client.connect()

        assert client.is_connected is True

    def test_connect_auth_failure_raises(self):
        """connect() raises JiraAuthenticationError on 401."""
        client = JiraClient(
            base_url="https://test.atlassian.net",
            email="user@test.com",
            token="bad-token",
        )
        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch("requests.Session") as MockSession:
            mock_session = MagicMock()
            mock_session.get.return_value = mock_response
            MockSession.return_value = mock_session

            with pytest.raises(JiraAuthenticationError, match="Authentication failed"):
                client.connect()

    def test_connect_forbidden_raises(self):
        """connect() raises JiraAuthenticationError on 403."""
        client = JiraClient(
            base_url="https://test.atlassian.net",
            email="user@test.com",
            token="token123",
        )
        mock_response = MagicMock()
        mock_response.status_code = 403

        with patch("requests.Session") as MockSession:
            mock_session = MagicMock()
            mock_session.get.return_value = mock_response
            MockSession.return_value = mock_session

            with pytest.raises(JiraAuthenticationError, match="Authorization failed"):
                client.connect()

    def test_connect_network_error_raises(self):
        """connect() raises JiraAPIError on connection error."""
        client = JiraClient(
            base_url="https://test.atlassian.net",
            email="user@test.com",
            token="token123",
        )

        with patch("requests.Session") as MockSession:
            mock_session = MagicMock()
            mock_session.get.side_effect = requests.exceptions.ConnectionError("timeout")
            MockSession.return_value = mock_session

            with pytest.raises(JiraAPIError, match="Cannot connect"):
                client.connect()


# ── GET tests ───────────────────────────────────────────────────────


class TestJiraClientGet:
    """Tests for JiraClient.get()."""

    @pytest.fixture
    def connected_client(self):
        """Create a connected JiraClient with mocked session."""
        client = JiraClient(
            base_url="https://test.atlassian.net",
            email="user@test.com",
            token="token123",
        )
        client._session = MagicMock()
        client._connected = True
        return client

    def test_get_success(self, connected_client):
        """get() returns parsed JSON response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"key": "value"}'
        mock_response.json.return_value = {"key": "value"}
        connected_client._session.get.return_value = mock_response

        result = connected_client.get("/rest/api/3/project")

        assert result == {"key": "value"}

    def test_get_not_connected_raises(self):
        """get() raises JiraConfigurationError if not connected."""
        client = JiraClient(
            base_url="https://test.atlassian.net",
            email="user@test.com",
            token="token123",
        )
        with pytest.raises(JiraConfigurationError, match="Not connected"):
            client.get("/rest/api/3/project")

    def test_get_404_project_raises(self, connected_client):
        """get() raises JiraProjectNotFoundError on 404 for project endpoint."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        connected_client._session.get.return_value = mock_response

        with pytest.raises(JiraProjectNotFoundError, match="PROJ"):
            connected_client.get("/rest/api/3/project/PROJ")

    def test_get_404_issue_raises(self, connected_client):
        """get() raises JiraIssueNotFoundError on 404 for issue endpoint."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        connected_client._session.get.return_value = mock_response

        with pytest.raises(JiraIssueNotFoundError, match="PROJ-123"):
            connected_client.get("/rest/api/3/issue/PROJ-123")

    def test_get_401_raises(self, connected_client):
        """get() raises JiraAuthenticationError on 401."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        connected_client._session.get.return_value = mock_response

        with pytest.raises(JiraAuthenticationError):
            connected_client.get("/rest/api/3/project")

    def test_get_500_raises(self, connected_client):
        """get() raises JiraAPIError on server error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"errorMessages": ["Server error"]}
        mock_response.reason = "Internal Server Error"
        connected_client._session.get.return_value = mock_response

        with pytest.raises(JiraAPIError, match="500"):
            connected_client.get("/rest/api/3/project")

    def test_get_passes_params(self, connected_client):
        """get() passes query parameters to the session."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{}'
        mock_response.json.return_value = {}
        connected_client._session.get.return_value = mock_response

        connected_client.get("/rest/api/3/project", params={"key": "value"})

        connected_client._session.get.assert_called_once()
        call_kwargs = connected_client._session.get.call_args
        assert call_kwargs.kwargs["params"] == {"key": "value"}


# ── POST tests ──────────────────────────────────────────────────────


class TestJiraClientPost:
    """Tests for JiraClient.post()."""

    @pytest.fixture
    def connected_client(self):
        """Create a connected JiraClient with mocked session."""
        client = JiraClient(
            base_url="https://test.atlassian.net",
            email="user@test.com",
            token="token123",
        )
        client._session = MagicMock()
        client._connected = True
        return client

    def test_post_success(self, connected_client):
        """post() returns parsed JSON response."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.content = b'{"id": "123"}'
        mock_response.json.return_value = {"id": "123"}
        connected_client._session.post.return_value = mock_response

        result = connected_client.post(
            "/rest/api/3/issue",
            json_data={"fields": {"summary": "Test"}},
        )

        assert result == {"id": "123"}

    def test_post_sends_json_body(self, connected_client):
        """post() sends the JSON body correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{}'
        mock_response.json.return_value = {}
        connected_client._session.post.return_value = mock_response

        body = {"fields": {"summary": "Test issue"}}
        connected_client.post("/rest/api/3/issue", json_data=body)

        connected_client._session.post.assert_called_once()
        call_kwargs = connected_client._session.post.call_args
        assert call_kwargs.kwargs["json"] == body


# ── Disconnect tests ────────────────────────────────────────────────


class TestJiraClientDisconnect:
    """Tests for JiraClient.disconnect()."""

    def test_disconnect_resets_state(self):
        """disconnect() resets connected state."""
        client = JiraClient(
            base_url="https://test.atlassian.net",
            email="user@test.com",
            token="token123",
        )
        client._session = MagicMock()
        client._connected = True

        client.disconnect()

        assert client.is_connected is False
        assert client._session is None

    def test_get_connection_info(self):
        """get_connection_info() returns connection details."""
        client = JiraClient(
            base_url="https://test.atlassian.net",
            email="user@test.com",
            token="token123",
        )
        info = client.get_connection_info()

        assert info["base_url"] == "https://test.atlassian.net"
        assert info["email"] == "user@test.com"
        assert info["connected"] == "False"
