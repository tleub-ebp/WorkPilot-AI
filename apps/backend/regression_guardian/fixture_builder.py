"""
Fixture Builder — Generate test fixtures from incident data.

Extracts request payloads, DB state snapshots, and environment context
from incident data and produces sanitised fixture files.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from .incident_parser import Incident

logger = logging.getLogger(__name__)

_PII_PATTERNS = [
    (
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        "redacted@example.com",
    ),
    (re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"), "000-000-0000"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "000-00-0000"),
    (
        re.compile(
            r"(?i)(password|secret|token|api_key|apikey|auth)[\"']?\s*[:=]\s*[\"']?[^\s,;\"']+"
        ),
        "REDACTED",
    ),
]


@dataclass
class Fixture:
    """A generated test fixture."""

    name: str
    data: dict[str, Any] = field(default_factory=dict)
    file_path: str = ""
    format: str = "json"
    sanitised: bool = False


class FixtureBuilder:
    """Build test fixtures from incident context.

    Usage::

        builder = FixtureBuilder()
        fixtures = builder.build(incident)
    """

    def __init__(self, redact_pii: bool = True) -> None:
        self._redact_pii = redact_pii

    def build(self, incident: Incident) -> list[Fixture]:
        """Build all available fixtures from the incident."""
        fixtures: list[Fixture] = []

        if incident.request_payload:
            fixtures.append(self._build_request_fixture(incident))

        if incident.breadcrumbs:
            fixtures.append(self._build_breadcrumb_fixture(incident))

        fixtures.append(self._build_context_fixture(incident))

        return fixtures

    def _build_request_fixture(self, incident: Incident) -> Fixture:
        payload = dict(incident.request_payload) if incident.request_payload else {}
        if self._redact_pii:
            payload = _redact_dict(payload)

        name = f"request_{_fixture_slug(incident)}"
        return Fixture(
            name=name,
            data=payload,
            file_path=f"tests/fixtures/regression/{name}.json",
            sanitised=self._redact_pii,
        )

    def _build_breadcrumb_fixture(self, incident: Incident) -> Fixture:
        crumbs = list(incident.breadcrumbs)
        if self._redact_pii:
            crumbs = [_redact_dict(c) if isinstance(c, dict) else c for c in crumbs]

        name = f"breadcrumbs_{_fixture_slug(incident)}"
        return Fixture(
            name=name,
            data={"breadcrumbs": crumbs},
            file_path=f"tests/fixtures/regression/{name}.json",
            sanitised=self._redact_pii,
        )

    def _build_context_fixture(self, incident: Incident) -> Fixture:
        """Build a context fixture with environment and service info."""
        name = f"context_{_fixture_slug(incident)}"
        return Fixture(
            name=name,
            data={
                "incident_id": incident.id,
                "source": incident.source.value,
                "service": incident.service,
                "environment": incident.environment,
                "version": incident.version,
                "exception_type": incident.exception_type,
                "exception_message": _redact_string(incident.exception_message)
                if self._redact_pii
                else incident.exception_message,
                "faulting_file": incident.faulting_file,
                "faulting_function": incident.faulting_function,
                "tags": incident.tags,
            },
            file_path=f"tests/fixtures/regression/{name}.json",
            sanitised=self._redact_pii,
        )

    def to_json(self, fixture: Fixture) -> str:
        """Serialise a fixture to JSON."""
        return json.dumps(fixture.data, indent=2, default=str)


# ------------------------------------------------------------------
# PII redaction helpers
# ------------------------------------------------------------------


def _redact_string(value: str) -> str:
    result = value
    for pattern, replacement in _PII_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def _redact_dict(data: dict[str, Any]) -> dict[str, Any]:
    sensitive_keys = {
        "password",
        "secret",
        "token",
        "api_key",
        "apikey",
        "authorization",
        "cookie",
        "ssn",
        "credit_card",
    }
    result: dict[str, Any] = {}
    for k, v in data.items():
        if k.lower() in sensitive_keys:
            result[k] = "REDACTED"
        elif isinstance(v, str):
            result[k] = _redact_string(v)
        elif isinstance(v, dict):
            result[k] = _redact_dict(v)
        elif isinstance(v, list):
            result[k] = [_redact_dict(i) if isinstance(i, dict) else i for i in v]
        else:
            result[k] = v
    return result


def _fixture_slug(incident: Incident) -> str:
    raw = f"{incident.id}_{incident.faulting_function or 'unknown'}"
    safe = re.sub(r"[^a-zA-Z0-9]", "_", raw).strip("_").lower()
    return safe[:60]
