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

from .database import init_database, get_db
from .database_schema import (
    Build, BuildPhase, TokenUsage, QAResult, 
    BuildError, AgentPerformance, AnalyticsConfig,
    BuildStatus, AgentType
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
