"""
Personal Agent Coach — Track agent performance and suggest improvements.

Monitors agent behaviour across runs, identifies patterns, and surfaces
personalised tips for prompt engineering, cost, and workflow efficiency.
"""

from .coach_engine import (
    AgentRunRecord,
    CoachEngine,
    CoachReport,
    CoachTip,
    TipCategory,
    TipPriority,
)

__all__ = [
    "CoachEngine",
    "CoachReport",
    "CoachTip",
    "AgentRunRecord",
    "TipCategory",
    "TipPriority",
]
