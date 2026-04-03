"""SonarQube connector — High-level interface for code quality analysis.

Provides methods for listing projects, retrieving metrics, checking
quality gate status, and searching issues from SonarQube or SonarCloud.

Example:
    >>> from src.connectors.sonarqube import SonarQubeConnector
    >>> connector = SonarQubeConnector.from_env()
    >>> status = connector.get_quality_gate_status("my-project")
    >>> print(status.is_passing)
"""

import logging
from typing import Any

from src.connectors.sonarqube.client import SonarQubeClient
from src.connectors.sonarqube.models import (
    QualityGateStatus,
    SonarIssue,
    SonarMeasure,
    SonarProject,
)

logger = logging.getLogger(__name__)

# Default metrics commonly used for dashboard integration
DEFAULT_METRICS = [
    "bugs",
    "vulnerabilities",
    "code_smells",
    "coverage",
    "duplicated_lines_density",
    "ncloc",
    "sqale_index",
    "reliability_rating",
    "security_rating",
    "sqale_rating",
]


class SonarQubeConnector:
    """Unified connector for SonarQube / SonarCloud code quality analysis.

    Provides high-level methods for interacting with SonarQube services
    including project listing, metrics retrieval, quality gate checks,
    and issue tracking.

    Attributes:
        _client: The underlying SonarQube HTTP client.

    Example:
        >>> connector = SonarQubeConnector.from_env()
        >>> projects = connector.list_projects()
        >>> for p in projects:
        ...     status = connector.get_quality_gate_status(p.key)
        ...     print(f"{p.name}: {status.status}")
    """

    def __init__(self, client: SonarQubeClient) -> None:
        """Initialize the SonarQube connector.

        Args:
            client: A SonarQubeClient instance. Does not need to be
                connected yet — call ``connect()`` to authenticate.
        """
        self._client = client

    @classmethod
    def from_env(cls) -> "SonarQubeConnector":
        """Create a connector from environment variables and connect.

        Reads ``SONARQUBE_URL`` and ``SONARQUBE_TOKEN`` from the
        environment, creates and connects the client.

        Returns:
            A connected SonarQubeConnector instance.

        Raises:
            SonarQubeConfigurationError: If required env vars are missing.
            SonarQubeAuthenticationError: If authentication fails.
        """
        client = SonarQubeClient.from_env()
        return cls(client)

    def connect(self) -> None:
        """Establish an authenticated connection to SonarQube.

        Raises:
            SonarQubeAuthenticationError: If the token is invalid.
            SonarQubeAPIError: If the server is unreachable.
        """
        self._client.connect()

    def disconnect(self) -> None:
        """Close the connection to SonarQube."""
        self._client.disconnect()

    @property
    def is_connected(self) -> bool:
        """Check whether the connector has an active connection."""
        return self._client.is_connected

    def get_connection_info(self) -> dict[str, str]:
        """Get information about the current connection."""
        return self._client.get_connection_info()

    # ── Project operations ───────────────────────────────────────────

    def list_projects(
        self,
        page_size: int = 100,
        page: int = 1,
    ) -> list[SonarProject]:
        """List all projects visible to the authenticated user.

        Args:
            page_size: Number of projects per page (max 500).
            page: Page number (1-indexed).

        Returns:
            A list of SonarProject objects.

        Raises:
            SonarQubeAPIError: If the API call fails.
        """
        logger.info("Listing SonarQube projects (page=%d, size=%d).", page, page_size)

        data = self._client.get(
            "/api/projects/search",
            params={"ps": page_size, "p": page},
        )

        components = data.get("components", [])
        projects = [SonarProject.from_api_response(c) for c in components]

        logger.info("Found %d projects.", len(projects))
        return projects

    def get_project(self, project_key: str) -> SonarProject:
        """Get details of a single project.

        Args:
            project_key: The unique project key.

        Returns:
            A SonarProject object.

        Raises:
            SonarQubeProjectNotFoundError: If the project does not exist.
            SonarQubeAPIError: If the API call fails.
        """
        logger.info("Getting project '%s'.", project_key)

        data = self._client.get(
            "/api/components/show",
            params={"component": project_key},
        )

        component = data.get("component", {})
        return SonarProject.from_api_response(component)

    # ── Metrics operations ───────────────────────────────────────────

    def get_measures(
        self,
        project_key: str,
        metric_keys: list[str] | None = None,
    ) -> list[SonarMeasure]:
        """Get metric measures for a project.

        Retrieves the current values of the specified metrics for the
        given project. If no metrics are specified, uses a default set
        of commonly used quality metrics.

        Args:
            project_key: The unique project key.
            metric_keys: List of metric keys to retrieve. If None, uses
                ``DEFAULT_METRICS``.

        Returns:
            A list of SonarMeasure objects.

        Raises:
            SonarQubeProjectNotFoundError: If the project does not exist.
            SonarQubeAPIError: If the API call fails.
        """
        metrics = metric_keys or DEFAULT_METRICS

        logger.info(
            "Getting measures for '%s' (metrics: %s).",
            project_key,
            metrics,
        )

        data = self._client.get(
            "/api/measures/component",
            params={
                "component": project_key,
                "metricKeys": ",".join(metrics),
            },
        )

        component = data.get("component", {})
        measures_data = component.get("measures", [])

        measures = [
            SonarMeasure.from_api_response(m, component=project_key)
            for m in measures_data
        ]

        logger.info(
            "Retrieved %d measures for '%s'.",
            len(measures),
            project_key,
        )
        return measures

    def get_measures_history(
        self,
        project_key: str,
        metric_keys: list[str] | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """Get historical measures for tracking technical debt evolution.

        Args:
            project_key: The unique project key.
            metric_keys: Metrics to track. Defaults to debt-related metrics.
            from_date: Start date in ``YYYY-MM-DD`` format, or None.
            to_date: End date in ``YYYY-MM-DD`` format, or None.

        Returns:
            A dictionary mapping metric keys to lists of
            ``{'date': str, 'value': str}`` entries.

        Raises:
            SonarQubeProjectNotFoundError: If the project does not exist.
            SonarQubeAPIError: If the API call fails.
        """
        metrics = metric_keys or ["sqale_index", "bugs", "vulnerabilities", "code_smells"]

        logger.info(
            "Getting measures history for '%s' (metrics: %s).",
            project_key,
            metrics,
        )

        params: dict[str, Any] = {
            "component": project_key,
            "metrics": ",".join(metrics),
        }
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date

        data = self._client.get("/api/measures/search_history", params=params)

        result: dict[str, list[dict[str, Any]]] = {}
        for measure in data.get("measures", []):
            metric = measure.get("metric", "")
            history = [
                {"date": h.get("date", ""), "value": h.get("value", "")}
                for h in measure.get("history", [])
            ]
            result[metric] = history

        return result

    # ── Quality Gate operations ──────────────────────────────────────

    def get_quality_gate_status(
        self,
        project_key: str,
        branch: str | None = None,
        pull_request: str | None = None,
    ) -> QualityGateStatus:
        """Get the quality gate status for a project.

        Checks whether the project passes its quality gate, including
        individual condition results.

        Args:
            project_key: The unique project key.
            branch: Optional branch name to check.
            pull_request: Optional pull request ID to check.

        Returns:
            A QualityGateStatus object with the overall status and
            individual condition results.

        Raises:
            SonarQubeProjectNotFoundError: If the project does not exist.
            SonarQubeAPIError: If the API call fails.
        """
        logger.info(
            "Checking quality gate for '%s' (branch=%s, pr=%s).",
            project_key,
            branch or "default",
            pull_request or "none",
        )

        params: dict[str, Any] = {"projectKey": project_key}
        if branch:
            params["branch"] = branch
        if pull_request:
            params["pullRequest"] = pull_request

        data = self._client.get(
            "/api/qualitygates/project_status",
            params=params,
        )

        project_status = data.get("projectStatus", {})
        status = QualityGateStatus.from_api_response(
            project_status, project_key=project_key
        )

        logger.info(
            "Quality gate for '%s': %s (%d conditions).",
            project_key,
            status.status,
            len(status.conditions),
        )
        return status

    # ── Issues operations ────────────────────────────────────────────

    def get_issues(
        self,
        project_key: str,
        severities: list[str] | None = None,
        issue_types: list[str] | None = None,
        statuses: list[str] | None = None,
        page_size: int = 100,
        page: int = 1,
        branch: str | None = None,
    ) -> list[SonarIssue]:
        """Search for issues in a project.

        Retrieves code issues (bugs, vulnerabilities, code smells)
        from the given project with optional filtering.

        Args:
            project_key: The unique project key.
            severities: Filter by severity (``'BLOCKER'``, ``'CRITICAL'``,
                ``'MAJOR'``, ``'MINOR'``, ``'INFO'``).
            issue_types: Filter by type (``'BUG'``, ``'VULNERABILITY'``,
                ``'CODE_SMELL'``).
            statuses: Filter by status (``'OPEN'``, ``'CONFIRMED'``,
                ``'RESOLVED'``, ``'CLOSED'``).
            page_size: Number of issues per page (max 500).
            page: Page number (1-indexed).
            branch: Optional branch name to search.

        Returns:
            A list of SonarIssue objects matching the filters.

        Raises:
            SonarQubeProjectNotFoundError: If the project does not exist.
            SonarQubeAPIError: If the API call fails.
        """
        logger.info(
            "Searching issues for '%s' (severities=%s, types=%s).",
            project_key,
            severities,
            issue_types,
        )

        params: dict[str, Any] = {
            "componentKeys": project_key,
            "ps": page_size,
            "p": page,
        }

        if severities:
            params["severities"] = ",".join(severities)
        if issue_types:
            params["types"] = ",".join(issue_types)
        if statuses:
            params["statuses"] = ",".join(statuses)
        if branch:
            params["branch"] = branch

        data = self._client.get("/api/issues/search", params=params)

        issues_data = data.get("issues", [])
        issues = [SonarIssue.from_api_response(i) for i in issues_data]

        total = data.get("total", len(issues))
        logger.info(
            "Found %d issues (total: %d) for '%s'.",
            len(issues),
            total,
            project_key,
        )
        return issues

    # ── Convenience / aggregation methods ────────────────────────────

    def get_project_summary(
        self,
        project_key: str,
    ) -> dict[str, Any]:
        """Get a comprehensive project quality summary.

        Aggregates project info, key metrics, quality gate status, and
        top issues into a single dictionary suitable for dashboard
        display or QA agent consumption.

        Args:
            project_key: The unique project key.

        Returns:
            A dictionary with keys: ``'project'``, ``'measures'``,
            ``'quality_gate'``, ``'top_issues'``.

        Raises:
            SonarQubeProjectNotFoundError: If the project does not exist.
            SonarQubeAPIError: If the API call fails.
        """
        logger.info("Building project summary for '%s'.", project_key)

        project = self.get_project(project_key)
        measures = self.get_measures(project_key)
        quality_gate = self.get_quality_gate_status(project_key)
        top_issues = self.get_issues(
            project_key,
            severities=["BLOCKER", "CRITICAL"],
            page_size=10,
        )

        return {
            "project": {
                "key": project.key,
                "name": project.name,
                "last_analysis": (
                    project.last_analysis_date.isoformat()
                    if project.last_analysis_date
                    else None
                ),
            },
            "measures": {m.metric: m.value for m in measures},
            "quality_gate": {
                "status": quality_gate.status,
                "is_passing": quality_gate.is_passing,
                "conditions": [
                    {
                        "metric": c.metric_key,
                        "status": c.status,
                        "actual": c.actual_value,
                        "threshold": c.error_threshold,
                    }
                    for c in quality_gate.conditions
                ],
            },
            "top_issues": [
                {
                    "key": i.key,
                    "rule": i.rule,
                    "severity": i.severity,
                    "message": i.message,
                    "component": i.component,
                    "line": i.line,
                }
                for i in top_issues
            ],
        }
