"""End-to-end verification tests for Azure DevOps connector API structure.

Validates that all public modules, classes, methods, exceptions, and models
are importable and have the expected interface. These tests do NOT make real
API calls — they verify the connector's structural contract so that
downstream consumers can rely on a stable public API.

Verification checklist:
  1. AzureDevOpsConnector is importable from src.connectors.azure_devops
  2. Required methods (connect, list_repositories, get_file_content,
     query_work_items) exist and are callable
  3. Repository and WorkItem models are accessible with expected fields
  4. All custom exceptions are defined with correct hierarchy
  5. Base abstract classes are implemented correctly
  6. Factory methods (from_settings, from_env) are present
  7. __all__ exports match actual defined symbols
"""

import inspect
from dataclasses import fields as dataclass_fields
from unittest.mock import MagicMock

import pytest

import sys
import os

from src.config.settings import Settings

# ── 1. Top-level imports ─────────────────────────────────────────────
from src.connectors.azure_devops import (
    APIError,
    AuthenticationError,
    AzureDevOpsClient,
    AzureDevOpsConnector,
    AzureDevOpsError,
    AzureReposClient,
    AzureWorkItemsClient,
    ConfigurationError,
    FileItem,
    RateLimitError,
    Repository,
    RepositoryNotFoundError,
    ResourceNotFoundError,
    WorkItem,
    WorkItemNotFoundError,
)
from src.connectors.base import (
    BaseConnector,
    BaseIntegratedConnector,
    BaseWorkItemTracker,
)

# ── 2. AzureDevOpsConnector method verification ─────────────────────


class TestConnectorMethodsExist:
    """Verify that AzureDevOpsConnector exposes all required public methods."""

    def test_connect_method_exists(self):
        """AzureDevOpsConnector has a connect() method."""
        assert hasattr(AzureDevOpsConnector, "connect")
        assert callable(AzureDevOpsConnector.connect)

    def test_list_repositories_method_exists(self):
        """AzureDevOpsConnector has a list_repositories() method."""
        assert hasattr(AzureDevOpsConnector, "list_repositories")
        assert callable(AzureDevOpsConnector.list_repositories)

    def test_get_file_content_method_exists(self):
        """AzureDevOpsConnector has a get_file_content() method."""
        assert hasattr(AzureDevOpsConnector, "get_file_content")
        assert callable(AzureDevOpsConnector.get_file_content)

    def test_query_method_exists(self):
        """AzureDevOpsConnector has a query() method (WIQL query interface)."""
        assert hasattr(AzureDevOpsConnector, "query")
        assert callable(AzureDevOpsConnector.query)

    def test_get_item_method_exists(self):
        """AzureDevOpsConnector has a get_item() method."""
        assert hasattr(AzureDevOpsConnector, "get_item")
        assert callable(AzureDevOpsConnector.get_item)

    def test_get_repository_method_exists(self):
        """AzureDevOpsConnector has a get_repository() method."""
        assert hasattr(AzureDevOpsConnector, "get_repository")
        assert callable(AzureDevOpsConnector.get_repository)

    def test_list_files_method_exists(self):
        """AzureDevOpsConnector has a list_files() method."""
        assert hasattr(AzureDevOpsConnector, "list_files")
        assert callable(AzureDevOpsConnector.list_files)

    def test_list_backlog_items_method_exists(self):
        """AzureDevOpsConnector has a list_backlog_items() method."""
        assert hasattr(AzureDevOpsConnector, "list_backlog_items")
        assert callable(AzureDevOpsConnector.list_backlog_items)

    def test_get_connection_info_method_exists(self):
        """AzureDevOpsConnector has a get_connection_info() method."""
        assert hasattr(AzureDevOpsConnector, "get_connection_info")
        assert callable(AzureDevOpsConnector.get_connection_info)

    def test_is_connected_property_exists(self):
        """AzureDevOpsConnector has an is_connected property."""
        assert hasattr(AzureDevOpsConnector, "is_connected")

    def test_disconnect_method_exists(self):
        """AzureDevOpsConnector has a disconnect() method."""
        assert hasattr(AzureDevOpsConnector, "disconnect")
        assert callable(AzureDevOpsConnector.disconnect)

    def test_from_settings_factory_exists(self):
        """AzureDevOpsConnector has a from_settings() classmethod."""
        assert hasattr(AzureDevOpsConnector, "from_settings")
        assert callable(AzureDevOpsConnector.from_settings)

    def test_from_env_factory_exists(self):
        """AzureDevOpsConnector has a from_env() classmethod."""
        assert hasattr(AzureDevOpsConnector, "from_env")
        assert callable(AzureDevOpsConnector.from_env)


# ── 3. AzureWorkItemsClient query_work_items verification ────────────


class TestWorkItemsClientMethods:
    """Verify that AzureWorkItemsClient has the query_work_items method."""

    def test_query_work_items_method_exists(self):
        """AzureWorkItemsClient has a query_work_items() method."""
        assert hasattr(AzureWorkItemsClient, "query_work_items")
        assert callable(AzureWorkItemsClient.query_work_items)

    def test_get_work_item_method_exists(self):
        """AzureWorkItemsClient has a get_work_item() method."""
        assert hasattr(AzureWorkItemsClient, "get_work_item")
        assert callable(AzureWorkItemsClient.get_work_item)

    def test_list_backlog_items_method_exists(self):
        """AzureWorkItemsClient has a list_backlog_items() method."""
        assert hasattr(AzureWorkItemsClient, "list_backlog_items")
        assert callable(AzureWorkItemsClient.list_backlog_items)


# ── 4. Repository model verification ────────────────────────────────


class TestRepositoryModel:
    """Verify Repository model fields and factory method."""

    def test_repository_is_dataclass(self):
        """Repository is a proper dataclass."""
        assert hasattr(Repository, "__dataclass_fields__")

    def test_repository_has_required_fields(self):
        """Repository dataclass has id, name, project fields."""
        field_names = {f.name for f in dataclass_fields(Repository)}
        assert "id" in field_names
        assert "name" in field_names
        assert "project" in field_names

    def test_repository_has_optional_fields(self):
        """Repository dataclass has default_branch and web_url optional fields."""
        field_names = {f.name for f in dataclass_fields(Repository)}
        assert "default_branch" in field_names
        assert "web_url" in field_names

    def test_repository_from_api_response_exists(self):
        """Repository has a from_api_response classmethod."""
        assert hasattr(Repository, "from_api_response")
        assert callable(Repository.from_api_response)

    def test_repository_can_be_instantiated(self):
        """Repository can be created with required fields."""
        repo = Repository(id="123", name="test-repo", project="TestProject")
        assert repo.id == "123"
        assert repo.name == "test-repo"
        assert repo.project == "TestProject"
        assert repo.default_branch is None
        assert repo.web_url is None


# ── 5. WorkItem model verification ──────────────────────────────────


class TestWorkItemModel:
    """Verify WorkItem model fields and factory method."""

    def test_work_item_is_dataclass(self):
        """WorkItem is a proper dataclass."""
        assert hasattr(WorkItem, "__dataclass_fields__")

    def test_work_item_has_required_fields(self):
        """WorkItem has id, title, state, work_item_type required fields."""
        field_names = {f.name for f in dataclass_fields(WorkItem)}
        assert "id" in field_names
        assert "title" in field_names
        assert "state" in field_names
        assert "work_item_type" in field_names

    def test_work_item_has_optional_fields(self):
        """WorkItem has all expected optional fields."""
        field_names = {f.name for f in dataclass_fields(WorkItem)}
        expected_optional = {
            "assigned_to",
            "description",
            "tags",
            "created_date",
            "area_path",
            "iteration_path",
            "priority",
            "url",
        }
        assert expected_optional.issubset(field_names)

    def test_work_item_from_api_response_exists(self):
        """WorkItem has a from_api_response classmethod."""
        assert hasattr(WorkItem, "from_api_response")
        assert callable(WorkItem.from_api_response)

    def test_work_item_can_be_instantiated(self):
        """WorkItem can be created with required fields."""
        item = WorkItem(
            id=42,
            title="Test item",
            state="Active",
            work_item_type="Bug",
        )
        assert item.id == 42
        assert item.title == "Test item"
        assert item.state == "Active"
        assert item.work_item_type == "Bug"
        assert item.assigned_to is None
        assert item.tags == []


# ── 6. FileItem model verification ──────────────────────────────────


class TestFileItemModel:
    """Verify FileItem model fields and factory method."""

    def test_file_item_is_dataclass(self):
        """FileItem is a proper dataclass."""
        assert hasattr(FileItem, "__dataclass_fields__")

    def test_file_item_has_required_fields(self):
        """FileItem has path, name, is_folder required fields."""
        field_names = {f.name for f in dataclass_fields(FileItem)}
        assert "path" in field_names
        assert "name" in field_names
        assert "is_folder" in field_names

    def test_file_item_from_api_response_exists(self):
        """FileItem has a from_api_response classmethod."""
        assert hasattr(FileItem, "from_api_response")
        assert callable(FileItem.from_api_response)

    def test_file_item_can_be_instantiated(self):
        """FileItem can be created with required fields."""
        item = FileItem(path="/src/main.py", name="main.py", is_folder=False)
        assert item.path == "/src/main.py"
        assert item.name == "main.py"
        assert item.is_folder is False


# ── 7. Exception hierarchy verification ─────────────────────────────


class TestExceptionHierarchy:
    """Verify all custom exceptions are defined and inherit correctly."""

    def test_azure_devops_error_is_exception(self):
        """AzureDevOpsError inherits from Exception."""
        assert issubclass(AzureDevOpsError, Exception)

    def test_authentication_error_hierarchy(self):
        """AuthenticationError inherits from AzureDevOpsError."""
        assert issubclass(AuthenticationError, AzureDevOpsError)

    def test_configuration_error_hierarchy(self):
        """ConfigurationError inherits from AzureDevOpsError."""
        assert issubclass(ConfigurationError, AzureDevOpsError)

    def test_resource_not_found_error_hierarchy(self):
        """ResourceNotFoundError inherits from AzureDevOpsError."""
        assert issubclass(ResourceNotFoundError, AzureDevOpsError)

    def test_repository_not_found_error_hierarchy(self):
        """RepositoryNotFoundError inherits from ResourceNotFoundError."""
        assert issubclass(RepositoryNotFoundError, ResourceNotFoundError)
        assert issubclass(RepositoryNotFoundError, AzureDevOpsError)

    def test_work_item_not_found_error_hierarchy(self):
        """WorkItemNotFoundError inherits from ResourceNotFoundError."""
        assert issubclass(WorkItemNotFoundError, ResourceNotFoundError)
        assert issubclass(WorkItemNotFoundError, AzureDevOpsError)

    def test_api_error_hierarchy(self):
        """APIError inherits from AzureDevOpsError."""
        assert issubclass(APIError, AzureDevOpsError)

    def test_rate_limit_error_hierarchy(self):
        """RateLimitError inherits from AzureDevOpsError."""
        assert issubclass(RateLimitError, AzureDevOpsError)

    def test_all_exceptions_are_catchable_as_base(self):
        """All custom exceptions can be caught via AzureDevOpsError."""
        exception_classes = [
            AuthenticationError,
            ConfigurationError,
            ResourceNotFoundError,
            RepositoryNotFoundError,
            WorkItemNotFoundError,
            APIError,
            RateLimitError,
        ]
        for exc_cls in exception_classes:
            assert issubclass(exc_cls, AzureDevOpsError), (
                f"{exc_cls.__name__} is not a subclass of AzureDevOpsError"
            )

    def test_exceptions_are_instantiable(self):
        """All custom exceptions can be instantiated with a message."""
        assert AzureDevOpsError("test").message == "test"
        assert AuthenticationError("auth fail").message == "auth fail"
        assert ConfigurationError("config fail").message == "config fail"

    def test_resource_not_found_has_resource_id(self):
        """ResourceNotFoundError stores a resource_id attribute."""
        exc = ResourceNotFoundError("not found", resource_id="res-123")
        assert exc.resource_id == "res-123"

    def test_repository_not_found_has_context(self):
        """RepositoryNotFoundError stores repository_id and project."""
        exc = RepositoryNotFoundError(repository_id="my-repo", project="MyProject")
        assert exc.repository_id == "my-repo"
        assert exc.project == "MyProject"
        assert "my-repo" in str(exc)
        assert "MyProject" in str(exc)

    def test_work_item_not_found_has_context(self):
        """WorkItemNotFoundError stores work_item_id and project."""
        exc = WorkItemNotFoundError(work_item_id=42, project="MyProject")
        assert exc.work_item_id == 42
        assert exc.project == "MyProject"
        assert "42" in str(exc)

    def test_api_error_has_status_code(self):
        """APIError stores a status_code attribute."""
        exc = APIError("server error", status_code=500)
        assert exc.status_code == 500
        assert "500" in str(exc)

    def test_rate_limit_error_has_retry_after(self):
        """RateLimitError stores a retry_after attribute."""
        exc = RateLimitError("rate limited", retry_after=30.0)
        assert exc.retry_after == 30
        assert "30.0" in str(exc)


# ── 8. Base class contract verification ──────────────────────────────


class TestBaseClassContract:
    """Verify AzureDevOpsConnector implements the abstract base classes."""

    def test_connector_inherits_base_integrated(self):
        """AzureDevOpsConnector inherits from BaseIntegratedConnector."""
        assert issubclass(AzureDevOpsConnector, BaseIntegratedConnector)

    def test_connector_inherits_base_connector(self):
        """AzureDevOpsConnector inherits from BaseConnector."""
        assert issubclass(AzureDevOpsConnector, BaseConnector)

    def test_connector_inherits_base_work_item_tracker(self):
        """AzureDevOpsConnector inherits from BaseWorkItemTracker."""
        assert issubclass(AzureDevOpsConnector, BaseWorkItemTracker)

    def test_connector_is_not_abstract(self):
        """AzureDevOpsConnector is concrete — all abstract methods implemented."""
        # If it were still abstract, instantiation would raise TypeError
        settings = Settings(
            pat="test-pat",
            organization_url="https://dev.azure.com/test",
        )
        connector = AzureDevOpsConnector(settings)
        assert connector is not None


# ── 9. __all__ exports verification ──────────────────────────────────


class TestModuleExports:
    """Verify __all__ exports match actual defined symbols."""

    def test_all_exports_are_importable(self):
        """Every symbol in __all__ is importable from the package."""
        import src.connectors.azure_devops as pkg

        for name in pkg.__all__:
            assert hasattr(pkg, name), (
                f"'{name}' is listed in __all__ but not importable"
            )

    def test_expected_exports_in_all(self):
        """__all__ contains all expected public symbols."""
        import src.connectors.azure_devops as pkg

        expected = {
            "AzureDevOpsConnector",
            "AzureDevOpsClient",
            "AzureReposClient",
            "AzureWorkItemsClient",
            "Repository",
            "WorkItem",
            "FileItem",
            "AzureDevOpsError",
            "AuthenticationError",
            "ConfigurationError",
            "ResourceNotFoundError",
            "RepositoryNotFoundError",
            "WorkItemNotFoundError",
            "APIError",
            "RateLimitError",
        }
        actual = set(pkg.__all__)
        missing = expected - actual
        assert not missing, f"Missing from __all__: {missing}"


# ── 10. Settings integration verification ────────────────────────────


class TestSettingsIntegration:
    """Verify Settings is properly integrated with the connector."""

    def test_settings_from_config_module(self):
        """Settings is importable from src.config.settings."""
        assert Settings is not None
        assert hasattr(Settings, "from_env")
        assert hasattr(Settings, "validate")

    def test_settings_dataclass_fields(self):
        """Settings has pat, organization_url, and project fields."""
        field_names = {f.name for f in dataclass_fields(Settings)}
        assert "pat" in field_names
        assert "organization_url" in field_names
        assert "project" in field_names

    def test_connector_accepts_settings(self):
        """AzureDevOpsConnector constructor accepts a Settings instance."""
        settings = Settings(
            pat="test-token",
            organization_url="https://dev.azure.com/test-org",
            project="TestProject",
        )
        connector = AzureDevOpsConnector(settings)
        assert connector is not None


# ── 11. Method signature verification ────────────────────────────────


class TestMethodSignatures:
    """Verify method signatures match the expected interface contract."""

    def test_connect_signature(self):
        """connect() takes no arguments and returns None."""
        sig = inspect.signature(AzureDevOpsConnector.connect)
        params = list(sig.parameters.keys())
        assert params == ["self"]

    def test_list_repositories_signature(self):
        """list_repositories() takes project argument."""
        sig = inspect.signature(AzureDevOpsConnector.list_repositories)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "project" in params

    def test_get_file_content_signature(self):
        """get_file_content() takes project, repository_id, file_path, branch."""
        sig = inspect.signature(AzureDevOpsConnector.get_file_content)
        params = list(sig.parameters.keys())
        assert "project" in params
        assert "repository_id" in params
        assert "file_path" in params
        assert "branch" in params

    def test_query_signature(self):
        """query() takes project, query, and optional max_items."""
        sig = inspect.signature(AzureDevOpsConnector.query)
        params = list(sig.parameters.keys())
        assert "project" in params
        assert "query" in params
        assert "max_items" in params

    def test_query_work_items_signature(self):
        """AzureWorkItemsClient.query_work_items() takes project, query, max_items."""
        sig = inspect.signature(AzureWorkItemsClient.query_work_items)
        params = list(sig.parameters.keys())
        assert "project" in params
        assert "query" in params
        assert "max_items" in params
