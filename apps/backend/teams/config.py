"""
Team Configuration
==================

Configuration options for Claude Teams collaborative mode.
"""

from dataclasses import dataclass, field
from enum import Enum


class TeamMode(str, Enum):
    """Team collaboration mode."""

    STANDARD = "standard"  # Default orchestrated pipeline
    COLLABORATIVE = "collaborative"  # Claude Teams with debate
    HYBRID = "hybrid"  # Mix: critical decisions use Teams, rest uses pipeline


class DebateStrategy(str, Enum):
    """Strategy for debate resolution."""

    MAJORITY_VOTE = "majority_vote"  # Simple majority wins
    WEIGHTED_VOTE = "weighted_vote"  # Weighted by role importance
    CONSENSUS = "consensus"  # Require unanimous agreement
    SUPER_MAJORITY = "super_majority"  # Require 75%+ agreement


@dataclass
class TeamConfig:
    """Configuration for Claude Teams."""

    # Mode
    mode: TeamMode = TeamMode.STANDARD

    # Debate settings
    max_debate_rounds: int = 3
    debate_strategy: DebateStrategy = DebateStrategy.WEIGHTED_VOTE
    require_consensus_for_critical: bool = True

    # Veto rights
    security_can_veto: bool = True
    architect_can_veto: bool = True
    qa_can_veto: bool = False

    # Token budget (Teams uses more tokens)
    token_budget_multiplier: float = 2.0

    # Active roles (can be customized per task)
    active_roles: list[str] = field(
        default_factory=lambda: [
            "architect",
            "developer",
            "security",
            "qa_engineer",
        ]
    )

    # Model configuration
    model: str = "claude-sonnet-4-5-20250929"
    thinking_budget: int = 10000

    # Timeouts
    debate_timeout_seconds: int = 300  # 5 minutes per debate
    agent_response_timeout_seconds: int = 60

    # Logging
    enable_debate_log: bool = True
    save_decision_tree: bool = True

    @classmethod
    def for_critical_task(cls) -> "TeamConfig":
        """Preset for critical/security-sensitive tasks."""
        return cls(
            mode=TeamMode.COLLABORATIVE,
            debate_strategy=DebateStrategy.CONSENSUS,
            require_consensus_for_critical=True,
            security_can_veto=True,
            architect_can_veto=True,
            token_budget_multiplier=2.5,
        )

    @classmethod
    def for_standard_task(cls) -> "TeamConfig":
        """Preset for standard tasks (uses regular pipeline)."""
        return cls(
            mode=TeamMode.STANDARD,
            token_budget_multiplier=1.0,
        )

    @classmethod
    def for_complex_task(cls) -> "TeamConfig":
        """Preset for complex architectural tasks."""
        return cls(
            mode=TeamMode.COLLABORATIVE,
            max_debate_rounds=5,
            debate_strategy=DebateStrategy.WEIGHTED_VOTE,
            active_roles=["architect", "developer", "security", "qa_engineer", "devops"],
            token_budget_multiplier=2.0,
        )

