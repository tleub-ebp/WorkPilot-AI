"""
Regression Guardian — Auto-generate regression tests from production incidents.

Each incident from Sentry/Datadog/CloudWatch/New Relic/PagerDuty becomes
a regression test.  The agent parses the stack trace, generates a failing
test, and once fixed the test joins the permanent regression suite.

Modules:
    - incident_parser: parse webhook payloads from multiple APM sources
    - test_generator: generate framework-appropriate regression tests
    - fixture_builder: extract and sanitise test fixtures from incidents
    - dedup_checker: avoid duplicate tests for the same root cause
    - webhook_handler: end-to-end pipeline from webhook to test
"""

from .dedup_checker import DedupChecker, DedupResult
from .fixture_builder import Fixture, FixtureBuilder
from .incident_parser import (
    Incident,
    IncidentParser,
    IncidentSeverity,
    IncidentSource,
    StackFrame,
)
from .test_generator import GeneratedTest, TestFramework, TestGenerator, TestStatus
from .webhook_handler import PipelineResult, PipelineStatus, WebhookHandler

__all__ = [
    "IncidentParser",
    "Incident",
    "IncidentSource",
    "IncidentSeverity",
    "StackFrame",
    "TestGenerator",
    "GeneratedTest",
    "TestFramework",
    "TestStatus",
    "FixtureBuilder",
    "Fixture",
    "DedupChecker",
    "DedupResult",
    "WebhookHandler",
    "PipelineResult",
    "PipelineStatus",
]
