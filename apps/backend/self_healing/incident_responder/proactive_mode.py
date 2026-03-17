"""
Proactive Mode - Predictive Analysis
======================================

Analyzes code fragility zones and generates preventive tests.
Uses the FragilityAnalyzer for metrics computation and an AI agent
for intelligent test generation targeting uncovered edge cases.

Flow:
1. scan_fragility() triggered on schedule or manually
2. FragilityAnalyzer computes per-file metrics
3. Files above risk threshold are flagged
4. Proactive analyzer agent generates preventive tests
5. Tests are committed in a PR for review
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .fragility_analyzer import FragilityAnalyzer
from .models import (
    FragilityReport,
    HealingStatus,
    Incident,
    IncidentMode,
    IncidentSeverity,
    IncidentSource,
)

logger = logging.getLogger(__name__)


class ProactiveMode:
    """Proactive code fragility analysis and preventive test generation."""

    def __init__(
        self,
        project_dir: str | Path,
        risk_threshold: float = 40.0,
        max_files: int = 100,
        churn_days: int = 30,
    ):
        self.project_dir = Path(project_dir)
        self.risk_threshold = risk_threshold
        self.max_files = max_files
        self.analyzer = FragilityAnalyzer(
            project_dir=project_dir,
            churn_days=churn_days,
        )
        self._last_reports: list[FragilityReport] = []

    async def scan_fragility(self) -> list[FragilityReport]:
        """Run fragility analysis on the project.

        Returns:
            List of FragilityReport for files above risk threshold,
            sorted by risk_score descending.
        """
        logger.info(
            f"Starting proactive fragility scan "
            f"(threshold={self.risk_threshold}, max_files={self.max_files})"
        )

        reports = await self.analyzer.analyze(
            max_files=self.max_files,
            risk_threshold=self.risk_threshold,
        )

        self._last_reports = reports
        logger.info(f"Fragility scan complete: {len(reports)} files above threshold")

        return reports

    async def create_incidents_from_scan(
        self,
        reports: list[FragilityReport] | None = None,
        top_n: int = 10,
    ) -> list[Incident]:
        """Create incidents for the most fragile files.

        Args:
            reports: Fragility reports to process. Uses last scan if None.
            top_n: Maximum number of incidents to create.

        Returns:
            List of Incident objects for the most fragile files.
        """
        reports = reports or self._last_reports
        if not reports:
            reports = await self.scan_fragility()

        incidents: list[Incident] = []
        for report in reports[:top_n]:
            severity = self._assess_fragility_severity(report)

            incident = Incident(
                mode=IncidentMode.PROACTIVE,
                source=IncidentSource.PROACTIVE_SCAN,
                severity=severity,
                title=f"Fragile code: {report.file_path} (risk {report.risk_score}/100)",
                description=(
                    f"File '{report.file_path}' has a high fragility risk score of {report.risk_score}/100. "
                    f"Cyclomatic complexity: {report.cyclomatic_complexity}, "
                    f"Git churn: {report.git_churn_count} commits in 30 days, "
                    f"Test coverage: {report.test_coverage_percent}%."
                ),
                status=HealingStatus.PENDING,
                source_data=report.to_dict(),
                affected_files=[report.file_path],
            )
            incidents.append(incident)

        logger.info(f"Created {len(incidents)} proactive incidents from fragility scan")
        return incidents

    def build_agent_prompt(self, incident: Incident) -> str:
        """Build the prompt for the proactive analyzer agent."""
        data = incident.source_data
        prompt_path = (
            Path(__file__).parent.parent.parent
            / "prompts"
            / "incident_proactive_analyzer.md"
        )

        try:
            template = prompt_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            template = self._fallback_prompt()

        replacements = {
            "{{FILE_PATH}}": data.get("file_path", ""),
            "{{RISK_SCORE}}": str(data.get("risk_score", 0)),
            "{{COMPLEXITY}}": str(data.get("cyclomatic_complexity", 0)),
            "{{CHURN_COUNT}}": str(data.get("git_churn_count", 0)),
            "{{COVERAGE_PERCENT}}": str(data.get("test_coverage_percent", 0)),
        }

        for key, value in replacements.items():
            template = template.replace(key, value)

        return template

    @property
    def last_reports(self) -> list[FragilityReport]:
        """Get the most recent fragility scan results."""
        return self._last_reports

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the last proactive scan."""
        if not self._last_reports:
            return {"scanned": False, "files_at_risk": 0, "avg_risk": 0.0}

        risk_scores = [r.risk_score for r in self._last_reports]
        return {
            "scanned": True,
            "files_at_risk": len(self._last_reports),
            "avg_risk": round(sum(risk_scores) / len(risk_scores), 1) if risk_scores else 0.0,
            "max_risk": max(risk_scores) if risk_scores else 0.0,
            "top_files": [
                {"file": r.file_path, "risk": r.risk_score}
                for r in self._last_reports[:5]
            ],
        }

    def _assess_fragility_severity(self, report: FragilityReport) -> IncidentSeverity:
        """Assess severity based on fragility metrics."""
        if report.risk_score >= 80:
            return IncidentSeverity.HIGH
        if report.risk_score >= 60:
            return IncidentSeverity.MEDIUM
        return IncidentSeverity.LOW

    def _fallback_prompt(self) -> str:
        return """## YOUR ROLE - PROACTIVE CODE ANALYZER

You analyze fragile code zones and generate preventive tests.

## TARGET FILE
- Path: {{FILE_PATH}}
- Risk score: {{RISK_SCORE}}/100
- Cyclomatic complexity: {{COMPLEXITY}}
- Git churn: {{CHURN_COUNT}} changes in 30 days
- Test coverage: {{COVERAGE_PERCENT}}%

## INSTRUCTIONS
1. Read and analyze the target file
2. Identify the most fragile functions/methods (complex logic, error-prone patterns)
3. Identify code paths lacking test coverage
4. Generate preventive tests targeting:
   - Error handling edge cases
   - Boundary conditions
   - Null/empty/invalid inputs
   - Race conditions (if applicable)
5. Follow the project's existing test patterns and frameworks
6. Ensure all generated tests pass on the current code
7. Commit with message: "test: add preventive tests for {{FILE_PATH}}"
"""
