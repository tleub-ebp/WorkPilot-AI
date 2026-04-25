"""Agent Health Monitor.

Scores each agent's reliability over a sliding window of executions
and proposes corrective actions (throttle, rotate, retrain, alert).

Different from `agent_coach/` (which produces narrative improvement tips
for the human) — this module produces a quantitative score and actionable
state for the orchestrator.
"""

from .monitor import (
    AgentHealthScore,
    AgentRun,
    HealthAction,
    HealthMonitor,
    HealthStatus,
)

__all__ = [
    "AgentHealthScore",
    "AgentRun",
    "HealthAction",
    "HealthMonitor",
    "HealthStatus",
]
