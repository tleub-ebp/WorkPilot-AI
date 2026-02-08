"""
Tests for Claude Teams - Voting System
=======================================

Tests the voting logic, veto rights, and weighted voting.
"""

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

# Add backend to path BEFORE any imports
backend_path = Path(__file__).parent.parent.parent / "apps" / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Mock the SDK before importing teams modules
from unittest.mock import MagicMock
sys.modules['claude_agent_sdk'] = MagicMock()
sys.modules['core.client'] = MagicMock()
sys.modules['debug'] = MagicMock()

from teams.config import DebateStrategy
from teams.voting import Vote, VoteChoice, VotingSystem


class TestVotingSystem:
    """Test suite for voting system."""

    def test_security_veto_blocks_decision(self):
        """Security veto should block despite majority approval."""
        with TemporaryDirectory() as tmpdir:
            voting = VotingSystem(Path(tmpdir))
            
            votes = [
                Vote("architect", VoteChoice.APPROVE, "Good design", weight=5, can_veto=True),
                Vote("developer", VoteChoice.APPROVE, "Easy to implement", weight=3, can_veto=False),
                Vote("security", VoteChoice.VETO, "SQL injection risk!", weight=5, can_veto=True),
                Vote("qa", VoteChoice.APPROVE, "Testable", weight=3, can_veto=False),
            ]
            
            result = voting.conduct_vote(votes, DebateStrategy.WEIGHTED_VOTE, "Feature X")
            
            assert result.decision == "rejected"
            assert "security" in result.reasoning.lower()
            assert len(result.vetoes) == 1
            assert result.vetoes[0].agent_role == "security"

    def test_weighted_vote_with_architect_majority(self):
        """Architect's high weight should sway decision."""
        with TemporaryDirectory() as tmpdir:
            voting = VotingSystem(Path(tmpdir))
            
            votes = [
                Vote("architect", VoteChoice.APPROVE, "Good", weight=5, can_veto=False),
                Vote("developer", VoteChoice.REJECT, "Too complex", weight=3, can_veto=False),
                Vote("qa", VoteChoice.REJECT, "Hard to test", weight=3, can_veto=False),
            ]
            
            result = voting.conduct_vote(votes, DebateStrategy.WEIGHTED_VOTE, "Approach")
            
            # Architect (5) < Developer + QA (6)
            assert result.decision == "rejected"
            assert result.approve_weight == 5
            assert result.reject_weight == 6

    def test_consensus_requires_all_approve(self):
        """Consensus strategy requires unanimous approval."""
        with TemporaryDirectory() as tmpdir:
            voting = VotingSystem(Path(tmpdir))
            
            votes = [
                Vote("architect", VoteChoice.APPROVE, "Good", weight=5, can_veto=False),
                Vote("developer", VoteChoice.APPROVE, "OK", weight=3, can_veto=False),
                Vote("security", VoteChoice.APPROVE_WITH_CHANGES, "Add auth", weight=5, can_veto=False),
                Vote("qa", VoteChoice.APPROVE, "Fine", weight=3, can_veto=False),
            ]
            
            result = voting.conduct_vote(votes, DebateStrategy.CONSENSUS, "Plan")
            
            # All approve or approve_with_changes = consensus
            assert result.decision == "approved"

    def test_consensus_fails_with_one_reject(self):
        """One rejection breaks consensus."""
        with TemporaryDirectory() as tmpdir:
            voting = VotingSystem(Path(tmpdir))
            
            votes = [
                Vote("architect", VoteChoice.APPROVE, "Good", weight=5, can_veto=False),
                Vote("developer", VoteChoice.REJECT, "No", weight=3, can_veto=False),
                Vote("security", VoteChoice.APPROVE, "OK", weight=5, can_veto=False),
            ]
            
            result = voting.conduct_vote(votes, DebateStrategy.CONSENSUS, "Plan")
            
            assert result.decision == "needs_changes"

    def test_veto_without_rights_ignored(self):
        """Veto from agent without veto rights should be ignored."""
        with TemporaryDirectory() as tmpdir:
            voting = VotingSystem(Path(tmpdir))
            
            votes = [
                Vote("architect", VoteChoice.APPROVE, "Good", weight=5, can_veto=True),
                Vote("developer", VoteChoice.VETO, "I veto!", weight=3, can_veto=False),  # No rights!
                Vote("security", VoteChoice.APPROVE, "OK", weight=5, can_veto=True),
            ]
            
            result = voting.conduct_vote(votes, DebateStrategy.WEIGHTED_VOTE, "Plan")
            
            # Developer veto ignored (no rights), so approved
            assert result.decision == "approved"
            assert len(result.vetoes) == 0

    def test_super_majority_requires_75_percent(self):
        """Super majority requires 75%+ of weight."""
        with TemporaryDirectory() as tmpdir:
            voting = VotingSystem(Path(tmpdir))
            
            # Total weight: 16, need 12+ to pass
            votes = [
                Vote("architect", VoteChoice.APPROVE, "Good", weight=5, can_veto=False),
                Vote("developer", VoteChoice.APPROVE, "OK", weight=3, can_veto=False),
                Vote("security", VoteChoice.APPROVE, "Fine", weight=5, can_veto=False),
                Vote("qa", VoteChoice.REJECT, "Concerns", weight=3, can_veto=False),
            ]
            
            result = voting.conduct_vote(votes, DebateStrategy.SUPER_MAJORITY, "Plan")
            
            # 13/16 = 81% > 75%
            assert result.decision == "approved"
            assert result.approve_weight == 13
            assert result.total_weight == 16

    def test_vote_result_saves_to_disk(self):
        """Vote results should be saved to JSON."""
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            voting = VotingSystem(tmppath)
            
            votes = [
                Vote("architect", VoteChoice.APPROVE, "Good", weight=5, can_veto=False),
            ]
            
            result = voting.conduct_vote(votes, DebateStrategy.WEIGHTED_VOTE, "test_topic")
            
            # Check file was created
            vote_files = list((tmppath / "debates" / "votes").glob("*.json"))
            assert len(vote_files) == 1
            
            # Check file contains result
            import json
            with open(vote_files[0]) as f:
                saved = json.load(f)
            
            assert saved["decision"] == result.decision
            assert len(saved["votes"]) == 1


def test_vote_is_blocking():
    """Test Vote.is_blocking() method."""
    # Veto with rights = blocking
    v1 = Vote("security", VoteChoice.VETO, "Risk", weight=5, can_veto=True)
    assert v1.is_blocking() is True
    
    # Veto without rights = not blocking
    v2 = Vote("developer", VoteChoice.VETO, "No", weight=3, can_veto=False)
    assert v2.is_blocking() is False
    
    # Regular reject = not blocking
    v3 = Vote("qa", VoteChoice.REJECT, "Issues", weight=3, can_veto=True)
    assert v3.is_blocking() is False


if __name__ == "__main__":
    # Run basic smoke test
    print("Running basic voting tests...\n")
    
    test = TestVotingSystem()
    
    try:
        test.test_security_veto_blocks_decision()
        print("✅ Security veto test passed")
        
        test.test_weighted_vote_with_architect_majority()
        print("✅ Weighted vote test passed")
        
        test.test_consensus_requires_all_approve()
        print("✅ Consensus test passed")
        
        test.test_veto_without_rights_ignored()
        print("✅ Veto rights test passed")
        
        test.test_vote_result_saves_to_disk()
        print("✅ Persistence test passed")
        
        test_vote_is_blocking()
        print("✅ Blocking logic test passed")
        
        print("\n🎉 All voting tests passed!")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

