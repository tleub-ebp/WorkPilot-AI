"""
Incident Parser — Extract structured data from APM incident payloads.

Supports Sentry, Datadog, CloudWatch, New Relic, PagerDuty, Grafana OnCall,
and OpsGenie webhook formats.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class IncidentSource(str, Enum):
    SENTRY = "sentry"
    DATADOG = "datadog"
    CLOUDWATCH = "cloudwatch"
    NEW_RELIC = "new_relic"
    PAGERDUTY = "pagerduty"
    GRAFANA = "grafana"
    OPSGENIE = "opsgenie"
    GENERIC = "generic"


class IncidentSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class StackFrame:
    """A single frame in a stack trace."""

    file: str = ""
    function: str = ""
    line: int = 0
    column: int = 0
    context: str = ""


@dataclass
class Incident:
    """Structured representation of a production incident."""

    id: str
    source: IncidentSource
    title: str
    severity: IncidentSeverity = IncidentSeverity.ERROR
    exception_type: str = ""
    exception_message: str = ""
    stack_frames: list[StackFrame] = field(default_factory=list)
    breadcrumbs: list[dict[str, Any]] = field(default_factory=list)
    request_payload: dict[str, Any] | None = None
    tags: dict[str, str] = field(default_factory=dict)
    service: str = ""
    environment: str = ""
    version: str = ""
    raw_payload: dict[str, Any] = field(default_factory=dict)

    @property
    def faulting_file(self) -> str | None:
        for frame in self.stack_frames:
            if frame.file and not _is_library_frame(frame.file):
                return frame.file
        return None

    @property
    def faulting_function(self) -> str | None:
        for frame in self.stack_frames:
            if frame.function and not _is_library_frame(frame.file):
                return frame.function
        return None


class IncidentParser:
    """Parse APM webhook payloads into structured Incident objects.

    Usage::

        parser = IncidentParser()
        incident = parser.parse(payload, source=IncidentSource.SENTRY)
    """

    def parse(
        self, payload: dict[str, Any], source: IncidentSource = IncidentSource.GENERIC
    ) -> Incident:
        """Parse a webhook payload into an Incident."""
        parsers = {
            IncidentSource.SENTRY: self._parse_sentry,
            IncidentSource.DATADOG: self._parse_datadog,
            IncidentSource.PAGERDUTY: self._parse_pagerduty,
            IncidentSource.NEW_RELIC: self._parse_new_relic,
            IncidentSource.CLOUDWATCH: self._parse_cloudwatch,
            IncidentSource.GRAFANA: self._parse_grafana,
            IncidentSource.OPSGENIE: self._parse_opsgenie,
        }
        parser_fn = parsers.get(source, self._parse_generic)
        return parser_fn(payload)

    def detect_source(self, payload: dict[str, Any]) -> IncidentSource:
        """Auto-detect the incident source from the payload structure."""
        if "event" in payload and "exception" in payload.get("event", {}):
            return IncidentSource.SENTRY
        if "alert_type" in payload or "event_type" in payload:
            return IncidentSource.DATADOG
        if "incident" in payload and "service" in payload.get("incident", {}):
            return IncidentSource.PAGERDUTY
        if "condition_name" in payload:
            return IncidentSource.NEW_RELIC
        if "AlarmName" in payload:
            return IncidentSource.CLOUDWATCH
        if "alerts" in payload:
            return IncidentSource.GRAFANA
        if "alert" in payload and "alertId" in payload.get("alert", {}):
            return IncidentSource.OPSGENIE
        return IncidentSource.GENERIC

    def _parse_sentry(self, payload: dict[str, Any]) -> Incident:
        event = payload.get("event", payload)
        exception = event.get("exception", {})
        values = exception.get("values", [{}])
        first_exc = values[0] if values else {}

        frames = []
        stacktrace = first_exc.get("stacktrace", {})
        for f in stacktrace.get("frames", []):
            frames.append(StackFrame(
                file=f.get("filename", ""),
                function=f.get("function", ""),
                line=f.get("lineno", 0),
                column=f.get("colno", 0),
                context=f.get("context_line", ""),
            ))
        frames.reverse()

        return Incident(
            id=event.get("event_id", payload.get("id", "unknown")),
            source=IncidentSource.SENTRY,
            title=event.get("title", first_exc.get("value", "Unknown error")),
            severity=self._map_sentry_level(event.get("level", "error")),
            exception_type=first_exc.get("type", ""),
            exception_message=first_exc.get("value", ""),
            stack_frames=frames,
            breadcrumbs=event.get("breadcrumbs", {}).get("values", []),
            request_payload=event.get("request"),
            tags={t[0]: t[1] for t in event.get("tags", []) if len(t) == 2},
            service=event.get("project", ""),
            environment=event.get("environment", ""),
            version=event.get("release", ""),
            raw_payload=payload,
        )

    def _parse_datadog(self, payload: dict[str, Any]) -> Incident:
        return Incident(
            id=str(payload.get("id", payload.get("alert_id", "unknown"))),
            source=IncidentSource.DATADOG,
            title=payload.get("title", payload.get("msg_title", "Datadog alert")),
            severity=self._map_datadog_priority(payload.get("priority", "normal")),
            exception_message=payload.get("body", payload.get("msg_text", "")),
            tags={
                k: v
                for t in payload.get("tags", [])
                if ":" in str(t)
                for k, v in [str(t).split(":", 1)]
            },
            service=payload.get("service", ""),
            raw_payload=payload,
        )

    def _parse_pagerduty(self, payload: dict[str, Any]) -> Incident:
        incident = payload.get("incident", payload)
        return Incident(
            id=str(incident.get("id", "unknown")),
            source=IncidentSource.PAGERDUTY,
            title=incident.get("title", "PagerDuty incident"),
            severity=self._map_pd_urgency(incident.get("urgency", "low")),
            exception_message=incident.get("description", ""),
            service=incident.get("service", {}).get("name", ""),
            raw_payload=payload,
        )

    def _parse_new_relic(self, payload: dict[str, Any]) -> Incident:
        return Incident(
            id=str(payload.get("incident_id", payload.get("id", "unknown"))),
            source=IncidentSource.NEW_RELIC,
            title=payload.get("condition_name", "New Relic alert"),
            severity=IncidentSeverity.ERROR,
            exception_message=payload.get("details", ""),
            service=payload.get("targets", [{}])[0].get("name", "") if payload.get("targets") else "",
            raw_payload=payload,
        )

    def _parse_cloudwatch(self, payload: dict[str, Any]) -> Incident:
        return Incident(
            id=payload.get("AlarmName", "unknown"),
            source=IncidentSource.CLOUDWATCH,
            title=payload.get("AlarmDescription", payload.get("AlarmName", "CloudWatch alarm")),
            severity=IncidentSeverity.ERROR if payload.get("NewStateValue") == "ALARM" else IncidentSeverity.WARNING,
            exception_message=payload.get("NewStateReason", ""),
            raw_payload=payload,
        )

    def _parse_grafana(self, payload: dict[str, Any]) -> Incident:
        alerts = payload.get("alerts", [{}])
        first = alerts[0] if alerts else {}
        return Incident(
            id=str(first.get("fingerprint", "unknown")),
            source=IncidentSource.GRAFANA,
            title=payload.get("title", first.get("labels", {}).get("alertname", "Grafana alert")),
            severity=IncidentSeverity.ERROR,
            exception_message=str(first.get("annotations", {}).get("description", "")),
            tags=first.get("labels", {}),
            raw_payload=payload,
        )

    def _parse_opsgenie(self, payload: dict[str, Any]) -> Incident:
        alert = payload.get("alert", payload)
        return Incident(
            id=str(alert.get("alertId", "unknown")),
            source=IncidentSource.OPSGENIE,
            title=alert.get("message", "OpsGenie alert"),
            severity=self._map_opsgenie_priority(alert.get("priority", "P3")),
            exception_message=alert.get("description", ""),
            tags=dict(alert.get("tags", [])) if isinstance(alert.get("tags"), list) else {},
            raw_payload=payload,
        )

    def _parse_generic(self, payload: dict[str, Any]) -> Incident:
        stack_text = payload.get("stacktrace", payload.get("stack_trace", ""))
        frames = _parse_stack_trace_text(stack_text) if stack_text else []
        return Incident(
            id=str(payload.get("id", "unknown")),
            source=IncidentSource.GENERIC,
            title=payload.get("title", payload.get("message", "Unknown incident")),
            severity=IncidentSeverity.ERROR,
            exception_message=payload.get("message", payload.get("error", "")),
            stack_frames=frames,
            raw_payload=payload,
        )

    @staticmethod
    def _map_sentry_level(level: str) -> IncidentSeverity:
        return {"fatal": IncidentSeverity.CRITICAL, "error": IncidentSeverity.ERROR,
                "warning": IncidentSeverity.WARNING, "info": IncidentSeverity.INFO}.get(level, IncidentSeverity.ERROR)

    @staticmethod
    def _map_datadog_priority(pri: str) -> IncidentSeverity:
        return {"low": IncidentSeverity.INFO, "normal": IncidentSeverity.WARNING,
                "high": IncidentSeverity.ERROR, "critical": IncidentSeverity.CRITICAL}.get(pri, IncidentSeverity.ERROR)

    @staticmethod
    def _map_pd_urgency(urgency: str) -> IncidentSeverity:
        return {"low": IncidentSeverity.WARNING, "high": IncidentSeverity.CRITICAL}.get(urgency, IncidentSeverity.ERROR)

    @staticmethod
    def _map_opsgenie_priority(pri: str) -> IncidentSeverity:
        return {"P1": IncidentSeverity.CRITICAL, "P2": IncidentSeverity.ERROR,
                "P3": IncidentSeverity.WARNING, "P4": IncidentSeverity.INFO, "P5": IncidentSeverity.INFO}.get(pri, IncidentSeverity.WARNING)


def _is_library_frame(filepath: str) -> bool:
    lib_markers = ["node_modules", "site-packages", "vendor", ".venv", "venv", "/lib/", "/dist/"]
    return any(m in filepath for m in lib_markers)


def _parse_stack_trace_text(text: str) -> list[StackFrame]:
    """Parse a plaintext stack trace into StackFrame objects."""
    frames: list[StackFrame] = []
    pattern = re.compile(r'File "([^"]+)", line (\d+)(?:, in (\w+))?')
    for match in pattern.finditer(text):
        frames.append(StackFrame(
            file=match.group(1),
            line=int(match.group(2)),
            function=match.group(3) or "",
        ))
    frames.reverse()
    return frames
