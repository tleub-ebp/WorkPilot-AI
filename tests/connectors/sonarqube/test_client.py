"""Unit tests for SonarQubeClient HTTP operations (Feature 4.4).

Tests the SonarQube HTTP client lifecycle including:
- Initialization and configuration validation
- Connection and authentication
- GET requests with error mapping (401, 403, 404, 5xx)
- Disconnect and connection info
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from src.connectors.sonarqube.client import SonarQubeClient
from src.connectors.sonarqube.exceptions import (
    SonarQubeAPIError,
    SonarQubeAuthenticationError,
    SonarQubeConfigurationError,
    SonarQubeProjectNotFoundError,
)

TEST_URL = "http://localhost:9000"
TEST_TOKEN = "squ_test_token_12345"


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def sonar_client():
    """Create a SonarQubeClient with a mocked session (already connected)."""
    client = SonarQubeClient(base_url=TEST_URL, token=TEST_TOKEN)
    client._session = MagicMock(spec=requests.Session)
    client._connected = True
    return client


@pytest.fixture
def mock_response():
    """Create a reusable mock response factory."""
    def _make(status_code=200, json_data=None, text=""):
        resp = MagicMock(spec=requests.Response)
        resp.status_code = status_code
        resp.json.return_value = json_data or {}
        resp.text = text
        resp.content = b'{"ok": true}' if json_data is not None else b""
        resp.reason = "OK" if status_code < 400 else "Error"
        resp.raise_for_status = MagicMock()
        if status_code >= 400:
            resp.raise_for_status.side_effect = requests.exceptions.HTTPError()
        return resp
    return _make


# ── Initialization tests ─────────────────────────────────────────


class TestClientInit:
    """Tests for SonarQubeClient.__init__()."""

    def test_valid_init(self):
        """Client initializes with valid base_url and token."""
        client = SonarQubeClient(base_url=TEST_URL, token=TEST_TOKEN)
        assert client.base_url == TEST_URL
        assert not client.is_connected

    def test_strips_trailing_slash(self):
        """Client strips trailing slash from base_url."""
        client = SonarQubeClient(base_url="http://localhost:9000/", token=TEST_TOKEN)
        assert client.base_url == "http://localhost:9000"

    def test_empty_base_url_raises(self):
        """Client raises ConfigurationError for empty base_url."""
        with pytest.raises(SonarQubeConfigurationError, match="base URL"):
            SonarQubeClient(base_url="", token=TEST_TOKEN)

    def test_empty_token_raises(self):
        """Client raises ConfigurationError for empty token."""
        with pytest.raises(SonarQubeConfigurationError, match="token"):
            SonarQubeClient(base_url=TEST_URL, token="")


# ── Connection tests ─────────────────────────────────────────────


class TestClientConnect:
    """Tests for SonarQubeClient.connect()."""

    def test_connect_success(self, mock_response):
        """connect() succeeds when /api/system/status returns 200."""
        client = SonarQubeClient(base_url=TEST_URL, token=TEST_TOKEN)

        with patch("src.connectors.sonarqube.client.requests.Session") as MockSession:
            mock_session = MagicMock()
            mock_session.get.return_value = mock_response(
                200, {"status": "UP"}
            )
            MockSession.return_value = mock_session

            client.connect()

        assert client.is_connected

    def test_connect_401_raises_auth_error(self, mock_response):
        """connect() raises AuthenticationError on HTTP 401."""
        client = SonarQubeClient(base_url=TEST_URL, token="bad-token")

        with patch("src.connectors.sonarqube.client.requests.Session") as MockSession:
            mock_session = MagicMock()
            mock_session.get.return_value = mock_response(401)
            MockSession.return_value = mock_session

            with pytest.raises(SonarQubeAuthenticationError, match="Authentication failed"):
                client.connect()

    def test_connect_unreachable_raises_api_error(self):
        """connect() raises APIError when server is unreachable."""
        client = SonarQubeClient(base_url="http://unreachable:9999", token=TEST_TOKEN)

        with patch("src.connectors.sonarqube.client.requests.Session") as MockSession:
            mock_session = MagicMock()
            mock_session.get.side_effect = requests.exceptions.ConnectionError("refused")
            MockSession.return_value = mock_session

            with pytest.raises(SonarQubeAPIError, match="Cannot connect"):
                client.connect()


# ── GET request tests ────────────────────────────────────────────


class TestClientGet:
    """Tests for SonarQubeClient.get()."""

    def test_get_returns_json(self, sonar_client, mock_response):
        """get() returns parsed JSON response."""
        sonar_client._session.get.return_value = mock_response(
            200, {"components": [{"key": "proj1"}]}
        )

        result = sonar_client.get("/api/projects/search")

        assert result == {"components": [{"key": "proj1"}]}

    def test_get_passes_params(self, sonar_client, mock_response):
        """get() forwards query parameters."""
        sonar_client._session.get.return_value = mock_response(200, {})

        sonar_client.get("/api/projects/search", params={"ps": 10, "p": 1})

        call_kwargs = sonar_client._session.get.call_args.kwargs
        assert call_kwargs["params"] == {"ps": 10, "p": 1}

    def test_get_not_connected_raises(self):
        """get() raises ConfigurationError when not connected."""
        client = SonarQubeClient(base_url=TEST_URL, token=TEST_TOKEN)

        with pytest.raises(SonarQubeConfigurationError, match="Not connected"):
            client.get("/api/projects/search")

    def test_get_401_raises_auth_error(self, sonar_client, mock_response):
        """get() raises AuthenticationError on HTTP 401."""
        sonar_client._session.get.return_value = mock_response(401)

        with pytest.raises(SonarQubeAuthenticationError):
            sonar_client.get("/api/projects/search")

    def test_get_403_raises_auth_error(self, sonar_client, mock_response):
        """get() raises AuthenticationError on HTTP 403."""
        sonar_client._session.get.return_value = mock_response(403)

        with pytest.raises(SonarQubeAuthenticationError):
            sonar_client.get("/api/measures/component")

    def test_get_404_with_project_key_raises_not_found(
        self, sonar_client, mock_response
    ):
        """get() raises ProjectNotFoundError on 404 with component param."""
        sonar_client._session.get.return_value = mock_response(404)

        with pytest.raises(SonarQubeProjectNotFoundError) as exc_info:
            sonar_client.get(
                "/api/components/show",
                params={"component": "missing-project"},
            )

        assert exc_info.value.project_key == "missing-project"

    def test_get_404_without_project_raises_api_error(
        self, sonar_client, mock_response
    ):
        """get() raises APIError on 404 without project context."""
        sonar_client._session.get.return_value = mock_response(404)

        with pytest.raises(SonarQubeAPIError, match="Resource not found"):
            sonar_client.get("/api/unknown/endpoint")

    def test_get_500_raises_api_error(self, sonar_client, mock_response):
        """get() raises APIError on HTTP 500."""
        sonar_client._session.get.return_value = mock_response(
            500,
            {"errors": [{"msg": "Internal server error"}]},
            text="Internal server error",
        )

        with pytest.raises(SonarQubeAPIError, match="Internal server error"):
            sonar_client.get("/api/projects/search")

    def test_get_request_exception_raises_api_error(self, sonar_client):
        """get() wraps requests exceptions as APIError."""
        sonar_client._session.get.side_effect = requests.exceptions.Timeout("timeout")

        with pytest.raises(SonarQubeAPIError, match="Request to"):
            sonar_client.get("/api/projects/search")

    def test_get_empty_response_returns_empty_dict(self, sonar_client):
        """get() returns empty dict for responses with no content."""
        resp = MagicMock(spec=requests.Response)
        resp.status_code = 200
        resp.content = b""
        sonar_client._session.get.return_value = resp

        result = sonar_client.get("/api/system/status")
        assert result == {}


# ── Disconnect and connection info tests ─────────────────────────


class TestClientDisconnect:
    """Tests for SonarQubeClient disconnect and info methods."""

    def test_disconnect(self, sonar_client):
        """disconnect() closes session and resets state."""
        sonar_client.disconnect()

        assert not sonar_client.is_connected
        assert sonar_client._session is None

    def test_connection_info(self, sonar_client):
        """get_connection_info() returns correct details."""
        info = sonar_client.get_connection_info()

        assert info["base_url"] == TEST_URL
        assert info["connected"] == "True"
