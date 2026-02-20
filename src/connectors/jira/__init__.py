"""Jira connector — Integration with Jira Cloud issue tracking.

Provides a unified interface for interacting with Jira Cloud services,
including project listing, issue import/creation, bidirectional status
synchronization, and Kanban board integration via a single
``JiraConnector`` class.

The connector communicates with the Jira Cloud REST API v3 using
email + API token authentication and maps all responses to clean
Python dataclasses.

Example:
    >>> from src.connectors.jira import JiraConnector
    >>> connector = JiraConnector.from_env()
    >>> projects = connector.list_projects()
    >>> issues = connector.search_issues("PROJ", "status = 'To Do'")
"""

from src.connectors.jira.client import JiraClient
from src.connectors.jira.connector import JiraConnector
from src.connectors.jira.exceptions import (
    JiraAPIError,
    JiraAuthenticationError,
    JiraConfigurationError,
    JiraError,
    JiraIssueNotFoundError,
    JiraProjectNotFoundError,
)
from src.connectors.jira.models import (
    JiraComment,
    JiraIssue,
    JiraProject,
    JiraStatus,
    JiraTransition,
    JiraUser,
)

__all__ = [
    # Main connector
    "JiraConnector",
    # Underlying client
    "JiraClient",
    # Data models
    "JiraProject",
    "JiraIssue",
    "JiraUser",
    "JiraStatus",
    "JiraTransition",
    "JiraComment",
    # Exceptions
    "JiraError",
    "JiraAuthenticationError",
    "JiraConfigurationError",
    "JiraAPIError",
    "JiraProjectNotFoundError",
    "JiraIssueNotFoundError",
]
