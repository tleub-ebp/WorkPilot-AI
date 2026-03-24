"""Data models for the Architecture Visualizer."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class DiagramType(Enum):
    MODULE_DEPENDENCIES = "module_dependencies"
    DATA_FLOW = "data_flow"
    COMPONENT_HIERARCHY = "component_hierarchy"
    DATABASE_SCHEMA = "database_schema"


class NodeType(Enum):
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    COMPONENT = "component"
    TABLE = "table"
    SERVICE = "service"
    PACKAGE = "package"


class EdgeType(Enum):
    IMPORT = "import"
    CALL = "call"
    EXTENDS = "extends"
    IMPLEMENTS = "implements"
    USES = "uses"
    FOREIGN_KEY = "foreign_key"
    RENDERS = "renders"
    EMITS = "emits"


@dataclass
class ModuleNode:
    id: str
    name: str
    path: str
    type: NodeType = NodeType.MODULE
    language: str = "unknown"
    size_lines: int = 0
    description: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class DependencyEdge:
    source_id: str
    target_id: str
    edge_type: EdgeType = EdgeType.IMPORT
    label: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class ArchitectureDiagram:
    diagram_type: DiagramType
    title: str
    nodes: list[ModuleNode] = field(default_factory=list)
    edges: list[DependencyEdge] = field(default_factory=list)
    mermaid_code: str = ""
    metadata: dict = field(default_factory=dict)
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "diagram_type": self.diagram_type.value,
            "title": self.title,
            "nodes": [
                {
                    "id": n.id,
                    "name": n.name,
                    "path": n.path,
                    "type": n.type.value,
                    "language": n.language,
                    "size_lines": n.size_lines,
                    "description": n.description,
                }
                for n in self.nodes
            ],
            "edges": [
                {
                    "source_id": e.source_id,
                    "target_id": e.target_id,
                    "edge_type": e.edge_type.value,
                    "label": e.label,
                }
                for e in self.edges
            ],
            "mermaid_code": self.mermaid_code,
            "metadata": self.metadata,
            "generated_at": self.generated_at,
        }
