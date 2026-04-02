"""
Swarm Mode — Multi-Agent Parallel Execution
============================================

Orchestrates parallel execution of independent subtasks using
wave-based scheduling with dependency analysis and semantic merge.
"""

from .dependency_analyzer import DependencyAnalyzer
from .orchestrator import SwarmOrchestrator
from .types import SubtaskNode, SwarmConfig, SwarmStatus, Wave
from .wave_executor import WaveExecutor

__all__ = [
    "DependencyAnalyzer",
    "SwarmOrchestrator",
    "SwarmConfig",
    "SwarmStatus",
    "SubtaskNode",
    "Wave",
    "WaveExecutor",
]
