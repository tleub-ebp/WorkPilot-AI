"""
Self-Healing Configuration
===========================

Configuration classes and enums for the self-healing system.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class HealingMode(str, Enum):
    """Self-healing operation modes."""
    
    PASSIVE = "passive"  # Only monitor and alert
    ACTIVE = "active"  # Auto-fix issues automatically
    AGGRESSIVE = "aggressive"  # Proactive refactoring + auto-fix


class HealingPriority(str, Enum):
    """Priority levels for healing actions."""
    
    CRITICAL = "critical"  # Security, crashes, data loss
    HIGH = "high"  # Performance degradation, major bugs
    MEDIUM = "medium"  # Code smells, minor bugs
    LOW = "low"  # Style, documentation


class MonitoringFrequency(str, Enum):
    """How often to run health checks."""
    
    REALTIME = "realtime"  # On every commit
    HOURLY = "hourly"  # Every hour
    DAILY = "daily"  # Once per day
    WEEKLY = "weekly"  # Once per week


class AlertChannel(str, Enum):
    """Channels for sending alerts."""
    
    EMAIL = "email"
    SLACK = "slack"
    GITHUB = "github"
    CONSOLE = "console"


@dataclass
class HealingConfig:
    """Configuration for self-healing system."""
    
    # Operation mode
    mode: HealingMode = HealingMode.ACTIVE
    
    # Monitoring
    frequency: MonitoringFrequency = MonitoringFrequency.DAILY
    monitoring_enabled: bool = True
    
    # Auto-healing settings
    auto_fix_enabled: bool = True
    auto_refactor_enabled: bool = True
    create_prs_for_fixes: bool = True
    max_fixes_per_run: int = 5
    
    # Thresholds
    min_health_score: float = 70.0  # Trigger healing below this score
    critical_threshold: float = 50.0  # Critical alert threshold
    
    # Priorities to act on
    priorities: list[HealingPriority] = field(
        default_factory=lambda: [
            HealingPriority.CRITICAL,
            HealingPriority.HIGH,
            HealingPriority.MEDIUM,
        ]
    )
    
    # Alert settings
    alert_channels: list[AlertChannel] = field(
        default_factory=lambda: [AlertChannel.CONSOLE]
    )
    alert_on_degradation: bool = True
    alert_threshold_change: float = 10.0  # Alert if score drops by this much
    
    # Scheduling
    schedule_night_runs: bool = True  # Run intensive ops at night
    night_start_hour: int = 22  # 10 PM
    night_end_hour: int = 6  # 6 AM
    
    # Technical debt
    track_debt: bool = True
    debt_max_age_days: int = 30  # Flag debt older than this
    
    # Performance
    max_files_per_scan: int = 1000
    timeout_seconds: int = 300
    
    # LLM settings
    model: str = "claude-3-5-sonnet-20241022"
    thinking_budget: str = "medium"
    
    # Exclusions
    excluded_paths: list[str] = field(
        default_factory=lambda: [
            "node_modules",
            ".venv",
            "__pycache__",
            ".git",
            "dist",
            "build",
        ]
    )
    
    # Git settings
    create_branch_per_fix: bool = True
    branch_prefix: str = "self-healing/"
    commit_message_prefix: str = "🧬 Self-Healing:"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "mode": self.mode.value,
            "frequency": self.frequency.value,
            "monitoring_enabled": self.monitoring_enabled,
            "auto_fix_enabled": self.auto_fix_enabled,
            "auto_refactor_enabled": self.auto_refactor_enabled,
            "create_prs_for_fixes": self.create_prs_for_fixes,
            "max_fixes_per_run": self.max_fixes_per_run,
            "min_health_score": self.min_health_score,
            "critical_threshold": self.critical_threshold,
            "priorities": [p.value for p in self.priorities],
            "alert_channels": [c.value for c in self.alert_channels],
            "alert_on_degradation": self.alert_on_degradation,
            "alert_threshold_change": self.alert_threshold_change,
            "schedule_night_runs": self.schedule_night_runs,
            "night_start_hour": self.night_start_hour,
            "night_end_hour": self.night_end_hour,
            "track_debt": self.track_debt,
            "debt_max_age_days": self.debt_max_age_days,
            "max_files_per_scan": self.max_files_per_scan,
            "timeout_seconds": self.timeout_seconds,
            "model": self.model,
            "thinking_budget": self.thinking_budget,
            "excluded_paths": self.excluded_paths,
            "create_branch_per_fix": self.create_branch_per_fix,
            "branch_prefix": self.branch_prefix,
            "commit_message_prefix": self.commit_message_prefix,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HealingConfig":
        """Create config from dictionary."""
        config = cls()
        
        if "mode" in data:
            config.mode = HealingMode(data["mode"])
        if "frequency" in data:
            config.frequency = MonitoringFrequency(data["frequency"])
        if "monitoring_enabled" in data:
            config.monitoring_enabled = data["monitoring_enabled"]
        if "auto_fix_enabled" in data:
            config.auto_fix_enabled = data["auto_fix_enabled"]
        if "auto_refactor_enabled" in data:
            config.auto_refactor_enabled = data["auto_refactor_enabled"]
        if "create_prs_for_fixes" in data:
            config.create_prs_for_fixes = data["create_prs_for_fixes"]
        if "max_fixes_per_run" in data:
            config.max_fixes_per_run = data["max_fixes_per_run"]
        if "min_health_score" in data:
            config.min_health_score = data["min_health_score"]
        if "critical_threshold" in data:
            config.critical_threshold = data["critical_threshold"]
        if "priorities" in data:
            config.priorities = [HealingPriority(p) for p in data["priorities"]]
        if "alert_channels" in data:
            config.alert_channels = [AlertChannel(c) for c in data["alert_channels"]]
        
        # Copy other simple fields
        for key in [
            "alert_on_degradation",
            "alert_threshold_change",
            "schedule_night_runs",
            "night_start_hour",
            "night_end_hour",
            "track_debt",
            "debt_max_age_days",
            "max_files_per_scan",
            "timeout_seconds",
            "model",
            "thinking_budget",
            "excluded_paths",
            "create_branch_per_fix",
            "branch_prefix",
            "commit_message_prefix",
        ]:
            if key in data:
                setattr(config, key, data[key])
        
        return config


# Preset configurations
PRESET_CONFIGS = {
    "conservative": HealingConfig(
        mode=HealingMode.PASSIVE,
        auto_fix_enabled=False,
        auto_refactor_enabled=False,
        frequency=MonitoringFrequency.DAILY,
    ),
    "balanced": HealingConfig(
        mode=HealingMode.ACTIVE,
        auto_fix_enabled=True,
        auto_refactor_enabled=False,
        frequency=MonitoringFrequency.DAILY,
        priorities=[HealingPriority.CRITICAL, HealingPriority.HIGH],
    ),
    "aggressive": HealingConfig(
        mode=HealingMode.AGGRESSIVE,
        auto_fix_enabled=True,
        auto_refactor_enabled=True,
        frequency=MonitoringFrequency.HOURLY,
        max_fixes_per_run=10,
    ),
}


def get_preset_config(preset: str = "balanced") -> HealingConfig:
    """Get a preset configuration."""
    return PRESET_CONFIGS.get(preset, PRESET_CONFIGS["balanced"])
