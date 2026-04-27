"""Audit Trail & Compliance Replay.

Append-only event log with hash chaining (a la Git/blockchain) so any
tampering is detectable. Captures every agent action (who, when, what,
why, what-was-the-input, what-was-the-output) and lets compliance
auditors replay any past decision.

Different from `compliance_collector/` which gathers evidence artefacts
for audit reports — this module is the **immutable source of truth** that
the collector (and anyone else) can consume.
"""

from .trail import (
    AuditEvent,
    AuditEventKind,
    AuditTrail,
    Decision,
    IntegrityReport,
    ReplayBundle,
)

__all__ = [
    "AuditEvent",
    "AuditEventKind",
    "AuditTrail",
    "Decision",
    "IntegrityReport",
    "ReplayBundle",
]
