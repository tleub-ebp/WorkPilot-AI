"""
Dependency Graph Builder
========================

Parses Python and TypeScript/JavaScript source files to extract
import/export relationships and build a structural dependency graph.
"""

from __future__ import annotations

import ast
import re
from datetime import datetime, timezone
from pathlib import Path

from .models import DependencyGraph, DependencyNode

# Extensions handled by each language parser
_PYTHON_EXTS = {".py"}
_JS_TS_EXTS = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}

# Directories to skip during traversal
_SKIP_DIRS = {
    "node_modules", "__pycache__", ".git", ".venv", "venv", "env",
    "dist", "build", "out", ".next", ".nuxt", ".cache", "coverage",
    ".mypy_cache", ".pytest_cache", ".tox", "site-packages",
}

# Maximum number of files to index (prevents runaway on huge repos)
_MAX_FILES = 5_000


class DependencyGraphBuilder:
    """
    Builds a dependency graph by parsing source files in the project.

    Supports:
    - Python: ast-based import analysis (import x, from x import y)
    - TypeScript/JavaScript: regex-based import analysis (import/require/export)
    """

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir).resolve()

    # ── Public API ─────────────────────────────────────────────────────────

    def build(self) -> DependencyGraph:
        """
        Walk the project directory, parse imports, and return a complete graph.
        Imported-by edges are computed as a reverse index after initial parsing.
        """
        graph = DependencyGraph()
        graph.build_timestamp = datetime.now(timezone.utc).isoformat()

        files_indexed = 0
        for source_file in self._iter_source_files():
            if files_indexed >= _MAX_FILES:
                break

            rel_path = str(source_file.relative_to(self.project_dir)).replace("\\", "/")
            ext = source_file.suffix.lower()

            if ext in _PYTHON_EXTS:
                node = self._parse_python(source_file, rel_path)
            elif ext in _JS_TS_EXTS:
                node = self._parse_js_ts(source_file, rel_path)
            else:
                continue

            graph.add_node(node)
            files_indexed += 1

        graph.file_count = files_indexed

        # Build reverse index: for every A → B edge, add A to B.imported_by
        self._build_imported_by(graph)

        return graph

    # ── File traversal ─────────────────────────────────────────────────────

    def _iter_source_files(self):
        for path in self.project_dir.rglob("*"):
            if not path.is_file():
                continue
            # Skip ignored directories (check all path parts)
            if any(part in _SKIP_DIRS for part in path.parts):
                continue
            if path.suffix.lower() in _PYTHON_EXTS | _JS_TS_EXTS:
                yield path

    # ── Python parser ──────────────────────────────────────────────────────

    def _parse_python(self, file_path: Path, rel_path: str) -> DependencyNode:
        node = DependencyNode(path=rel_path, language="python")
        try:
            source = file_path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError:
            return node

        for stmt in ast.walk(tree):
            if isinstance(stmt, ast.Import):
                for alias in stmt.names:
                    resolved = self._resolve_python_import(alias.name, rel_path)
                    if resolved:
                        node.imports.append(resolved)

            elif isinstance(stmt, ast.ImportFrom):
                if stmt.module:
                    resolved = self._resolve_python_import(
                        stmt.module, rel_path, level=stmt.level
                    )
                    if resolved:
                        node.imports.append(resolved)

            # Collect top-level exports (function/class defs at module level)
            elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if not stmt.col_offset:  # Top-level only
                    node.export_symbols.append(stmt.name)

        # Deduplicate
        node.imports = list(dict.fromkeys(node.imports))
        return node

    def _resolve_python_import(
        self, module: str, from_file: str, level: int = 0
    ) -> str | None:
        """
        Try to resolve a Python import to a relative file path.
        Returns None for third-party packages that don't exist in the project.
        """
        if level > 0:
            # Relative import
            base_parts = from_file.split("/")[: -(level)]
            module_parts = module.split(".") if module else []
            candidate_parts = base_parts + module_parts
        else:
            candidate_parts = module.split(".")

        # Try as a module file or package __init__
        for suffix in (".py", "/__init__.py"):
            candidate = "/".join(candidate_parts) + suffix
            if (self.project_dir / candidate).exists():
                return candidate.replace("/__init__.py", "/__init__.py")

        return None

    # ── TypeScript/JavaScript parser ───────────────────────────────────────

    # Matches: import ... from '...' | require('...')
    _IMPORT_RE = re.compile(
        r"""(?:import\s.*?from\s+|import\s+|require\s*\(\s*)['"]([^'"]+)['"]""",
        re.MULTILINE,
    )
    # Matches: export { ... } from '...'
    _REEXPORT_RE = re.compile(r"""export\s+.*?from\s+['"]([^'"]+)['"]""", re.MULTILINE)
    # Matches exported symbols: export function|class|const|let|var NAME
    _EXPORT_SYMBOL_RE = re.compile(
        r"""^export\s+(?:default\s+)?(?:function|class|const|let|var|async\s+function)\s+(\w+)""",
        re.MULTILINE,
    )

    def _parse_js_ts(self, file_path: Path, rel_path: str) -> DependencyNode:
        lang = "typescript" if file_path.suffix.lower() in {".ts", ".tsx"} else "javascript"
        node = DependencyNode(path=rel_path, language=lang)

        try:
            source = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return node

        base_dir = str(Path(rel_path).parent).replace("\\", "/")

        # Collect all import paths
        raw_imports = self._IMPORT_RE.findall(source)
        raw_imports += self._REEXPORT_RE.findall(source)

        for raw in raw_imports:
            resolved = self._resolve_js_import(raw, base_dir)
            if resolved:
                node.imports.append(resolved)

        # Export symbols
        node.export_symbols = self._EXPORT_SYMBOL_RE.findall(source)

        node.imports = list(dict.fromkeys(node.imports))
        return node

    _JS_EXTENSIONS_TRY = ["", ".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.tsx", "/index.js"]

    def _resolve_js_import(self, raw: str, from_dir: str) -> str | None:
        """Resolve a JS/TS import specifier to a relative path, or None if external."""
        if not raw.startswith("."):
            return None  # External package, skip

        # Normalize path relative to the importing file's directory
        if from_dir and from_dir != ".":
            joined = from_dir + "/" + raw
        else:
            joined = raw

        # Resolve ".." and "." segments
        try:
            resolved_base = str(Path(joined).as_posix())
        except Exception:
            return None

        for ext in self._JS_EXTENSIONS_TRY:
            candidate = resolved_base + ext
            # Normalize to forward slashes
            candidate = candidate.lstrip("/")
            if (self.project_dir / candidate).exists():
                return candidate

        return None

    # ── Reverse index ──────────────────────────────────────────────────────

    def _build_imported_by(self, graph: DependencyGraph) -> None:
        """Populate the imported_by field for each node using the forward edges."""
        for node in graph.nodes.values():
            for dep_path in node.imports:
                dep_node = graph.nodes.get(dep_path)
                if dep_node and node.path not in dep_node.imported_by:
                    dep_node.imported_by.append(node.path)
