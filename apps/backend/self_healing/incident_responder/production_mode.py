"""
Production Mode - Incident Responder
======================================

Connects to APM tools (Sentry, Datadog, CloudWatch, New Relic, PagerDuty)
via MCP servers. Detects production errors in real-time, correlates with
source code, identifies root cause, and generates fixes with regression tests.

Flow:
1. MCPConnector polls or receives incidents from APM tools
2. on_incident() creates Incident with production context
3. Correlates stack trace with source files
4. Launches production responder agent
5. Agent generates fix + regression test in isolated worktree
6. QA validates -> PR with [hotfix] label
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any

from .mcp_connector import MCPConnector, MCPSourceConfig
from .models import (
    HealingStatus,
    Incident,
    IncidentMode,
    IncidentSeverity,
    IncidentSource,
    ProductionIncidentData,
)

logger = logging.getLogger(__name__)


class ProductionMode:
    """Production incident detection and response mode."""

    def __init__(self, project_dir: str | Path):
        self.project_dir = Path(project_dir)
        self.connector = MCPConnector()

    async def connect_source(self, config: MCPSourceConfig) -> bool:
        """Connect to a monitoring source."""
        return await self.connector.connect_source(config)

    async def disconnect_source(self, source: IncidentSource) -> bool:
        """Disconnect from a monitoring source."""
        return await self.connector.disconnect_source(source)

    async def poll_incidents(self) -> list[Incident]:
        """Poll all connected sources for new incidents.

        Returns:
            List of new Incident objects from production monitoring.
        """
        raw_incidents = await self.connector.poll_all()
        incidents: list[Incident] = []

        for raw in raw_incidents:
            incident = self._create_incident_from_production_data(raw)
            incidents.append(incident)

        return incidents

    async def on_incident(
        self,
        source: IncidentSource,
        error_data: dict[str, Any],
    ) -> Incident:
        """Handle an incoming production incident.

        Args:
            source: Which monitoring source reported the incident.
            error_data: Raw error data from the source.

        Returns:
            Created Incident ready for healing.
        """
        prod_data = ProductionIncidentData(
            error_type=error_data.get("error_type", "Unknown"),
            error_message=error_data.get("error_message", ""),
            stack_trace=error_data.get("stack_trace", ""),
            occurrence_count=error_data.get("occurrence_count", 1),
            first_seen=error_data.get("first_seen", ""),
            last_seen=error_data.get("last_seen", ""),
            affected_users=error_data.get("affected_users", 0),
            environment=error_data.get("environment", "production"),
            service_name=error_data.get("service_name"),
            event_url=error_data.get("event_url"),
        )

        # Determine severity
        severity = self._assess_severity(prod_data)

        # Correlate with source files
        affected_files = self._correlate_stack_trace(prod_data.stack_trace)

        incident = Incident(
            mode=IncidentMode.PRODUCTION,
            source=source,
            severity=severity,
            title=f"[{source.value}] {prod_data.error_type}: {prod_data.error_message[:100]}",
            description=(
                f"Production error detected by {source.value}. "
                f"Type: {prod_data.error_type}. "
                f"Occurrences: {prod_data.occurrence_count}. "
                f"Affected users: {prod_data.affected_users}."
            ),
            status=HealingStatus.PENDING,
            source_data=prod_data.to_dict(),
            affected_files=affected_files,
            error_message=prod_data.error_message,
            stack_trace=prod_data.stack_trace,
        )

        logger.info(
            f"Production incident created: {incident.title} "
            f"(severity={severity.value}, files={len(affected_files)})"
        )
        return incident

    def build_agent_prompt(self, incident: Incident) -> str:
        """Build the prompt for the production incident responder agent."""
        data = incident.source_data
        prompt_path = (
            Path(__file__).parent.parent.parent
            / "prompts"
            / "incident_production_responder.md"
        )

        try:
            template = prompt_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            template = self._fallback_prompt()

        replacements = {
            "{{ERROR_TYPE}}": data.get("error_type", "Unknown"),
            "{{ERROR_MESSAGE}}": data.get("error_message", ""),
            "{{STACK_TRACE}}": data.get("stack_trace", "No stack trace"),
            "{{OCCURRENCE_COUNT}}": str(data.get("occurrence_count", 1)),
            "{{FIRST_SEEN}}": data.get("first_seen", ""),
            "{{LAST_SEEN}}": data.get("last_seen", ""),
            "{{AFFECTED_USERS}}": str(data.get("affected_users", 0)),
            "{{ENVIRONMENT}}": data.get("environment", "production"),
            "{{SERVICE_NAME}}": data.get("service_name", "unknown"),
            "{{AFFECTED_FILES}}": "\n".join(f"- {f}" for f in incident.affected_files),
        }

        for key, value in replacements.items():
            template = template.replace(key, value)

        return template

    def _create_incident_from_production_data(
        self, data: ProductionIncidentData
    ) -> Incident:
        """Create an Incident from raw production data."""
        severity = self._assess_severity(data)
        affected_files = self._correlate_stack_trace(data.stack_trace)

        source = IncidentSource.SENTRY  # Default, overridden by connector
        if data.service_name:
            for src in IncidentSource:
                if src.value in (data.service_name or "").lower():
                    source = src
                    break

        return Incident(
            mode=IncidentMode.PRODUCTION,
            source=source,
            severity=severity,
            title=f"{data.error_type}: {data.error_message[:100]}",
            description=f"Occurrences: {data.occurrence_count}, Users: {data.affected_users}",
            status=HealingStatus.PENDING,
            source_data=data.to_dict(),
            affected_files=affected_files,
            error_message=data.error_message,
            stack_trace=data.stack_trace,
        )

    def _assess_severity(self, data: ProductionIncidentData) -> IncidentSeverity:
        """Assess incident severity based on production impact."""
        if data.affected_users > 100 or data.occurrence_count > 1000:
            return IncidentSeverity.CRITICAL
        if data.affected_users > 10 or data.occurrence_count > 100:
            return IncidentSeverity.HIGH
        if data.occurrence_count > 10:
            return IncidentSeverity.MEDIUM
        return IncidentSeverity.LOW

    def _correlate_stack_trace(self, stack_trace: str) -> list[str]:
        """Extract file paths from a stack trace and match with project files."""
        if not stack_trace:
            return []

        import re

        # Match common stack trace file patterns
        patterns = [
            r'File "([^"]+)", line \d+',  # Python
            r"at\s+(?:\S+\s+\()?(/[^\s:)]+):\d+",  # Node.js
            r"at\s+(?:\S+\s+\()?([^\s:)]+\.(?:ts|js|tsx|jsx)):\d+",  # JS relative
            r"(\S+\.(?:go|rs|java|rb)):\d+",  # Go/Rust/Java/Ruby
        ]

        found_files: list[str] = []
        for pattern in patterns:
            for match in re.finditer(pattern, stack_trace):
                file_path = match.group(1)
                # Try to resolve relative to project
                resolved = self._resolve_project_file(file_path)
                if resolved and resolved not in found_files:
                    found_files.append(resolved)

        return found_files[:20]  # Limit to 20 files

    def _resolve_project_file(self, file_path: str) -> str | None:
        """Resolve a file path to a project-relative path."""
        path = Path(file_path)

        # Already relative and exists in project
        if (self.project_dir / path).exists():
            return str(path)

        # Absolute path - make relative
        try:
            rel = path.relative_to(self.project_dir)
            if (self.project_dir / rel).exists():
                return str(rel)
        except ValueError:
            pass

        # Try finding by filename
        name = path.name
        try:
            result = subprocess.run(
                ["git", "ls-files", f"*/{name}"],
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                timeout=10,
            )
            matches = result.stdout.strip().splitlines()
            if len(matches) == 1:
                return matches[0]
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass

        return None

    def get_status(self) -> dict[str, Any]:
        """Get production mode status for the dashboard."""
        return {
            "connector": self.connector.get_status(),
            "connected_sources": [s.value for s in self.connector.connected_sources],
        }

    def _fallback_prompt(self) -> str:
        return """## YOUR ROLE - PRODUCTION INCIDENT RESPONDER

You analyze production errors and generate fixes with regression tests.

## ERROR DETAILS
- Type: {{ERROR_TYPE}}
- Message: {{ERROR_MESSAGE}}
- Occurrences: {{OCCURRENCE_COUNT}} since {{FIRST_SEEN}}
- Affected users: {{AFFECTED_USERS}}
- Environment: {{ENVIRONMENT}}

## STACK TRACE
{{STACK_TRACE}}

## AFFECTED FILES
{{AFFECTED_FILES}}

## INSTRUCTIONS
1. Parse the stack trace to identify the root cause
2. Read the affected source files
3. Generate a fix for the root cause
4. Write a regression test that reproduces the error
5. Ensure the test fails without fix, passes with fix
6. Commit with message: "hotfix: {{ERROR_TYPE}} - [short description]"
"""
