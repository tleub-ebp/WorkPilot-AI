"""
Incident Responder - Self-Healing Codebase
============================================

Feature #3 (Tier S+) - Unified surveillance, detection and automatic correction.

Three modes:
- CI/CD Mode: Auto-detect test regressions, analyze, fix, QA, open PR
- Production Mode: APM integration via MCP, root cause analysis, hotfix
- Proactive Mode: Fragility analysis, preventive test generation

Usage:
    from self_healing.incident_responder import IncidentResponderOrchestrator

    orchestrator = IncidentResponderOrchestrator(project_dir)

    # CI/CD: Handle test failure
    operation = await orchestrator.handle_cicd_failure(
        commit_sha="abc123",
        branch="main",
        test_output="FAILED tests/test_auth.py::test_login",
    )

    # Production: Handle APM incident
    operation = await orchestrator.handle_production_incident(
        source=IncidentSource.SENTRY,
        error_data={"error_type": "TypeError", "stack_trace": "..."},
    )

    # Proactive: Run fragility scan
    reports = await orchestrator.run_proactive_scan()
"""

from .cicd_mode import CICDMode
from .fragility_analyzer import FragilityAnalyzer
from .mcp_connector import MCPConnector, MCPSourceConfig
from .models import (
    CICDIncidentData,
    FragilityReport,
    HealingOperation,
    HealingStatus,
    HealingStep,
    Incident,
    IncidentMode,
    IncidentSeverity,
    IncidentSource,
    ProductionIncidentData,
    SelfHealingStats,
)
from .orchestrator import IncidentResponderOrchestrator
from .proactive_mode import ProactiveMode
from .production_mode import ProductionMode

__all__ = [
    # Orchestrator
    "IncidentResponderOrchestrator",
    # Modes
    "CICDMode",
    "ProductionMode",
    "ProactiveMode",
    # Analysis
    "FragilityAnalyzer",
    # MCP
    "MCPConnector",
    "MCPSourceConfig",
    # Models
    "Incident",
    "IncidentMode",
    "IncidentSeverity",
    "IncidentSource",
    "HealingStatus",
    "HealingOperation",
    "HealingStep",
    "FragilityReport",
    "CICDIncidentData",
    "ProductionIncidentData",
    "SelfHealingStats",
]
