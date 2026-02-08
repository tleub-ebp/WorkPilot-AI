"""
Quick smoke test for Claude Teams
==================================

Fast validation that basic components work.
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent.parent / "apps" / "backend"
sys.path.insert(0, str(backend_path))

# Mock dependencies
from unittest.mock import MagicMock
sys.modules['claude_agent_sdk'] = MagicMock()
sys.modules['core.client'] = MagicMock()
sys.modules['debug'] = MagicMock()

print("🔍 Testing Claude Teams components...\n")

# Test 1: Config
print("1️⃣  Testing TeamConfig...")
from teams.config import TeamConfig, TeamMode, DebateStrategy

config = TeamConfig.for_critical_task()
assert config.mode == TeamMode.COLLABORATIVE
assert config.security_can_veto is True
assert config.architect_can_veto is True
print("   ✅ TeamConfig works")

# Test 2: Roles
print("2️⃣  Testing Agent Roles...")
from teams.roles import AgentRole, get_role_definition, get_active_roles

architect = get_role_definition(AgentRole.ARCHITECT)
assert architect.name == "System Architect"
assert architect.decision_weight == 5
assert architect.can_veto is True

security = get_role_definition(AgentRole.SECURITY)
assert security.decision_weight == 5
assert security.can_veto is True

roles = get_active_roles(["architect", "developer", "security"])
assert len(roles) == 3
print("   ✅ Roles work")

# Test 3: Voting
print("3️⃣  Testing Voting System...")
from teams.voting import Vote, VoteChoice, VotingSystem, VotingResult
from tempfile import TemporaryDirectory

with TemporaryDirectory() as tmpdir:
    voting = VotingSystem(Path(tmpdir))
    
    votes = [
        Vote("architect", VoteChoice.APPROVE, "Good", weight=5, can_veto=True),
        Vote("security", VoteChoice.VETO, "Risk!", weight=5, can_veto=True),
    ]
    
    result = voting.conduct_vote(votes, DebateStrategy.WEIGHTED_VOTE, "test")
    assert result.decision == "rejected"
    assert len(result.vetoes) == 1

print("   ✅ Voting System works")

# Test 4: Communication
print("4️⃣  Testing Communication Bus...")
from teams.communication import CommunicationBus, MessageType

with TemporaryDirectory() as tmpdir:
    bus = CommunicationBus(Path(tmpdir))
    thread = bus.create_thread("Test topic")
    
    assert thread.thread_id == "thread_1"
    
    bus.post_message(
        thread.thread_id,
        "architect",
        "System Architect",
        MessageType.PROPOSAL,
        "Use REST API"
    )
    
    assert len(thread.messages) == 1
    assert thread.messages[0].content == "Use REST API"

print("   ✅ Communication Bus works")

# Test 5: Orchestrator (imports only)
print("5️⃣  Testing Orchestrator imports...")
from teams.orchestrator import ClaudeTeam

print("   ✅ Orchestrator imports successfully")

# Test 6: Package exports
print("6️⃣  Testing package exports...")
from teams import ClaudeTeam, TeamConfig, TeamMode, AgentRole

assert ClaudeTeam is not None
assert TeamConfig is not None
assert TeamMode is not None
assert AgentRole is not None
print("   ✅ Package exports work")

print("\n" + "=" * 50)
print("🎉 All Claude Teams components are working!")
print("=" * 50)
print("\nNext steps:")
print("  1. Integrate with SpecOrchestrator")
print("  2. Add CLI flags (--enable-teams)")
print("  3. Test with real Claude API")
print("  4. Build UI components")

