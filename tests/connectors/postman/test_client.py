"""Unit tests for PostmanClient HTTP operations (Feature 4.5).

Tests the Postman HTTP client including:
- Initialization and configuration validation
- Connection and authentication
- GET, POST, PUT, DELETE requests
- Error handling and exception mapping
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.parse import urlparse

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
project_root = Path(__file__).parent.parent.parent.parent

# Import exceptions first
exceptions_module = import_module_direct("postman_exceptions", project_root / "src" / "connectors" / "postman" / "exceptions.py")

# Make exceptions available in sys.modules so client can import them
sys.modules["src.connectors.postman.exceptions"] = exceptions_module
postman_package = type('Package', (), {'exceptions': exceptions_module})()
sys.modules["src.connectors.postman"] = postman_package
sys.modules["src.connectors"] = type('Package', (), {'postman': postman_package})()

# Now import client
client_module = import_module_direct("postman_client", project_root / "src" / "connectors" / "postman" / "client.py")

PostmanClient = client_module.PostmanClient
PostmanAPIError = exceptions_module.PostmanAPIError
PostmanAuthenticationError = exceptions_module.PostmanAuthenticationError
PostmanCollectionNotFoundError = exceptions_module.PostmanCollectionNotFoundError
PostmanConfigurationError = exceptions_module.PostmanConfigurationError
PostmanEnvironmentNotFoundError = exceptions_module.PostmanEnvironmentNotFoundError


# ── Initialization tests ────────────────────────────────────────────


class TestPostmanClientInit:
    """Tests for PostmanClient initialization."""

    def test_init_valid_params(self):
        """PostmanClient initializes with valid parameters."""
        client = PostmanClient(api_key="PMAK-test-key")
        assert client.is_connected is False

    def test_init_custom_base_url(self):
        """PostmanClient accepts custom base URL."""
        client = PostmanClient(api_key="PMAK-test", base_url="https://custom.api.com/")
        assert client._base_url == "https://custom.api.com"

    def test_init_missing_api_key_raises(self):
        """PostmanClient raises PostmanConfigurationError for empty api_key."""
        with pytest.raises(PostmanConfigurationError, match="API key"):
            PostmanClient(api_key="")


# ── from_env tests ──────────────────────────────────────────────────


class TestPostmanClientFromEnv:
    """Tests for PostmanClient.from_env()."""

    @patch.dict("os.environ", {}, clear=True)
    def test_from_env_missing_key_raises(self):
        """from_env() raises when POSTMAN_API_KEY is missing."""
        with pytest.raises(PostmanConfigurationError, match="POSTMAN_API_KEY"):
            PostmanClient.from_env()


# ── Connect tests ───────────────────────────────────────────────────


class TestPostmanClientConnect:
    """Tests for PostmanClient.connect()."""

    def test_connect_success(self):
        """connect() sets connected state on success."""
        client = PostmanClient(api_key="PMAK-test-key")
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
        """connect() raises PostmanAuthenticationError on 401."""
        client = PostmanClient(api_key="bad-key")
        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch("requests.Session") as MockSession:
            mock_session = MagicMock()
            mock_session.get.return_value = mock_response
            MockSession.return_value = mock_session

            with pytest.raises(PostmanAuthenticationError, match="Authentication failed"):
                client.connect()

    def test_connect_network_error_raises(self):
        """connect() raises PostmanAPIError on connection error."""
        client = PostmanClient(api_key="PMAK-test-key")

        with patch("requests.Session") as MockSession:
            mock_session = MagicMock()
            mock_session.get.side_effect = requests.exceptions.ConnectionError("timeout")
            MockSession.return_value = mock_session

            with pytest.raises(PostmanAPIError, match="Cannot connect"):
                client.connect()


# ── GET tests ───────────────────────────────────────────────────────


class TestPostmanClientGet:
    """Tests for PostmanClient.get()."""

    @pytest.fixture
    def connected_client(self):
        """Create a connected PostmanClient with mocked session."""
        client = PostmanClient(api_key="PMAK-test-key")
        client._session = MagicMock()
        client._connected = True
        return client

    def test_get_success(self, connected_client):
        """get() returns parsed JSON response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"collections": []}'
        mock_response.json.return_value = {"collections": []}
        connected_client._session.get.return_value = mock_response

        result = connected_client.get("/collections")

        assert result == {"collections": []}

    def test_get_not_connected_raises(self):
        """get() raises PostmanConfigurationError if not connected."""
        client = PostmanClient(api_key="PMAK-test-key")
        with pytest.raises(PostmanConfigurationError, match="Not connected"):
            client.get("/collections")

    def test_get_404_collection_raises(self, connected_client):
        """get() raises PostmanCollectionNotFoundError on 404 for collection endpoint."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        connected_client._session.get.return_value = mock_response

        with pytest.raises(PostmanCollectionNotFoundError, match="col-123"):
            connected_client.get("/collections/col-123")

    def test_get_404_environment_raises(self, connected_client):
        """get() raises PostmanEnvironmentNotFoundError on 404 for environment endpoint."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        connected_client._session.get.return_value = mock_response

        with pytest.raises(PostmanEnvironmentNotFoundError, match="env-456"):
            connected_client.get("/environments/env-456")

    def test_get_401_raises(self, connected_client):
        """get() raises PostmanAuthenticationError on 401."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        connected_client._session.get.return_value = mock_response

        with pytest.raises(PostmanAuthenticationError):
            connected_client.get("/collections")

    def test_get_500_raises(self, connected_client):
        """get() raises PostmanAPIError on server error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": {"message": "Server error"}}
        mock_response.reason = "Internal Server Error"
        connected_client._session.get.return_value = mock_response

        with pytest.raises(PostmanAPIError, match="500"):
            connected_client.get("/collections")

    def test_get_passes_params(self, connected_client):
        """get() passes query parameters to the session."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{}'
        mock_response.json.return_value = {}
        connected_client._session.get.return_value = mock_response

        connected_client.get("/collections", params={"workspace": "ws-1"})

        call_kwargs = connected_client._session.get.call_args
        assert call_kwargs.kwargs["params"] == {"workspace": "ws-1"}


# ── POST tests ──────────────────────────────────────────────────────


class TestPostmanClientPost:
    """Tests for PostmanClient.post()."""

    @pytest.fixture
    def connected_client(self):
        """Create a connected PostmanClient with mocked session."""
        client = PostmanClient(api_key="PMAK-test-key")
        client._session = MagicMock()
        client._connected = True
        return client

    def test_post_success(self, connected_client):
        """post() returns parsed JSON response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"collection": {"id": "col-1"}}'
        mock_response.json.return_value = {"collection": {"id": "col-1"}}
        connected_client._session.post.return_value = mock_response

        result = connected_client.post("/collections", json_data={"collection": {}})

        assert result["collection"]["id"] == "col-1"

    def test_post_sends_json_body(self, connected_client):
        """post() sends the JSON body correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{}'
        mock_response.json.return_value = {}
        connected_client._session.post.return_value = mock_response

        body = {"collection": {"info": {"name": "Test"}}}
        connected_client.post("/collections", json_data=body)

        call_kwargs = connected_client._session.post.call_args
        assert call_kwargs.kwargs["json"] == body


# ── DELETE tests ────────────────────────────────────────────────────


class TestPostmanClientDelete:
    """Tests for PostmanClient.delete()."""

    @pytest.fixture
    def connected_client(self):
        """Create a connected PostmanClient with mocked session."""
        client = PostmanClient(api_key="PMAK-test-key")
        client._session = MagicMock()
        client._connected = True
        return client

    def test_delete_success(self, connected_client):
        """delete() returns parsed JSON response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"collection": {"id": "col-1"}}'
        mock_response.json.return_value = {"collection": {"id": "col-1"}}
        connected_client._session.delete.return_value = mock_response

        result = connected_client.delete("/collections/col-1")

        assert result["collection"]["id"] == "col-1"


# ── Disconnect tests ────────────────────────────────────────────────


class TestPostmanClientDisconnect:
    """Tests for PostmanClient.disconnect()."""

    def test_disconnect_resets_state(self):
        """disconnect() resets connected state."""
        client = PostmanClient(api_key="PMAK-test-key")
        client._session = MagicMock()
        client._connected = True

        client.disconnect()

        assert client.is_connected is False
        assert client._session is None

    def test_get_connection_info(self):
        """get_connection_info() returns connection details."""
        client = PostmanClient(api_key="PMAK-test-key")
        info = client.get_connection_info()
        parsed = urlparse(info["base_url"])

        assert parsed.hostname == "api.getpostman.com"
        assert info["connected"] == "False"
