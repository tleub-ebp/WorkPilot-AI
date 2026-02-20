"""Unit tests for PostmanConnector high-level operations (Feature 4.5).

Tests the Postman connector including:
- Listing workspaces
- Listing and getting collections
- Extracting requests from collections
- Importing collections as API specs
- Generating collections from endpoints
- Environment operations and sync
- Collection validation
- Collection summary
"""

from unittest.mock import MagicMock, patch

import pytest

from src.connectors.postman.connector import PostmanConnector
from src.connectors.postman.models import (
    PostmanCollection,
    PostmanCollectionRun,
    PostmanEnvironment,
    PostmanRequest,
    PostmanTestResult,
    PostmanWorkspace,
)


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def mock_postman_client():
    """Create a mock PostmanClient."""
    client = MagicMock()
    client.is_connected = True
    return client


@pytest.fixture
def connector(mock_postman_client):
    """Create a PostmanConnector with a mocked client."""
    return PostmanConnector(mock_postman_client)


# ── list_workspaces tests ───────────────────────────────────────


class TestListWorkspaces:
    """Tests for PostmanConnector.list_workspaces()."""

    def test_returns_workspaces(self, connector, mock_postman_client):
        """list_workspaces() returns a list of PostmanWorkspace objects."""
        mock_postman_client.get.return_value = {
            "workspaces": [
                {"id": "ws-1", "name": "My Workspace", "type": "personal"},
                {"id": "ws-2", "name": "Team Workspace", "type": "team"},
            ]
        }

        result = connector.list_workspaces()

        assert len(result) == 2
        assert all(isinstance(w, PostmanWorkspace) for w in result)
        assert result[0].workspace_id == "ws-1"
        assert result[1].workspace_type == "team"

    def test_returns_empty_list(self, connector, mock_postman_client):
        """list_workspaces() returns empty list when no workspaces exist."""
        mock_postman_client.get.return_value = {"workspaces": []}

        result = connector.list_workspaces()

        assert result == []


# ── list_collections tests ──────────────────────────────────────


class TestListCollections:
    """Tests for PostmanConnector.list_collections()."""

    def test_returns_collections(self, connector, mock_postman_client):
        """list_collections() returns a list of PostmanCollection objects."""
        mock_postman_client.get.return_value = {
            "collections": [
                {"id": "col-1", "name": "API v1", "uid": "123-col-1"},
                {"id": "col-2", "name": "API v2", "uid": "123-col-2"},
            ]
        }

        result = connector.list_collections()

        assert len(result) == 2
        assert all(isinstance(c, PostmanCollection) for c in result)
        assert result[0].collection_id == "col-1"

    def test_passes_workspace_filter(self, connector, mock_postman_client):
        """list_collections() passes workspace filter parameter."""
        mock_postman_client.get.return_value = {"collections": []}

        connector.list_collections(workspace_id="ws-1")

        mock_postman_client.get.assert_called_once_with(
            "/collections",
            params={"workspace": "ws-1"},
        )

    def test_returns_empty_list(self, connector, mock_postman_client):
        """list_collections() returns empty list when no collections exist."""
        mock_postman_client.get.return_value = {"collections": []}

        result = connector.list_collections()

        assert result == []


# ── get_collection tests ────────────────────────────────────────


class TestGetCollection:
    """Tests for PostmanConnector.get_collection()."""

    def test_returns_collection_data(self, connector, mock_postman_client):
        """get_collection() returns full collection data."""
        mock_postman_client.get.return_value = {
            "collection": {
                "info": {"name": "My API", "schema": "v2.1.0"},
                "item": [
                    {"name": "Get Users", "request": {"method": "GET", "url": "/users"}},
                ],
            }
        }

        result = connector.get_collection("col-1")

        assert result["info"]["name"] == "My API"
        assert len(result["item"]) == 1


# ── get_collection_requests tests ───────────────────────────────


class TestGetCollectionRequests:
    """Tests for PostmanConnector.get_collection_requests()."""

    def test_extracts_flat_requests(self, connector, mock_postman_client):
        """get_collection_requests() extracts top-level requests."""
        mock_postman_client.get.return_value = {
            "collection": {
                "info": {"name": "API"},
                "item": [
                    {
                        "id": "req-1",
                        "name": "Get Users",
                        "request": {
                            "method": "GET",
                            "url": {"raw": "http://localhost/users"},
                        },
                    },
                    {
                        "id": "req-2",
                        "name": "Create User",
                        "request": {
                            "method": "POST",
                            "url": {"raw": "http://localhost/users"},
                        },
                    },
                ],
            }
        }

        result = connector.get_collection_requests("col-1")

        assert len(result) == 2
        assert all(isinstance(r, PostmanRequest) for r in result)
        assert result[0].name == "Get Users"
        assert result[0].method == "GET"
        assert result[1].method == "POST"

    def test_extracts_nested_requests(self, connector, mock_postman_client):
        """get_collection_requests() extracts requests from folders."""
        mock_postman_client.get.return_value = {
            "collection": {
                "info": {"name": "API"},
                "item": [
                    {
                        "id": "folder-1",
                        "name": "Users",
                        "item": [
                            {
                                "id": "req-1",
                                "name": "Get Users",
                                "request": {"method": "GET", "url": "/users"},
                            },
                        ],
                    },
                    {
                        "id": "req-2",
                        "name": "Health Check",
                        "request": {"method": "GET", "url": "/health"},
                    },
                ],
            }
        }

        result = connector.get_collection_requests("col-1")

        assert len(result) == 2

    def test_returns_empty_for_empty_collection(self, connector, mock_postman_client):
        """get_collection_requests() returns empty list for empty collection."""
        mock_postman_client.get.return_value = {
            "collection": {"info": {"name": "Empty"}, "item": []}
        }

        result = connector.get_collection_requests("col-1")

        assert result == []


# ── import_collection_as_spec tests ─────────────────────────────


class TestImportCollectionAsSpec:
    """Tests for PostmanConnector.import_collection_as_spec()."""

    def test_converts_to_spec_format(self, connector, mock_postman_client):
        """import_collection_as_spec() converts requests to spec format."""
        mock_postman_client.get.return_value = {
            "collection": {
                "info": {"name": "API"},
                "item": [
                    {
                        "id": "req-1",
                        "name": "Get Users",
                        "request": {
                            "method": "GET",
                            "url": {"raw": "http://localhost/users"},
                            "description": "List all users",
                        },
                    },
                ],
            }
        }

        result = connector.import_collection_as_spec("col-1")

        assert len(result) == 1
        assert result[0]["name"] == "Get Users"
        assert result[0]["method"] == "GET"
        assert result[0]["source"] == "postman"


# ── generate_collection_from_endpoints tests ────────────────────


class TestGenerateCollection:
    """Tests for PostmanConnector.generate_collection_from_endpoints()."""

    def test_generates_collection(self, connector, mock_postman_client):
        """generate_collection_from_endpoints() creates a collection."""
        mock_postman_client.post.return_value = {
            "collection": {
                "id": "col-new",
                "name": "Generated API",
                "uid": "123-col-new",
            }
        }

        endpoints = [
            {"name": "Get Users", "method": "GET", "path": "/api/users"},
            {"name": "Create User", "method": "POST", "path": "/api/users", "body": '{"name": "test"}'},
        ]

        result = connector.generate_collection_from_endpoints(
            workspace_id="ws-1",
            collection_name="Generated API",
            endpoints=endpoints,
        )

        assert isinstance(result, PostmanCollection)
        assert result.collection_id == "col-new"

        # Verify POST was called with collection structure
        call_args = mock_postman_client.post.call_args
        payload = call_args.kwargs["json_data"]
        assert payload["collection"]["info"]["name"] == "Generated API"
        assert len(payload["collection"]["item"]) == 2
        assert payload["workspace"] == "ws-1"

    def test_includes_test_scripts(self, connector, mock_postman_client):
        """generate_collection_from_endpoints() adds test scripts."""
        mock_postman_client.post.return_value = {
            "collection": {"id": "col-new", "name": "API"}
        }

        endpoints = [{"name": "Health", "method": "GET", "path": "/health"}]

        connector.generate_collection_from_endpoints("ws-1", "API", endpoints)

        call_args = mock_postman_client.post.call_args
        items = call_args.kwargs["json_data"]["collection"]["item"]
        assert "event" in items[0]
        assert items[0]["event"][0]["listen"] == "test"


# ── Environment operations tests ────────────────────────────────


class TestEnvironmentOperations:
    """Tests for environment-related operations."""

    def test_list_environments(self, connector, mock_postman_client):
        """list_environments() returns PostmanEnvironment objects."""
        mock_postman_client.get.return_value = {
            "environments": [
                {"id": "env-1", "name": "Development", "uid": "123-env-1"},
                {"id": "env-2", "name": "Production", "uid": "123-env-2"},
            ]
        }

        result = connector.list_environments()

        assert len(result) == 2
        assert all(isinstance(e, PostmanEnvironment) for e in result)
        assert result[0].name == "Development"

    def test_get_environment(self, connector, mock_postman_client):
        """get_environment() returns a single environment."""
        mock_postman_client.get.return_value = {
            "environment": {
                "id": "env-1",
                "name": "Development",
                "values": [
                    {"key": "base_url", "value": "http://localhost:3000"},
                ],
            }
        }

        result = connector.get_environment("env-1")

        assert isinstance(result, PostmanEnvironment)
        assert result.name == "Development"
        assert len(result.values) == 1

    def test_sync_environment(self, connector, mock_postman_client):
        """sync_environment() updates environment variables."""
        mock_postman_client.put.return_value = {}
        mock_postman_client.get.return_value = {
            "environment": {
                "id": "env-1",
                "name": "Development",
                "values": [
                    {"key": "base_url", "value": "http://localhost:8080"},
                    {"key": "api_key", "value": "test-key"},
                ],
            }
        }

        result = connector.sync_environment(
            "env-1",
            {"base_url": "http://localhost:8080", "api_key": "test-key"},
        )

        assert isinstance(result, PostmanEnvironment)
        mock_postman_client.put.assert_called_once()


# ── Validation tests ────────────────────────────────────────────


class TestValidateCollection:
    """Tests for PostmanConnector.validate_collection_structure()."""

    def test_validates_good_collection(self, connector, mock_postman_client):
        """validate_collection_structure() passes for valid collection."""
        mock_postman_client.get.return_value = {
            "collection": {
                "info": {"name": "API"},
                "item": [
                    {
                        "id": "req-1",
                        "name": "Get Users",
                        "request": {
                            "method": "GET",
                            "url": {"raw": "http://localhost/users"},
                        },
                    },
                ],
            }
        }

        result = connector.validate_collection_structure("col-1")

        assert isinstance(result, PostmanCollectionRun)
        assert result.is_passing is True
        assert result.failed_tests == 0
        assert result.success_rate == 100.0

    def test_detects_empty_url(self, connector, mock_postman_client):
        """validate_collection_structure() detects empty URLs."""
        mock_postman_client.get.return_value = {
            "collection": {
                "info": {"name": "API"},
                "item": [
                    {
                        "id": "req-1",
                        "name": "Bad Request",
                        "request": {"method": "GET", "url": ""},
                    },
                ],
            }
        }

        result = connector.validate_collection_structure("col-1")

        assert result.is_passing is False
        assert result.failed_tests >= 1


# ── Collection summary tests ────────────────────────────────────


class TestGetCollectionSummary:
    """Tests for PostmanConnector.get_collection_summary()."""

    def test_returns_summary(self, connector, mock_postman_client):
        """get_collection_summary() returns aggregated data."""
        mock_postman_client.get.return_value = {
            "collection": {
                "info": {"name": "My API", "description": "API description"},
                "item": [
                    {
                        "id": "req-1",
                        "name": "Get Users",
                        "request": {"method": "GET", "url": {"raw": "/users"}},
                    },
                    {
                        "id": "req-2",
                        "name": "Create User",
                        "request": {"method": "POST", "url": {"raw": "/users"}},
                    },
                    {
                        "id": "req-3",
                        "name": "Get User",
                        "request": {"method": "GET", "url": {"raw": "/users/1"}},
                    },
                ],
            }
        }

        result = connector.get_collection_summary("col-1")

        assert result["name"] == "My API"
        assert result["total_requests"] == 3
        assert result["methods"]["GET"] == 2
        assert result["methods"]["POST"] == 1


# ── Model unit tests ─────────────────────────────────────────────


class TestPostmanModels:
    """Direct unit tests for Postman data models."""

    def test_collection_run_success_rate(self):
        """PostmanCollectionRun.success_rate calculates correctly."""
        run = PostmanCollectionRun(
            collection_id="col-1",
            total_tests=10,
            passed_tests=8,
            failed_tests=2,
        )
        assert run.success_rate == 80.0

    def test_collection_run_is_passing(self):
        """PostmanCollectionRun.is_passing returns True when no failures."""
        run = PostmanCollectionRun(
            collection_id="col-1",
            total_tests=5,
            passed_tests=5,
            failed_tests=0,
        )
        assert run.is_passing is True

    def test_collection_run_not_passing(self):
        """PostmanCollectionRun.is_passing returns False with failures."""
        run = PostmanCollectionRun(
            collection_id="col-1",
            total_tests=5,
            passed_tests=3,
            failed_tests=2,
        )
        assert run.is_passing is False

    def test_collection_run_empty_tests(self):
        """PostmanCollectionRun.success_rate handles zero tests."""
        run = PostmanCollectionRun(collection_id="col-1")
        assert run.success_rate == 100.0

    def test_postman_request_from_api(self):
        """PostmanRequest.from_api_response maps fields correctly."""
        req = PostmanRequest.from_api_response({
            "id": "req-1",
            "name": "Get Users",
            "request": {
                "method": "POST",
                "url": {"raw": "http://localhost/users"},
                "header": [{"key": "Content-Type", "value": "application/json"}],
                "body": {"mode": "raw", "raw": "{}"},
                "description": "Create a user",
            },
        })
        assert req.request_id == "req-1"
        assert req.method == "POST"
        assert req.url == "http://localhost/users"
        assert len(req.headers) == 1
        assert req.description == "Create a user"

    def test_postman_request_string_url(self):
        """PostmanRequest handles string URL format."""
        req = PostmanRequest.from_api_response({
            "id": "req-2",
            "name": "Simple",
            "request": {
                "method": "GET",
                "url": "http://example.com/api",
            },
        })
        assert req.url == "http://example.com/api"

    def test_postman_workspace_from_api(self):
        """PostmanWorkspace.from_api_response maps fields correctly."""
        ws = PostmanWorkspace.from_api_response({
            "id": "ws-1",
            "name": "Team",
            "type": "team",
            "description": "Team workspace",
        })
        assert ws.workspace_id == "ws-1"
        assert ws.workspace_type == "team"

    def test_postman_environment_from_api(self):
        """PostmanEnvironment.from_api_response maps fields correctly."""
        env = PostmanEnvironment.from_api_response({
            "id": "env-1",
            "name": "Dev",
            "uid": "123-env-1",
            "values": [{"key": "url", "value": "http://localhost"}],
        })
        assert env.environment_id == "env-1"
        assert env.name == "Dev"
        assert len(env.values) == 1
