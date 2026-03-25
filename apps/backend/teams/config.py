"""
Claude Teams - Configuration
==============================

Team configuration, modes, and debate strategies.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class TeamMode(str, Enum):
    COLLABORATIVE = "collaborative"
    HIERARCHICAL = "hierarchical"
    ADVERSARIAL = "adversarial"


class DebateStrategy(str, Enum):
    WEIGHTED_VOTE = "weighted_vote"
    CONSENSUS = "consensus"
    SUPER_MAJORITY = "super_majority"
    SIMPLE_MAJORITY = "simple_majority"


@dataclass
class TeamConfig:
    mode: TeamMode = TeamMode.COLLABORATIVE
    debate_strategy: DebateStrategy = DebateStrategy.WEIGHTED_VOTE
    security_can_veto: bool = False
    architect_can_veto: bool = False
    max_debate_rounds: int = 3
    active_roles: List[str] = field(default_factory=lambda: ["architect", "developer", "security", "qa"])

    @classmethod
    def for_critical_task(cls) -> "TeamConfig":
        return cls(
            mode=TeamMode.COLLABORATIVE,
            debate_strategy=DebateStrategy.WEIGHTED_VOTE,
            security_can_veto=True,
            architect_can_veto=True,
        )

    @classmethod
    def for_quick_task(cls) -> "TeamConfig":
        return cls(
            mode=TeamMode.HIERARCHICAL,
            debate_strategy=DebateStrategy.SIMPLE_MAJORITY,
            security_can_veto=False,
            architect_can_veto=False,
            max_debate_rounds=1,
            active_roles=["architect", "developer"],
        )
