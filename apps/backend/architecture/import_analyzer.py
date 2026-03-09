"""
Import Analyzer
================

Parses source files and builds a dependency/import graph.
Supports Python (AST-based) and JavaScript/TypeScript (regex-based).
"""

from __future__ import annotations

import ast
import fnmatch
import os
import re
from pathlib import Path

from .models import (
    ArchitectureConfig,
    ArchitectureViolation,
    ForbiddenPattern,
    ImportEdge,
    ImportGraph,
    LayerConfig,
)

# Directories to always skip
SKIP_DIRS = {
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".git",
    ".auto-claude",
    "dist",
    "build",
    ".next",
    ".nuxt",
    "coverage",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "egg-info",
}

# File extensions to analyze
PYTHON_EXTENSIONS = {".py"}
JS_TS_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}

# JS/TS import patterns
_JS_IMPORT_FROM_RE = re.compile(
    r"""(?:import\s+(?:[\w{},\s*]+)\s+from\s+['"]([^'"]+)['"])"""
    r"""|(?:import\s*\(\s*['"]([^'"]+)['"]\s*\))"""
    r"""|(?:require\s*\(\s*['"]([^'"]+)['"]\s*\))""",
    re.MULTILINE,
)

# Re-export pattern: export { ... } from '...'
_JS_REEXPORT_RE = re.compile(
    r"""export\s+(?:[\w{},\s*]+)\s+from\s+['"]([^'"]+)['"]""",
    re.MULTILINE,
)


class ImportAnalyzer:
    """Analyzes source files and builds an import dependency graph."""

    def __init__(self, project_dir: Path, config: ArchitectureConfig):
        self.project_dir = project_dir
        self.config = config

    def analyze_imports(
        self, changed_files: list[str] | None = None
    ) -> ImportGraph:
        """
        Build an import graph from source files.

        Args:
            changed_files: If provided, only analyze these files (relative to project_dir).
                          If None, analyze all source files in the project.

        Returns:
            ImportGraph with all import edges.
        """
        graph = ImportGraph()

        if changed_files:
            files_to_analyze = [
                self.project_dir / f for f in changed_files if self._is_analyzable(f)
            ]
        else:
            files_to_analyze = list(self._walk_source_files())

        for file_path in files_to_analyze:
            if not file_path.exists():
                continue

            rel_path = str(file_path.relative_to(self.project_dir)).replace("\\", "/")
            ext = file_path.suffix.lower()

            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            if ext in PYTHON_EXTENSIONS:
                edges = self._parse_python_imports(rel_path, content)
            elif ext in JS_TS_EXTENSIONS:
                edges = self._parse_js_ts_imports(rel_path, content)
            else:
                continue

            graph.edges.extend(edges)
            graph.files_analyzed += 1

        return graph

    def check_layer_violations(
        self, graph: ImportGraph
    ) -> list[ArchitectureViolation]:
        """Check import edges against layer rules."""
        if not self.config.layers:
            return []

        violations = []
        layer_map = self._build_layer_map()

        for edge in graph.edges:
            source_layer = self._get_layer_for_file(edge.source_file, layer_map)
            if not source_layer:
                continue

            # Check if the import target resolves to a forbidden layer
            target_layer_name = self._resolve_import_to_layer(
                edge.target_module, edge.source_file, layer_map
            )
            if not target_layer_name:
                continue

            if target_layer_name in source_layer.forbidden_imports:
                severity = "warning" if self.config.inferred else "error"
                violations.append(
                    ArchitectureViolation(
                        type="layer_violation",
                        severity=severity,
                        file=edge.source_file,
                        line=edge.line,
                        import_target=edge.target_module,
                        rule=f"Layer '{source_layer.name}' cannot import from '{target_layer_name}'",
                        description=(
                            f"File '{edge.source_file}' in layer '{source_layer.name}' "
                            f"imports '{edge.target_module}' from forbidden layer '{target_layer_name}'"
                        ),
                        suggestion=(
                            f"Move this import to use an abstraction or interface "
                            f"that respects the '{source_layer.name}' layer boundaries"
                        ),
                    )
                )

        return violations

    def check_forbidden_imports(
        self, graph: ImportGraph
    ) -> list[ArchitectureViolation]:
        """Check imports against forbidden pattern rules."""
        if not self.config.rules.forbidden_patterns:
            return []

        violations = []
        for edge in graph.edges:
            for pattern in self.config.rules.forbidden_patterns:
                if not self._file_matches_pattern(edge.source_file, pattern.from_pattern):
                    continue

                if re.search(pattern.import_pattern, edge.target_module, re.IGNORECASE):
                    severity = "warning" if self.config.inferred else "error"
                    violations.append(
                        ArchitectureViolation(
                            type="forbidden_import",
                            severity=severity,
                            file=edge.source_file,
                            line=edge.line,
                            import_target=edge.target_module,
                            rule=pattern.description or f"Forbidden import pattern: {pattern.import_pattern}",
                            description=(
                                f"File '{edge.source_file}' imports '{edge.target_module}' "
                                f"which matches forbidden pattern '{pattern.import_pattern}'"
                            ),
                            suggestion=(
                                f"Remove or replace this import. {pattern.description}"
                            ),
                        )
                    )

        return violations

    # ---------------------------------------------------------------------------
    # Python import parsing
    # ---------------------------------------------------------------------------

    def _parse_python_imports(
        self, rel_path: str, content: str
    ) -> list[ImportEdge]:
        """Parse Python imports using AST."""
        edges = []
        try:
            tree = ast.parse(content, filename=rel_path)
        except SyntaxError:
            return edges

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    edges.append(
                        ImportEdge(
                            source_file=rel_path,
                            target_module=alias.name,
                            line=node.lineno,
                            import_statement=f"import {alias.name}",
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if node.level > 0:
                    # Relative import: resolve to absolute-ish path
                    module = self._resolve_relative_import(
                        rel_path, module, node.level
                    )
                if module:
                    edges.append(
                        ImportEdge(
                            source_file=rel_path,
                            target_module=module,
                            line=node.lineno,
                            import_statement=f"from {module} import ...",
                        )
                    )

        return edges

    def _resolve_relative_import(
        self, source_file: str, module: str, level: int
    ) -> str:
        """Resolve a relative Python import to a dotted module path."""
        parts = source_file.replace("\\", "/").split("/")
        # Remove the filename
        if parts:
            parts = parts[:-1]
        # Go up `level` directories
        for _ in range(level - 1):
            if parts:
                parts.pop()
        # Build the resolved module
        base = ".".join(parts)
        if module:
            return f"{base}.{module}" if base else module
        return base

    # ---------------------------------------------------------------------------
    # JS/TS import parsing
    # ---------------------------------------------------------------------------

    def _parse_js_ts_imports(
        self, rel_path: str, content: str
    ) -> list[ImportEdge]:
        """Parse JavaScript/TypeScript imports using regex."""
        edges = []

        for line_num, line in enumerate(content.split("\n"), 1):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("/*"):
                continue

            # Standard imports, dynamic imports, require()
            for match in _JS_IMPORT_FROM_RE.finditer(line):
                target = match.group(1) or match.group(2) or match.group(3)
                if target:
                    edges.append(
                        ImportEdge(
                            source_file=rel_path,
                            target_module=target,
                            line=line_num,
                            import_statement=stripped,
                        )
                    )

            # Re-exports
            for match in _JS_REEXPORT_RE.finditer(line):
                target = match.group(1)
                if target:
                    edges.append(
                        ImportEdge(
                            source_file=rel_path,
                            target_module=target,
                            line=line_num,
                            import_statement=stripped,
                        )
                    )

        return edges

    # ---------------------------------------------------------------------------
    # Layer matching
    # ---------------------------------------------------------------------------

    def _build_layer_map(self) -> dict[str, LayerConfig]:
        """Build a mapping of layer name -> LayerConfig."""
        return {layer.name: layer for layer in self.config.layers}

    def _get_layer_for_file(
        self, file_path: str, layer_map: dict[str, LayerConfig]
    ) -> LayerConfig | None:
        """Determine which layer a file belongs to."""
        for layer in self.config.layers:
            for pattern in layer.patterns:
                if fnmatch.fnmatch(file_path, pattern):
                    return layer
        return None

    def _resolve_import_to_layer(
        self,
        import_target: str,
        source_file: str,
        layer_map: dict[str, LayerConfig],
    ) -> str | None:
        """
        Try to resolve an import target to a layer name.

        For relative imports (./foo, ../bar), resolve relative to source file.
        For named imports, check if any layer's patterns match.
        """
        # Convert module path to potential file paths
        candidate_paths = self._import_to_file_paths(import_target, source_file)

        for candidate in candidate_paths:
            for layer in self.config.layers:
                for pattern in layer.patterns:
                    if fnmatch.fnmatch(candidate, pattern):
                        return layer.name

        # Also check by module name segments (e.g., "infrastructure" in "src/infrastructure/db")
        import_parts = import_target.replace(".", "/").replace("\\", "/").split("/")
        for part in import_parts:
            if part in layer_map:
                return part

        return None

    def _import_to_file_paths(
        self, import_target: str, source_file: str
    ) -> list[str]:
        """Convert an import target to potential file paths for matching."""
        candidates = []

        if import_target.startswith("."):
            # Relative JS/TS import
            source_dir = "/".join(source_file.replace("\\", "/").split("/")[:-1])
            # Normalize the path
            parts = (source_dir + "/" + import_target).split("/")
            resolved: list[str] = []
            for part in parts:
                if part == "." or part == "":
                    continue
                elif part == "..":
                    if resolved:
                        resolved.pop()
                else:
                    resolved.append(part)
            base = "/".join(resolved)
            # Add potential extensions
            for ext in ["", ".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.tsx", "/index.js"]:
                candidates.append(base + ext)
        else:
            # Absolute/module import — convert dots to path separators
            as_path = import_target.replace(".", "/")
            for ext in ["", ".py", ".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.js", "/__init__.py"]:
                candidates.append(as_path + ext)

        return candidates

    # ---------------------------------------------------------------------------
    # File utilities
    # ---------------------------------------------------------------------------

    def _walk_source_files(self):
        """Walk project directory yielding analyzable source files."""
        for root, dirs, files in os.walk(self.project_dir):
            # Prune skipped directories
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]

            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext in PYTHON_EXTENSIONS or ext in JS_TS_EXTENSIONS:
                    yield Path(root) / fname

    def _is_analyzable(self, file_path: str) -> bool:
        """Check if a file path has an analyzable extension."""
        ext = os.path.splitext(file_path)[1].lower()
        return ext in PYTHON_EXTENSIONS or ext in JS_TS_EXTENSIONS

    def _file_matches_pattern(self, file_path: str, pattern: str) -> bool:
        """Check if a file path matches a glob pattern."""
        return fnmatch.fnmatch(file_path, pattern)
