"""
Multi-Repo Orchestration Module
================================
Coordinates spec execution across multiple repositories simultaneously.

A single task can target multiple repos (microservices, frontend + backend, shared libs).
The orchestrator coordinates modifications, manages inter-repo dependencies,
detects breaking changes, and creates linked PRs.
"""

from .repo_graph import RepoDependencyGraph, RepoDependency, DependencyType
from .cross_repo_spec import CrossRepoSpecManager, MultiRepoManifest, RepoSubSpec
from .breaking_changes import BreakingChangeDetector, BreakingChange
from .orchestrator import MultiRepoOrchestrator

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
