"""Work item operations for the Azure DevOps connector.

Provides methods for querying work items using WIQL, retrieving work item
details, and listing backlog items from Azure DevOps Boards via the
Azure DevOps SDK.

Work item retrieval follows a two-step process: WIQL queries return only
work item IDs, then a second call fetches the full work item details.

Example:
    >>> from src.connectors.azure_devops.client import AzureDevOpsClient
    >>> from src.connectors.azure_devops.work_items import AzureWorkItemsClient
    >>> client = AzureDevOpsClient.from_env()
    >>> work_items = AzureWorkItemsClient(client)
    >>> items = work_items.list_backlog_items("MyProject")
"""

import logging
from typing import Any, List, Optional

from azure.devops.v7_0.work_item_tracking.models import TeamContext, Wiql

from src.connectors.azure_devops.client import AzureDevOpsClient
from src.connectors.azure_devops.exceptions import (
    APIError,
    AzureDevOpsError,
    WorkItemNotFoundError,
)
from src.connectors.azure_devops.models import WorkItem

logger = logging.getLogger(__name__)

# Default backlog work item types for Azure DevOps
DEFAULT_BACKLOG_TYPES = ["Bug", "User Story", "Task"]


class AzureWorkItemsClient:
    """Client for Azure DevOps work item tracking operations.

    Wraps the Azure DevOps Work Item Tracking API client to provide
    high-level methods for querying work items, retrieving details,
    and listing backlog items. All API responses are mapped to clean
    WorkItem data models.

    Attributes:
        _client: The underlying AzureDevOpsClient providing authenticated
            access to the Work Item Tracking API.

    Example:
        >>> client = AzureDevOpsClient.from_env()
        >>> wit_client = AzureWorkItemsClient(client)
        >>> for item in wit_client.list_backlog_items("MyProject"):
        ...     print(f"{item.work_item_type}: {item.title}")
    """

    def __init__(self, client: AzureDevOpsClient) -> None:
        """Initialize the work item operations client.

        Args:
            client: An authenticated AzureDevOpsClient instance.
                Must have an active connection (connect() must have
                been called).
        """
        self._client = client

    def _get_wit_client(self) -> Any:
        """Get the Work Item Tracking API client from the underlying connection.

        Returns:
            An Azure DevOps WorkItemTrackingClient instance for making
            API calls.

        Raises:
            ConfigurationError: If the client is not connected.
            AuthenticationError: If credentials are invalid.
        """
        return self._client.get_wit_client()

    def query_work_items(
        self,
        project: str,
        query: str,
        max_items: int = 100,
    ) -> List[WorkItem]:
        """Query work items using WIQL (Work Item Query Language).

        Executes a WIQL query to find matching work items. This follows
        a two-step process: the WIQL query returns only work item IDs,
        then a second call fetches the full work item details.

        Uses ``error_policy='omit'`` when fetching work items to
        gracefully skip any deleted or inaccessible items.

        Args:
            project: The project name or identifier.
            query: A WIQL query string (e.g.,
                ``"SELECT [System.Id] FROM WorkItems WHERE ..."``).
            max_items: Maximum number of work items to return.
                Defaults to 100.

        Returns:
            A list of WorkItem objects matching the query. Returns an
            empty list if no items match.

        Raises:
            APIError: If the WIQL query is malformed or the API call
                fails unexpectedly.
        """
        logger.info(
            "Querying work items in project '%s' (max_items=%d).",
            project,
            max_items,
        )

        # Step 1: Execute WIQL query to get work item IDs
        try:
            wit_client = self._get_wit_client()
            wiql = Wiql(query=query)
            team_context = TeamContext(project=project)
            results = wit_client.query_by_wiql(
                wiql=wiql,
                team_context=team_context,
                top=max_items,
            )
        except AzureDevOpsError:
            raise
        except Exception as exc:
            error_msg = str(exc)
            # Check if the error is about a non-existent project
            if "does not exist" in error_msg.lower() and "project" in error_msg.lower():
                raise APIError(
                    f"Failed to execute WIQL query in project '{project}': {exc}\n"
                    f"Note: Ensure you are passing the Azure DevOps PROJECT name, "
                    f"not the repository name. Projects contain repositories."
                ) from exc
            raise APIError(
                f"Failed to execute WIQL query in project "
                f"'{project}': {exc}"
            ) from exc

        if not results.work_items:
            logger.info(
                "No work items matched the query in project '%s'.",
                project,
            )
            return []

        ids = [item.id for item in results.work_items]
        logger.info(
            "WIQL query returned %d work item IDs in project '%s'.",
            len(ids),
            project,
        )

        # Step 2: Fetch full work item details by IDs
        # CRITICAL: error_policy='omit' to skip inaccessible items
        api_work_items: List[Any] = []
        batch_size = 200
        for i in range(0, len(ids), batch_size):
            batch = ids[i : i + batch_size]
            try:
                api_work_items.extend(
                    wit_client.get_work_items(
                        ids=batch,
                        project=project,
                        error_policy="omit",
                    )
                )
            except AzureDevOpsError:
                raise
            except Exception as exc:
                raise APIError(
                    f"Failed to fetch work item details for "
                    f"{len(ids)} items in project '{project}': {exc}"
                ) from exc

        # Filter out None entries (omitted due to error_policy)
        work_items = [
            WorkItem.from_api_response(item)
            for item in api_work_items
            if item is not None
        ]

        logger.info(
            "Retrieved %d work items from project '%s'.",
            len(work_items),
            project,
        )
        return work_items

    def get_work_item(
        self,
        project: str,
        work_item_id: int,
    ) -> WorkItem:
        """Get a single work item by its ID.

        Retrieves the full details of a specific work item, including
        all standard fields (title, state, type, assigned_to, etc.).

        Args:
            project: The project name or identifier.
            work_item_id: The unique integer ID of the work item.

        Returns:
            A WorkItem object with all fields populated.

        Raises:
            WorkItemNotFoundError: If the work item does not exist
                or is inaccessible.
            APIError: If the API call fails unexpectedly.
        """
        logger.info(
            "Getting work item %d in project '%s'.",
            work_item_id,
            project,
        )

        try:
            wit_client = self._get_wit_client()
            api_work_item = wit_client.get_work_item(
                id=work_item_id,
            )
        except AzureDevOpsError:
            raise
        except Exception as exc:
            error_msg = str(exc).lower()
            if "404" in error_msg or "not found" in error_msg:
                raise WorkItemNotFoundError(
                    work_item_id=work_item_id, project=project
                ) from exc
            raise APIError(
                f"Failed to get work item {work_item_id} "
                f"in project '{project}': {exc}"
            ) from exc

        if api_work_item is None:
            raise WorkItemNotFoundError(
                work_item_id=work_item_id, project=project
            )

        work_item = WorkItem.from_api_response(api_work_item)

        logger.info(
            "Retrieved work item %d: '%s' (%s).",
            work_item.id,
            work_item.title,
            work_item.work_item_type,
        )
        return work_item

    def list_backlog_items(
        self,
        project: str,
        item_types: Optional[List[str]] = None,
        max_items: int = 100,
    ) -> List[WorkItem]:
        """List work items from the project backlog.

        Retrieves backlog items filtered by work item type. By default,
        queries for Bugs, User Stories, and Tasks that are not in a
        closed or done state.

        Args:
            project: The project name or identifier.
            item_types: Filter by work item types (e.g., ``['Bug',
                'User Story', 'Task']``). If None, uses the default
                backlog types.
            max_items: Maximum number of items to return. Defaults to 100.

        Returns:
            A list of WorkItem objects from the backlog, ordered by
            priority. Returns an empty list if the backlog is empty.

        Raises:
            APIError: If the API call fails unexpectedly.
        """
        types = item_types or DEFAULT_BACKLOG_TYPES

        logger.info(
            "Listing backlog items in project '%s' "
            "(types=%s, max_items=%d).",
            project,
            types,
            max_items,
        )

        # Build WIQL query for backlog items
        type_conditions = " OR ".join(
            f"[System.WorkItemType] = '{wt}'" for wt in types
        )
        wiql_query = (
            "SELECT [System.Id] FROM WorkItems "
            f"WHERE [System.TeamProject] = '{project}' "
            f"AND ({type_conditions}) "
            "AND [System.State] <> 'Closed' "
            "AND [System.State] <> 'Done' "
            "AND [System.State] <> 'Removed' "
            "ORDER BY [Microsoft.VSTS.Common.Priority] ASC, "
            "[System.CreatedDate] DESC"
        )

        return self.query_work_items(
            project=project,
            query=wiql_query,
            max_items=max_items,
        )
