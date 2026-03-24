"""Diagram Generator - Converts ArchitectureDiagram objects to Mermaid syntax."""

import re

from .models import ArchitectureDiagram, DiagramType, EdgeType, NodeType


class DiagramGenerator:
    """Generates Mermaid diagram code from ArchitectureDiagram objects."""

    def generate_mermaid(self, diagram: ArchitectureDiagram) -> str:
        """Dispatch to the correct Mermaid generator based on diagram type."""
        generators = {
            DiagramType.MODULE_DEPENDENCIES: self._generate_module_deps_mermaid,
            DiagramType.COMPONENT_HIERARCHY: self._generate_component_hierarchy_mermaid,
            DiagramType.DATA_FLOW: self._generate_data_flow_mermaid,
            DiagramType.DATABASE_SCHEMA: self._generate_db_schema_mermaid,
        }
        gen = generators.get(diagram.diagram_type, self._generate_module_deps_mermaid)
        return gen(diagram)

    def _generate_module_deps_mermaid(self, diagram: ArchitectureDiagram) -> str:
        """Generate graph TD Mermaid for module dependencies."""
        lines = ["graph TD"]

        # Node type shapes
        node_shapes: dict[str, str] = {
            NodeType.MODULE.value: ("(", ")"),
            NodeType.PACKAGE.value: ("[", "]"),
            NodeType.SERVICE.value: ("[/", "/]"),
            NodeType.COMPONENT.value: ("([", "])"),
            NodeType.TABLE.value: ("[(", ")]"),
        }

        for node in diagram.nodes:
            nid = self.sanitize_node_id(node.id)
            label = node.name[:30]
            open_s, close_s = node_shapes.get(node.type.value, ("(", ")"))
            lines.append(f'    {nid}{open_s}"{label}"{close_s}')

        for edge in diagram.edges:
            src = self.sanitize_node_id(edge.source_id)
            tgt = self.sanitize_node_id(edge.target_id)
            arrow = "-->" if edge.edge_type != EdgeType.EXTENDS else "--|>"
            if edge.label:
                lines.append(f"    {src} {arrow}|{edge.label[:20]}| {tgt}")
            else:
                lines.append(f"    {src} {arrow} {tgt}")

        return "\n".join(lines)

    def _generate_component_hierarchy_mermaid(
        self, diagram: ArchitectureDiagram
    ) -> str:
        """Generate graph TD Mermaid for component hierarchy."""
        lines = ["graph TD"]
        for node in diagram.nodes:
            nid = self.sanitize_node_id(node.id)
            lines.append(f'    {nid}(["{node.name}"])')
        for edge in diagram.edges:
            src = self.sanitize_node_id(edge.source_id)
            tgt = self.sanitize_node_id(edge.target_id)
            lines.append(f"    {src} --> {tgt}")
        return "\n".join(lines)

    def _generate_data_flow_mermaid(self, diagram: ArchitectureDiagram) -> str:
        """Generate flowchart LR Mermaid for data flow."""
        lines = ["flowchart LR"]
        for node in diagram.nodes:
            nid = self.sanitize_node_id(node.id)
            shape = (
                "[/" + node.name[:25] + "/]"
                if "service" in node.type.value
                else f'["{node.name[:25]}"]'
            )
            lines.append(f"    {nid}{shape}")
        for edge in diagram.edges:
            src = self.sanitize_node_id(edge.source_id)
            tgt = self.sanitize_node_id(edge.target_id)
            label = edge.label[:20] if edge.label else ""
            if label:
                lines.append(f"    {src} -->|{label}| {tgt}")
            else:
                lines.append(f"    {src} --> {tgt}")
        return "\n".join(lines)

    def _generate_db_schema_mermaid(self, diagram: ArchitectureDiagram) -> str:
        """Generate erDiagram Mermaid for database schema."""
        if not diagram.nodes:
            return "erDiagram\n    %% No database models detected"
        lines = ["erDiagram"]
        # Add tables
        for node in diagram.nodes:
            lines.append(f"    {self.sanitize_node_id(node.name)} {{")
            lines.append("        string id PK")
            lines.append("    }")
        # Add relationships
        for edge in diagram.edges:
            src_name = ""
            tgt_name = ""
            for node in diagram.nodes:
                nid = f"table_{node.name.lower()}"
                if nid == edge.source_id:
                    src_name = self.sanitize_node_id(node.name)
                if nid == edge.target_id:
                    tgt_name = self.sanitize_node_id(node.name)
            if src_name and tgt_name:
                lines.append(f'    {src_name} ||--o{{ {tgt_name} : "has"')
        return "\n".join(lines)

    def sanitize_node_id(self, name: str) -> str:
        """Sanitize a name to be a valid Mermaid node ID."""
        result = re.sub(r"[^a-zA-Z0-9_]", "_", name)
        if result and result[0].isdigit():
            result = "n_" + result
        return result or "unknown"
