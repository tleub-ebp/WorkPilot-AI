"""Custom exceptions for the Azure DevOps connector.

Defines a hierarchy of exceptions for handling errors specific to Azure
DevOps operations, including authentication failures, missing resources,
API errors, and rate limiting.

Exception hierarchy:
    AzureDevOpsError (base)
    ├── AuthenticationError
    ├── ConfigurationError
    ├── ResourceNotFoundError
    │   ├── RepositoryNotFoundError
    │   └── WorkItemNotFoundError
    ├── APIError
    └── RateLimitError
"""


class AzureDevOpsError(Exception):
    """Base exception for all Azure DevOps connector errors.

    All custom exceptions in this module inherit from this class,
    allowing callers to catch any Azure DevOps-related error with
    a single except clause.

    Args:
        message: A human-readable description of the error.
    """

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


class AuthenticationError(AzureDevOpsError):
    """Raised when authentication with Azure DevOps fails.

    This typically occurs when the Personal Access Token (PAT) is
    invalid, expired, or lacks the required scopes.

    Args:
        message: A human-readable description of the authentication error.
    """


class ConfigurationError(AzureDevOpsError):
    """Raised when required configuration is missing or invalid.

    This occurs when environment variables such as AZURE_DEVOPS_PAT or
    AZURE_DEVOPS_ORG_URL are missing, empty, or contain invalid values.

    Args:
        message: A human-readable description of the configuration error.
    """


class ResourceNotFoundError(AzureDevOpsError):
    """Base exception for resource not found errors.

    Parent class for specific not-found exceptions such as
    RepositoryNotFoundError and WorkItemNotFoundError.

    Args:
        message: A human-readable description of the error.
        resource_id: The identifier of the resource that was not found.
    """

    def __init__(self, message: str, resource_id: str = "") -> None:
        self.resource_id = resource_id
        super().__init__(message)


class RepositoryNotFoundError(ResourceNotFoundError):
    """Raised when a requested repository does not exist.

    Args:
        repository_id: The repository name or ID that was not found.
        project: The project in which the repository was searched.
    """

    def __init__(self, repository_id: str, project: str = "") -> None:
        self.repository_id = repository_id
        self.project = project
        if project:
            message = f"Repository '{repository_id}' not found in project '{project}'."
        else:
            message = f"Repository '{repository_id}' not found."
        super().__init__(message, resource_id=repository_id)


class WorkItemNotFoundError(ResourceNotFoundError):
    """Raised when a requested work item does not exist or is inaccessible.

    Args:
        work_item_id: The ID of the work item that was not found.
        project: The project in which the work item was searched.
    """

    def __init__(self, work_item_id: int, project: str = "") -> None:
        self.work_item_id = work_item_id
        self.project = project
        if project:
            message = f"Work item {work_item_id} not found in project '{project}'."
        else:
            message = f"Work item {work_item_id} not found."
        super().__init__(message, resource_id=str(work_item_id))


class APIError(AzureDevOpsError):
    """Raised when an Azure DevOps API call fails.

    Wraps HTTP errors and unexpected API responses with contextual
    information about the failed operation.

    Args:
        message: A human-readable description of the API error.
        status_code: The HTTP status code returned by the API, if available.
    """

    def __init__(self, message: str, status_code: int = 0) -> None:
        self.status_code = status_code
        if status_code:
            full_message = f"API error (HTTP {status_code}): {message}"
        else:
            full_message = f"API error: {message}"
        super().__init__(full_message)


class RateLimitError(AzureDevOpsError):
    """Raised when Azure DevOps API rate limits are exceeded.

    Azure DevOps may return HTTP 200 with a Retry-After header instead
    of the standard HTTP 429. This exception includes the retry delay
    to support exponential backoff strategies.

    Args:
        message: A human-readable description of the rate limit error.
        retry_after: The number of seconds to wait before retrying,
            as indicated by the Retry-After header.
    """

    def __init__(self, message: str, retry_after: float = 0.0) -> None:
        self.retry_after = retry_after
        if retry_after > 0:
            full_message = f"{message} Retry after {retry_after:.1f} seconds."
        else:
            full_message = message
        super().__init__(full_message)
