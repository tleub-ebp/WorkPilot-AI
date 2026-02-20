"""Custom exceptions for the Jira connector.

Defines a hierarchy of exceptions for handling errors specific to Jira
operations, including authentication failures, missing resources, and API
errors.

Exception hierarchy:
    JiraError (base)
    ├── JiraAuthenticationError
    ├── JiraConfigurationError
    ├── JiraProjectNotFoundError
    ├── JiraIssueNotFoundError
    └── JiraAPIError
"""


class JiraError(Exception):
    """Base exception for all Jira connector errors.

    All custom exceptions in this module inherit from this class,
    allowing callers to catch any Jira-related error with
    a single except clause.

    Args:
        message: A human-readable description of the error.
    """

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


class JiraAuthenticationError(JiraError):
    """Raised when authentication with Jira fails.

    This typically occurs when the API token is invalid, expired, or
    lacks the required permissions.

    Args:
        message: A human-readable description of the authentication error.
    """


class JiraConfigurationError(JiraError):
    """Raised when required configuration is missing or invalid.

    This occurs when environment variables such as JIRA_URL, JIRA_EMAIL,
    or JIRA_API_TOKEN are missing, empty, or contain invalid values.

    Args:
        message: A human-readable description of the configuration error.
    """


class JiraProjectNotFoundError(JiraError):
    """Raised when a requested project does not exist in Jira.

    Args:
        project_key: The project key that was not found.
    """

    def __init__(self, project_key: str) -> None:
        self.project_key = project_key
        message = f"Jira project '{project_key}' not found."
        super().__init__(message)


class JiraIssueNotFoundError(JiraError):
    """Raised when a requested issue does not exist in Jira.

    Args:
        issue_key: The issue key that was not found.
    """

    def __init__(self, issue_key: str) -> None:
        self.issue_key = issue_key
        message = f"Jira issue '{issue_key}' not found."
        super().__init__(message)


class JiraAPIError(JiraError):
    """Raised when a Jira API call fails.

    Wraps HTTP errors and unexpected API responses with contextual
    information about the failed operation.

    Args:
        message: A human-readable description of the API error.
        status_code: The HTTP status code returned by the API, if available.
    """

    def __init__(self, message: str, status_code: int = 0) -> None:
        self.status_code = status_code
        if status_code:
            full_message = f"Jira API error (HTTP {status_code}): {message}"
        else:
            full_message = f"Jira API error: {message}"
        super().__init__(full_message)
