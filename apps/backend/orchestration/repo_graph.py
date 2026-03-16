"""
Repository Dependency Graph
============================
Builds and analyzes dependency relationships between repositories.
Provides topological sorting for execution ordering and cycle detection.
"""

from __future__ import annotations

import json
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class DependencyType(str, Enum):
    """Type of dependency between repositories."""

    PACKAGE = "package"  # npm/pip/cargo package dependency
    API = "api"  # HTTP/gRPC API consumer
    SHARED_TYPES = "shared_types"  # Shared type definitions / proto files
    DATABASE = "database"  # Shared database schema
    EVENT = "event"  # Event/message bus (Kafka, RabbitMQ, etc.)
    MONOREPO_INTERNAL = "monorepo_internal"  # Internal monorepo workspace dep


@dataclass
class RepoDependency:
    """A directed dependency edge: source_repo depends on target_repo."""

    source_repo: str  # The repo that depends on another
    target_repo: str  # The repo being depended upon
    dependency_type: DependencyType
    details: str = ""  # e.g., package name, API endpoint, proto file

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_repo": self.source_repo,
            "target_repo": self.target_repo,
            "dependency_type": self.dependency_type.value,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RepoDependency:
        return cls(
            source_repo=data["source_repo"],
            target_repo=data["target_repo"],
            dependency_type=DependencyType(data["dependency_type"]),
            details=data.get("details", ""),
        )


@dataclass
class RepoDependencyGraph:
    """
    Directed acyclic graph of repository dependencies.

    Edges point from consumer → provider (source depends on target).
    Topological sort returns providers first, consumers last.
    """

    repos: list[str] = field(default_factory=list)
    dependencies: list[RepoDependency] = field(default_factory=list)

    def add_repo(self, repo: str) -> None:
        """Add a repository node to the graph."""
        if repo not in self.repos:
            self.repos.append(repo)

    def add_dependency(self, dep: RepoDependency) -> None:
        """Add a dependency edge to the graph."""
        self.add_repo(dep.source_repo)
        self.add_repo(dep.target_repo)
        self.dependencies.append(dep)

    def topological_sort(self) -> list[str]:
        """
        Return repos in dependency order (providers first, consumers last).

        Uses Kahn's algorithm. Raises ValueError if circular dependencies exist.
        """
        # Build adjacency list and in-degree count
        # Edge: source -> target means source depends on target
        # For execution order, target (provider) must come before source (consumer)
        in_degree: dict[str, int] = {repo: 0 for repo in self.repos}
        # Reverse edges: target provides to source, so source must wait for target
        adj: dict[str, list[str]] = defaultdict(list)

        for dep in self.dependencies:
            # target_repo must be processed before source_repo
            adj[dep.target_repo].append(dep.source_repo)
            in_degree[dep.source_repo] = in_degree.get(dep.source_repo, 0) + 1

        # Start with nodes that have no dependencies (in_degree == 0)
        queue = deque(
            repo for repo in self.repos if in_degree.get(repo, 0) == 0
        )
        result: list[str] = []

        while queue:
            repo = queue.popleft()
            result.append(repo)
            for dependent in adj.get(repo, []):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(result) != len(self.repos):
            # Find the cycle for error reporting
            remaining = set(self.repos) - set(result)
            raise ValueError(
                f"Circular dependency detected between repositories: "
                f"{', '.join(sorted(remaining))}"
            )

        return result

    def get_downstream_repos(self, repo: str) -> list[str]:
        """Get repos that depend on the given repo (consumers)."""
        return [
            dep.source_repo
            for dep in self.dependencies
            if dep.target_repo == repo
        ]

    def get_upstream_repos(self, repo: str) -> list[str]:
        """Get repos that the given repo depends on (providers)."""
        return [
            dep.target_repo
            for dep in self.dependencies
            if dep.source_repo == repo
        ]

    def get_dependencies_for_repo(self, repo: str) -> list[RepoDependency]:
        """Get all dependency edges involving a repo (as source or target)."""
        return [
            dep
            for dep in self.dependencies
            if dep.source_repo == repo or dep.target_repo == repo
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "repos": self.repos,
            "dependencies": [dep.to_dict() for dep in self.dependencies],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RepoDependencyGraph:
        graph = cls(repos=data.get("repos", []))
        for dep_data in data.get("dependencies", []):
            graph.dependencies.append(RepoDependency.from_dict(dep_data))
        return graph

    def save(self, path: Path) -> None:
        """Save graph to JSON file."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> RepoDependencyGraph:
        """Load graph from JSON file."""
        with open(path, encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    @classmethod
    def from_analysis(
        cls,
        repo_analyses: dict[str, dict[str, Any]],
    ) -> RepoDependencyGraph:
        """
        Build dependency graph from ProjectAnalyzer results for multiple repos.

        Args:
            repo_analyses: Dict mapping repo name to analysis result dict.
                Each analysis may contain:
                - "dependencies": list of package dependencies
                - "services": list of detected microservices
                - "package_json" / "requirements": dependency manifests

        Returns:
            A RepoDependencyGraph with detected cross-repo dependencies.
        """
        graph = cls()
        repo_names = list(repo_analyses.keys())

        for repo_name in repo_names:
            graph.add_repo(repo_name)

        # Build a map of package names to their providing repo
        package_to_repo: dict[str, str] = {}
        for repo_name, analysis in repo_analyses.items():
            # Check for published packages
            for pkg_name in analysis.get("published_packages", []):
                package_to_repo[pkg_name] = repo_name

            # Use repo name itself as a potential package
            short_name = repo_name.split("/")[-1] if "/" in repo_name else repo_name
            package_to_repo[short_name] = repo_name

        # Detect cross-repo package dependencies
        for repo_name, analysis in repo_analyses.items():
            for dep_name in analysis.get("dependencies", []):
                if dep_name in package_to_repo:
                    provider_repo = package_to_repo[dep_name]
                    if provider_repo != repo_name:
                        graph.add_dependency(
                            RepoDependency(
                                source_repo=repo_name,
                                target_repo=provider_repo,
                                dependency_type=DependencyType.PACKAGE,
                                details=dep_name,
                            )
                        )

            # Detect API dependencies from service analysis
            for service in analysis.get("services", []):
                for consumed_api in service.get("consumes", []):
                    for other_repo in repo_names:
                        if other_repo == repo_name:
                            continue
                        other_services = repo_analyses[other_repo].get(
                            "services", []
                        )
                        for other_svc in other_services:
                            if consumed_api in other_svc.get("provides", []):
                                graph.add_dependency(
                                    RepoDependency(
                                        source_repo=repo_name,
                                        target_repo=other_repo,
                                        dependency_type=DependencyType.API,
                                        details=consumed_api,
                                    )
                                )

        return graph
