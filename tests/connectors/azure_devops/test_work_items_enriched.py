"""Unit tests for enriched Azure DevOps Boards operations (Feature 4.2).

Tests the new write operations on AzureWorkItemsClient including:
- Creating work items (with various field combinations)
- Updating work items (field changes, state transitions, not found)
- Linking work items (related, hierarchy, with comments, not found)
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, call

import pytest

import sys
import os

from src.connectors.azure_devops.exceptions import (
    APIError,
    AuthenticationError,
    WorkItemNotFoundError,
)
from src.connectors.azure_devops.models import WorkItem

TEST_PROJECT = "TestProject"


# ── create_work_item tests ───────────────────────────────────────


class TestCreateWorkItem:
    """Tests for AzureWorkItemsClient.create_work_item()."""

    def test_creates_work_item_with_title_only(
        self, work_items_client, mock_wit_client, sample_api_work_item
    ):
        """create_work_item() creates a work item with just a title."""
        mock_wit_client.create_work_item.return_value = sample_api_work_item

        result = work_items_client.create_work_item(
            TEST_PROJECT, "Task", "My new task"
        )

        assert isinstance(result, WorkItem)
        assert result.id == 42
        mock_wit_client.create_work_item.assert_called_once()

    def test_passes_title_in_patch_document(
        self, work_items_client, mock_wit_client, sample_api_work_item
    ):
        """create_work_item() includes System.Title in the patch document."""
        mock_wit_client.create_work_item.return_value = sample_api_work_item

        work_items_client.create_work_item(TEST_PROJECT, "Bug", "Fix crash")

        call_kwargs = mock_wit_client.create_work_item.call_args.kwargs
        assert call_kwargs["project"] == TEST_PROJECT
        assert call_kwargs["type"] == "Bug"

        doc = call_kwargs["document"]
        title_ops = [op for op in doc if op.path == "/fields/System.Title"]
        assert len(title_ops) == 1
        assert title_ops[0].value == "Fix crash"
        assert title_ops[0].op == "add"

    def test_includes_optional_fields(
        self, work_items_client, mock_wit_client, sample_api_work_item
    ):
        """create_work_item() includes all optional fields in the patch."""
        mock_wit_client.create_work_item.return_value = sample_api_work_item

        work_items_client.create_work_item(
            TEST_PROJECT,
            "User Story",
            "Add feature",
            description="<p>Details here</p>",
            assigned_to="John Doe",
            state="Active",
            priority=2,
            tags=["frontend", "v2"],
            area_path="TestProject\\Web",
            iteration_path="TestProject\\Sprint 1",
        )

        doc = mock_wit_client.create_work_item.call_args.kwargs["document"]
        paths = {op.path: op.value for op in doc}

        assert paths["/fields/System.Description"] == "<p>Details here</p>"
        assert paths["/fields/System.AssignedTo"] == "John Doe"
        assert paths["/fields/System.State"] == "Active"
        assert paths["/fields/Microsoft.VSTS.Common.Priority"] == 2
        assert paths["/fields/System.Tags"] == "frontend; v2"
        assert paths["/fields/System.AreaPath"] == "TestProject\\Web"
        assert paths["/fields/System.IterationPath"] == "TestProject\\Sprint 1"

    def test_includes_additional_fields(
        self, work_items_client, mock_wit_client, sample_api_work_item
    ):
        """create_work_item() includes custom additional fields."""
        mock_wit_client.create_work_item.return_value = sample_api_work_item

        work_items_client.create_work_item(
            TEST_PROJECT,
            "Task",
            "Custom task",
            additional_fields={"Custom.MyField": "my_value"},
        )

        doc = mock_wit_client.create_work_item.call_args.kwargs["document"]
        custom_ops = [op for op in doc if op.path == "/fields/Custom.MyField"]
        assert len(custom_ops) == 1
        assert custom_ops[0].value == "my_value"

    def test_omits_none_optional_fields(
        self, work_items_client, mock_wit_client, sample_api_work_item
    ):
        """create_work_item() does not include fields with None values."""
        mock_wit_client.create_work_item.return_value = sample_api_work_item

        work_items_client.create_work_item(TEST_PROJECT, "Task", "Simple task")

        doc = mock_wit_client.create_work_item.call_args.kwargs["document"]
        # Only System.Title should be in the patch
        assert len(doc) == 1
        assert doc[0].path == "/fields/System.Title"

    def test_api_failure_raises_api_error(
        self, work_items_client, mock_wit_client
    ):
        """create_work_item() wraps unexpected errors as APIError."""
        mock_wit_client.create_work_item.side_effect = RuntimeError("Server error")

        with pytest.raises(APIError, match="Failed to create"):
            work_items_client.create_work_item(TEST_PROJECT, "Task", "Fail")

    def test_azure_devops_error_passthrough(
        self, work_items_client, mock_wit_client
    ):
        """create_work_item() re-raises AzureDevOpsError subclasses."""
        mock_wit_client.create_work_item.side_effect = AuthenticationError(
            "Token expired"
        )

        with pytest.raises(AuthenticationError, match="Token expired"):
            work_items_client.create_work_item(TEST_PROJECT, "Task", "Fail")


# ── update_work_item tests ───────────────────────────────────────


class TestUpdateWorkItem:
    """Tests for AzureWorkItemsClient.update_work_item()."""

    def test_updates_work_item_fields(
        self, work_items_client, mock_wit_client, sample_api_work_item
    ):
        """update_work_item() returns updated WorkItem on success."""
        mock_wit_client.update_work_item.return_value = sample_api_work_item

        result = work_items_client.update_work_item(
            TEST_PROJECT, 42, {"System.State": "Closed"}
        )

        assert isinstance(result, WorkItem)
        assert result.id == 42

    def test_builds_replace_patch_document(
        self, work_items_client, mock_wit_client, sample_api_work_item
    ):
        """update_work_item() uses 'replace' op for field updates."""
        mock_wit_client.update_work_item.return_value = sample_api_work_item

        work_items_client.update_work_item(
            TEST_PROJECT,
            42,
            {"System.State": "Resolved", "System.Title": "New title"},
        )

        doc = mock_wit_client.update_work_item.call_args.kwargs["document"]
        assert all(op.op == "replace" for op in doc)
        paths = {op.path: op.value for op in doc}
        assert paths["/fields/System.State"] == "Resolved"
        assert paths["/fields/System.Title"] == "New title"

    def test_passes_correct_api_params(
        self, work_items_client, mock_wit_client, sample_api_work_item
    ):
        """update_work_item() passes correct id and project."""
        mock_wit_client.update_work_item.return_value = sample_api_work_item

        work_items_client.update_work_item(
            TEST_PROJECT, 42, {"System.State": "Active"}
        )

        call_kwargs = mock_wit_client.update_work_item.call_args.kwargs
        assert call_kwargs["id"] == 42
        assert call_kwargs["project"] == TEST_PROJECT

    def test_404_raises_work_item_not_found(
        self, work_items_client, mock_wit_client
    ):
        """update_work_item() maps 404 errors to WorkItemNotFoundError."""
        mock_wit_client.update_work_item.side_effect = Exception("HTTP 404 Not Found")

        with pytest.raises(WorkItemNotFoundError) as exc_info:
            work_items_client.update_work_item(
                TEST_PROJECT, 999, {"System.State": "Closed"}
            )

        assert exc_info.value.work_item_id == 999

    def test_api_failure_raises_api_error(
        self, work_items_client, mock_wit_client
    ):
        """update_work_item() wraps unexpected errors as APIError."""
        mock_wit_client.update_work_item.side_effect = RuntimeError("Timeout")

        with pytest.raises(APIError, match="Failed to update work item 42"):
            work_items_client.update_work_item(
                TEST_PROJECT, 42, {"System.State": "Active"}
            )

    def test_azure_devops_error_passthrough(
        self, work_items_client, mock_wit_client
    ):
        """update_work_item() re-raises AzureDevOpsError subclasses."""
        mock_wit_client.update_work_item.side_effect = AuthenticationError(
            "Access denied"
        )

        with pytest.raises(AuthenticationError, match="Access denied"):
            work_items_client.update_work_item(
                TEST_PROJECT, 42, {"System.State": "Active"}
            )


# ── link_work_items tests ────────────────────────────────────────


class TestLinkWorkItems:
    """Tests for AzureWorkItemsClient.link_work_items()."""

    def test_links_work_items_with_default_type(
        self, work_items_client, mock_wit_client, sample_api_work_item
    ):
        """link_work_items() creates a Related link by default."""
        mock_wit_client.update_work_item.return_value = sample_api_work_item

        result = work_items_client.link_work_items(TEST_PROJECT, 42, 55)

        assert isinstance(result, WorkItem)
        assert result.id == 42

    def test_builds_relation_patch_document(
        self, work_items_client, mock_wit_client, sample_api_work_item
    ):
        """link_work_items() builds correct relation patch."""
        mock_wit_client.update_work_item.return_value = sample_api_work_item

        work_items_client.link_work_items(TEST_PROJECT, 42, 55)

        doc = mock_wit_client.update_work_item.call_args.kwargs["document"]
        assert len(doc) == 1
        op = doc[0]
        assert op.op == "add"
        assert op.path == "/relations/-"
        assert op.value["rel"] == "System.LinkTypes.Related"
        assert "55" in op.value["url"]

    def test_uses_custom_link_type(
        self, work_items_client, mock_wit_client, sample_api_work_item
    ):
        """link_work_items() supports custom link types."""
        mock_wit_client.update_work_item.return_value = sample_api_work_item

        work_items_client.link_work_items(
            TEST_PROJECT,
            42,
            55,
            link_type="System.LinkTypes.Hierarchy-Forward",
        )

        doc = mock_wit_client.update_work_item.call_args.kwargs["document"]
        assert doc[0].value["rel"] == "System.LinkTypes.Hierarchy-Forward"

    def test_includes_comment(
        self, work_items_client, mock_wit_client, sample_api_work_item
    ):
        """link_work_items() includes comment in relation attributes."""
        mock_wit_client.update_work_item.return_value = sample_api_work_item

        work_items_client.link_work_items(
            TEST_PROJECT, 42, 55, comment="Linked by automation"
        )

        doc = mock_wit_client.update_work_item.call_args.kwargs["document"]
        assert doc[0].value["attributes"]["comment"] == "Linked by automation"

    def test_no_comment_attribute_when_none(
        self, work_items_client, mock_wit_client, sample_api_work_item
    ):
        """link_work_items() omits attributes when no comment provided."""
        mock_wit_client.update_work_item.return_value = sample_api_work_item

        work_items_client.link_work_items(TEST_PROJECT, 42, 55)

        doc = mock_wit_client.update_work_item.call_args.kwargs["document"]
        assert "attributes" not in doc[0].value

    def test_404_raises_work_item_not_found(
        self, work_items_client, mock_wit_client
    ):
        """link_work_items() maps 404 errors to WorkItemNotFoundError."""
        mock_wit_client.update_work_item.side_effect = Exception("404 Not Found")

        with pytest.raises(WorkItemNotFoundError) as exc_info:
            work_items_client.link_work_items(TEST_PROJECT, 42, 55)

        assert exc_info.value.work_item_id == 42

    def test_api_failure_raises_api_error(
        self, work_items_client, mock_wit_client
    ):
        """link_work_items() wraps unexpected errors as APIError."""
        mock_wit_client.update_work_item.side_effect = RuntimeError("Timeout")

        with pytest.raises(APIError, match="Failed to link work items"):
            work_items_client.link_work_items(TEST_PROJECT, 42, 55)

    def test_azure_devops_error_passthrough(
        self, work_items_client, mock_wit_client
    ):
        """link_work_items() re-raises AzureDevOpsError subclasses."""
        mock_wit_client.update_work_item.side_effect = AuthenticationError(
            "Token expired"
        )

        with pytest.raises(AuthenticationError, match="Token expired"):
            work_items_client.link_work_items(TEST_PROJECT, 42, 55)
