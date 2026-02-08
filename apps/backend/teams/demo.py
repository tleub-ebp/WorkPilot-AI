"""
Claude Teams - Demo Script
===========================

Demonstrates Claude Teams collaborative mode with a sample task.
This is a demo that shows the flow without making real API calls.
"""

import asyncio
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

# Add backend to a path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

# Mock Claude SDK for demo
from unittest.mock import AsyncMock, MagicMock, Mock

class MockResponse:
    def __init__(self, text):
        self.text = text

# Mock the client module
mock_client_module = MagicMock()
mock_create_client = Mock()

class MockClient:
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        pass
    
    async def run_turn(self, prompt):
        # Simulate agent responses based on role
        if "Architect" in prompt:
            return MockResponse(
                "I propose using a microservices architecture with REST APIs. "
                "This provides scalability and clear separation of concerns."
            )
        elif "Security" in prompt:
            if "vote" in prompt.lower():
                return MockResponse(
                    "APPROVE: The proposed architecture is secure. "
                    "Make sure to add authentication middleware."
                )
            else:
                return MockResponse(
                    "CONCERN: We need to ensure all endpoints have proper authentication. "
                    "I recommend using JWT tokens with httpOnly cookies."
                )
        elif "Developer" in prompt:
            if "vote" in prompt.lower():
                return MockResponse("APPROVE: Looks implementable and maintainable.")
            else:
                return MockResponse(
                    "SUPPORT: I agree with the microservices approach. "
                    "It's a bit complex but manageable."
                )
        elif "QA" in prompt:
            if "vote" in prompt.lower():
                return MockResponse(
                    "APPROVE_WITH_CHANGES: Good approach but we need comprehensive "
                    "integration tests for the service boundaries."
                )
            else:
                return MockResponse(
                    "SUPPORT: This is testable. Let's ensure we have "
                    "proper test isolation between services."
                )
        return MockResponse("I agree with the proposal.")

def mock_create_client(*args, **kwargs):
    return MockClient()

mock_client_module.create_client = mock_create_client
sys.modules['core.client'] = mock_client_module

# Mock debug module
mock_debug = MagicMock()
sys.modules['debug'] = mock_debug

# Now import teams
from teams import ClaudeTeam, TeamConfig, TeamMode


async def demo_collaborative_mode():
    """Demonstrate Claude Teams in collaborative mode."""
    
    print("=" * 70)
    print(" CLAUDE TEAMS - DEMO")
    print("=" * 70)
    print()
    print("This demo shows how Claude Teams works in collaborative mode.")
    print("Agents will debate, challenge, and vote on a design decision.")
    print()
    
    # Create temporary directories
    with TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "project"
        spec_dir = Path(tmpdir) / "spec"
        project_dir.mkdir()
        spec_dir.mkdir()
        
        # Configure team for demo
        config = TeamConfig(
            mode=TeamMode.COLLABORATIVE,
            max_debate_rounds=2,  # Keep it short for demo
            active_roles=["architect", "developer", "security", "qa_engineer"],
            security_can_veto=True,
            architect_can_veto=True,
        )
        
        # Create team
        print("🤖 Creating Claude Team...")
        print(f"   Mode: {config.mode.value}")
        print(f"   Active roles: {', '.join(config.active_roles)}")
        print(f"   Max debate rounds: {config.max_debate_rounds}")
        print()
        
        team = ClaudeTeam(
            project_dir=project_dir,
            spec_dir=spec_dir,
            config=config,
        )
        
        # Run collaboration
        task = "Design a user authentication system for our web application"
        
        print(f"📝 Task: {task}")
        print()
        
        result = await team.collaborate_on_task(task)
        
        # Show results
        print()
        print("=" * 70)
        print(" RESULTS")
        print("=" * 70)
        print()
        print(f"Status: {result['status']}")
        
        if result['status'] == 'success':
            print("✅ Team approved the approach!")
            print()
            print("Debate logs saved to:")
            print(f"  {spec_dir / 'debates'}")
            print()
            
            # Show debate files
            debate_dir = spec_dir / "debates"
            if debate_dir.exists():
                print("Generated files:")
                for file in debate_dir.glob("**/*.json"):
                    print(f"  - {file.relative_to(spec_dir)}")
        else:
            print(f"❌ Team rejected: {result.get('reason', 'Unknown')}")
        
        print()
        print("=" * 70)


async def demo_veto_scenario():
    """Demonstrate security veto blocking a bad decision."""
    
    print()
    print("=" * 70)
    print(" CLAUDE TEAMS - VETO DEMO")
    print("=" * 70)
    print()
    print("This demo shows Security Engineer using veto rights.")
    print()
    
    with TemporaryDirectory() as tmpdir:
        from teams.voting import Vote, VoteChoice, VotingSystem
        from teams.config import DebateStrategy
        
        voting = VotingSystem(Path(tmpdir))
        
        # Simulate a bad security decision
        print("Scenario: Team voting on storing passwords in localStorage")
        print()
        
        votes = [
            Vote("architect", VoteChoice.APPROVE, 
                 "Convenient for users", weight=5, can_veto=True),
            Vote("developer", VoteChoice.APPROVE, 
                 "Easy to implement", weight=3, can_veto=False),
            Vote("security", VoteChoice.VETO, 
                 "CRITICAL SECURITY VIOLATION: localStorage is vulnerable to XSS attacks. "
                 "Passwords must NEVER be stored in localStorage. Use httpOnly cookies instead.",
                 weight=5, can_veto=True),
            Vote("qa", VoteChoice.APPROVE, 
                 "Testable approach", weight=3, can_veto=False),
        ]
        
        result = voting.conduct_vote(votes, DebateStrategy.WEIGHTED_VOTE, "localStorage passwords")
        
        print("Votes:")
        for vote in votes:
            icon = "🛑" if vote.vote_choice == VoteChoice.VETO else "✓" if vote.vote_choice == VoteChoice.APPROVE else "✗"
            veto_badge = " [CAN VETO]" if vote.can_veto else ""
            print(f"  {icon} {vote.agent_role.upper()}{veto_badge}: {vote.vote_choice.value}")
            print(f"     Reasoning: {vote.reasoning[:80]}...")
            print()
        
        print(f"Decision: {result.decision.upper()}")
        print(f"Reasoning: {result.reasoning}")
        print()
        
        if result.vetoes:
            print("🛑 VETO EXERCISED BY:")
            for veto in result.vetoes:
                print(f"   - {veto.agent_role.upper()}")
        
        print()
        print("=" * 70)


async def demo_weighted_voting():
    """Demonstrate weighted voting without veto."""
    
    print()
    print("=" * 70)
    print(" CLAUDE TEAMS - WEIGHTED VOTING DEMO")
    print("=" * 70)
    print()
    print("This demo shows how role weights affect decisions.")
    print()
    
    with TemporaryDirectory() as tmpdir:
        from teams.voting import Vote, VoteChoice, VotingSystem
        from teams.config import DebateStrategy
        
        voting = VotingSystem(Path(tmpdir))
        
        print("Scenario: Technical approach decision")
        print()
        
        votes = [
            Vote("architect", VoteChoice.APPROVE, 
                 "Solid architecture", weight=5, can_veto=False),
            Vote("developer", VoteChoice.REJECT, 
                 "Too complex to implement", weight=3, can_veto=False),
            Vote("security", VoteChoice.APPROVE, 
                 "Secure design", weight=5, can_veto=False),
            Vote("qa", VoteChoice.REJECT, 
                 "Hard to test", weight=3, can_veto=False),
        ]
        
        result = voting.conduct_vote(votes, DebateStrategy.WEIGHTED_VOTE, "approach")
        
        print("Votes (with weights):")
        for vote in votes:
            icon = "✓" if vote.vote_choice == VoteChoice.APPROVE else "✗"
            print(f"  {icon} {vote.agent_role.upper()} (weight: {vote.weight}): {vote.vote_choice.value}")
        
        print()
        print(f"Total weight: {result.total_weight}")
        print(f"Approve weight: {result.approve_weight} ({result.approve_weight/result.total_weight*100:.1f}%)")
        print(f"Reject weight: {result.reject_weight} ({result.reject_weight/result.total_weight*100:.1f}%)")
        print()
        print(f"Decision: {result.decision.upper()}")
        print()
        print("Note: Architect (5) + Security (5) = 10 points > Developer (3) + QA (3) = 6 points")
        print()
        print("=" * 70)


async def main():
    """Run all demos."""
    
    print()
    print("🎬 CLAUDE TEAMS - COMPREHENSIVE DEMO")
    print()
    print("This demo showcases the key features of Claude Teams:")
    print("  1. Collaborative debate and voting")
    print("  2. Security veto rights")
    print("  3. Weighted voting system")
    print()
    input("Press Enter to start...")
    
    # Demo 1: Full collaborative flow
    await demo_collaborative_mode()
    input("\nPress Enter for next demo...")
    
    # Demo 2: Veto scenario
    await demo_veto_scenario()
    input("\nPress Enter for next demo...")
    
    # Demo 3: Weighted voting
    await demo_weighted_voting()
    
    print()
    print("=" * 70)
    print(" DEMO COMPLETE")
    print("=" * 70)
    print()
    print("Claude Teams is ready to use!")
    print()
    print("To use in your code:")
    print()
    print("  from teams import ClaudeTeam, TeamConfig")
    print()
    print("  team = ClaudeTeam(project_dir, spec_dir,")
    print("                    TeamConfig.for_critical_task())")
    print()
    print("  result = await team.collaborate_on_task(task)")
    print()
    print("See apps/backend/teams/README.md for full documentation.")
    print()


if __name__ == "__main__":
    asyncio.run(main())

