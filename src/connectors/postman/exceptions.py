"""Custom exceptions for the Postman connector.

Defines a hierarchy of exceptions for handling errors specific to Postman
operations, including authentication failures, missing resources, and API
errors.

Exception hierarchy:
    PostmanError (base)
    ├── PostmanAuthenticationError
    ├── PostmanConfigurationError
    ├── PostmanCollectionNotFoundError
    ├── PostmanEnvironmentNotFoundError
    └── PostmanAPIError
"""


class PostmanError(Exception):
    """Base exception for all Postman connector errors.

    All custom exceptions in this module inherit from this class,
    allowing callers to catch any Postman-related error with
    a single except clause.

    Args:
        message: A human-readable description of the error.
    """

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


class PostmanAuthenticationError(PostmanError):
    """Raised when authentication with Postman fails.

    This typically occurs when the API key is invalid, expired, or
    lacks the required permissions.

    Args:
        message: A human-readable description of the authentication error.
    """


class PostmanConfigurationError(PostmanError):
    """Raised when required configuration is missing or invalid.

    This occurs when environment variables such as POSTMAN_API_KEY
    are missing, empty, or contain invalid values.

    Args:
        message: A human-readable description of the configuration error.
    """


class PostmanCollectionNotFoundError(PostmanError):
    """Raised when a requested collection does not exist in Postman.

    Args:
        collection_id: The collection ID that was not found.
    """

    def __init__(self, collection_id: str) -> None:
        self.collection_id = collection_id
        message = f"Postman collection '{collection_id}' not found."
        super().__init__(message)


class PostmanEnvironmentNotFoundError(PostmanError):
    """Raised when a requested environment does not exist in Postman.

    Args:
        environment_id: The environment ID that was not found.
    """

    def __init__(self, environment_id: str) -> None:
        self.environment_id = environment_id
        message = f"Postman environment '{environment_id}' not found."
        super().__init__(message)


class PostmanAPIError(PostmanError):
    """Raised when a Postman API call fails.

    Wraps HTTP errors and unexpected API responses with contextual
    information about the failed operation.

    Args:
        message: A human-readable description of the API error.
        status_code: The HTTP status code returned by the API, if available.
    """

    def __init__(self, message: str, status_code: int = 0) -> None:
        self.status_code = status_code
        if status_code:
            full_message = f"Postman API error (HTTP {status_code}): {message}"
        else:
            full_message = f"Postman API error: {message}"
        super().__init__(full_message)
