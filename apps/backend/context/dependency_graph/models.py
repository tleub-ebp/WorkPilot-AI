"""
Dependency Graph Data Models
=============================
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DependencyNode:
    """A file/module node in the dependency graph."""

    path: str  # Relative path from project root
    language: str = "unknown"  # python | typescript | javascript | unknown
    imports: list[str] = field(default_factory=list)  # Paths this file imports
    imported_by: list[str] = field(default_factory=list)  # Paths that import this file
    export_symbols: list[str] = field(default_factory=list)  # Top-level exports

    @property
    def in_degree(self) -> int:
        """Number of files that import this node."""
        return len(self.imported_by)

    @property
    def out_degree(self) -> int:
        """Number of files this node imports."""
        return len(self.imports)

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "language": self.language,
            "imports": self.imports,
            "imported_by": self.imported_by,
            "export_symbols": self.export_symbols,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DependencyNode:
        return cls(
            path=data["path"],
            language=data.get("language", "unknown"),
            imports=data.get("imports", []),
            imported_by=data.get("imported_by", []),
            export_symbols=data.get("export_symbols", []),
        )


@dataclass
class DependencyEdge:
    """A directed dependency edge from source → target."""

    source: str  # Relative path of the importing file
    target: str  # Relative path of the imported file
    symbol: str | None = None  # Imported symbol (if known)


@dataclass
class DependencyGraph:
    """
    Full dependency graph for a project.

    Nodes are keyed by relative file path.
    """

    nodes: dict[str, DependencyNode] = field(default_factory=dict)
    file_count: int = 0
    build_timestamp: str = ""

    def add_node(self, node: DependencyNode) -> None:
        self.nodes[node.path] = node

    def get_node(self, path: str) -> DependencyNode | None:
        return self.nodes.get(path)

    def get_dependents(self, path: str, depth: int = 1) -> list[str]:
        """
        Get files that depend on `path` up to the given depth.
        (files that import `path`, transitively)
        """
        visited: set[str] = set()
        frontier = {path}
        for _ in range(depth):
            next_frontier: set[str] = set()
            for p in frontier:
                node = self.nodes.get(p)
                if node:
                    for importer in node.imported_by:
                        if importer not in visited and importer != path:
                            next_frontier.add(importer)
            visited.update(next_frontier)
            frontier = next_frontier
        return [p for p in visited if p != path]

    def get_dependencies(self, path: str, depth: int = 1) -> list[str]:
        """
        Get files that `path` depends on up to the given depth.
        (files that `path` imports, transitively)
        """
        visited: set[str] = set()
        frontier = {path}
        for _ in range(depth):
            next_frontier: set[str] = set()
            for p in frontier:
                node = self.nodes.get(p)
                if node:
                    for dep in node.imports:
                        if dep not in visited and dep != path:
                            next_frontier.add(dep)
            visited.update(next_frontier)
            frontier = next_frontier
        return [p for p in visited if p != path]

    def to_dict(self) -> dict:
        return {
            "file_count": self.file_count,
            "build_timestamp": self.build_timestamp,
            "nodes": {path: node.to_dict() for path, node in self.nodes.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> DependencyGraph:
        graph = cls(
            file_count=data.get("file_count", 0),
            build_timestamp=data.get("build_timestamp", ""),
        )
        for path, node_data in data.get("nodes", {}).items():
            node_data["path"] = path
            graph.nodes[path] = DependencyNode.from_dict(node_data)
        return graph
