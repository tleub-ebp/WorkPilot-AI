"""
Continuous AI — Always-On Background Daemon
============================================

Proactive AI daemon that monitors and acts on:
- CI/CD failures (auto-diagnosis + fix PRs)
- Dependency vulnerabilities (auto-patch + security PRs)
- New GitHub/GitLab issues (auto-triage + investigation)
- External PRs (auto-review before human review)

Built on top of the existing HealthCheckScheduler, AutoDetector,
and self-healing infrastructure.
"""

from .daemon import ContinuousAIDaemon
from .types import (
    ContinuousAIConfig,
    ContinuousAIStatus,
    DaemonModule,
    DaemonModuleConfig,
    ModuleState,
)

__all__ = [
    "ContinuousAIDaemon",
    "ContinuousAIConfig",
    "ContinuousAIStatus",
    "DaemonModule",
    "DaemonModuleConfig",
    "ModuleState",
]
