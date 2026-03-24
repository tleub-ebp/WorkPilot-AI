"""
Build Analytics Dashboard Package.

This package provides comprehensive analytics and monitoring capabilities
for the WorkPilot AI agent system, including:
- Build performance metrics
- Token usage tracking
- QA success rates
- Error pattern analysis
- Agent performance comparison
"""

from .database import get_db, init_database
from .database_schema import (
    AgentPerformance,
    AgentType,
    AnalyticsConfig,
    Build,
    BuildError,
    BuildPhase,
    BuildStatus,
    QAResult,
    TokenUsage,
)

__all__ = [
    # Database
    "init_database",
    "get_db",
    # Models
    "Build",
    "BuildPhase",
    "TokenUsage",
    "QAResult",
    "BuildError",
    "AgentPerformance",
    "AnalyticsConfig",
    # Enums
    "BuildStatus",
    "AgentType",
]
