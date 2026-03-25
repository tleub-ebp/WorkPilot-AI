"""
Claude Teams - Orchestrator
==============================

Coordinates multi-agent team debates, voting, and decision-making.
"""

from pathlib import Path
from typing import List, Optional

from teams.config import TeamConfig, DebateStrategy
from teams.communication import CommunicationBus, MessageType
from teams.roles import AgentRole, get_role_definition, get_active_roles
from teams.voting import Vote, VoteChoice, VotingSystem


class ClaudeTeam:
    """Orchestrates a team of AI agents for collaborative decision-making."""

    def __init__(self, config: TeamConfig, work_dir: Path):
        self.config = config
        self.work_dir = Path(work_dir)
        self.bus = CommunicationBus(work_dir)
        self.voting = VotingSystem(work_dir)
        self.roles = get_active_roles(config.active_roles)
