"""CI/CD Anomaly Detective.

Parses raw CI logs (GitHub Actions / GitLab CI / Azure Pipelines / Jenkins)
to detect anomaly patterns at the infrastructure level — timeouts, OOM,
dependency conflicts, network failures, resource exhaustion — and
proposes structural fixes (increase timeouts, parallelism, retries…).

Different from:
* `flaky_test_detective/` — analyses individual test outcomes across runs.
* `self_healing/incident_responder/cicd_mode.py` — handles a single failure
  event by spawning a healing pipeline (LLM-driven).

This module is **rules-based and LLM-free** so it stays cheap to run on
every CI run, and can be the first cheap filter before invoking the
heavier `CICDMode`.
"""

from .detective import (
    AnomalyDetective,
    AnomalyKind,
    AnomalyReport,
    AnomalySignal,
    Severity,
)

__all__ = [
    "AnomalyDetective",
    "AnomalyKind",
    "AnomalyReport",
    "AnomalySignal",
    "Severity",
]
