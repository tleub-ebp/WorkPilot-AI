"""Claude Teams - Multi-agent collaborative decision-making."""

from teams.orchestrator import ClaudeTeam
from teams.config import TeamConfig, TeamMode, DebateStrategy
from teams.roles import AgentRole

__all__ = ["ClaudeTeam", "TeamConfig", "TeamMode", "DebateStrategy", "AgentRole"]
