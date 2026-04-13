"""
Compliance Evidence Collector — Auto-collect audit evidence for SOC2/ISO/HIPAA.

Aggregates evidence from Git history, CI/CD logs, test results,
security scans, and code review records into structured compliance
artifacts ready for auditor review.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ComplianceFramework(str, Enum):
    SOC2 = "soc2"
    ISO_27001 = "iso_27001"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    GDPR = "gdpr"
    CCPA = "ccpa"


class EvidenceType(str, Enum):
    CODE_REVIEW = "code_review"
    TEST_RESULTS = "test_results"
    SECURITY_SCAN = "security_scan"
    ACCESS_LOG = "access_log"
    CHANGE_LOG = "change_log"
    APPROVAL_RECORD = "approval_record"
    DEPLOYMENT_LOG = "deployment_log"
    POLICY_DOCUMENT = "policy_document"
    TRAINING_RECORD = "training_record"


class EvidenceStatus(str, Enum):
    COLLECTED = "collected"
    VERIFIED = "verified"
    MISSING = "missing"
    EXPIRED = "expired"


@dataclass
class EvidenceItem:
    """A single piece of compliance evidence."""

    id: str
    evidence_type: EvidenceType
    framework: ComplianceFramework
    control_id: str
    title: str
    description: str = ""
    status: EvidenceStatus = EvidenceStatus.COLLECTED
    collected_at: float = field(default_factory=time.time)
    expires_at: float | None = None
    source: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    file_path: str = ""


@dataclass
class ComplianceReport:
    """Aggregated compliance evidence report."""

    framework: ComplianceFramework
    evidence: list[EvidenceItem] = field(default_factory=list)
    coverage: float = 0.0
    missing_controls: list[str] = field(default_factory=list)
    generated_at: float = field(default_factory=time.time)

    @property
    def collected_count(self) -> int:
        return sum(1 for e in self.evidence if e.status in (EvidenceStatus.COLLECTED, EvidenceStatus.VERIFIED))

    @property
    def summary(self) -> str:
        return (
            f"{self.framework.value}: {self.collected_count}/{len(self.evidence)} controls covered "
            f"({self.coverage:.0%}), {len(self.missing_controls)} missing"
        )


# SOC2 control mapping (subset of TSC criteria)
_SOC2_CONTROLS = {
    "CC6.1": ("Logical access security", EvidenceType.ACCESS_LOG),
    "CC6.2": ("Access credentials management", EvidenceType.ACCESS_LOG),
    "CC7.1": ("System monitoring", EvidenceType.SECURITY_SCAN),
    "CC7.2": ("Anomaly detection", EvidenceType.SECURITY_SCAN),
    "CC8.1": ("Change management", EvidenceType.CHANGE_LOG),
    "CC9.1": ("Risk mitigation", EvidenceType.POLICY_DOCUMENT),
    "A1.1": ("Availability commitments", EvidenceType.DEPLOYMENT_LOG),
}

_ISO27001_CONTROLS = {
    "A.8.1": ("Asset management", EvidenceType.POLICY_DOCUMENT),
    "A.9.1": ("Access control policy", EvidenceType.ACCESS_LOG),
    "A.12.1": ("Operations security", EvidenceType.SECURITY_SCAN),
    "A.12.6": ("Vulnerability management", EvidenceType.SECURITY_SCAN),
    "A.14.2": ("Development security", EvidenceType.CODE_REVIEW),
}


class EvidenceCollector:
    """Collect and organise compliance evidence.

    Usage::

        collector = EvidenceCollector()
        report = collector.collect(ComplianceFramework.SOC2, sources)
    """

    def collect(
        self,
        framework: ComplianceFramework,
        sources: dict[EvidenceType, list[dict[str, Any]]] | None = None,
    ) -> ComplianceReport:
        """Collect evidence for a compliance framework."""
        controls = self._get_controls(framework)
        sources = sources or {}
        evidence: list[EvidenceItem] = []
        missing: list[str] = []

        for control_id, (title, evidence_type) in controls.items():
            source_data = sources.get(evidence_type, [])
            if source_data:
                for i, item in enumerate(source_data):
                    evidence.append(EvidenceItem(
                        id=f"{control_id}-{i}",
                        evidence_type=evidence_type,
                        framework=framework,
                        control_id=control_id,
                        title=title,
                        description=item.get("description", ""),
                        status=EvidenceStatus.COLLECTED,
                        source=item.get("source", ""),
                        data=item,
                    ))
            else:
                missing.append(control_id)
                evidence.append(EvidenceItem(
                    id=f"{control_id}-missing",
                    evidence_type=evidence_type,
                    framework=framework,
                    control_id=control_id,
                    title=title,
                    status=EvidenceStatus.MISSING,
                ))

        total = len(controls)
        covered = total - len(missing)
        coverage = covered / total if total else 0.0

        return ComplianceReport(
            framework=framework,
            evidence=evidence,
            coverage=coverage,
            missing_controls=missing,
        )

    @staticmethod
    def _get_controls(
        framework: ComplianceFramework,
    ) -> dict[str, tuple[str, EvidenceType]]:
        mapping = {
            ComplianceFramework.SOC2: _SOC2_CONTROLS,
            ComplianceFramework.ISO_27001: _ISO27001_CONTROLS,
        }
        return mapping.get(framework, _SOC2_CONTROLS)

    def export_markdown(self, report: ComplianceReport) -> str:
        """Export a compliance report as Markdown."""
        lines = [
            f"# Compliance Report: {report.framework.value.upper()}",
            f"\n**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(report.generated_at))}",
            f"**Coverage:** {report.coverage:.0%}\n",
            "## Evidence Items\n",
            "| Control | Title | Status | Type |",
            "|---------|-------|--------|------|",
        ]
        for e in report.evidence:
            status_icon = {"collected": "✅", "verified": "🔒", "missing": "❌", "expired": "⏰"}.get(e.status.value, "?")
            lines.append(f"| {e.control_id} | {e.title} | {status_icon} {e.status.value} | {e.evidence_type.value} |")

        if report.missing_controls:
            lines.append(f"\n## Missing Controls ({len(report.missing_controls)})\n")
            for ctrl in report.missing_controls:
                lines.append(f"- {ctrl}")

        return "\n".join(lines)
