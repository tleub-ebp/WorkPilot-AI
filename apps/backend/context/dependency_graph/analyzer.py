"""
Dependency Graph Analyzer
==========================

Analyzes a dependency graph to detect:
- Circular dependencies (import cycles)
- Orphan modules (unreachable, never imported)
- High-coupling hotspots (files with excessive fan-in or fan-out)
- Direct neighbors of a set of files (for context enrichment)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .models import DependencyGraph


@dataclass
class CircularDependency:
    """A detected import cycle."""
    cycle: list[str]   # Ordered list of files forming the cycle

    def __str__(self) -> str:
        return " → ".join(self.cycle) + f" → {self.cycle[0]}"


@dataclass
class GraphInsights:
    """Summary of dependency graph analysis results."""

    circular_dependencies: list[CircularDependency] = field(default_factory=list)
    orphan_modules: list[str] = field(default_factory=list)
    high_coupling_files: list[dict] = field(default_factory=list)  # {path, fan_in, fan_out}
    total_nodes: int = 0
    total_edges: int = 0

    def to_dict(self) -> dict:
        return {
            "total_nodes": self.total_nodes,
            "total_edges": self.total_edges,
            "circular_dependencies": [c.cycle for c in self.circular_dependencies],
            "orphan_modules": self.orphan_modules,
            "high_coupling_files": self.high_coupling_files,
        }


class DependencyAnalyzer:
    """
    Analyzes a DependencyGraph to surface structural insights.
    """

    # Files with more incoming/outgoing edges than these thresholds are flagged
    HIGH_FAN_IN_THRESHOLD = 15
    HIGH_FAN_OUT_THRESHOLD = 20
    MAX_CYCLES_REPORTED = 10   # Limit cycle reporting for large codebases

    def __init__(self, graph: DependencyGraph):
        self.graph = graph

    # ── Public API ─────────────────────────────────────────────────────────

    def analyze(self) -> GraphInsights:
        """Run all analyses and return consolidated insights."""
        insights = GraphInsights(
            total_nodes=len(self.graph.nodes),
            total_edges=sum(len(n.imports) for n in self.graph.nodes.values()),
        )
        insights.circular_dependencies = self.detect_cycles()
        insights.orphan_modules = self.detect_orphans()
        insights.high_coupling_files = self.detect_high_coupling()
        return insights

    def get_related_files(
        self,
        file_paths: list[str],
        depth: int = 2,
        max_files: int = 15,
    ) -> list[str]:
        """
        Given a set of files being worked on, return the most relevant
        related files (dependencies + dependents), ranked by proximity.

        Args:
            file_paths: Files the agent will work on
            depth: How many hops to traverse (1 = direct, 2 = transitive)
            max_files: Maximum related files to return

        Returns:
            Ranked list of related file paths (not including input files)
        """
        input_set = set(file_paths)
        scored: dict[str, int] = {}

        for fp in file_paths:
            # Direct dependencies (what this file needs)
            for dep in self.graph.get_dependencies(fp, depth=depth):
                if dep not in input_set:
                    scored[dep] = scored.get(dep, 0) + (2 if dep in self.graph.get_dependencies(fp, depth=1) else 1)

            # Dependents (who will be affected by changes)
            for dep in self.graph.get_dependents(fp, depth=depth):
                if dep not in input_set:
                    scored[dep] = scored.get(dep, 0) + (3 if dep in self.graph.get_dependents(fp, depth=1) else 1)

        # Sort by score descending, return top N
        ranked = sorted(scored.keys(), key=lambda p: scored[p], reverse=True)
        return ranked[:max_files]

    # ── Cycle Detection (DFS-based) ────────────────────────────────────────

    def detect_cycles(self) -> list[CircularDependency]:
        """Detect all import cycles using DFS with path tracking."""
        visited: set[str] = set()
        in_stack: list[str] = []
        in_stack_set: set[str] = set()
        cycles: list[CircularDependency] = []

        def dfs(node_path: str) -> None:
            if len(cycles) >= self.MAX_CYCLES_REPORTED:
                return
            visited.add(node_path)
            in_stack.append(node_path)
            in_stack_set.add(node_path)

            node = self.graph.nodes.get(node_path)
            if node:
                for dep in node.imports:
                    if dep not in self.graph.nodes:
                        continue
                    if dep not in visited:
                        dfs(dep)
                    elif dep in in_stack_set:
                        # Found a cycle — extract the cycle path
                        idx = in_stack.index(dep)
                        cycle_path = in_stack[idx:]
                        cycles.append(CircularDependency(cycle=list(cycle_path)))

            in_stack.pop()
            in_stack_set.discard(node_path)

        for path in self.graph.nodes:
            if path not in visited:
                dfs(path)

        return cycles

    # ── Orphan Detection ───────────────────────────────────────────────────

    def detect_orphans(self) -> list[str]:
        """
        Find modules that are never imported by any other module.
        Excludes likely entry-points (main.py, index.ts, __init__.py, etc.).
        """
        entry_point_patterns = {
            "main.py", "app.py", "run.py", "server.py", "manage.py",
            "index.ts", "index.tsx", "index.js", "index.jsx",
            "__init__.py", "vite.config.ts", "webpack.config.js",
            "jest.config.ts", "vitest.config.ts",
        }

        orphans = []
        for path, node in self.graph.nodes.items():
            filename = path.rsplit("/", 1)[-1]
            if filename in entry_point_patterns:
                continue
            if not node.imported_by and node.imports:  # Has deps but nobody imports it
                orphans.append(path)

        return sorted(orphans)

    # ── High Coupling Detection ────────────────────────────────────────────

    def detect_high_coupling(self) -> list[dict]:
        """
        Find files with high fan-in (many importers) or high fan-out (many imports).
        These are architectural hotspots that deserve extra attention.
        """
        results = []
        for path, node in self.graph.nodes.items():
            fan_in = node.in_degree
            fan_out = node.out_degree
            if fan_in >= self.HIGH_FAN_IN_THRESHOLD or fan_out >= self.HIGH_FAN_OUT_THRESHOLD:
                results.append({
                    "path": path,
                    "fan_in": fan_in,
                    "fan_out": fan_out,
                    "coupling_type": self._coupling_type(fan_in, fan_out),
                })

        return sorted(results, key=lambda x: x["fan_in"] + x["fan_out"], reverse=True)

    @staticmethod
    def _coupling_type(fan_in: int, fan_out: int) -> str:
        if fan_in >= 15 and fan_out >= 20:
            return "god_module"
        if fan_in >= 15:
            return "high_fan_in"
        return "high_fan_out"
