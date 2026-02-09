"""
Auto-Migration Engine
Automatic technology stack migration with business logic preservation.
"""

__version__ = "1.0.0"
__author__ = "Auto-Claude Team"

from .models import (
    StackInfo,
    MigrationPlan,
    MigrationPhase,
    MigrationStep,
    TransformationResult,
    MigrationState,
)
from .analyzer import StackAnalyzer
from .planner import MigrationPlanner
from .transformer import TransformationEngine
from .orchestrator import MigrationOrchestrator
from .reporter import MigrationReporter
from .validator import MigrationValidator
from .rollback import RollbackManager

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
