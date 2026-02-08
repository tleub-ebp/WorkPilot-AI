"""
Claude Teams - Collaborative Multi-Agent System
================================================

Feature #4 from the roadmap: Multi-agent team with autonomous collaboration,
debate, and consensus decision-making.

This is an OPTIONAL mode that can be enabled for critical/complex tasks.
The standard orchestrated pipeline remains the default.

Architecture:
    - Agent Roles: Specialized agents with distinct personalities
    - Communication Bus: Inter-agent messaging system
    - Debate Framework: Multi-round discussions
    - Voting System: Weighted votes with veto rights
    - Consensus Detection: Automatic agreement detection

Usage:
    from teams import ClaudeTeam, TeamConfig
    
    team = ClaudeTeam(
        project_dir=project_dir,
        spec_dir=spec_dir,
        config=TeamConfig(mode="collaborative")
    )
    
    result = await team.collaborate_on_task(task_description)
"""

from .config import DebateStrategy, TeamConfig, TeamMode
from .orchestrator import ClaudeTeam
from .roles import AgentRole, RoleDefinition

__all__ = [
    "ClaudeTeam",
    "TeamConfig",
    "TeamMode",
    "DebateStrategy",
    "AgentRole",
    "RoleDefinition",
]

