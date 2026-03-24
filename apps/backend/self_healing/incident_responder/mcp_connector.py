"""
MCP Connector for Production Monitoring
=========================================

Unified interface to connect with APM/monitoring MCP servers:
- Sentry
- Datadog
- CloudWatch
- New Relic
- PagerDuty

Each source is accessed via standard MCP protocol through external MCP servers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .models import IncidentSource, ProductionIncidentData

logger = logging.getLogger(__name__)


@dataclass
class MCPSourceConfig:
    """Configuration for a single MCP monitoring source."""

    source: IncidentSource = IncidentSource.SENTRY
    server_url: str = ""
    api_key: str | None = None
    project_id: str | None = None
    environment: str = "production"
    enabled: bool = True
    poll_interval_seconds: int = 60
    severity_filter: list[str] = field(default_factory=lambda: ["critical", "high"])
    extra_config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source.value,
            "server_url": self.server_url,
            "api_key": "***" if self.api_key else None,
            "project_id": self.project_id,
            "environment": self.environment,
            "enabled": self.enabled,
            "poll_interval_seconds": self.poll_interval_seconds,
            "severity_filter": self.severity_filter,
        }


class MCPSourceAdapter:
    """Base adapter for a monitoring MCP source.

    Each APM tool has a specific adapter that translates between
    the MCP server's tool calls and our standardized incident format.
    """

    def __init__(self, source: IncidentSource, config: MCPSourceConfig):
        self.source = source
        self.config = config
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> bool:
        """Establish connection to the MCP server."""
        if not self.config.server_url:
            logger.warning(f"No server URL configured for {self.source.value}")
            return False

        # MCP connection would be established via the Claude SDK's MCP support.
        # The actual connection is handled by the runtime when the agent starts.
        self._connected = True
        logger.info(f"MCP adapter connected: {self.source.value}")
        return True

    async def disconnect(self) -> bool:
        """Disconnect from the MCP server."""
        self._connected = False
        logger.info(f"MCP adapter disconnected: {self.source.value}")
        return True

    async def poll_incidents(self) -> list[ProductionIncidentData]:
        """Poll for new incidents from this source.

        In practice, this calls the MCP server's tools to list recent errors.
        The specific tool names depend on the MCP server implementation.
        """
        if not self._connected:
            return []

        # This is a framework method. Actual implementation would use
        # the MCP server tools via the Claude SDK runtime.
        return []

    async def get_incident_details(self, event_id: str) -> dict[str, Any] | None:
        """Get detailed information about a specific incident."""
        if not self._connected:
            return None
        return None

    def _normalize_severity(self, raw_severity: str) -> str:
        """Normalize severity from source-specific format to our enum."""
        severity_map = {
            # Sentry
            "fatal": "critical",
            "error": "high",
            "warning": "medium",
            "info": "info",
            # Datadog
            "alert": "critical",
            "warn": "medium",
            # CloudWatch
            "alarm": "critical",
            "insufficient_data": "info",
            "ok": "info",
            # PagerDuty
            "p1": "critical",
            "p2": "high",
            "p3": "medium",
            "p4": "low",
            "p5": "info",
        }
        normalized = raw_severity.lower().strip()
        return severity_map.get(normalized, normalized)


class SentryAdapter(MCPSourceAdapter):
    """Adapter for Sentry MCP server."""

    def __init__(self, config: MCPSourceConfig):
        super().__init__(IncidentSource.SENTRY, config)

    def _parse_sentry_event(self, event: dict[str, Any]) -> ProductionIncidentData:
        """Parse a Sentry event into our standard format."""
        exception = event.get("exception", {})
        values = exception.get("values", [{}])
        first_exc = values[0] if values else {}

        frames = first_exc.get("stacktrace", {}).get("frames", [])
        stack_lines = []
        for frame in reversed(frames):
            filename = frame.get("filename", "?")
            lineno = frame.get("lineno", "?")
            function = frame.get("function", "?")
            stack_lines.append(f'  File "{filename}", line {lineno}, in {function}')

        return ProductionIncidentData(
            error_type=first_exc.get("type", "Unknown"),
            error_message=first_exc.get("value", ""),
            stack_trace="\n".join(stack_lines),
            occurrence_count=event.get("count", 1),
            first_seen=event.get("firstSeen", ""),
            last_seen=event.get("lastSeen", ""),
            affected_users=event.get("userCount", 0),
            environment=self.config.environment,
            service_name=event.get("project", {}).get("slug"),
            event_url=event.get("permalink"),
        )


class DatadogAdapter(MCPSourceAdapter):
    """Adapter for Datadog MCP server."""

    def __init__(self, config: MCPSourceConfig):
        super().__init__(IncidentSource.DATADOG, config)


class CloudWatchAdapter(MCPSourceAdapter):
    """Adapter for AWS CloudWatch MCP server."""

    def __init__(self, config: MCPSourceConfig):
        super().__init__(IncidentSource.CLOUDWATCH, config)


class NewRelicAdapter(MCPSourceAdapter):
    """Adapter for New Relic MCP server."""

    def __init__(self, config: MCPSourceConfig):
        super().__init__(IncidentSource.NEW_RELIC, config)


class PagerDutyAdapter(MCPSourceAdapter):
    """Adapter for PagerDuty MCP server."""

    def __init__(self, config: MCPSourceConfig):
        super().__init__(IncidentSource.PAGERDUTY, config)


# Registry of adapter classes by source
_ADAPTER_REGISTRY: dict[IncidentSource, type[MCPSourceAdapter]] = {
    IncidentSource.SENTRY: SentryAdapter,
    IncidentSource.DATADOG: DatadogAdapter,
    IncidentSource.CLOUDWATCH: CloudWatchAdapter,
    IncidentSource.NEW_RELIC: NewRelicAdapter,
    IncidentSource.PAGERDUTY: PagerDutyAdapter,
}


class MCPConnector:
    """Unified interface to APM MCP servers.

    Manages connections to multiple monitoring sources and provides
    a standardized interface for polling and querying incidents.
    """

    def __init__(self):
        self._adapters: dict[IncidentSource, MCPSourceAdapter] = {}
        self._configs: dict[IncidentSource, MCPSourceConfig] = {}

    @property
    def connected_sources(self) -> list[IncidentSource]:
        return [s for s, a in self._adapters.items() if a.is_connected]

    async def connect_source(self, config: MCPSourceConfig) -> bool:
        """Connect to a monitoring source."""
        adapter_cls = _ADAPTER_REGISTRY.get(config.source)
        if not adapter_cls:
            logger.error(f"No adapter for source: {config.source.value}")
            return False

        adapter = adapter_cls(config)
        success = await adapter.connect()
        if success:
            self._adapters[config.source] = adapter
            self._configs[config.source] = config
            logger.info(f"Connected to {config.source.value}")
        return success

    async def disconnect_source(self, source: IncidentSource) -> bool:
        """Disconnect from a monitoring source."""
        adapter = self._adapters.get(source)
        if not adapter:
            return False

        success = await adapter.disconnect()
        if success:
            del self._adapters[source]
            self._configs.pop(source, None)
        return success

    async def poll_all(self) -> list[ProductionIncidentData]:
        """Poll all connected sources for new incidents."""
        all_incidents: list[ProductionIncidentData] = []
        for source, adapter in self._adapters.items():
            try:
                incidents = await adapter.poll_incidents()
                all_incidents.extend(incidents)
            except Exception as e:
                logger.error(f"Error polling {source.value}: {e}")
        return all_incidents

    async def poll_source(self, source: IncidentSource) -> list[ProductionIncidentData]:
        """Poll a specific source for new incidents."""
        adapter = self._adapters.get(source)
        if not adapter:
            return []
        try:
            return await adapter.poll_incidents()
        except Exception as e:
            logger.error(f"Error polling {source.value}: {e}")
            return []

    async def get_incident_details(
        self, source: IncidentSource, event_id: str
    ) -> dict[str, Any] | None:
        """Get detailed incident information from a specific source."""
        adapter = self._adapters.get(source)
        if not adapter:
            return None
        return await adapter.get_incident_details(event_id)

    def get_status(self) -> dict[str, Any]:
        """Get connector status for dashboard display."""
        return {
            "connected_sources": [s.value for s in self.connected_sources],
            "configs": {s.value: c.to_dict() for s, c in self._configs.items()},
        }
