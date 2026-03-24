"""
Multi-Repo Orchestration Module
================================
Coordinates spec execution across multiple repositories simultaneously.

A single task can target multiple repos (microservices, frontend + backend, shared libs).
The orchestrator coordinates modifications, manages inter-repo dependencies,
detects breaking changes, and creates linked PRs.
"""

from .breaking_changes import BreakingChange, BreakingChangeDetector
from .cross_repo_spec import CrossRepoSpecManager, MultiRepoManifest, RepoSubSpec
from .orchestrator import MultiRepoOrchestrator
from .repo_graph import DependencyType, RepoDependency, RepoDependencyGraph

__all__ = [
    "MultiRepoOrchestrator",
    "RepoDependencyGraph",
    "RepoDependency",
    "DependencyType",
    "CrossRepoSpecManager",
    "MultiRepoManifest",
    "RepoSubSpec",
    "BreakingChangeDetector",
    "BreakingChange",
]
