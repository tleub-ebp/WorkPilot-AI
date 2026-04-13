"""
Cross-Agent Consensus Arbiter — Resolve inter-agent conflicts.

Scores opinions by confidence and domain authority, applies resolution
strategies, and escalates unresolvable conflicts to humans.
"""

from .arbiter_engine import (
    AgentDomain,
    AgentOpinion,
    ArbiterEngine,
    Conflict,
    ConflictSeverity,
    ConsensusResult,
    ResolutionStrategy,
)

__all__ = [
    "ArbiterEngine",
    "ConsensusResult",
    "Conflict",
    "AgentOpinion",
    "AgentDomain",
    "ConflictSeverity",
    "ResolutionStrategy",
]
