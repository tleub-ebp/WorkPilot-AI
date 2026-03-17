"""Architecture Analyzer - Scans codebase and extracts architectural structure."""
import ast
import hashlib
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

from .models import (
    ArchitectureDiagram,
    DependencyEdge,
    DiagramType,
    EdgeType,
    ModuleNode,
    NodeType,
)

IGNORE_PATTERNS = {
    "node_modules", ".git", "__pycache__", "dist", "build",
    ".venv", "venv", ".next", "out", "coverage", ".cache",
}

PYTHON_EXTENSIONS = {".py"}
JS_EXTENSIONS = {".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"}
ALL_EXTENSIONS = PYTHON_EXTENSIONS | JS_EXTENSIONS


class ArchitectureAnalyzer:
    """Analyzes a project codebase to extract its architecture."""

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)

    def analyze_all(self) -> Dict[str, ArchitectureDiagram]:
        """Run all analyses and return diagrams by type name."""
        results = {}
        analyses = [
            ("module_dependencies", self.analyze_module_dependencies),
            ("component_hierarchy", self.analyze_component_hierarchy),
            ("data_flow", self.analyze_data_flow),
            ("database_schema", self.analyze_database_schema),
        ]
        for name, method in analyses:
            try:
                results[name] = method()
            except Exception as e:
                print(f"[ArchViz] Warning: {name} analysis failed: {e}")
        return results

    def analyze_module_dependencies(self) -> ArchitectureDiagram:
        """Build module dependency graph from imports."""
        nodes: Dict[str, ModuleNode] = {}
        edges: List[DependencyEdge] = []
        seen_edges: Set[Tuple[str, str]] = set()

        source_files = self._get_source_files(list(ALL_EXTENSIONS))

        for file_path in source_files:
            rel_path = str(file_path.relative_to(self.project_dir))
            node_id = self._path_to_id(rel_path)
            lang = "python" if file_path.suffix == ".py" else "javascript"

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                lines = content.count("\n") + 1
            except Exception:
                lines = 0

            # Determine top-level package
            parts = Path(rel_path).parts
            top_package = parts[0] if len(parts) > 1 else rel_path

            if node_id not in nodes:
                nodes[node_id] = ModuleNode(
                    id=node_id,
                    name=file_path.stem,
                    path=rel_path,
                    type=NodeType.MODULE,
                    language=lang,
                    size_lines=lines,
                    description=f"{top_package} module",
                )

            # Extract imports
            if file_path.suffix == ".py":
                imports = self._extract_python_imports(file_path)
            else:
                imports = self._extract_js_imports(file_path)

            for imp in imports:
                target_id = self._import_to_id(imp, file_path)
                if target_id and target_id != node_id:
                    edge_key = (node_id, target_id)
                    if edge_key not in seen_edges:
                        seen_edges.add(edge_key)
                        edges.append(DependencyEdge(
                            source_id=node_id,
                            target_id=target_id,
                            edge_type=EdgeType.IMPORT,
                            label=imp[:40],
                        ))

        # Only keep nodes that have at least one edge
        connected_ids = {e.source_id for e in edges} | {e.target_id for e in edges}
        filtered_nodes = {k: v for k, v in nodes.items() if k in connected_ids}

        # Limit to top 50 most connected nodes
        if len(filtered_nodes) > 50:
            counts: Dict[str, int] = {}
            for e in edges:
                counts[e.source_id] = counts.get(e.source_id, 0) + 1
                counts[e.target_id] = counts.get(e.target_id, 0) + 1
            top_ids = set(sorted(counts.keys(), key=lambda x: counts[x], reverse=True)[:50])
            filtered_nodes = {k: v for k, v in filtered_nodes.items() if k in top_ids}
            edges = [e for e in edges if e.source_id in top_ids and e.target_id in top_ids]

        from .diagram_generator import DiagramGenerator
        diagram = ArchitectureDiagram(
            diagram_type=DiagramType.MODULE_DEPENDENCIES,
            title="Module Dependencies",
            nodes=list(filtered_nodes.values()),
            edges=edges,
            metadata={"total_files": len(source_files)},
        )
        gen = DiagramGenerator()
        diagram.mermaid_code = gen.generate_mermaid(diagram)
        return diagram

    def analyze_component_hierarchy(self) -> ArchitectureDiagram:
        """Build React component hierarchy."""
        nodes: Dict[str, ModuleNode] = {}
        edges: List[DependencyEdge] = []

        react_files = self._get_source_files([".tsx", ".jsx"])
        component_pattern = re.compile(
            r"(?:export\s+(?:default\s+)?(?:function|class)\s+([A-Z][A-Za-z0-9]*)|"
            r"const\s+([A-Z][A-Za-z0-9]*)\s*=\s*(?:React\.memo\(|forwardRef\()?(?:\([^)]*\)\s*(?:=>|:)|function))",
        )
        import_pattern = re.compile(r"import\s+\{([^}]+)\}|import\s+(\w+)\s+from")

        for file_path in react_files:
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            rel_path = str(file_path.relative_to(self.project_dir))

            # Find components defined in this file
            components = []
            for m in component_pattern.finditer(content):
                name = m.group(1) or m.group(2)
                if name and name[0].isupper():
                    components.append(name)

            for comp in components:
                node_id = f"comp_{comp}"
                if node_id not in nodes:
                    nodes[node_id] = ModuleNode(
                        id=node_id,
                        name=comp,
                        path=rel_path,
                        type=NodeType.COMPONENT,
                        language="typescript",
                        description=f"React component in {Path(rel_path).name}",
                    )

            # Find imported components
            for m in import_pattern.finditer(content):
                group = m.group(1) or m.group(2) or ""
                imported_names = [n.strip().split(" as ")[0] for n in group.split(",")]
                for imported in imported_names:
                    imported = imported.strip()
                    if imported and imported[0].isupper():
                        target_id = f"comp_{imported}"
                        for src_comp in components:
                            src_id = f"comp_{src_comp}"
                            if src_id != target_id:
                                edges.append(DependencyEdge(
                                    source_id=src_id,
                                    target_id=target_id,
                                    edge_type=EdgeType.RENDERS,
                                    label="renders",
                                ))

        from .diagram_generator import DiagramGenerator
        diagram = ArchitectureDiagram(
            diagram_type=DiagramType.COMPONENT_HIERARCHY,
            title="Component Hierarchy",
            nodes=list(nodes.values())[:60],
            edges=edges[:100],
            metadata={"react_files": len(react_files)},
        )
        gen = DiagramGenerator()
        diagram.mermaid_code = gen.generate_mermaid(diagram)
        return diagram

    def analyze_data_flow(self) -> ArchitectureDiagram:
        """Identify services/agents and their data flow."""
        nodes: Dict[str, ModuleNode] = {}
        edges: List[DependencyEdge] = []

        # Look for service-like patterns in the project
        patterns = {
            "agent": re.compile(r"(?i)(agent|runner|orchestrat)", re.I),
            "service": re.compile(r"(?i)(service|handler|manager|client)", re.I),
            "store": re.compile(r"(?i)(store|state|context)", re.I),
            "api": re.compile(r"(?i)(api|endpoint|route|controller)", re.I),
        }

        source_files = self._get_source_files(list(ALL_EXTENSIONS))
        for file_path in source_files:
            rel_path = str(file_path.relative_to(self.project_dir))
            name = file_path.stem

            node_type = NodeType.MODULE
            for type_name, pattern in patterns.items():
                if pattern.search(name):
                    node_type = NodeType.SERVICE
                    break

            node_id = self._path_to_id(rel_path)
            if node_type == NodeType.SERVICE and node_id not in nodes:
                nodes[node_id] = ModuleNode(
                    id=node_id,
                    name=name,
                    path=rel_path,
                    type=node_type,
                    language="python" if file_path.suffix == ".py" else "typescript",
                    description=f"Service: {name}",
                )

        # Build edges between services
        service_ids = set(nodes.keys())
        for file_path in source_files:
            rel_path = str(file_path.relative_to(self.project_dir))
            src_id = self._path_to_id(rel_path)
            if src_id not in service_ids:
                continue

            if file_path.suffix == ".py":
                imports = self._extract_python_imports(file_path)
            else:
                imports = self._extract_js_imports(file_path)

            for imp in imports:
                target_id = self._import_to_id(imp, file_path)
                if target_id and target_id in service_ids and target_id != src_id:
                    edges.append(DependencyEdge(
                        source_id=src_id,
                        target_id=target_id,
                        edge_type=EdgeType.USES,
                        label="uses",
                    ))

        from .diagram_generator import DiagramGenerator
        diagram = ArchitectureDiagram(
            diagram_type=DiagramType.DATA_FLOW,
            title="Data Flow",
            nodes=list(nodes.values())[:40],
            edges=edges[:80],
        )
        gen = DiagramGenerator()
        diagram.mermaid_code = gen.generate_mermaid(diagram)
        return diagram

    def analyze_database_schema(self) -> ArchitectureDiagram:
        """Extract DB tables from ORM models."""
        nodes: Dict[str, ModuleNode] = {}
        edges: List[DependencyEdge] = []

        # Patterns for different ORMs
        sqlalchemy_model = re.compile(
            r"class\s+(\w+)\s*\(.*?(?:Base|db\.Model|DeclarativeBase).*?\):"
        )
        django_model = re.compile(r"class\s+(\w+)\s*\(.*?models\.Model.*?\):")
        prisma_model = re.compile(r"^model\s+(\w+)\s*\{", re.MULTILINE)
        fk_pattern = re.compile(
            r"(?:ForeignKey|relationship|OneToOne|ManyToMany|ManyToOne)\s*\(\s*['\"]?(\w+)"
        )

        source_files = self._get_source_files([".py", ".prisma"])
        for file_path in source_files:
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            rel_path = str(file_path.relative_to(self.project_dir))

            for pattern in [sqlalchemy_model, django_model, prisma_model]:
                for m in pattern.finditer(content):
                    table_name = m.group(1)
                    node_id = f"table_{table_name.lower()}"
                    if node_id not in nodes:
                        nodes[node_id] = ModuleNode(
                            id=node_id,
                            name=table_name,
                            path=rel_path,
                            type=NodeType.TABLE,
                            language="sql",
                            description=f"Database table: {table_name}",
                        )

            # Extract foreign keys
            for m in fk_pattern.finditer(content):
                ref_name = m.group(1)
                ref_id = f"table_{ref_name.lower()}"
                # Find which table this FK belongs to
                for match in sqlalchemy_model.finditer(content):
                    src_id = f"table_{match.group(1).lower()}"
                    if src_id in nodes and ref_id in nodes and src_id != ref_id:
                        edges.append(DependencyEdge(
                            source_id=src_id,
                            target_id=ref_id,
                            edge_type=EdgeType.FOREIGN_KEY,
                            label="FK",
                        ))

        from .diagram_generator import DiagramGenerator
        diagram = ArchitectureDiagram(
            diagram_type=DiagramType.DATABASE_SCHEMA,
            title="Database Schema",
            nodes=list(nodes.values()),
            edges=edges,
        )
        gen = DiagramGenerator()
        diagram.mermaid_code = gen.generate_mermaid(diagram)
        return diagram

    def _get_source_files(self, extensions: List[str]) -> List[Path]:
        """Return source files matching extensions, excluding ignored paths."""
        files = []
        ext_set = set(extensions)
        for file_path in self.project_dir.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix not in ext_set:
                continue
            if any(part in IGNORE_PATTERNS for part in file_path.parts):
                continue
            files.append(file_path)
        return files

    def _extract_python_imports(self, file_path: Path) -> List[str]:
        """Extract import module names from a Python file using ast."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content)
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
            return imports
        except Exception:
            return []

    def _extract_js_imports(self, file_path: Path) -> List[str]:
        """Extract import/require paths from JS/TS files."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []
        patterns = [
            re.compile(r"""import\s+.*?\s+from\s+['"]([^'"]+)['"]"""),
            re.compile(r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)"""),
            re.compile(r"""import\s*\(\s*['"]([^'"]+)['"]\s*\)"""),
        ]
        imports = []
        for pattern in patterns:
            for m in pattern.finditer(content):
                imports.append(m.group(1))
        return imports

    def _path_to_id(self, rel_path: str) -> str:
        """Convert a relative path to a stable node ID."""
        return hashlib.md5(rel_path.encode()).hexdigest()[:12]

    def _import_to_id(self, import_str: str, from_file: Path) -> str:
        """Attempt to resolve an import string to a node ID."""
        # Relative import
        if import_str.startswith("."):
            try:
                resolved = (from_file.parent / import_str.lstrip("./").replace(".", "/"))
                for ext in list(ALL_EXTENSIONS) + [""]:
                    candidate = resolved.with_suffix(ext) if ext else resolved / "__init__.py"
                    if candidate.exists():
                        rel = str(candidate.relative_to(self.project_dir))
                        return self._path_to_id(rel)
            except Exception:
                pass
            return ""
        # Absolute/package import — try to find in project
        parts = import_str.split(".")
        for i in range(len(parts), 0, -1):
            candidate_path = self.project_dir / Path(*parts[:i])
            for ext in list(ALL_EXTENSIONS) + [""]:
                f = candidate_path.with_suffix(ext) if ext else candidate_path / "__init__.py"
                if f.exists():
                    rel = str(f.relative_to(self.project_dir))
                    return self._path_to_id(rel)
        return ""
