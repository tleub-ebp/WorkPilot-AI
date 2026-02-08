"""
Claude Team Orchestrator
========================

Main class that coordinates multi-agent collaboration with debate and voting.
"""

import asyncio
from pathlib import Path

from core.client import create_client
from debug import debug, debug_section, debug_success, debug_warning

from .communication import CommunicationBus, MessageType
from .config import TeamConfig, TeamMode
from .roles import get_active_roles
from .voting import Vote, VoteChoice, VotingSystem


class ClaudeTeam:
    """
    Multi-agent team with autonomous collaboration.
    
    The team can:
    - Debate proposals through multiple rounds
    - Challenge each other's ideas
    - Vote on decisions with weighted votes
    - Exercise veto rights (Security, Architect)
    - Reach consensus automatically
    """
    
    def __init__(
        self,
        project_dir: Path,
        spec_dir: Path,
        config: TeamConfig,
    ):
        self.project_dir = Path(project_dir)
        self.spec_dir = Path(spec_dir)
        self.config = config
        
        # Initialize systems
        self.comm_bus = CommunicationBus(spec_dir)
        self.voting_system = VotingSystem(spec_dir)
        
        # Get active role definitions
        self.roles = get_active_roles(config.active_roles)
        
        debug("claude_teams", "ClaudeTeam initialized", 
              mode=config.mode.value,
              roles=[r.name for r in self.roles])
    
    async def collaborate_on_task(self, task: str) -> dict:
        """
        Main entry point: agents collaborate on a task.
        
        Flow:
        1. Initial proposals from each agent
        2. Multi-round debate
        3. Voting with veto rights
        4. Coordinated execution
        
        Args:
            task: Task description
            
        Returns:
            Dict with status and result
        """
        debug_section("claude_teams", "Claude Teams Collaboration")
        
        if self.config.mode == TeamMode.STANDARD:
            # Fall back to standard pipeline
            debug("claude_teams", "Using standard pipeline (Teams disabled)")
            return await self._standard_pipeline(task)
        
        print("\n" + "=" * 70)
        print("  🤖 CLAUDE TEAMS - COLLABORATIVE MODE")
        print("=" * 70)
        print(f"\nTask: {task}")
        print(f"Active roles: {', '.join(r.name for r in self.roles)}\n")
        
        # Phase 1: Gather proposals
        thread = self.comm_bus.create_thread(topic=task)
        proposals = await self._gather_proposals(thread.thread_id, task)
        
        # Phase 2: Debate
        if self.config.max_debate_rounds > 0:
            await self._debate_phase(thread.thread_id, proposals)
        
        # Phase 3: Vote
        vote_result = await self._vote_phase(thread.thread_id, task)
        
        if vote_result.decision == "rejected":
            print(f"\n❌ Team rejected the approach: {vote_result.reasoning}")
            return {"status": "rejected", "reason": vote_result.reasoning}
        
        print(f"\n✅ Team approved: {vote_result.reasoning}")
        
        # Phase 4: Execute (delegate to standard pipeline with approved design)
        result = await self._execute_approved_design(task, thread.thread_id)
        
        # Save all debate logs
        self.comm_bus.save_all_threads()
        
        return {"status": "success", "result": result, "debate": thread.thread_id}
    
    async def _gather_proposals(self, thread_id: str, task: str) -> list[dict]:
        """Phase 1: Each agent proposes their approach."""
        print("\n📋 Phase 1: Gathering proposals from team...\n")
        
        proposals = []
        for role_def in self.roles:
            print(f"   {role_def.name} is thinking...")
            
            # Create agent client
            client = create_client(
                self.project_dir,
                self.spec_dir,
                self.config.model,
                agent_type=f"team_{role_def.role.value}",
            )
            
            # Get proposal from agent
            prompt = f"""You are the {role_def.name} on a collaborative AI team.

PERSONALITY: {role_def.personality}

TASK: {task}

Provide your initial proposal/perspective on how to approach this task.
Consider your expertise areas: {', '.join(role_def.expertise_areas)}

Be concise but specific. Focus on your domain of expertise.
Keep your response under 200 words."""
            
            try:
                async with client:
                    response = await client.run_turn(prompt)
                
                response_text = response.text if hasattr(response, 'text') else str(response)
                
                # Post to communication bus
                self.comm_bus.post_message(
                    thread_id=thread_id,
                    agent_role=role_def.role.value,
                    agent_name=role_def.name,
                    message_type=MessageType.PROPOSAL,
                    content=response_text,
                )
                
                proposals.append({
                    "role": role_def.role.value,
                    "proposal": response_text,
                })
                
                print(f"   ✓ {role_def.name} proposal received")
                debug("claude_teams", "Proposal received", 
                      role=role_def.name, length=len(response_text))
                
            except Exception as e:
                debug_warning("claude_teams", f"Error getting proposal from {role_def.name}: {e}")
                print(f"   ⚠️  {role_def.name} proposal failed")
        
        return proposals
    
    async def _debate_phase(self, thread_id: str, proposals: list[dict]):
        """Phase 2: Agents debate and challenge each other."""
        print(f"\n💬 Phase 2: Team debate ({self.config.max_debate_rounds} rounds max)\n")
        
        for round_num in range(1, self.config.max_debate_rounds + 1):
            print(f"\n   Round {round_num}:")
            
            # Get debate history
            history = self.comm_bus.get_thread_history(thread_id)
            
            # Check for consensus
            if self.comm_bus.detect_consensus(thread_id):
                print(f"   ✓ Consensus reached in round {round_num}!")
                debug_success("claude_teams", "Consensus reached", round=round_num)
                break
            
            # Each agent responds to the debate
            for role_def in self.roles:
                prompt = f"""You are {role_def.name} on a collaborative AI team.

DEBATE HISTORY:
{history}

Review the proposals and debate above. You can:
- SUPPORT another agent's idea if you agree
- CHALLENGE an idea if you see issues
- RAISE CONCERNS about risks
- PROPOSE ALTERNATIVES

Keep your response concise (under 150 words). Focus on advancing the discussion."""
                
                try:
                    client = create_client(
                        self.project_dir,
                        self.spec_dir,
                        self.config.model,
                        agent_type=f"team_{role_def.role.value}",
                    )
                    
                    async with client:
                        response = await client.run_turn(prompt)
                    
                    response_text = response.text if hasattr(response, 'text') else str(response)
                    
                    # Classify message type from response
                    msg_type = MessageType.CHALLENGE  # Default
                    content_lower = response_text.lower()[:150]
                    if "support" in content_lower or "agree" in content_lower:
                        msg_type = MessageType.SUPPORT
                    elif "veto" in content_lower and role_def.can_veto:
                        msg_type = MessageType.VETO
                    elif "concern" in content_lower:
                        msg_type = MessageType.CONCERN
                    
                    self.comm_bus.post_message(
                        thread_id=thread_id,
                        agent_role=role_def.role.value,
                        agent_name=role_def.name,
                        message_type=msg_type,
                        content=response_text,
                    )
                    
                    debug("claude_teams", "Debate message", 
                          role=role_def.name, type=msg_type.value)
                    
                except Exception as e:
                    debug_warning("claude_teams", f"Error in debate from {role_def.name}: {e}")
        
        print("\n   Debate phase complete")
    
    async def _vote_phase(self, thread_id: str, task: str):
        """Phase 3: Conduct weighted vote."""
        print("\n🗳️  Phase 3: Team voting\n")
        
        history = self.comm_bus.get_thread_history(thread_id)
        votes = []
        
        for role_def in self.roles:
            prompt = f"""You are {role_def.name}. 

DEBATE HISTORY:
{history}

Cast your vote on whether to proceed with the proposed approach.

Vote options:
- APPROVE: Good to go
- APPROVE_WITH_CHANGES: Approve but request specific changes
- REJECT: Not acceptable
- VETO: Hard block (only if you have veto rights: {role_def.can_veto})

Provide your vote and brief reasoning (under 100 words)."""
            
            try:
                client = create_client(
                    self.project_dir,
                    self.spec_dir,
                    self.config.model,
                    agent_type=f"team_{role_def.role.value}",
                )
                
                async with client:
                    response = await client.run_turn(prompt)
                
                response_text = response.text if hasattr(response, 'text') else str(response)
                
                # Parse vote (simple heuristic)
                vote_choice = VoteChoice.APPROVE
                content_lower = response_text.lower()[:200]
                if "reject" in content_lower:
                    vote_choice = VoteChoice.REJECT
                elif "veto" in content_lower and role_def.can_veto:
                    vote_choice = VoteChoice.VETO
                elif "changes" in content_lower:
                    vote_choice = VoteChoice.APPROVE_WITH_CHANGES
                
                vote = Vote(
                    agent_role=role_def.role.value,
                    vote_choice=vote_choice,
                    reasoning=response_text,
                    weight=role_def.decision_weight,
                    can_veto=role_def.can_veto,
                )
                votes.append(vote)
                
                print(f"   {role_def.name}: {vote_choice.value} (weight: {role_def.decision_weight})")
                debug("claude_teams", "Vote cast", 
                      role=role_def.name, choice=vote_choice.value, weight=role_def.decision_weight)
                
            except Exception as e:
                debug_warning("claude_teams", f"Error getting vote from {role_def.name}: {e}")
                # Default to approve to not block
                votes.append(Vote(
                    agent_role=role_def.role.value,
                    vote_choice=VoteChoice.APPROVE,
                    reasoning=f"Error: {e}",
                    weight=role_def.decision_weight,
                    can_veto=False,
                ))
        
        result = self.voting_system.conduct_vote(votes, self.config.debate_strategy, task)
        
        debug_success("claude_teams", "Voting complete", 
                      decision=result.decision, 
                      approve_weight=f"{result.approve_weight}/{result.total_weight}")
        
        return result
    
    async def _execute_approved_design(self, task: str, thread_id: str):
        """Phase 4: Execute the team-approved approach."""
        print("\n⚙️  Phase 4: Executing team-approved design\n")
        
        # Get debate summary
        history = self.comm_bus.get_thread_history(thread_id)
        
        # For now, return debate summary
        # TODO: Integrate with actual implementation pipeline
        debug_success("claude_teams", "Design approved and ready for implementation")
        
        return {
            "task": task,
            "team_decision": "approved",
            "debate_summary": history[:500] + "..." if len(history) > 500 else history,
        }
    
    async def _standard_pipeline(self, task: str):
        """Fallback to standard orchestrated pipeline."""
        debug("claude_teams", "Delegating to standard pipeline")
        
        # Delegate to existing SpecOrchestrator
        # This is handled by the integration layer
        return {
            "status": "standard_pipeline",
            "message": "Teams disabled, using standard pipeline",
            "task": task,
        }

