"""Data models for the SonarQube connector.

Defines dataclass representations for SonarQube entities including
projects, measures, issues, and quality gate statuses. Each model
includes factory methods for converting raw SonarQube API responses
into clean, typed data structures.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class SonarProject:
    """SonarQube project representation.

    Attributes:
        key: The unique project key (e.g., ``'my-org:my-project'``).
        name: The display name of the project.
        qualifier: The component qualifier (``'TRK'`` for projects).
        visibility: The project visibility (``'public'`` or ``'private'``).
        last_analysis_date: The date of the last analysis, or None.
        revision: The last analysis revision/commit SHA, or None.
    """

    key: str
    name: str
    qualifier: str = "TRK"
    visibility: str = "public"
    last_analysis_date: datetime | None = None
    revision: str | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "SonarProject":
        """Create a SonarProject from a SonarQube API response dict.

        Args:
            data: A dictionary from the SonarQube API ``/api/projects/search``
                or ``/api/components/show`` endpoints.

        Returns:
            A SonarProject instance populated from the API response.
        """
        last_analysis = data.get("lastAnalysisDate")
        parsed_date = None
        if last_analysis:
            try:
                parsed_date = datetime.fromisoformat(
                    last_analysis.replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                parsed_date = None

        return cls(
            key=data.get("key", ""),
            name=data.get("name", ""),
            qualifier=data.get("qualifier", "TRK"),
            visibility=data.get("visibility", "public"),
            last_analysis_date=parsed_date,
            revision=data.get("revision"),
        )


@dataclass
class SonarMeasure:
    """A single metric measurement for a SonarQube component.

    Attributes:
        metric: The metric key (e.g., ``'coverage'``, ``'bugs'``,
            ``'code_smells'``, ``'ncloc'``).
        value: The metric value as a string. Numeric values are
            returned as strings by the API.
        component: The component key this measure belongs to.
        best_value: Whether this is the best possible value, or None.
    """

    metric: str
    value: str
    component: str = ""
    best_value: bool | None = None

    @classmethod
    def from_api_response(
        cls, data: dict[str, Any], component: str = ""
    ) -> "SonarMeasure":
        """Create a SonarMeasure from a SonarQube API response dict.

        Args:
            data: A measure dictionary from the ``/api/measures/component``
                endpoint.
            component: The component key for context.

        Returns:
            A SonarMeasure instance.
        """
        return cls(
            metric=data.get("metric", ""),
            value=data.get("value", ""),
            component=component,
            best_value=data.get("bestValue"),
        )

    @property
    def numeric_value(self) -> float | None:
        """Parse the value as a float, or return None if not numeric."""
        try:
            return float(self.value)
        except (ValueError, TypeError):
            return None


@dataclass
class SonarIssue:
    """A SonarQube code issue (bug, vulnerability, code smell).

    Attributes:
        key: The unique issue key.
        rule: The rule key (e.g., ``'python:S1066'``).
        severity: The severity level (``'BLOCKER'``, ``'CRITICAL'``,
            ``'MAJOR'``, ``'MINOR'``, ``'INFO'``).
        component: The component key containing the issue.
        project: The project key.
        line: The line number where the issue occurs, or None.
        message: The issue description message.
        status: The issue status (``'OPEN'``, ``'CONFIRMED'``,
            ``'RESOLVED'``, ``'CLOSED'``).
        issue_type: The issue type (``'BUG'``, ``'VULNERABILITY'``,
            ``'CODE_SMELL'``).
        effort: The estimated effort to fix (e.g., ``'15min'``), or None.
        tags: Tags associated with the issue.
        creation_date: When the issue was created, or None.
    """

    key: str
    rule: str
    severity: str
    component: str
    project: str
    line: int | None = None
    message: str = ""
    status: str = "OPEN"
    issue_type: str = ""
    effort: str | None = None
    tags: list[str] = field(default_factory=list)
    creation_date: datetime | None = None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "SonarIssue":
        """Create a SonarIssue from a SonarQube API response dict.

        Args:
            data: An issue dictionary from the ``/api/issues/search``
                endpoint.

        Returns:
            A SonarIssue instance.
        """
        creation = data.get("creationDate")
        parsed_date = None
        if creation:
            try:
                parsed_date = datetime.fromisoformat(
                    creation.replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                parsed_date = None

        return cls(
            key=data.get("key", ""),
            rule=data.get("rule", ""),
            severity=data.get("severity", ""),
            component=data.get("component", ""),
            project=data.get("project", ""),
            line=data.get("line"),
            message=data.get("message", ""),
            status=data.get("status", "OPEN"),
            issue_type=data.get("type", ""),
            effort=data.get("effort"),
            tags=data.get("tags", []),
            creation_date=parsed_date,
        )


@dataclass
class QualityGateCondition:
    """A single condition within a quality gate evaluation.

    Attributes:
        metric_key: The metric being evaluated (e.g., ``'new_coverage'``).
        comparator: The comparison operator (``'GT'``, ``'LT'``).
        error_threshold: The threshold value that triggers an error.
        actual_value: The actual measured value.
        status: The condition status (``'OK'``, ``'ERROR'``).
    """

    metric_key: str
    comparator: str
    error_threshold: str
    actual_value: str
    status: str

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "QualityGateCondition":
        """Create a QualityGateCondition from a SonarQube API response dict.

        Args:
            data: A condition dictionary from the
                ``/api/qualitygates/project_status`` endpoint.

        Returns:
            A QualityGateCondition instance.
        """
        return cls(
            metric_key=data.get("metricKey", ""),
            comparator=data.get("comparator", ""),
            error_threshold=data.get("errorThreshold", ""),
            actual_value=data.get("actualValue", ""),
            status=data.get("status", ""),
        )


@dataclass
class QualityGateStatus:
    """Quality gate evaluation result for a project.

    Attributes:
        project_key: The project key that was evaluated.
        status: The overall quality gate status (``'OK'``, ``'ERROR'``,
            ``'WARN'``, ``'NONE'``).
        conditions: The list of individual condition evaluations.
    """

    project_key: str
    status: str
    conditions: list[QualityGateCondition] = field(default_factory=list)

    @property
    def is_passing(self) -> bool:
        """Return True if the quality gate is passing (status is OK)."""
        return self.status == "OK"

    @classmethod
    def from_api_response(
        cls, data: dict[str, Any], project_key: str = ""
    ) -> "QualityGateStatus":
        """Create a QualityGateStatus from a SonarQube API response dict.

        Args:
            data: The ``projectStatus`` dict from the
                ``/api/qualitygates/project_status`` endpoint.
            project_key: The project key for context.

        Returns:
            A QualityGateStatus instance.
        """
        conditions = [
            QualityGateCondition.from_api_response(c)
            for c in data.get("conditions", [])
        ]

        return cls(
            project_key=project_key,
            status=data.get("status", "NONE"),
            conditions=conditions,
        )
