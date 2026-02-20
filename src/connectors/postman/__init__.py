"""Postman connector — Integration with Postman API collections.

Provides a unified interface for interacting with the Postman API,
including collection import/export, environment synchronization,
automatic collection generation from API endpoints, and test
validation via a single ``PostmanConnector`` class.

The connector communicates with the Postman API using API key
authentication and maps all responses to clean Python dataclasses.

Example:
    >>> from src.connectors.postman import PostmanConnector
    >>> connector = PostmanConnector.from_env()
    >>> collections = connector.list_collections()
    >>> requests = connector.get_collection_requests("col-123")
"""

from src.connectors.postman.client import PostmanClient
from src.connectors.postman.connector import PostmanConnector
from src.connectors.postman.exceptions import (
    PostmanAPIError,
    PostmanAuthenticationError,
    PostmanCollectionNotFoundError,
    PostmanConfigurationError,
    PostmanEnvironmentNotFoundError,
    PostmanError,
)
from src.connectors.postman.models import (
    PostmanCollection,
    PostmanCollectionRun,
    PostmanEnvironment,
    PostmanRequest,
    PostmanTestResult,
    PostmanWorkspace,
)

__all__ = [
    # Main connector
    "PostmanConnector",
    # Underlying client
    "PostmanClient",
    # Data models
    "PostmanCollection",
    "PostmanRequest",
    "PostmanEnvironment",
    "PostmanWorkspace",
    "PostmanTestResult",
    "PostmanCollectionRun",
    # Exceptions
    "PostmanError",
    "PostmanAuthenticationError",
    "PostmanConfigurationError",
    "PostmanAPIError",
    "PostmanCollectionNotFoundError",
    "PostmanEnvironmentNotFoundError",
]
