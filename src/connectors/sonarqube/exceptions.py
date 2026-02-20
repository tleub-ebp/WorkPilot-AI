"""Custom exceptions for the SonarQube connector.

Defines a hierarchy of exceptions for handling errors specific to SonarQube
operations, including authentication failures, missing resources, and API
errors.

Exception hierarchy:
    SonarQubeError (base)
    ├── SonarQubeAuthenticationError
    ├── SonarQubeConfigurationError
    ├── SonarQubeProjectNotFoundError
    └── SonarQubeAPIError
"""


class SonarQubeError(Exception):
    """Base exception for all SonarQube connector errors.

    All custom exceptions in this module inherit from this class,
    allowing callers to catch any SonarQube-related error with
    a single except clause.

    Args:
        message: A human-readable description of the error.
    """

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


class SonarQubeAuthenticationError(SonarQubeError):
    """Raised when authentication with SonarQube fails.

    This typically occurs when the token is invalid, expired, or
    lacks the required permissions.

    Args:
        message: A human-readable description of the authentication error.
    """


class SonarQubeConfigurationError(SonarQubeError):
    """Raised when required configuration is missing or invalid.

    This occurs when environment variables such as SONARQUBE_URL or
    SONARQUBE_TOKEN are missing, empty, or contain invalid values.

    Args:
        message: A human-readable description of the configuration error.
    """


class SonarQubeProjectNotFoundError(SonarQubeError):
    """Raised when a requested project does not exist in SonarQube.

    Args:
        project_key: The project key that was not found.
    """

    def __init__(self, project_key: str) -> None:
        self.project_key = project_key
        message = f"SonarQube project '{project_key}' not found."
        super().__init__(message)


class SonarQubeAPIError(SonarQubeError):
    """Raised when a SonarQube API call fails.

    Wraps HTTP errors and unexpected API responses with contextual
    information about the failed operation.

    Args:
        message: A human-readable description of the API error.
        status_code: The HTTP status code returned by the API, if available.
    """

    def __init__(self, message: str, status_code: int = 0) -> None:
        self.status_code = status_code
        if status_code:
            full_message = f"SonarQube API error (HTTP {status_code}): {message}"
        else:
            full_message = f"SonarQube API error: {message}"
        super().__init__(full_message)
