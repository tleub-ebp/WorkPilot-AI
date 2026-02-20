"""SonarQube / SonarCloud connector — Integration with code quality analysis.

Provides a unified interface for interacting with SonarQube or SonarCloud
services, including project metrics, quality gates, issues tracking, and
source code analysis via a single ``SonarQubeConnector`` class.

The connector communicates with the SonarQube Web API using token-based
authentication and maps all responses to clean Python dataclasses.

Example:
    >>> from src.connectors.sonarqube import SonarQubeConnector
    >>> connector = SonarQubeConnector.from_env()
    >>> projects = connector.list_projects()
    >>> status = connector.get_quality_gate_status("my-project-key")
"""

from src.connectors.sonarqube.client import SonarQubeClient
from src.connectors.sonarqube.connector import SonarQubeConnector
from src.connectors.sonarqube.exceptions import (
    SonarQubeAPIError,
    SonarQubeAuthenticationError,
    SonarQubeConfigurationError,
    SonarQubeError,
    SonarQubeProjectNotFoundError,
)
from src.connectors.sonarqube.models import (
    QualityGateCondition,
    QualityGateStatus,
    SonarIssue,
    SonarMeasure,
    SonarProject,
)

__all__ = [
    # Main connector
    "SonarQubeConnector",
    # Underlying client
    "SonarQubeClient",
    # Data models
    "SonarProject",
    "SonarMeasure",
    "SonarIssue",
    "QualityGateStatus",
    "QualityGateCondition",
    # Exceptions
    "SonarQubeError",
    "SonarQubeAuthenticationError",
    "SonarQubeConfigurationError",
    "SonarQubeAPIError",
    "SonarQubeProjectNotFoundError",
]
