"""
Voting and Consensus System
============================

Handles voting, veto rights, and consensus detection for team decisions.
"""

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .config import DebateStrategy


class VoteChoice(str, Enum):
    """Vote options."""

    APPROVE = "approve"
    APPROVE_WITH_CHANGES = "approve_with_changes"
    NEUTRAL = "neutral"
    REJECT = "reject"
    VETO = "veto"  # Hard block (only if role has veto rights)


@dataclass
class Vote:
    """A vote from an agent."""

    agent_role: str
    vote_choice: VoteChoice
    reasoning: str
    weight: int  # Role's decision weight
    can_veto: bool
    proposed_changes: list[str] = field(default_factory=list)
    timestamp: float = 0.0

    def is_blocking(self) -> bool:
        """Check if this vote blocks the decision."""
        return self.vote_choice == VoteChoice.VETO and self.can_veto

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class VotingResult:
    """Result of a voting session."""

    votes: list[Vote]
    strategy: DebateStrategy
    decision: str  # "approved", "rejected", "needs_changes"
    reasoning: str
    total_weight: int
    approve_weight: int
    reject_weight: int
    vetoes: list[Vote]
    required_changes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        data = asdict(self)
        data["votes"] = [v.to_dict() for v in self.votes]
        data["vetoes"] = [v.to_dict() for v in self.vetoes]
        return data


class VotingSystem:
    """Manages voting and consensus for team decisions."""

    def __init__(self, spec_dir: Path):
        self.spec_dir = Path(spec_dir)
        self.vote_history: list[VotingResult] = []

        # Create votes directory
        self.votes_dir = self.spec_dir / "debates" / "votes"
        self.votes_dir.mkdir(parents=True, exist_ok=True)

    def conduct_vote(
        self,
        votes: list[Vote],
        strategy: DebateStrategy,
        topic: str,
    ) -> VotingResult:
        """
        Conduct a vote and determine the outcome.

        Args:
            votes: List of votes from agents
            strategy: Voting strategy to use
            topic: What is being voted on

        Returns:
            VotingResult with decision and reasoning
        """
        # Check for vetoes first
        vetoes = [v for v in votes if v.is_blocking()]
        if vetoes:
            result = VotingResult(
                votes=votes,
                strategy=strategy,
                decision="rejected",
                reasoning=f"Vetoed by {', '.join(v.agent_role for v in vetoes)}",
                total_weight=sum(v.weight for v in votes),
                approve_weight=0,
                reject_weight=sum(v.weight for v in votes),
                vetoes=vetoes,
            )
            self._save_vote_result(result, topic)
            return result

        # Calculate weighted scores
        total_weight = sum(v.weight for v in votes)
        approve_weight = sum(
            v.weight
            for v in votes
            if v.vote_choice in [VoteChoice.APPROVE, VoteChoice.APPROVE_WITH_CHANGES]
        )
        reject_weight = sum(v.weight for v in votes if v.vote_choice == VoteChoice.REJECT)

        # Gather required changes
        required_changes = []
        for v in votes:
            if v.vote_choice == VoteChoice.APPROVE_WITH_CHANGES:
                required_changes.extend(v.proposed_changes)

        # Determine outcome based on strategy
        if strategy == DebateStrategy.MAJORITY_VOTE:
            decision = self._majority_vote_decision(votes)
        elif strategy == DebateStrategy.WEIGHTED_VOTE:
            decision = self._weighted_vote_decision(approve_weight, reject_weight, total_weight)
        elif strategy == DebateStrategy.CONSENSUS:
            decision = self._consensus_decision(votes)
        elif strategy == DebateStrategy.SUPER_MAJORITY:
            decision = self._super_majority_decision(approve_weight, total_weight)
        else:
            decision = "rejected"

        # Build reasoning
        reasoning = self._build_reasoning(votes, decision, approve_weight, reject_weight, total_weight)

        result = VotingResult(
            votes=votes,
            strategy=strategy,
            decision=decision,
            reasoning=reasoning,
            total_weight=total_weight,
            approve_weight=approve_weight,
            reject_weight=reject_weight,
            vetoes=[],
            required_changes=required_changes,
            metadata={"topic": topic},
        )

        self._save_vote_result(result, topic)
        self.vote_history.append(result)

        return result

    def _majority_vote_decision(self, votes: list[Vote]) -> str:
        """Simple majority (> 50% of agents)."""
        approve_count = sum(
            1
            for v in votes
            if v.vote_choice in [VoteChoice.APPROVE, VoteChoice.APPROVE_WITH_CHANGES]
        )
        return "approved" if approve_count > len(votes) / 2 else "rejected"

    def _weighted_vote_decision(
        self, approve_weight: int, reject_weight: int, total_weight: int
    ) -> str:
        """Weighted vote (considers role importance)."""
        if approve_weight > total_weight / 2:
            return "approved"
        elif reject_weight > total_weight / 2:
            return "rejected"
        else:
            return "needs_changes"

    def _consensus_decision(self, votes: list[Vote]) -> str:
        """Unanimous agreement required."""
        all_approve = all(
            v.vote_choice in [VoteChoice.APPROVE, VoteChoice.APPROVE_WITH_CHANGES]
            for v in votes
        )
        return "approved" if all_approve else "needs_changes"

    def _super_majority_decision(self, approve_weight: int, total_weight: int) -> str:
        """Require 75%+ approval."""
        return "approved" if approve_weight >= total_weight * 0.75 else "rejected"

    def _build_reasoning(
        self,
        votes: list[Vote],
        decision: str,
        approve_weight: int,
        reject_weight: int,
        total_weight: int,
    ) -> str:
        """Build human-readable reasoning for the decision."""
        lines = [f"Decision: {decision.upper()}"]
        lines.append(
            f"Vote breakdown: {approve_weight}/{total_weight} weight in favor"
        )

        # Group by vote choice
        by_choice = {}
        for vote in votes:
            choice = vote.vote_choice.value
            if choice not in by_choice:
                by_choice[choice] = []
            by_choice[choice].append(vote.agent_role)

        lines.append("\nVotes:")
        for choice, roles in sorted(by_choice.items()):
            lines.append(f"  {choice}: {', '.join(roles)}")

        return "\n".join(lines)

    def _save_vote_result(self, result: VotingResult, topic: str):
        """Save vote result to disk."""
        vote_num = len(self.vote_history) + 1
        filename = f"vote_{vote_num:03d}_{topic[:30].replace(' ', '_')}.json"
        filepath = self.votes_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, indent=2)

    def get_vote_summary(self) -> dict:
        """Get summary of all votes."""
        return {
            "total_votes": len(self.vote_history),
            "approved": sum(1 for v in self.vote_history if v.decision == "approved"),
            "rejected": sum(1 for v in self.vote_history if v.decision == "rejected"),
            "needs_changes": sum(
                1 for v in self.vote_history if v.decision == "needs_changes"
            ),
            "vetoes": sum(len(v.vetoes) for v in self.vote_history),
        }

