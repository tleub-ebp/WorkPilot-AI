"""
Compliance Evidence Collector — Auto-collect audit evidence.

Aggregates evidence from Git history, CI/CD logs, test results,
security scans, and code reviews into structured compliance artifacts
for SOC2, ISO 27001, HIPAA, PCI-DSS, GDPR, and CCPA.
"""

from .evidence_collector import (
    ComplianceFramework,
    ComplianceReport,
    EvidenceCollector,
    EvidenceItem,
    EvidenceStatus,
    EvidenceType,
)

__all__ = [
    "EvidenceCollector",
    "ComplianceReport",
    "EvidenceItem",
    "EvidenceType",
    "EvidenceStatus",
    "ComplianceFramework",
]
