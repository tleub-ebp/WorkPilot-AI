"""
Mission Control Orchestrator — Central hub for multi-agent management.

Manages multiple AgentSlots, coordinates their execution,
broadcasts state changes via WebSocket, and provides the API
surface for the frontend Mission Control dashboard.
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Any, Optional

from .agent_slot import AgentSlot, AgentStatus, AgentRole, TokenUsage
from .decision_tree import DecisionTree

logger = logging.getLogger(__name__)


class MissionControlOrchestrator:
    """
    Central orchestrator for Mission Control.

    Manages a pool of agent slots, tracks their state, and broadcasts
    updates to connected frontend clients via WebSocket events.
    """

    def __init__(self):
        self._slots: dict[str, AgentSlot] = {}
        self._decision_trees: dict[str, DecisionTree] = {}
        self._subscribers: set[Any] = set()
        self._session_id: str = f"mc-{uuid.uuid4().hex[:8]}"
        self._created_at: float = time.time()
        self._is_active: bool = False
        self._event_log: list[dict[str, Any]] = []

    # ---------------------------------------------------------------
    # Session lifecycle
    # ---------------------------------------------------------------

    def start_session(self) -> dict[str, Any]:
        """Start a new Mission Control session."""
        self._is_active = True
        self._created_at = time.time()
        self._session_id = f"mc-{uuid.uuid4().hex[:8]}"
        self._event_log = []
        logger.info(f"Mission Control session started: {self._session_id}")
        return self.get_session_info()

    def stop_session(self):
        """Stop the current session and reset all agents."""
        self._is_active = False
        for slot in self._slots.values():
            if slot.status == AgentStatus.RUNNING:
                slot.complete()
        logger.info(f"Mission Control session stopped: {self._session_id}")

    def get_session_info(self) -> dict[str, Any]:
        """Get current session information."""
        return {
            "session_id": self._session_id,
            "is_active": self._is_active,
            "created_at": self._created_at,
            "agent_count": len(self._slots),
            "running_count": sum(
                1 for s in self._slots.values()
                if s.status == AgentStatus.RUNNING
            ),
            "total_tokens": sum(
                s.tokens.total_tokens for s in self._slots.values()
            ),
            "total_cost_usd": round(sum(
                s.tokens.estimated_cost_usd for s in self._slots.values()
            ), 6),
            "elapsed_seconds": round(time.time() - self._created_at, 1),
        }

    # ---------------------------------------------------------------
    # Agent slot management
    # ---------------------------------------------------------------

    def create_agent(
        self,
        name: str,
        role: str = "custom",
        provider: str = "",
        model: str = "",
        model_label: str = "",
    ) -> AgentSlot:
        """Create a new agent slot."""
        try:
            agent_role = AgentRole(role)
        except ValueError:
            agent_role = AgentRole.CUSTOM

        slot = AgentSlot(
            name=name,
            role=agent_role,
            provider=provider,
            model=model,
            model_label=model_label or model,
        )
        self._slots[slot.id] = slot
        self._decision_trees[slot.id] = DecisionTree(slot.id)

        self._log_event("agent_created", {
            "agent_id": slot.id,
            "name": name,
            "role": role,
            "provider": provider,
            "model": model,
        })
        logger.info(f"Agent created: {slot.id} ({name}, {role}, {provider}:{model})")
        return slot

    def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent slot."""
        if agent_id not in self._slots:
            return False
        slot = self._slots[agent_id]
        if slot.status == AgentStatus.RUNNING:
            slot.fail("Removed while running")
        del self._slots[agent_id]
        self._decision_trees.pop(agent_id, None)
        self._log_event("agent_removed", {"agent_id": agent_id})
        return True

    def get_agent(self, agent_id: str) -> Optional[AgentSlot]:
        """Get a specific agent slot."""
        return self._slots.get(agent_id)

    def get_all_agents(self) -> list[dict[str, Any]]:
        """Get all agent slots as dicts."""
        return [slot.to_dict() for slot in self._slots.values()]

    def update_agent_config(
        self,
        agent_id: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        model_label: Optional[str] = None,
        name: Optional[str] = None,
        role: Optional[str] = None,
    ) -> Optional[AgentSlot]:
        """Update agent configuration (provider, model, name, role)."""
        slot = self._slots.get(agent_id)
        if not slot:
            return None

        if provider is not None:
            slot.provider = provider
        if model is not None:
            slot.model = model
        if model_label is not None:
            slot.model_label = model_label
        if name is not None:
            slot.name = name
        if role is not None:
            try:
                slot.role = AgentRole(role)
            except ValueError:
                pass

        self._log_event("agent_config_updated", {
            "agent_id": agent_id,
            "provider": slot.provider,
            "model": slot.model,
        })
        return slot

    # ---------------------------------------------------------------
    # Agent control (pause / resume / start / stop)
    # ---------------------------------------------------------------

    def start_agent(self, agent_id: str, task: str = "") -> bool:
        """Start or restart an agent."""
        slot = self._slots.get(agent_id)
        if not slot:
            return False
        slot.start(task)
        tree = self._decision_trees.get(agent_id)
        if tree:
            tree.create_root(f"Task: {task[:80]}" if task else "Start")
        self._log_event("agent_started", {
            "agent_id": agent_id,
            "task": task,
        })
        return True

    def pause_agent(self, agent_id: str) -> bool:
        """Pause a running agent."""
        slot = self._slots.get(agent_id)
        if not slot:
            return False
        slot.pause()
        self._log_event("agent_paused", {"agent_id": agent_id})
        return True

    def resume_agent(self, agent_id: str) -> bool:
        """Resume a paused agent."""
        slot = self._slots.get(agent_id)
        if not slot:
            return False
        slot.resume()
        self._log_event("agent_resumed", {"agent_id": agent_id})
        return True

    def stop_agent(self, agent_id: str) -> bool:
        """Stop an agent (mark as completed)."""
        slot = self._slots.get(agent_id)
        if not slot:
            return False
        slot.complete()
        self._log_event("agent_stopped", {"agent_id": agent_id})
        return True

    # ---------------------------------------------------------------
    # Live state updates (called from agent processes)
    # ---------------------------------------------------------------

    def update_agent_thinking(self, agent_id: str, thinking: str):
        """Update agent's current thinking/reasoning."""
        slot = self._slots.get(agent_id)
        if not slot:
            return
        slot.current_thinking = thinking[:500]
        tree = self._decision_trees.get(agent_id)
        if tree:
            tree.add_thinking(thinking)

    def update_agent_tool_call(
        self,
        agent_id: str,
        tool_name: str,
        tool_input: str = "",
    ):
        """Record a tool call from the agent."""
        slot = self._slots.get(agent_id)
        if not slot:
            return
        slot.last_tool_call = tool_name
        slot.last_tool_input = tool_input[:300]
        tree = self._decision_trees.get(agent_id)
        if tree:
            tree.add_tool_call(tool_name, tool_input)

    def update_agent_file(self, agent_id: str, file_path: str):
        """Track file changes by the agent."""
        slot = self._slots.get(agent_id)
        if not slot:
            return
        if file_path not in slot.active_files:
            slot.active_files.append(file_path)
            # Keep last 20 files
            if len(slot.active_files) > 20:
                slot.active_files = slot.active_files[-20:]

    def update_agent_tokens(
        self,
        agent_id: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_usd: float = 0.0,
    ):
        """Update token consumption for an agent."""
        slot = self._slots.get(agent_id)
        if not slot:
            return
        slot.tokens.add(input_tokens, output_tokens, cost_usd)

    def update_agent_progress(
        self,
        agent_id: str,
        progress: float,
        current_step: str = "",
    ):
        """Update agent progress (0.0 to 1.0)."""
        slot = self._slots.get(agent_id)
        if not slot:
            return
        slot.progress = max(0.0, min(1.0, progress))
        if current_step:
            slot.current_step = current_step

    def update_agent_status(self, agent_id: str, status: str, error: str = ""):
        """Update agent status directly."""
        slot = self._slots.get(agent_id)
        if not slot:
            return
        try:
            slot.status = AgentStatus(status)
        except ValueError:
            return
        if error:
            slot.error_message = error

    # ---------------------------------------------------------------
    # Decision tree access
    # ---------------------------------------------------------------

    def get_decision_tree(self, agent_id: str) -> Optional[dict[str, Any]]:
        """Get the decision tree for a specific agent."""
        tree = self._decision_trees.get(agent_id)
        if not tree:
            return None
        return tree.to_dict()

    def get_decision_path(self, agent_id: str) -> list[dict[str, Any]]:
        """Get the flat decision path for a specific agent."""
        tree = self._decision_trees.get(agent_id)
        if not tree:
            return []
        return tree.get_flat_path()

    # ---------------------------------------------------------------
    # Full state snapshot
    # ---------------------------------------------------------------

    def get_full_state(self) -> dict[str, Any]:
        """Get the complete Mission Control state for the frontend."""
        return {
            "session": self.get_session_info(),
            "agents": self.get_all_agents(),
            "decision_trees": {
                aid: tree.to_dict()
                for aid, tree in self._decision_trees.items()
            },
            "recent_events": self._event_log[-50:],
        }

    # ---------------------------------------------------------------
    # Event logging
    # ---------------------------------------------------------------

    def _log_event(self, event_type: str, data: dict[str, Any]):
        """Log an internal event."""
        event = {
            "type": event_type,
            "timestamp": time.time(),
            "data": data,
        }
        self._event_log.append(event)
        # Keep last 200 events
        if len(self._event_log) > 200:
            self._event_log = self._event_log[-200:]

    def get_event_log(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent events."""
        return self._event_log[-limit:]


# ---------------------------------------------------------------------------
# Singleton access
# ---------------------------------------------------------------------------

_mission_control: Optional[MissionControlOrchestrator] = None


def get_mission_control() -> MissionControlOrchestrator:
    """Get or create the global Mission Control orchestrator."""
    global _mission_control
    if _mission_control is None:
        _mission_control = MissionControlOrchestrator()
    return _mission_control
