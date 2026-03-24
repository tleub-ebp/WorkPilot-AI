#!/usr/bin/env python3
"""
Optimization Configuration for AI Skills System

Central configuration for all optimization parameters and constants.
This file ensures consistent optimization settings across the entire skills system.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TokenOptimizationConfig:
    """Configuration for token optimization."""

    max_description_length: int = 512  # Limit skill descriptions to 512 chars
    max_triggers_count: int = 5  # Keep trigger lists under 5 items
    sampling_threshold: int = 5  # Sample file collections >5 items
    compression_threshold: int = 100  # Compress metadata >100 chars
    predictive_cache_size: int = 1000  # Cache size for predictive caching
    deduplication_min_length: int = 50  # Minimum length for deduplication


@dataclass
class ContextOptimizationConfig:
    """Configuration for context optimization."""

    max_context_limit_ratio: float = 0.7  # Aggressive cleanup at 70% of limit
    default_max_workers: int = 3  # Reduced from 4 for stability
    default_timeout: int = 25  # Reduced from 30s for responsiveness
    checkpoint_interval: int = 300  # Checkpoints every 5 minutes
    priority_threshold: float = 0.5  # Minimum priority for context preservation


@dataclass
class PerformanceOptimizationConfig:
    """Configuration for performance optimization."""

    optimization_enabled: bool = True  # Enable optimization for all composite skills
    subagent_threshold: int = 3  # Use subagents for >3 skills combinations
    validation_cache_size: int = 500  # Cache for validation results
    memory_cleanup_interval: int = 600  # Memory cleanup every 10 minutes
    parallel_execution: bool = True  # Enable parallel script execution


@dataclass
class ClaudeCodeOptimizationConfig:
    """Configuration specific to Claude Code optimizations."""

    oauth_token_support: bool = True  # Support OAuth tokens
    encrypted_token_validation: bool = True  # Validate encrypted tokens
    keychain_integration: bool = True  # Integrate with keychain
    sdk_integration: bool = True  # SDK integration for performance
    context_compression: bool = True  # Context compression adapted for Claude


@dataclass
class OptimizationConfig:
    """Main optimization configuration combining all settings."""

    token: TokenOptimizationConfig = field(default_factory=TokenOptimizationConfig)
    context: ContextOptimizationConfig = field(
        default_factory=ContextOptimizationConfig
    )
    performance: PerformanceOptimizationConfig = field(
        default_factory=PerformanceOptimizationConfig
    )
    claude_code: ClaudeCodeOptimizationConfig = field(
        default_factory=ClaudeCodeOptimizationConfig
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "token": self.token.__dict__,
            "context": self.context.__dict__,
            "performance": self.performance.__dict__,
            "claude_code": self.claude_code.__dict__,
        }

    def validate(self) -> bool:
        """Validate configuration parameters."""
        # Validate token optimization
        if self.token.max_description_length <= 0:
            return False
        if self.token.max_triggers_count <= 0:
            return False
        if self.token.sampling_threshold <= 0:
            return False

        # Validate context optimization
        if not 0 < self.context.max_context_limit_ratio < 1:
            return False
        if self.context.default_max_workers <= 0:
            return False
        if self.context.default_timeout <= 0:
            return False

        # Validate performance optimization
        if self.performance.subagent_threshold <= 0:
            return False
        if self.performance.validation_cache_size <= 0:
            return False

        return True


# Global configuration instance
OPTIMIZATION_CONFIG = OptimizationConfig()


def get_optimization_config() -> OptimizationConfig:
    """Get the global optimization configuration."""
    return OPTIMIZATION_CONFIG


def update_optimization_config(config: dict[str, Any]) -> bool:
    """Update the global optimization configuration."""
    try:
        if "token" in config:
            token_config = config["token"]
            OPTIMIZATION_CONFIG.token.max_description_length = token_config.get(
                "max_description_length",
                OPTIMIZATION_CONFIG.token.max_description_length,
            )
            OPTIMIZATION_CONFIG.token.max_triggers_count = token_config.get(
                "max_triggers_count", OPTIMIZATION_CONFIG.token.max_triggers_count
            )
            OPTIMIZATION_CONFIG.token.sampling_threshold = token_config.get(
                "sampling_threshold", OPTIMIZATION_CONFIG.token.sampling_threshold
            )

        if "context" in config:
            context_config = config["context"]
            OPTIMIZATION_CONFIG.context.max_context_limit_ratio = context_config.get(
                "max_context_limit_ratio",
                OPTIMIZATION_CONFIG.context.max_context_limit_ratio,
            )
            OPTIMIZATION_CONFIG.context.default_max_workers = context_config.get(
                "default_max_workers", OPTIMIZATION_CONFIG.context.default_max_workers
            )
            OPTIMIZATION_CONFIG.context.default_timeout = context_config.get(
                "default_timeout", OPTIMIZATION_CONFIG.context.default_timeout
            )

        if "performance" in config:
            perf_config = config["performance"]
            OPTIMIZATION_CONFIG.performance.optimization_enabled = perf_config.get(
                "optimization_enabled",
                OPTIMIZATION_CONFIG.performance.optimization_enabled,
            )
            OPTIMIZATION_CONFIG.performance.subagent_threshold = perf_config.get(
                "subagent_threshold", OPTIMIZATION_CONFIG.performance.subagent_threshold
            )

        return OPTIMIZATION_CONFIG.validate()
    except Exception:
        return False


def reset_optimization_config():
    """Reset optimization configuration to defaults."""
    global OPTIMIZATION_CONFIG
    OPTIMIZATION_CONFIG = OptimizationConfig()


# Export constants for backward compatibility
MAX_DESCRIPTION_LENGTH = OPTIMIZATION_CONFIG.token.max_description_length
MAX_TRIGGERS_COUNT = OPTIMIZATION_CONFIG.token.max_triggers_count
SAMPLING_THRESHOLD = OPTIMIZATION_CONFIG.token.sampling_threshold
MAX_CONTEXT_LIMIT_RATIO = OPTIMIZATION_CONFIG.context.max_context_limit_ratio
DEFAULT_MAX_WORKERS = OPTIMIZATION_CONFIG.context.default_max_workers
DEFAULT_TIMEOUT = OPTIMIZATION_CONFIG.context.default_timeout
OPTIMIZATION_ENABLED = OPTIMIZATION_CONFIG.performance.optimization_enabled
SUBAGENT_THRESHOLD = OPTIMIZATION_CONFIG.performance.subagent_threshold
CHECKPOINT_INTERVAL = OPTIMIZATION_CONFIG.context.checkpoint_interval
PRIORITY_THRESHOLD = OPTIMIZATION_CONFIG.context.priority_threshold
VALIDATION_CACHE_SIZE = OPTIMIZATION_CONFIG.performance.validation_cache_size
COMPRESSION_THRESHOLD = OPTIMIZATION_CONFIG.token.compression_threshold
PREDICTIVE_CACHE_SIZE = OPTIMIZATION_CONFIG.token.predictive_cache_size
DEDUPLICATION_MIN_LENGTH = OPTIMIZATION_CONFIG.token.deduplication_min_length
