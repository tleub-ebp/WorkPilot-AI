"""Unit tests for SonarQubeConnector high-level operations (Feature 4.4).

Tests the SonarQube connector including:
- Listing projects
- Getting project details
- Retrieving measures/metrics
- Checking quality gate status
- Searching issues
- Building project summaries
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# Helper function to import modules directly
def import_module_direct(module_name, file_path):
    """Import a module directly from file path, bypassing package __init__.py"""
    import importlib.util
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Import modules directly to avoid circular import issues in __init__.py
project_root = Path(__file__).parent.parent.parent.parent

# Define paths
connector_path = project_root / "src" / "connectors" / "sonarqube" / "connector.py"

# Import dependencies first
exceptions_module = import_module_direct("sonarqube_exceptions", project_root / "src" / "connectors" / "sonarqube" / "exceptions.py")
models_module = import_module_direct("sonarqube_models", project_root / "src" / "connectors" / "sonarqube" / "models.py")
client_module = import_module_direct("sonarqube_client", project_root / "src" / "connectors" / "sonarqube" / "client.py")

# Make modules available in sys.modules so connector can import them
sonarqube_package = type('Package', (), {
    'exceptions': exceptions_module,
    'models': models_module,
    'client': client_module
})()
sys.modules["src.connectors.sonarqube.exceptions"] = exceptions_module
sys.modules["src.connectors.sonarqube.models"] = models_module
sys.modules["src.connectors.sonarqube.client"] = client_module
sys.modules["src.connectors.sonarqube"] = sonarqube_package

# Create parent package structure
if "src.connectors" not in sys.modules:
    sys.modules["src.connectors"] = type('Package', (), {})()
connectors_package = sys.modules["src.connectors"]
if not hasattr(connectors_package, 'sonarqube'):
    connectors_package.sonarqube = sonarqube_package

# Now import connector
SonarQubeConnector = import_module_direct("SonarQubeConnector", str(connector_path)).SonarQubeConnector

QualityGateCondition = models_module.QualityGateCondition
QualityGateStatus = models_module.QualityGateStatus
SonarIssue = models_module.SonarIssue
SonarMeasure = models_module.SonarMeasure
SonarProject = models_module.SonarProject

# Helper function to check object attributes instead of exact type
def check_sonar_object(obj, expected_type, required_attrs=None):
    """Check if an object has the expected attributes for a SonarQube model."""
    if required_attrs is None:
        # Map expected types to their required attributes
        attr_map = {
            'SonarProject': ['key', 'name'],
            'SonarMeasure': ['metric'],
            'QualityGateStatus': ['project_key', 'status'],
            'SonarIssue': ['key', 'rule'],
            'QualityGateCondition': ['metric_key', 'status'],
        }
        required_attrs = attr_map.get(expected_type.__name__, [])
    
    return all(hasattr(obj, attr) for attr in required_attrs)


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def mock_sonar_client():
    """Create a mock SonarQubeClient."""
    client = MagicMock()
    client.is_connected = True
    return client


@pytest.fixture
def connector(mock_sonar_client):
    """Create a SonarQubeConnector with a mocked client."""
    return SonarQubeConnector(mock_sonar_client)


# ── list_projects tests ──────────────────────────────────────────


class TestListProjects:
    """Tests for SonarQubeConnector.list_projects()."""

    def test_returns_projects(self, connector, mock_sonar_client):
        """list_projects() returns a list of SonarProject objects."""
        mock_sonar_client.get.return_value = {
            "components": [
                {"key": "proj1", "name": "Project One", "qualifier": "TRK"},
                {"key": "proj2", "name": "Project Two", "qualifier": "TRK"},
            ]
        }

        result = connector.list_projects()

        assert len(result) == 2
        assert all(check_sonar_object(p, SonarProject) for p in result)
        assert result[0].key == "proj1"
        assert result[1].name == "Project Two"

    def test_returns_empty_list(self, connector, mock_sonar_client):
        """list_projects() returns empty list when no projects exist."""
        mock_sonar_client.get.return_value = {"components": []}

        result = connector.list_projects()

        assert result == []

    def test_passes_pagination_params(self, connector, mock_sonar_client):
        """list_projects() passes page size and page number."""
        mock_sonar_client.get.return_value = {"components": []}

        connector.list_projects(page_size=50, page=3)

        mock_sonar_client.get.assert_called_once_with(
            "/api/projects/search",
            params={"ps": 50, "p": 3},
        )


# ── get_project tests ────────────────────────────────────────────


class TestGetProject:
    """Tests for SonarQubeConnector.get_project()."""

    def test_returns_project(self, connector, mock_sonar_client):
        """get_project() returns a SonarProject for a valid key."""
        mock_sonar_client.get.return_value = {
            "component": {
                "key": "my-project",
                "name": "My Project",
                "qualifier": "TRK",
                "visibility": "private",
            }
        }

        result = connector.get_project("my-project")

        assert check_sonar_object(result, SonarProject)
        assert result.key == "my-project"
        assert result.visibility == "private"


# ── get_measures tests ───────────────────────────────────────────


class TestGetMeasures:
    """Tests for SonarQubeConnector.get_measures()."""

    def test_returns_measures(self, connector, mock_sonar_client):
        """get_measures() returns a list of SonarMeasure objects."""
        mock_sonar_client.get.return_value = {
            "component": {
                "key": "my-project",
                "measures": [
                    {"metric": "bugs", "value": "3"},
                    {"metric": "coverage", "value": "82.5"},
                ],
            }
        }

        result = connector.get_measures("my-project")

        assert len(result) == 2
        assert all(check_sonar_object(m, SonarMeasure) for m in result)
        assert result[0].metric == "bugs"
        assert result[0].value == "3"
        import math
        assert math.isclose(result[1].numeric_value, 82.5, rel_tol=1e-9)

    def test_uses_default_metrics(self, connector, mock_sonar_client):
        """get_measures() uses DEFAULT_METRICS when none specified."""
        mock_sonar_client.get.return_value = {"component": {"measures": []}}

        connector.get_measures("my-project")

        call_params = mock_sonar_client.get.call_args.kwargs["params"]
        assert "bugs" in call_params["metricKeys"]
        assert "coverage" in call_params["metricKeys"]

    def test_uses_custom_metrics(self, connector, mock_sonar_client):
        """get_measures() uses custom metrics when provided."""
        mock_sonar_client.get.return_value = {"component": {"measures": []}}

        connector.get_measures("my-project", metric_keys=["ncloc", "complexity"])

        call_params = mock_sonar_client.get.call_args.kwargs["params"]
        assert call_params["metricKeys"] == "ncloc,complexity"


# ── get_quality_gate_status tests ────────────────────────────────


class TestGetQualityGateStatus:
    """Tests for SonarQubeConnector.get_quality_gate_status()."""

    def test_returns_passing_status(self, connector, mock_sonar_client):
        """get_quality_gate_status() returns OK status."""
        mock_sonar_client.get.return_value = {
            "projectStatus": {
                "status": "OK",
                "conditions": [
                    {
                        "status": "OK",
                        "metricKey": "new_coverage",
                        "comparator": "LT",
                        "errorThreshold": "80",
                        "actualValue": "85.3",
                    }
                ],
            }
        }

        result = connector.get_quality_gate_status("my-project")

        assert check_sonar_object(result, QualityGateStatus)
        assert result.status == "OK"
        assert result.is_passing is True
        assert len(result.conditions) == 1
        assert result.conditions[0].metric_key == "new_coverage"

    def test_returns_failing_status(self, connector, mock_sonar_client):
        """get_quality_gate_status() returns ERROR status."""
        mock_sonar_client.get.return_value = {
            "projectStatus": {
                "status": "ERROR",
                "conditions": [
                    {
                        "status": "ERROR",
                        "metricKey": "new_coverage",
                        "comparator": "LT",
                        "errorThreshold": "80",
                        "actualValue": "45.0",
                    }
                ],
            }
        }

        result = connector.get_quality_gate_status("my-project")

        assert result.status == "ERROR"
        assert result.is_passing is False

    def test_passes_branch_param(self, connector, mock_sonar_client):
        """get_quality_gate_status() passes branch parameter."""
        mock_sonar_client.get.return_value = {
            "projectStatus": {"status": "OK", "conditions": []}
        }

        connector.get_quality_gate_status("my-project", branch="develop")

        call_params = mock_sonar_client.get.call_args.kwargs["params"]
        assert call_params["branch"] == "develop"

    def test_passes_pull_request_param(self, connector, mock_sonar_client):
        """get_quality_gate_status() passes PR parameter."""
        mock_sonar_client.get.return_value = {
            "projectStatus": {"status": "OK", "conditions": []}
        }

        connector.get_quality_gate_status("my-project", pull_request="123")

        call_params = mock_sonar_client.get.call_args.kwargs["params"]
        assert call_params["pullRequest"] == "123"


# ── get_issues tests ─────────────────────────────────────────────


class TestGetIssues:
    """Tests for SonarQubeConnector.get_issues()."""

    def test_returns_issues(self, connector, mock_sonar_client):
        """get_issues() returns a list of SonarIssue objects."""
        mock_sonar_client.get.return_value = {
            "issues": [
                {
                    "key": "issue-1",
                    "rule": "python:S1066",
                    "severity": "MAJOR",
                    "component": "my-project:src/main.py",
                    "project": "my-project",
                    "line": 42,
                    "message": "Merge this if statement",
                    "status": "OPEN",
                    "type": "CODE_SMELL",
                },
            ],
            "total": 1,
        }

        result = connector.get_issues("my-project")

        assert len(result) == 1
        assert check_sonar_object(result[0], SonarIssue)
        assert result[0].key == "issue-1"
        assert result[0].severity == "MAJOR"
        assert result[0].line == 42

    def test_passes_filter_params(self, connector, mock_sonar_client):
        """get_issues() passes severity, type, and status filters."""
        mock_sonar_client.get.return_value = {"issues": [], "total": 0}

        connector.get_issues(
            "my-project",
            severities=["BLOCKER", "CRITICAL"],
            issue_types=["BUG"],
            statuses=["OPEN"],
            branch="main",
        )

        call_params = mock_sonar_client.get.call_args.kwargs["params"]
        assert call_params["severities"] == "BLOCKER,CRITICAL"
        assert call_params["types"] == "BUG"
        assert call_params["statuses"] == "OPEN"
        assert call_params["branch"] == "main"

    def test_returns_empty_list(self, connector, mock_sonar_client):
        """get_issues() returns empty list when no issues match."""
        mock_sonar_client.get.return_value = {"issues": [], "total": 0}

        result = connector.get_issues("my-project")

        assert result == []


# ── get_project_summary tests ────────────────────────────────────


class TestGetProjectSummary:
    """Tests for SonarQubeConnector.get_project_summary()."""

    def test_returns_complete_summary(self, connector, mock_sonar_client):
        """get_project_summary() aggregates project info, measures, gate, issues."""
        # Mock 4 sequential API calls
        mock_sonar_client.get.side_effect = [
            # get_project
            {"component": {"key": "proj", "name": "My Project"}},
            # get_measures
            {
                "component": {
                    "measures": [
                        {"metric": "bugs", "value": "5"},
                        {"metric": "coverage", "value": "80"},
                    ]
                }
            },
            # get_quality_gate_status
            {
                "projectStatus": {
                    "status": "OK",
                    "conditions": [],
                }
            },
            # get_issues (BLOCKER + CRITICAL)
            {"issues": [], "total": 0},
        ]

        result = connector.get_project_summary("proj")

        assert result["project"]["key"] == "proj"
        assert result["project"]["name"] == "My Project"
        assert result["measures"]["bugs"] == "5"
        assert result["measures"]["coverage"] == "80"
        assert result["quality_gate"]["status"] == "OK"
        assert result["quality_gate"]["is_passing"] is True
        assert result["top_issues"] == []


# ── Model unit tests ─────────────────────────────────────────────


class TestSonarModels:
    """Direct unit tests for SonarQube data models."""

    def test_sonar_measure_numeric_value(self):
        """SonarMeasure.numeric_value parses float values."""
        m = SonarMeasure(metric="coverage", value="82.5")
        import math
        assert math.isclose(m.numeric_value, 82.5, rel_tol=1e-9)

    def test_sonar_measure_non_numeric_value(self):
        """SonarMeasure.numeric_value returns None for non-numeric."""
        m = SonarMeasure(metric="quality_gate", value="OK")
        assert m.numeric_value is None

    def test_quality_gate_is_passing(self):
        """QualityGateStatus.is_passing returns True for OK."""
        qs = QualityGateStatus(project_key="p", status="OK")
        assert qs.is_passing is True

    def test_quality_gate_is_not_passing(self):
        """QualityGateStatus.is_passing returns False for ERROR."""
        qs = QualityGateStatus(project_key="p", status="ERROR")
        assert qs.is_passing is False

    def test_sonar_project_from_api_with_date(self):
        """SonarProject parses lastAnalysisDate correctly."""
        p = SonarProject.from_api_response({
            "key": "proj",
            "name": "Project",
            "lastAnalysisDate": "2026-01-15T10:30:00+0000",
        })
        assert p.last_analysis_date is not None

    def test_sonar_issue_from_api(self):
        """SonarIssue.from_api_response maps all fields."""
        issue = SonarIssue.from_api_response({
            "key": "k1",
            "rule": "python:S1066",
            "severity": "CRITICAL",
            "component": "proj:src/main.py",
            "project": "proj",
            "line": 10,
            "message": "Fix this",
            "status": "OPEN",
            "type": "BUG",
            "effort": "15min",
            "tags": ["security"],
        })
        assert issue.key == "k1"
        assert issue.issue_type == "BUG"
        assert issue.effort == "15min"
        assert issue.tags == ["security"]
