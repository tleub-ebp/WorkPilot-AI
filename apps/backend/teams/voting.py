"""
Claude Teams - Voting System
==============================

Weighted voting, veto rights, consensus detection, and super-majority logic.
"""

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class VoteChoice(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    VETO = "veto"
    APPROVE_WITH_CHANGES = "approve_with_changes"
    ABSTAIN = "abstain"


@dataclass
class Vote:
    agent_role: str
    vote_choice: VoteChoice
    reasoning: str
    weight: int = 1
    can_veto: bool = False

    def is_blocking(self) -> bool:
        return self.vote_choice == VoteChoice.VETO and self.can_veto

    def to_dict(self) -> dict:
        return {
            "agent_role": self.agent_role,
            "vote_choice": self.vote_choice.value,
            "reasoning": self.reasoning,
            "weight": self.weight,
            "can_veto": self.can_veto,
            "is_blocking": self.is_blocking(),
        }


@dataclass
class VotingResult:
    decision: str
    reasoning: str
    votes: list[Vote]
    vetoes: list[Vote]
    approve_weight: int
    reject_weight: int
    total_weight: int
    strategy: str
    topic: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "decision": self.decision,
            "reasoning": self.reasoning,
            "votes": [v.to_dict() for v in self.votes],
            "vetoes": [v.to_dict() for v in self.vetoes],
            "approve_weight": self.approve_weight,
            "reject_weight": self.reject_weight,
            "total_weight": self.total_weight,
            "strategy": self.strategy,
            "topic": self.topic,
            "timestamp": self.timestamp,
        }


class VotingSystem:
    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.votes_dir = self.base_path / "debates" / "votes"
        self.votes_dir.mkdir(parents=True, exist_ok=True)

    def conduct_vote(
        self, votes: list[Vote], strategy, topic: str
    ) -> VotingResult:
        from teams.config import DebateStrategy

        # Check for blocking vetoes first
        blocking_vetoes = [v for v in votes if v.is_blocking()]

        approve_weight = sum(
            v.weight for v in votes
            if v.vote_choice in (VoteChoice.APPROVE, VoteChoice.APPROVE_WITH_CHANGES)
        )
        reject_weight = sum(
            v.weight for v in votes
            if v.vote_choice in (VoteChoice.REJECT, VoteChoice.VETO)
        )
        total_weight = sum(v.weight for v in votes)

        if blocking_vetoes:
            veto_roles = ", ".join(v.agent_role for v in blocking_vetoes)
            reasoning = f"Blocked by veto from: {veto_roles}"
            decision = "rejected"
        elif strategy == DebateStrategy.CONSENSUS:
            decision, reasoning = self._consensus_decision(votes)
        elif strategy == DebateStrategy.SUPER_MAJORITY:
            decision, reasoning = self._super_majority_decision(approve_weight, total_weight)
        else:  # WEIGHTED_VOTE / SIMPLE_MAJORITY
            decision, reasoning = self._weighted_decision(approve_weight, reject_weight)

        result = VotingResult(
            decision=decision,
            reasoning=reasoning,
            votes=votes,
            vetoes=blocking_vetoes,
            approve_weight=approve_weight,
            reject_weight=reject_weight,
            total_weight=total_weight,
            strategy=strategy.value if hasattr(strategy, "value") else str(strategy),
            topic=topic,
        )
        self._save_result(result)
        return result

    def _consensus_decision(self, votes: list[Vote]) -> tuple[str, str]:
        for v in votes:
            if v.vote_choice == VoteChoice.REJECT:
                return "needs_changes", f"{v.agent_role} rejected: {v.reasoning}"
            if v.vote_choice == VoteChoice.VETO and not v.can_veto:
                return "needs_changes", f"{v.agent_role} has concerns: {v.reasoning}"
        return "approved", "All agents approved (consensus)"

    def _super_majority_decision(self, approve_weight: int, total_weight: int) -> tuple[str, str]:
        if total_weight == 0:
            return "rejected", "No votes cast"
        ratio = approve_weight / total_weight
        if ratio >= 0.75:
            return "approved", f"Super majority reached ({ratio:.0%} approval)"
        return "rejected", f"Super majority not reached ({ratio:.0%} approval, need 75%)"

    def _weighted_decision(self, approve_weight: int, reject_weight: int) -> tuple[str, str]:
        if approve_weight > reject_weight:
            return "approved", f"Approved by weighted vote ({approve_weight} vs {reject_weight})"
        return "rejected", f"Rejected by weighted vote ({reject_weight} vs {approve_weight})"

    def _save_result(self, result: VotingResult) -> None:
        filename = f"vote_{int(result.timestamp * 1000)}.json"
        vote_file = self.votes_dir / filename
        with open(vote_file, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
