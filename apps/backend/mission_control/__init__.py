"""
Mission Control — Multi-Agent Orchestration Hub
================================================

NASA-style dashboard for orchestrating multiple AI agents simultaneously
with full visibility on each agent's status, reasoning, files, and tokens.

Key features:
- Multi-agent orchestration with per-agent model assignment
- Real-time reasoning tree visualization
- Pause/resume/redirect agents
- Token consumption tracking per agent
- Provider mixing (Anthropic, OpenAI, Google, Grok, Ollama, local)
"""

from .orchestrator import MissionControlOrchestrator, get_mission_control
from .agent_slot import AgentSlot, AgentStatus, AgentRole
from .decision_tree import DecisionNode, DecisionTree

__all__ = [
    "MissionControlOrchestrator",
    "get_mission_control",
    "AgentSlot",
    "AgentStatus",
    "AgentRole",
    "DecisionNode",
    "DecisionTree",
]
