"""Shared pytest fixtures for the Azure DevOps connector test suite.

Provides reusable fixtures for creating mock API clients, sample
API response objects, and pre-configured connector instances. All
fixtures use ``unittest.mock`` to avoid real Azure DevOps API calls.
"""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.config.settings import Settings
from src.connectors.azure_devops.client import AzureDevOpsClient
from src.connectors.azure_devops.repos import AzureReposClient
from src.connectors.azure_devops.work_items import AzureWorkItemsClient


# ── Constants for test data ──────────────────────────────────────────

TEST_PAT = "test-pat-token-value"
TEST_ORG_URL = "https://dev.azure.com/test-organization"
TEST_PROJECT = "TestProject"
TEST_REPO_ID = "abc12345-def6-7890-abcd-ef1234567890"
TEST_REPO_NAME = "test-repository"


# ── Settings fixtures ───────────────────────────────────────────────


@pytest.fixture
def sample_settings():
    """Create a Settings instance with valid test credentials."""
    return Settings(
        pat=TEST_PAT,
        organization_url=TEST_ORG_URL,
        project=TEST_PROJECT,
    )


@pytest.fixture
def settings_no_project():
    """Create a Settings instance without a default project."""
    return Settings(
        pat=TEST_PAT,
        organization_url=TEST_ORG_URL,
        project=None,
    )


# ── Mock API client fixtures ────────────────────────────────────────


@pytest.fixture
def mock_git_client():
    """Create a mock Azure DevOps Git API client.

    Returns a MagicMock with the same interface as the Azure DevOps
    GitClient, suitable for stubbing repository operation calls.
    """
    client = MagicMock()
    client.get_repositories = MagicMock(return_value=[])
    client.get_repository = MagicMock(return_value=None)
    client.get_items = MagicMock(return_value=[])
    client.get_item = MagicMock(return_value=None)
    return client


@pytest.fixture
def mock_wit_client():
    """Create a mock Azure DevOps Work Item Tracking API client.

    Returns a MagicMock with the same interface as the Azure DevOps
    WorkItemTrackingClient, suitable for stubbing work item calls.
    """
    client = MagicMock()
    client.query_by_wiql = MagicMock(return_value=MagicMock(work_items=[]))
    client.get_work_items = MagicMock(return_value=[])
    client.get_work_item = MagicMock(return_value=None)
    return client


@pytest.fixture
def mock_connection(mock_git_client, mock_wit_client):
    """Create a mock Azure DevOps Connection object.

    The connection exposes ``clients.get_git_client()`` and
    ``clients.get_work_item_tracking_client()`` that return the
    corresponding mock API clients.
    """
    connection = MagicMock()
    connection.clients.get_git_client.return_value = mock_git_client
    connection.clients.get_work_item_tracking_client.return_value = (
        mock_wit_client
    )
    return connection


# ── Azure DevOps client fixtures ────────────────────────────────────


@pytest.fixture
def azure_client(sample_settings, mock_connection):
    """Create an AzureDevOpsClient with a mocked connection.

    The client is configured with valid test settings and a mock
    connection is injected so that ``get_git_client()`` and
    ``get_wit_client()`` return controlled mock objects.
    """
    client = AzureDevOpsClient(sample_settings)
    client._connection = mock_connection
    return client


# ── Repos and Work Items client fixtures ────────────────────────────


@pytest.fixture
def repos_client(azure_client):
    """Create an AzureReposClient with a mocked underlying client."""
    return AzureReposClient(azure_client)


@pytest.fixture
def work_items_client(azure_client):
    """Create an AzureWorkItemsClient with a mocked underlying client."""
    return AzureWorkItemsClient(azure_client)


# ── Sample API response fixtures ────────────────────────────────────


@pytest.fixture
def sample_api_repo():
    """Create a mock Azure DevOps Git repository API response.

    Mimics the structure returned by ``git_client.get_repositories()``
    and ``git_client.get_repository()``.
    """
    repo = SimpleNamespace(
        id=TEST_REPO_ID,
        name=TEST_REPO_NAME,
        project=SimpleNamespace(name=TEST_PROJECT),
        default_branch="refs/heads/main",
        remote_url=f"{TEST_ORG_URL}/{TEST_PROJECT}/_git/{TEST_REPO_NAME}",
    )
    return repo


@pytest.fixture
def sample_api_repo_list(sample_api_repo):
    """Create a list of mock repository API responses.

    Returns a list with two repositories for testing list operations.
    """
    second_repo = SimpleNamespace(
        id="second-repo-id-0000-0000-000000000000",
        name="second-repository",
        project=SimpleNamespace(name=TEST_PROJECT),
        default_branch="refs/heads/develop",
        remote_url=f"{TEST_ORG_URL}/{TEST_PROJECT}/_git/second-repository",
    )
    return [sample_api_repo, second_repo]


@pytest.fixture
def sample_api_work_item():
    """Create a mock Azure DevOps work item API response.

    Mimics the structure returned by ``wit_client.get_work_item()``
    and ``wit_client.get_work_items()``. Includes all commonly used
    System.* and Microsoft.VSTS.* fields.
    """
    work_item = SimpleNamespace(
        id=42,
        fields={
            "System.Title": "Fix login page timeout",
            "System.State": "Active",
            "System.WorkItemType": "Bug",
            "System.AssignedTo": {"displayName": "John Doe"},
            "System.Description": "<p>Login page times out after 30s.</p>",
            "System.Tags": "frontend;urgent",
            "System.CreatedDate": datetime(2025, 1, 15, 10, 30, 0),
            "System.AreaPath": f"{TEST_PROJECT}\\Web",
            "System.IterationPath": f"{TEST_PROJECT}\\Sprint 5",
            "Microsoft.VSTS.Common.Priority": 1,
        },
        url=(
            f"{TEST_ORG_URL}/{TEST_PROJECT}/_apis/wit/workItems/42"
        ),
    )
    return work_item


@pytest.fixture
def sample_api_work_item_minimal():
    """Create a work item API response with minimal fields.

    Tests graceful handling of missing optional fields such as
    AssignedTo, Tags, and Priority.
    """
    work_item = SimpleNamespace(
        id=99,
        fields={
            "System.Title": "Minimal work item",
            "System.State": "New",
            "System.WorkItemType": "Task",
        },
        url=None,
    )
    return work_item


@pytest.fixture
def sample_api_work_item_string_assigned():
    """Create a work item with AssignedTo as a plain string.

    Some Azure DevOps configurations return AssignedTo as a string
    rather than an identity object dictionary.
    """
    work_item = SimpleNamespace(
        id=55,
        fields={
            "System.Title": "Task with string assignee",
            "System.State": "Active",
            "System.WorkItemType": "User Story",
            "System.AssignedTo": "Jane Smith",
        },
        url=None,
    )
    return work_item


@pytest.fixture
def sample_wiql_result():
    """Create a mock WIQL query result with work item ID references.

    Mimics the structure returned by ``wit_client.query_by_wiql()``,
    which contains only work item IDs (not full details).
    """
    result = SimpleNamespace(
        work_items=[
            SimpleNamespace(id=42),
            SimpleNamespace(id=55),
            SimpleNamespace(id=99),
        ],
    )
    return result


@pytest.fixture
def sample_wiql_result_empty():
    """Create a mock WIQL query result with no matches."""
    return SimpleNamespace(work_items=[])


@pytest.fixture
def sample_api_file_item_blob():
    """Create a mock file item API response for a regular file (blob)."""
    item = SimpleNamespace(
        path="/src/main.py",
        git_object_type="blob",
        object_id="abc123def456",
        commit_id="commit789",
        url=f"{TEST_ORG_URL}/_apis/git/repositories/{TEST_REPO_ID}/items/src/main.py",
        size=1024,
    )
    return item


@pytest.fixture
def sample_api_file_item_tree():
    """Create a mock file item API response for a directory (tree)."""
    item = SimpleNamespace(
        path="/src",
        git_object_type="tree",
        object_id="tree123def456",
        commit_id="commit789",
        url=f"{TEST_ORG_URL}/_apis/git/repositories/{TEST_REPO_ID}/items/src",
        size=None,
    )
    return item


@pytest.fixture
def sample_api_file_list(sample_api_file_item_tree, sample_api_file_item_blob):
    """Create a list of file items mimicking a directory listing.

    Includes the scope path entry (directory itself) plus child items,
    matching the real Azure DevOps API behavior where the first item
    returned is the queried directory itself.
    """
    root_entry = SimpleNamespace(
        path="/",
        git_object_type="tree",
        object_id="root000",
        commit_id="commit789",
        url=f"{TEST_ORG_URL}/_apis/git/repositories/{TEST_REPO_ID}/items/",
        size=None,
    )
    return [root_entry, sample_api_file_item_tree, sample_api_file_item_blob]


@pytest.fixture
def sample_api_file_content():
    """Create a mock file item API response with content included.

    Mimics the response from ``git_client.get_item()`` when called
    with ``include_content=True``.
    """
    item = SimpleNamespace(
        path="/README.md",
        git_object_type="blob",
        object_id="readme123",
        commit_id="commit456",
        url=f"{TEST_ORG_URL}/_apis/git/repositories/{TEST_REPO_ID}/items/README.md",
        size=42,
        content="# Test Repository\n\nThis is a test README file.\n",
    )
    return item
