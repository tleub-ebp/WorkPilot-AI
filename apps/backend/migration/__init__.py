"""
Auto-Migration Engine
Automatic technology stack migration with business logic preservation.
"""

__version__ = "1.0.0"
__author__ = "WorkPilot AI Team"

from .analyzer import StackAnalyzer
from .models import (
    MigrationPhase,
    MigrationPlan,
    MigrationState,
    MigrationStep,
    StackInfo,
    TransformationResult,
)
from .orchestrator import MigrationOrchestrator
from .planner import MigrationPlanner
from .reporter import MigrationReporter
from .rollback import RollbackManager
from .transformer import TransformationEngine
from .validator import MigrationValidator

__all__ = [
    "StackInfo",
    "MigrationPlan",
    "MigrationPhase",
    "MigrationStep",
    "TransformationResult",
    "MigrationState",
    "StackAnalyzer",
    "MigrationPlanner",
    "TransformationEngine",
    "MigrationOrchestrator",
    "MigrationReporter",
    "MigrationValidator",
    "RollbackManager",
]
