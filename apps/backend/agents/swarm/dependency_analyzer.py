"""
Dependency Analyzer
===================

Builds a directed acyclic graph (DAG) from the implementation plan's subtasks
and schedules them into execution waves based on their dependencies.

Dependency signals:
1. Explicit `depends_on` / `after` fields in subtasks
2. File overlap: two subtasks modifying the same file -> sequential
3. Phase ordering: subtasks in later phases depend on earlier phases
4. Creation-before-modification: if subtask A creates a file that B modifies -> A before B
"""

from __future__ import annotations

import logging
from collections import defaultdict, deque

from .types import SubtaskNode, Wave

logger = logging.getLogger(__name__)


class DependencyAnalyzer:
    """
    Analyzes an implementation plan and builds a wave execution schedule.

    Given subtasks with their metadata (files_to_modify, files_to_create,
    explicit dependencies), produces an ordered list of Waves where each
    wave contains subtasks that can execute in parallel.
    """

    def __init__(self, max_parallel: int = 4) -> None:
        self.max_parallel = max_parallel
        self._nodes: dict[str, SubtaskNode] = {}
        self._adjacency: dict[str, set[str]] = defaultdict(set)  # node -> depends_on
        self._reverse_adj: dict[str, set[str]] = defaultdict(set)  # node -> depended_by

    def analyze(self, plan: dict) -> tuple[list[Wave], dict[str, SubtaskNode]]:
        """
        Analyze an implementation plan and return waves + node map.

        Args:
            plan: The implementation_plan.json dict with phases[].subtasks[]

        Returns:
            (waves, nodes) where waves are ordered execution groups
            and nodes is the full subtask graph keyed by id.
        """
        self._nodes.clear()
        self._adjacency.clear()
        self._reverse_adj.clear()

        self._extract_nodes(plan)
        self._build_explicit_edges()
        self._build_file_overlap_edges()
        self._build_creation_edges()
        self._build_phase_ordering_edges(plan)

        waves = self._topological_wave_sort()

        logger.info(
            "Dependency analysis complete: %d subtasks -> %d waves (max parallelism: %d)",
            len(self._nodes),
            len(waves),
            max((len(w.subtask_ids) for w in waves), default=0),
        )

        return waves, dict(self._nodes)

    def _extract_nodes(self, plan: dict) -> None:
        """Extract SubtaskNode objects from the plan."""
        for phase in plan.get("phases", []):
            phase_name = phase.get("name", "unknown")
            for subtask in phase.get("subtasks", []):
                subtask_id = subtask.get("id", "")
                if not subtask_id:
                    continue

                # Skip already completed subtasks
                if subtask.get("status") == "completed":
                    continue

                node = SubtaskNode(
                    id=subtask_id,
                    phase_name=phase_name,
                    description=subtask.get("description", ""),
                    files_to_modify=subtask.get("files_to_modify", []),
                    files_to_create=subtask.get("files_to_create", []),
                    depends_on=subtask.get("depends_on", []),
                )
                self._nodes[subtask_id] = node

    def _build_explicit_edges(self) -> None:
        """Add edges from explicit depends_on/after fields."""
        for node_id, node in self._nodes.items():
            for dep_id in node.depends_on:
                if dep_id in self._nodes:
                    self._add_edge(dep_id, node_id)

    def _build_file_overlap_edges(self) -> None:
        """
        Detect subtasks that modify the same file and serialize them.

        When two subtasks both modify the same file, the one appearing earlier
        in the plan runs first. This avoids merge conflicts within a wave.
        """
        file_to_subtasks: dict[str, list[str]] = defaultdict(list)

        # Group subtasks by files they modify (not create — new files don't conflict)
        ordered_ids = list(self._nodes.keys())
        for node_id in ordered_ids:
            node = self._nodes[node_id]
            for f in node.files_to_modify:
                file_to_subtasks[f].append(node_id)

        # For each file modified by multiple subtasks, chain them sequentially
        for _file_path, subtask_ids in file_to_subtasks.items():
            if len(subtask_ids) <= 1:
                continue
            for i in range(len(subtask_ids) - 1):
                self._add_edge(subtask_ids[i], subtask_ids[i + 1])

    def _build_creation_edges(self) -> None:
        """If subtask A creates a file that subtask B modifies, A must run first."""
        created_by: dict[str, str] = {}
        for node_id, node in self._nodes.items():
            for f in node.files_to_create:
                created_by[f] = node_id

        for node_id, node in self._nodes.items():
            for f in node.files_to_modify:
                creator = created_by.get(f)
                if creator and creator != node_id:
                    self._add_edge(creator, node_id)

    def _build_phase_ordering_edges(self, plan: dict) -> None:
        """
        Ensure subtasks in later phases depend on all subtasks from earlier phases.

        This is a soft constraint: only applied between subtasks that don't already
        have explicit dependency paths, to avoid over-serialization.
        """
        phase_subtask_ids: list[list[str]] = []
        for phase in plan.get("phases", []):
            ids = []
            for subtask in phase.get("subtasks", []):
                sid = subtask.get("id", "")
                if sid in self._nodes:
                    ids.append(sid)
            if ids:
                phase_subtask_ids.append(ids)

        # For each pair of consecutive phases, add edges from last phase's tasks
        # to next phase's tasks (only if no existing path connects them)
        for i in range(len(phase_subtask_ids) - 1):
            prev_ids = phase_subtask_ids[i]
            next_ids = phase_subtask_ids[i + 1]
            for next_id in next_ids:
                # Check if next_id already depends on ANY node in prev phase
                existing_deps = self._get_all_ancestors(next_id)
                has_existing_dep = any(pid in existing_deps for pid in prev_ids)
                if not has_existing_dep:
                    # Add dependency on the first node of previous phase
                    # (lightweight: doesn't create N*M edges)
                    self._add_edge(prev_ids[0], next_id)

    def _add_edge(self, from_id: str, to_id: str) -> None:
        """Add a directed edge: to_id depends on from_id."""
        if from_id == to_id:
            return
        self._adjacency[to_id].add(from_id)
        self._reverse_adj[from_id].add(to_id)

    def _get_all_ancestors(self, node_id: str) -> set[str]:
        """Get all transitive dependencies of a node (BFS)."""
        visited: set[str] = set()
        queue = deque(self._adjacency.get(node_id, set()))
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            queue.extend(self._adjacency.get(current, set()) - visited)
        return visited

    def _topological_wave_sort(self) -> list[Wave]:
        """
        Kahn's algorithm variant that groups nodes by depth level into waves.

        Nodes with no unresolved dependencies go into the current wave.
        After a wave is "executed", its nodes are resolved and the next
        wave is computed. Respects max_parallel by splitting large waves.
        """
        in_degree: dict[str, int] = dict.fromkeys(self._nodes, 0)
        for node_id in self._nodes:
            in_degree[node_id] = len(self._adjacency.get(node_id, set()))

        waves: list[Wave] = []
        resolved: set[str] = set()

        while True:
            # Find all nodes with no unresolved dependencies
            ready = [
                nid
                for nid, deg in in_degree.items()
                if deg == 0 and nid not in resolved
            ]

            if not ready:
                # Check for cycles
                unresolved = set(self._nodes.keys()) - resolved
                if unresolved:
                    logger.warning(
                        "Dependency cycle detected among: %s — falling back to sequential",
                        ", ".join(sorted(unresolved)),
                    )
                    # Break cycle by adding remaining as individual waves
                    for nid in sorted(unresolved):
                        wave = Wave(
                            index=len(waves),
                            subtask_ids=[nid],
                        )
                        self._nodes[nid].wave_index = wave.index
                        waves.append(wave)
                        resolved.add(nid)
                break

            # Split ready list into chunks of max_parallel
            for chunk_start in range(0, len(ready), self.max_parallel):
                chunk = ready[chunk_start : chunk_start + self.max_parallel]
                wave = Wave(
                    index=len(waves),
                    subtask_ids=chunk,
                )
                for nid in chunk:
                    self._nodes[nid].wave_index = wave.index
                waves.append(wave)

            # Mark all ready nodes as resolved and decrement dependents
            for nid in ready:
                resolved.add(nid)
                for dependent in self._reverse_adj.get(nid, set()):
                    in_degree[dependent] = max(0, in_degree[dependent] - 1)

        return waves

    def get_parallelism_stats(self, waves: list[Wave]) -> dict:
        """Get statistics about the parallelism achieved."""
        if not waves:
            return {"total_waves": 0, "max_parallelism": 0, "avg_parallelism": 0.0}

        sizes = [len(w.subtask_ids) for w in waves]
        return {
            "total_waves": len(waves),
            "max_parallelism": max(sizes),
            "avg_parallelism": sum(sizes) / len(sizes),
            "wave_sizes": sizes,
            "total_subtasks": sum(sizes),
            "speedup_estimate": sum(sizes) / len(waves) if waves else 1.0,
        }
