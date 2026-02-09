"""
Self-Healing Codebase Module
============================

Feature #11 from Killing Features Roadmap - Tier 3

Autonomous code health monitoring and self-repair system.

Key Features:
- Continuous health monitoring
- Proactive degradation detection (code smells, performance)
- Auto-refactoring with automated PRs
- Technical debt tracking and resolution
- Predictive alerts before issues become critical

Usage:
    from self_healing import SelfHealingMonitor, HealthCheckScheduler
    
    monitor = SelfHealingMonitor(project_dir)
    health = await monitor.check_health()
    
    scheduler = HealthCheckScheduler(project_dir)
    await scheduler.start_monitoring()
"""

from .config import (
    HealingConfig,
    HealingMode,
    HealingPriority,
    MonitoringFrequency,
)
from .health_checker import HealthChecker, HealthReport, HealthStatus
from .monitor import SelfHealingMonitor
from .scheduler import HealthCheckScheduler
from .debt_tracker import TechnicalDebtTracker, DebtItem
from .refactoring_engine import RefactoringEngine, RefactoringPlan
from .alert_manager import AlertManager, Alert, AlertLevel

__all__ = [
    # Config
    "HealingConfig",
    "HealingMode",
    "HealingPriority",
    "MonitoringFrequency",
    # Health Check
    "HealthChecker",
    "HealthReport",
    "HealthStatus",
    # Monitor
    "SelfHealingMonitor",
    # Scheduler
    "HealthCheckScheduler",
    # Debt Tracking
    "TechnicalDebtTracker",
    "DebtItem",
    # Refactoring
    "RefactoringEngine",
    "RefactoringPlan",
    # Alerts
    "AlertManager",
    "Alert",
    "AlertLevel",
]

__version__ = "1.0.0"
