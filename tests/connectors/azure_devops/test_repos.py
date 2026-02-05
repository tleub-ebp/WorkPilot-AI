"""Unit tests for AzureReposClient repository operations.

Tests the repository client lifecycle including:
- Listing repositories (success, empty result, API error)
- Getting a single repository (success, not found, API error)
- Listing files (success with scope filtering, empty, with branch)
- Getting file content (success, file not found, no content, with branch)
- AzureDevOpsError passthrough for all operations
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.connectors.azure_devops.exceptions import (
    APIError,
    AuthenticationError,
    RepositoryNotFoundError,
)
from src.connectors.azure_devops.models import FileItem, Repository

TEST_PROJECT = "TestProject"
TEST_REPO_ID = "abc12345-def6-7890-abcd-ef1234567890"
TEST_REPO_NAME = "test-repository"


# ── list_repositories tests ────────────────────────────────────────


class TestListRepositories:
    """Tests for AzureReposClient.list_repositories()."""

    def test_returns_repository_list(
        self, repos_client, mock_git_client, sample_api_repo_list
    ):
        """list_repositories() maps API responses to Repository models."""
        mock_git_client.get_repositories.return_value = (
            sample_api_repo_list
        )

        result = repos_client.list_repositories(TEST_PROJECT)

        assert len(result) == 2
        assert all(isinstance(repo, Repository) for repo in result)
        mock_git_client.get_repositories.assert_called_once_with(
            project=TEST_PROJECT
        )

    def test_returns_correct_repository_data(
        self, repos_client, mock_git_client, sample_api_repo
    ):
        """list_repositories() correctly maps repository fields."""
        mock_git_client.get_repositories.return_value = [sample_api_repo]

        result = repos_client.list_repositories(TEST_PROJECT)

        repo = result[0]
        assert repo.name == TEST_REPO_NAME
        assert repo.project == TEST_PROJECT
        assert repo.default_branch == "refs/heads/main"

    def test_returns_empty_list_when_no_repos(
        self, repos_client, mock_git_client
    ):
        """list_repositories() returns an empty list for an empty project."""
        mock_git_client.get_repositories.return_value = []

        result = repos_client.list_repositories(TEST_PROJECT)

        assert result == []

    def test_returns_empty_list_when_none_response(
        self, repos_client, mock_git_client
    ):
        """list_repositories() returns an empty list when the API returns None."""
        mock_git_client.get_repositories.return_value = None

        result = repos_client.list_repositories(TEST_PROJECT)

        assert result == []

    def test_api_failure_raises_api_error(
        self, repos_client, mock_git_client
    ):
        """list_repositories() wraps unexpected errors as APIError."""
        mock_git_client.get_repositories.side_effect = RuntimeError(
            "Connection reset by peer"
        )

        with pytest.raises(APIError, match="Failed to list repositories"):
            repos_client.list_repositories(TEST_PROJECT)

    def test_azure_devops_error_passthrough(
        self, repos_client, mock_git_client
    ):
        """list_repositories() re-raises AzureDevOpsError subclasses directly."""
        mock_git_client.get_repositories.side_effect = (
            AuthenticationError("Token expired")
        )

        with pytest.raises(AuthenticationError, match="Token expired"):
            repos_client.list_repositories(TEST_PROJECT)


# ── get_repository tests ───────────────────────────────────────────


class TestGetRepository:
    """Tests for AzureReposClient.get_repository()."""

    def test_returns_repository(
        self, repos_client, mock_git_client, sample_api_repo
    ):
        """get_repository() returns a Repository model for a valid repo."""
        mock_git_client.get_repository.return_value = sample_api_repo

        result = repos_client.get_repository(TEST_PROJECT, TEST_REPO_ID)

        assert isinstance(result, Repository)
        assert result.name == TEST_REPO_NAME
        assert result.project == TEST_PROJECT
        mock_git_client.get_repository.assert_called_once_with(
            repository_id=TEST_REPO_ID,
            project=TEST_PROJECT,
        )

    def test_404_raises_repository_not_found(
        self, repos_client, mock_git_client
    ):
        """get_repository() maps 404 errors to RepositoryNotFoundError."""
        mock_git_client.get_repository.side_effect = Exception(
            "HTTP 404 Not Found"
        )

        with pytest.raises(RepositoryNotFoundError) as exc_info:
            repos_client.get_repository(TEST_PROJECT, "nonexistent-repo")

        assert exc_info.value.repository_id == "nonexistent-repo"
        assert exc_info.value.project == TEST_PROJECT

    def test_not_found_text_raises_repository_not_found(
        self, repos_client, mock_git_client
    ):
        """get_repository() maps 'not found' text to RepositoryNotFoundError."""
        mock_git_client.get_repository.side_effect = Exception(
            "Resource not found on server"
        )

        with pytest.raises(RepositoryNotFoundError):
            repos_client.get_repository(TEST_PROJECT, "missing-repo")

    def test_api_failure_raises_api_error(
        self, repos_client, mock_git_client
    ):
        """get_repository() wraps unexpected errors as APIError."""
        mock_git_client.get_repository.side_effect = RuntimeError(
            "Internal server error"
        )

        with pytest.raises(APIError, match="Failed to get repository"):
            repos_client.get_repository(TEST_PROJECT, TEST_REPO_ID)

    def test_azure_devops_error_passthrough(
        self, repos_client, mock_git_client
    ):
        """get_repository() re-raises AzureDevOpsError subclasses directly."""
        mock_git_client.get_repository.side_effect = (
            AuthenticationError("Invalid credentials")
        )

        with pytest.raises(
            AuthenticationError, match="Invalid credentials"
        ):
            repos_client.get_repository(TEST_PROJECT, TEST_REPO_ID)


# ── list_files tests ───────────────────────────────────────────────


class TestListFiles:
    """Tests for AzureReposClient.list_files()."""

    def test_returns_file_items(
        self, repos_client, mock_git_client, sample_api_file_list
    ):
        """list_files() maps API items to FileItem models, filtering scope path."""
        mock_git_client.get_items.return_value = sample_api_file_list

        result = repos_client.list_files(TEST_PROJECT, TEST_REPO_ID)

        # sample_api_file_list has 3 items: root ("/"), tree ("/src"),
        # and blob ("/src/main.py"). Root is filtered out as scope path.
        assert len(result) == 2
        assert all(isinstance(item, FileItem) for item in result)

    def test_filters_out_scope_path(
        self, repos_client, mock_git_client, sample_api_file_list
    ):
        """list_files() excludes the scope path itself from results."""
        mock_git_client.get_items.return_value = sample_api_file_list

        result = repos_client.list_files(TEST_PROJECT, TEST_REPO_ID, path="/")

        paths = [item.path for item in result]
        assert "/" not in paths
        assert "/src" in paths
        assert "/src/main.py" in paths

    def test_identifies_folders_and_files(
        self, repos_client, mock_git_client, sample_api_file_list
    ):
        """list_files() correctly distinguishes folders from files."""
        mock_git_client.get_items.return_value = sample_api_file_list

        result = repos_client.list_files(TEST_PROJECT, TEST_REPO_ID)

        folders = [item for item in result if item.is_folder]
        files = [item for item in result if not item.is_folder]
        assert len(folders) == 1
        assert folders[0].path == "/src"
        assert len(files) == 1
        assert files[0].path == "/src/main.py"

    def test_returns_empty_list_when_no_items(
        self, repos_client, mock_git_client
    ):
        """list_files() returns an empty list for an empty directory."""
        mock_git_client.get_items.return_value = []

        result = repos_client.list_files(TEST_PROJECT, TEST_REPO_ID)

        assert result == []

    def test_returns_empty_list_when_none_response(
        self, repos_client, mock_git_client
    ):
        """list_files() returns an empty list when the API returns None."""
        mock_git_client.get_items.return_value = None

        result = repos_client.list_files(TEST_PROJECT, TEST_REPO_ID)

        assert result == []

    def test_passes_branch_as_version_descriptor(
        self, repos_client, mock_git_client
    ):
        """list_files() passes a GitVersionDescriptor when branch is specified."""
        mock_git_client.get_items.return_value = []

        repos_client.list_files(
            TEST_PROJECT, TEST_REPO_ID, branch="develop"
        )

        call_kwargs = mock_git_client.get_items.call_args.kwargs
        descriptor = call_kwargs["version_descriptor"]
        assert descriptor.version == "develop"
        assert descriptor.version_type == "branch"

    def test_no_version_descriptor_without_branch(
        self, repos_client, mock_git_client
    ):
        """list_files() passes None version_descriptor when no branch given."""
        mock_git_client.get_items.return_value = []

        repos_client.list_files(TEST_PROJECT, TEST_REPO_ID)

        call_kwargs = mock_git_client.get_items.call_args.kwargs
        assert call_kwargs["version_descriptor"] is None

    def test_passes_scope_path_and_recursion_level(
        self, repos_client, mock_git_client
    ):
        """list_files() passes the correct scope_path and recursion_level."""
        mock_git_client.get_items.return_value = []

        repos_client.list_files(
            TEST_PROJECT, TEST_REPO_ID, path="/src/components"
        )

        mock_git_client.get_items.assert_called_once_with(
            repository_id=TEST_REPO_ID,
            project=TEST_PROJECT,
            scope_path="/src/components",
            recursion_level="oneLevel",
            version_descriptor=None,
        )

    def test_404_raises_repository_not_found(
        self, repos_client, mock_git_client
    ):
        """list_files() maps 404 errors to RepositoryNotFoundError."""
        mock_git_client.get_items.side_effect = Exception(
            "HTTP 404 Not Found"
        )

        with pytest.raises(RepositoryNotFoundError) as exc_info:
            repos_client.list_files(TEST_PROJECT, TEST_REPO_ID)

        assert exc_info.value.repository_id == TEST_REPO_ID

    def test_api_failure_raises_api_error(
        self, repos_client, mock_git_client
    ):
        """list_files() wraps unexpected errors as APIError."""
        mock_git_client.get_items.side_effect = RuntimeError(
            "Timeout exceeded"
        )

        with pytest.raises(APIError, match="Failed to list files"):
            repos_client.list_files(TEST_PROJECT, TEST_REPO_ID)

    def test_azure_devops_error_passthrough(
        self, repos_client, mock_git_client
    ):
        """list_files() re-raises AzureDevOpsError subclasses directly."""
        mock_git_client.get_items.side_effect = AuthenticationError(
            "Session expired"
        )

        with pytest.raises(AuthenticationError, match="Session expired"):
            repos_client.list_files(TEST_PROJECT, TEST_REPO_ID)

    def test_custom_scope_path_filters_correctly(
        self, repos_client, mock_git_client
    ):
        """list_files() filters out the scope path when path is not root."""
        scope_entry = SimpleNamespace(
            path="/src",
            git_object_type="tree",
            object_id="scope000",
            commit_id="commit789",
            url="http://example.com",
            size=None,
        )
        child_entry = SimpleNamespace(
            path="/src/main.py",
            git_object_type="blob",
            object_id="child123",
            commit_id="commit789",
            url="http://example.com",
            size=512,
        )
        mock_git_client.get_items.return_value = [scope_entry, child_entry]

        result = repos_client.list_files(
            TEST_PROJECT, TEST_REPO_ID, path="/src"
        )

        assert len(result) == 1
        assert result[0].path == "/src/main.py"


# ── get_file_content tests ─────────────────────────────────────────


class TestGetFileContent:
    """Tests for AzureReposClient.get_file_content()."""

    def test_returns_file_content(
        self, repos_client, mock_git_client, sample_api_file_content
    ):
        """get_file_content() returns the content string from the API."""
        mock_git_client.get_item.return_value = sample_api_file_content

        result = repos_client.get_file_content(
            TEST_PROJECT, TEST_REPO_ID, "/README.md"
        )

        assert result == "# Test Repository\n\nThis is a test README file.\n"

    def test_calls_api_with_include_content(
        self, repos_client, mock_git_client, sample_api_file_content
    ):
        """get_file_content() passes include_content=True to the API."""
        mock_git_client.get_item.return_value = sample_api_file_content

        repos_client.get_file_content(
            TEST_PROJECT, TEST_REPO_ID, "/README.md"
        )

        mock_git_client.get_item.assert_called_once_with(
            repository_id=TEST_REPO_ID,
            path="/README.md",
            project=TEST_PROJECT,
            version_descriptor=None,
            include_content=True,
        )

    def test_passes_branch_as_version_descriptor(
        self, repos_client, mock_git_client, sample_api_file_content
    ):
        """get_file_content() passes a GitVersionDescriptor for the branch."""
        mock_git_client.get_item.return_value = sample_api_file_content

        repos_client.get_file_content(
            TEST_PROJECT, TEST_REPO_ID, "/README.md", branch="feature/x"
        )

        call_kwargs = mock_git_client.get_item.call_args.kwargs
        descriptor = call_kwargs["version_descriptor"]
        assert descriptor.version == "feature/x"
        assert descriptor.version_type == "branch"

    def test_no_version_descriptor_without_branch(
        self, repos_client, mock_git_client, sample_api_file_content
    ):
        """get_file_content() passes None version_descriptor without branch."""
        mock_git_client.get_item.return_value = sample_api_file_content

        repos_client.get_file_content(
            TEST_PROJECT, TEST_REPO_ID, "/README.md"
        )

        call_kwargs = mock_git_client.get_item.call_args.kwargs
        assert call_kwargs["version_descriptor"] is None

    def test_file_not_found_raises_file_not_found_error(
        self, repos_client, mock_git_client
    ):
        """get_file_content() raises FileNotFoundError for missing files."""
        mock_git_client.get_item.side_effect = Exception(
            "HTTP 404 Not Found - item not found"
        )

        with pytest.raises(FileNotFoundError, match="not found"):
            repos_client.get_file_content(
                TEST_PROJECT, TEST_REPO_ID, "/nonexistent.py"
            )

    def test_repository_not_found_in_error_raises_repo_error(
        self, repos_client, mock_git_client
    ):
        """get_file_content() maps 'repository not found' to RepositoryNotFoundError."""
        mock_git_client.get_item.side_effect = Exception(
            "HTTP 404 Repository not found"
        )

        with pytest.raises(RepositoryNotFoundError) as exc_info:
            repos_client.get_file_content(
                TEST_PROJECT, TEST_REPO_ID, "/file.py"
            )

        assert exc_info.value.repository_id == TEST_REPO_ID

    def test_no_content_raises_file_not_found_error(
        self, repos_client, mock_git_client
    ):
        """get_file_content() raises FileNotFoundError when content is None."""
        item_no_content = SimpleNamespace(
            path="/empty.txt",
            git_object_type="blob",
            object_id="empty123",
            commit_id="commit456",
            url="http://example.com",
            size=0,
            content=None,
        )
        mock_git_client.get_item.return_value = item_no_content

        with pytest.raises(
            FileNotFoundError, match="returned no content"
        ):
            repos_client.get_file_content(
                TEST_PROJECT, TEST_REPO_ID, "/empty.txt"
            )

    def test_missing_content_attribute_raises_file_not_found_error(
        self, repos_client, mock_git_client
    ):
        """get_file_content() raises FileNotFoundError when content attr is missing."""
        item_no_attr = MagicMock(spec=[])  # No attributes
        mock_git_client.get_item.return_value = item_no_attr

        with pytest.raises(
            FileNotFoundError, match="returned no content"
        ):
            repos_client.get_file_content(
                TEST_PROJECT, TEST_REPO_ID, "/missing-attr.txt"
            )

    def test_api_failure_raises_api_error(
        self, repos_client, mock_git_client
    ):
        """get_file_content() wraps unexpected errors as APIError."""
        mock_git_client.get_item.side_effect = RuntimeError(
            "Connection refused"
        )

        with pytest.raises(
            APIError, match="Failed to get file content"
        ):
            repos_client.get_file_content(
                TEST_PROJECT, TEST_REPO_ID, "/file.py"
            )

    def test_azure_devops_error_passthrough(
        self, repos_client, mock_git_client
    ):
        """get_file_content() re-raises AzureDevOpsError subclasses directly."""
        mock_git_client.get_item.side_effect = AuthenticationError(
            "Access denied"
        )

        with pytest.raises(AuthenticationError, match="Access denied"):
            repos_client.get_file_content(
                TEST_PROJECT, TEST_REPO_ID, "/file.py"
            )
