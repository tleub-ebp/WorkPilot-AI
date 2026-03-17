"""
Dependency Graph Intelligence
==============================

Builds and caches a structural dependency graph of the project.
Used by the context builder to deliver graph-aware file context to agents.
"""

from .analyzer import DependencyAnalyzer, GraphInsights
from .builder import DependencyGraphBuilder
from .cache import DependencyGraphCache
from .models import DependencyEdge, DependencyGraph, DependencyNode

__all__ = [
    "DependencyGraph",
    "DependencyNode",
    "DependencyEdge",
    "DependencyGraphBuilder",
    "DependencyAnalyzer",
    "GraphInsights",
    "DependencyGraphCache",
]
