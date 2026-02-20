"""Data models for the Postman connector.

Defines dataclass representations for Postman entities including
collections, environments, requests, and test results. Each model
includes factory methods for converting raw Postman API responses
into clean, typed data structures.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class PostmanWorkspace:
    """Postman workspace representation.

    Attributes:
        workspace_id: The unique workspace ID.
        name: The workspace name.
        workspace_type: The workspace type (``'personal'``, ``'team'``, etc.).
        description: The workspace description.
    """

    workspace_id: str
    name: str
    workspace_type: str = "personal"
    description: str = ""

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "PostmanWorkspace":
        """Create a PostmanWorkspace from a Postman API response dict."""
        return cls(
            workspace_id=data.get("id", ""),
            name=data.get("name", ""),
            workspace_type=data.get("type", "personal"),
            description=data.get("description", ""),
        )


@dataclass
class PostmanCollection:
    """Postman collection representation.

    Attributes:
        collection_id: The unique collection ID.
        name: The collection name.
        uid: The collection UID (owner-id format).
        description: The collection description.
        created_at: Creation datetime, or None.
        updated_at: Last update datetime, or None.
        owner: The collection owner ID.
        fork_info: Fork information if forked, or None.
    """

    collection_id: str
    name: str
    uid: str = ""
    description: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    owner: str = ""
    fork_info: dict[str, Any] | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "PostmanCollection":
        """Create a PostmanCollection from a Postman API response dict."""
        created = data.get("createdAt")
        parsed_created = None
        if created:
            try:
                parsed_created = datetime.fromisoformat(
                    created.replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                parsed_created = None

        updated = data.get("updatedAt")
        parsed_updated = None
        if updated:
            try:
                parsed_updated = datetime.fromisoformat(
                    updated.replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                parsed_updated = None

        return cls(
            collection_id=data.get("id", ""),
            name=data.get("name", ""),
            uid=data.get("uid", ""),
            description=data.get("description", ""),
            created_at=parsed_created,
            updated_at=parsed_updated,
            owner=data.get("owner", ""),
            fork_info=data.get("fork"),
        )


@dataclass
class PostmanRequest:
    """A single request within a Postman collection.

    Attributes:
        request_id: The unique request ID.
        name: The request name.
        method: The HTTP method (``'GET'``, ``'POST'``, etc.).
        url: The request URL.
        description: The request description.
        headers: List of header key-value pairs.
        body: The request body, or None.
        folder_id: The parent folder ID, if any.
    """

    request_id: str
    name: str
    method: str = "GET"
    url: str = ""
    description: str = ""
    headers: list[dict[str, str]] = field(default_factory=list)
    body: dict[str, Any] | None = None
    folder_id: str | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "PostmanRequest":
        """Create a PostmanRequest from a Postman API response dict."""
        request_data = data.get("request", {})
        if isinstance(request_data, str):
            url = request_data
            method = "GET"
            headers = []
            body = None
            description = ""
        else:
            url_data = request_data.get("url", "")
            if isinstance(url_data, dict):
                url = url_data.get("raw", "")
            else:
                url = str(url_data)
            method = request_data.get("method", "GET")
            headers = request_data.get("header", [])
            body = request_data.get("body")
            description = request_data.get("description", "") or ""

        return cls(
            request_id=data.get("id", ""),
            name=data.get("name", ""),
            method=method,
            url=url,
            description=description,
            headers=headers if isinstance(headers, list) else [],
            body=body,
        )


@dataclass
class PostmanEnvironment:
    """Postman environment representation.

    Attributes:
        environment_id: The unique environment ID.
        name: The environment name.
        uid: The environment UID.
        values: List of environment variable key-value pairs.
        created_at: Creation datetime, or None.
        updated_at: Last update datetime, or None.
    """

    environment_id: str
    name: str
    uid: str = ""
    values: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "PostmanEnvironment":
        """Create a PostmanEnvironment from a Postman API response dict."""
        return cls(
            environment_id=data.get("id", ""),
            name=data.get("name", ""),
            uid=data.get("uid", ""),
            values=data.get("values", []),
            created_at=None,
            updated_at=None,
        )


@dataclass
class PostmanTestResult:
    """Result of a Postman collection test run.

    Attributes:
        request_name: The name of the request that was tested.
        test_name: The test assertion name.
        passed: Whether the test passed.
        error_message: Error message if test failed, or empty string.
        response_code: The HTTP response status code.
        response_time_ms: Response time in milliseconds.
    """

    request_name: str
    test_name: str
    passed: bool
    error_message: str = ""
    response_code: int = 0
    response_time_ms: int = 0

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "PostmanTestResult":
        """Create a PostmanTestResult from a Postman API response dict."""
        return cls(
            request_name=data.get("request_name", ""),
            test_name=data.get("test_name", ""),
            passed=data.get("passed", False),
            error_message=data.get("error_message", ""),
            response_code=data.get("response_code", 0),
            response_time_ms=data.get("response_time_ms", 0),
        )


@dataclass
class PostmanCollectionRun:
    """Summary of a Postman collection run.

    Attributes:
        collection_id: The collection that was run.
        total_tests: Total number of tests.
        passed_tests: Number of passing tests.
        failed_tests: Number of failing tests.
        total_requests: Total number of requests executed.
        results: Individual test results.
        duration_ms: Total run duration in milliseconds.
    """

    collection_id: str
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    total_requests: int = 0
    results: list[PostmanTestResult] = field(default_factory=list)
    duration_ms: int = 0

    @property
    def success_rate(self) -> float:
        """Calculate the test success rate as a percentage."""
        if self.total_tests == 0:
            return 100.0
        return (self.passed_tests / self.total_tests) * 100.0

    @property
    def is_passing(self) -> bool:
        """Return True if all tests passed."""
        return self.failed_tests == 0
