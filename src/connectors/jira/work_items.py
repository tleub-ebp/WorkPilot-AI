"""
JIRA Work Items Client

High-level client for JIRA issue tracking operations.
Wraps the JIRA REST API client to provide convenient methods for
querying issues, retrieving details, and listing backlog items.
"""

import logging
from typing import Any

import requests

from src.connectors.jira.client import JiraClient
from src.connectors.jira.exceptions import (
    JiraAPIError,
    JiraError,
    JiraIssueNotFoundError,
)
from src.connectors.jira.models import JiraIssue, JiraProject

logger = logging.getLogger(__name__)

# Default backlog issue types for JIRA
DEFAULT_BACKLOG_TYPES = ["Bug", "Story", "Task", "Epic"]


class JiraWorkItemsClient:
    """Client for JIRA issue tracking operations.

    Wraps the JIRA REST API client to provide high-level methods for
    querying issues, retrieving details, and listing backlog items. All API
    responses are mapped to clean JiraIssue data models.

    Attributes:
        _client: The underlying JiraClient providing authenticated
            access to the JIRA REST API.

    Example:
        >>> client = JiraClient.from_env()
        >>> wit_client = JiraWorkItemsClient(client)
        >>> for item in wit_client.list_backlog_items("PROJ"):
        ...     print(f"{item.issue_type}: {item.summary}")
    """

    def __init__(self, client: JiraClient) -> None:
        """Initialize the work items client.

        Args:
            client: An authenticated JiraClient instance.
                Must have an active connection (connect() must have
                been called).
        """
        self._client = client

    def _get_api_client(self) -> Any:
        """Get the JIRA API client from the underlying connection.

        Returns:
            The authenticated requests session or API client.

        Raises:
            JiraError: If the client is not connected.
        """
        if not self._client._connected:
            raise JiraError("JiraClient must be connected before use")
        return self._client._session

    def list_backlog_items(
        self,
        project: str,
        issue_types: list[str] | None = None,
        max_items: int = 100,
        status_filter: list[str] | None = None,
    ) -> list[JiraIssue]:
        """List issues from project backlog.

        Args:
            project: The JIRA project key (e.g., "PROJ")
            issue_types: List of issue types to include (default: DEFAULT_BACKLOG_TYPES)
            max_items: Maximum number of items to return
            status_filter: List of status names to filter by (default: ["To Do", "Backlog"])

        Returns:
            List of JiraIssue objects representing backlog items

        Raises:
            JiraProjectNotFoundError: If the project doesn't exist
            JiraAPIError: If the API call fails
        """
        if issue_types is None:
            issue_types = DEFAULT_BACKLOG_TYPES
        
        if status_filter is None:
            status_filter = ["To Do", "Backlog", "New"]

        api_client = self._get_api_client()
        
        # Build JQL query
        jql_parts = [
            f'project = "{project}"',
            f'issuetype in ({", ".join(issue_types)})',
            f'status in ({", ".join(f'"{s}"' for s in status_filter)})'
        ]
        jql = " AND ".join(jql_parts)
        
        params = {
            "jql": jql,
            "fields": "summary,description,status,issuetype,priority,assignee,reporter,labels,created,updated,project",
            "maxResults": max_items,
            "startAt": 0
        }
        
        try:
            response = api_client.get(
                f"{self._client.base_url}/rest/api/3/search",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            issues = []
            
            for issue_data in data.get("issues", []):
                issue = JiraIssue.from_api_response(issue_data)
                issues.append(issue)
                
            logger.info(f"Retrieved {len(issues)} backlog items for project {project}")
            return issues
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise JiraProjectNotFoundError(project)
            else:
                raise JiraAPIError(f"Failed to list backlog items: {e}", e.response.status_code)
        except Exception as e:
            raise JiraAPIError(f"Failed to list backlog items: {e}")

    def get_issue_details(self, issue_key: str) -> JiraIssue:
        """Get detailed information about a specific issue.

        Args:
            issue_key: The issue key (e.g., "PROJ-123")

        Returns:
            JiraIssue object with complete issue details

        Raises:
            JiraIssueNotFoundError: If the issue doesn't exist
            JiraAPIError: If the API call fails
        """
        api_client = self._get_api_client()
        
        params = {
            "fields": "summary,description,status,issuetype,priority,assignee,reporter,labels,created,updated,project,comment,transitions"
        }
        
        try:
            response = api_client.get(
                f"{self._client.base_url}/rest/api/3/issue/{issue_key}",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            issue = JiraIssue.from_api_response(data)
            
            logger.info(f"Retrieved details for issue {issue_key}")
            return issue
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise JiraIssueNotFoundError(issue_key)
            else:
                raise JiraAPIError(f"Failed to get issue details: {e}", e.response.status_code)
        except Exception as e:
            raise JiraAPIError(f"Failed to get issue details: {e}")

    def list_projects(self) -> list[JiraProject]:
        """List all accessible JIRA projects.

        Returns:
            List of JiraProject objects

        Raises:
            JiraAPIError: If the API call fails
        """
        api_client = self._get_api_client()
        
        try:
            response = api_client.get(f"{self._client.base_url}/rest/api/3/project")
            response.raise_for_status()
            
            data = response.json()
            projects = []
            
            for project_data in data:
                project = JiraProject.from_api_response(project_data)
                projects.append(project)
                
            logger.info(f"Retrieved {len(projects)} projects")
            return projects
            
        except Exception as e:
            raise JiraAPIError(f"Failed to list projects: {e}")

    def search_issues(
        self,
        jql: str,
        max_results: int = 50,
        fields: list[str] | None = None
    ) -> list[JiraIssue]:
        """Search issues using JQL (JIRA Query Language).

        Args:
            jql: JQL query string
            max_results: Maximum number of results to return
            fields: List of field names to retrieve (default: standard fields)

        Returns:
            List of JiraIssue objects matching the query

        Raises:
            JiraAPIError: If the API call fails
        """
        api_client = self._get_api_client()
        
        if fields is None:
            fields = "summary,description,status,issuetype,priority,assignee,reporter,labels,created,updated,project"
        
        params = {
            "jql": jql,
            "fields": fields,
            "maxResults": max_results,
            "startAt": 0
        }
        
        try:
            response = api_client.get(
                f"{self._client.base_url}/rest/api/3/search",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            issues = []
            
            for issue_data in data.get("issues", []):
                issue = JiraIssue.from_api_response(issue_data)
                issues.append(issue)
                
            logger.info(f"Search returned {len(issues)} issues for JQL: {jql[:100]}...")
            return issues
            
        except Exception as e:
            raise JiraAPIError(f"Failed to search issues: {e}")

    def get_issue_transitions(self, issue_key: str) -> list[dict[str, Any]]:
        """Get available transitions for an issue.

        Args:
            issue_key: The issue key (e.g., "PROJ-123")

        Returns:
            List of available transitions

        Raises:
            JiraIssueNotFoundError: If the issue doesn't exist
            JiraAPIError: If the API call fails
        """
        api_client = self._get_api_client()
        
        try:
            response = api_client.get(
                f"{self._client.base_url}/rest/api/3/issue/{issue_key}/transitions"
            )
            response.raise_for_status()
            
            data = response.json()
            transitions = data.get("transitions", [])
            
            logger.info(f"Retrieved {len(transitions)} transitions for issue {issue_key}")
            return transitions
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise JiraIssueNotFoundError(issue_key)
            else:
                raise JiraAPIError(f"Failed to get issue transitions: {e}", e.response.status_code)
        except Exception as e:
            raise JiraAPIError(f"Failed to get issue transitions: {e}")

    def transition_issue(self, issue_key: str, transition_id: str, comment: str | None = None) -> bool:
        """Transition an issue to a new status.

        Args:
            issue_key: The issue key (e.g., "PROJ-123")
            transition_id: The transition ID or name
            comment: Optional comment to add during transition

        Returns:
            True if transition was successful

        Raises:
            JiraIssueNotFoundError: If the issue doesn't exist
            JiraAPIError: If the API call fails
        """
        api_client = self._get_api_client()
        
        payload = {
            "transition": {
                "id": transition_id
            }
        }
        
        if comment:
            payload["update"] = {
                "comment": [{"add": {"body": comment}}]
            }
        
        try:
            response = api_client.post(
                f"{self._client.base_url}/rest/api/3/issue/{issue_key}/transitions",
                json=payload
            )
            response.raise_for_status()
            
            logger.info(f"Successfully transitioned issue {issue_key}")
            return True
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise JiraIssueNotFoundError(issue_key)
            else:
                raise JiraAPIError(f"Failed to transition issue: {e}", e.response.status_code)
        except Exception as e:
            raise JiraAPIError(f"Failed to transition issue: {e}")
