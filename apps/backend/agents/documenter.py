"""Documentation Agent — Automatic documentation generation and maintenance.

Specialized agent that analyzes source code and generates comprehensive
documentation including docstrings, README files, architecture diagrams
(Mermaid), and keeps documentation in sync with code changes.

Feature 2.2 — Agent de documentation automatique.

Example:
    >>> from apps.backend.agents.documenter import DocumentationAgent
    >>> agent = DocumentationAgent()
    >>> result = agent.generate_docstrings("src/connectors/jira/connector.py")
    >>> readme = agent.generate_module_readme("src/connectors/jira/")
    >>> diagram = agent.generate_architecture_diagram("src/connectors/")
"""

import ast
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DocFormat(str, Enum):
    """Supported documentation output formats."""

    MARKDOWN = "markdown"
    JSDOC = "jsdoc"
    SPHINX = "sphinx"
    STORYBOOK = "storybook"
    GOOGLE = "google"
    NUMPY = "numpy"


class DiagramType(str, Enum):
    """Types of architecture diagrams."""

    CLASS_DIAGRAM = "class_diagram"
    MODULE_DEPENDENCY = "module_dependency"
    SEQUENCE = "sequence"
    FLOWCHART = "flowchart"


class DocStatus(str, Enum):
    """Documentation coverage status for a symbol."""

    DOCUMENTED = "documented"
    PARTIAL = "partial"
    MISSING = "missing"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class SymbolDoc:
    """Documentation status for a single symbol (function, class, module).

    Attributes:
        name: Symbol name.
        symbol_type: Type (function, class, module).
        file_path: Path to the file containing the symbol.
        line_number: Line number in the file.
        status: Documentation status.
        existing_doc: Existing docstring/documentation if any.
        generated_doc: Newly generated documentation.
        args: Function arguments (for functions).
        return_type: Return type annotation (for functions).
    """

    name: str
    symbol_type: str = "function"
    file_path: str = ""
    line_number: int = 0
    status: DocStatus = DocStatus.MISSING
    existing_doc: str = ""
    generated_doc: str = ""
    args: list[str] = field(default_factory=list)
    return_type: str | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "symbol_type": self.symbol_type,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "status": self.status.value,
            "existing_doc": self.existing_doc,
            "generated_doc": self.generated_doc,
            "args": self.args,
            "return_type": self.return_type,
        }


@dataclass
class ModuleInfo:
    """Information about a module for README generation.

    Attributes:
        module_path: Path to the module directory.
        name: Module name.
        description: Brief description.
        files: Python files in the module.
        classes: Classes defined in the module.
        functions: Top-level functions.
        dependencies: Imported modules/packages.
        submodules: Sub-directories that are packages.
    """

    module_path: str
    name: str = ""
    description: str = ""
    files: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    submodules: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DocGenerationResult:
    """Result of a documentation generation run.

    Attributes:
        source_path: File or directory that was analyzed.
        symbols_analyzed: Number of symbols analyzed.
        symbols_documented: Number of symbols with new documentation.
        symbols_already_documented: Number already documented.
        generated_docs: List of generated SymbolDoc objects.
        readme_content: Generated README content (if applicable).
        diagram_content: Generated diagram content (if applicable).
        output_format: Format used.
    """

    source_path: str
    symbols_analyzed: int = 0
    symbols_documented: int = 0
    symbols_already_documented: int = 0
    generated_docs: list[SymbolDoc] = field(default_factory=list)
    readme_content: str = ""
    diagram_content: str = ""
    output_format: DocFormat = DocFormat.GOOGLE

    def to_dict(self) -> dict:
        return {
            "source_path": self.source_path,
            "symbols_analyzed": self.symbols_analyzed,
            "symbols_documented": self.symbols_documented,
            "symbols_already_documented": self.symbols_already_documented,
            "generated_docs": [d.to_dict() for d in self.generated_docs],
            "readme_content": self.readme_content,
            "diagram_content": self.diagram_content,
            "output_format": self.output_format.value,
        }


# ---------------------------------------------------------------------------
# Code analyzer for documentation
# ---------------------------------------------------------------------------


class DocAnalyzer:
    """Analyzes Python source code to extract symbols and documentation status."""

    def analyze_file(self, file_path: str) -> list[SymbolDoc]:
        """Analyze a Python file for documentation coverage.

        Args:
            file_path: Path to the Python file.

        Returns:
            List of SymbolDoc with documentation status for each symbol.
        """
        with open(file_path, encoding="utf-8") as f:
            source = f.read()
        return self.analyze_source(source, file_path)

    def analyze_source(
        self, source: str, file_path: str = "<source>"
    ) -> list[SymbolDoc]:
        """Analyze Python source code for documentation coverage.

        Args:
            source: Python source code.
            file_path: Display path.

        Returns:
            List of SymbolDoc objects.
        """
        try:
            tree = ast.parse(source)
        except SyntaxError:
            logger.warning("Cannot parse %s for documentation analysis", file_path)
            return []

        symbols: list[SymbolDoc] = []
        self._visit(tree, symbols, file_path, class_name=None)
        return symbols

    def _visit(
        self,
        node: ast.AST,
        symbols: list[SymbolDoc],
        file_path: str,
        class_name: str | None,
    ) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                docstring = ast.get_docstring(child) or ""
                status = DocStatus.DOCUMENTED if docstring else DocStatus.MISSING
                symbols.append(
                    SymbolDoc(
                        name=child.name,
                        symbol_type="class",
                        file_path=file_path,
                        line_number=child.lineno,
                        status=status,
                        existing_doc=docstring,
                    )
                )
                self._visit(child, symbols, file_path, class_name=child.name)

            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                docstring = ast.get_docstring(child) or ""
                args = [a.arg for a in child.args.args if a.arg not in ("self", "cls")]
                return_type = None
                if child.returns:
                    try:
                        return_type = ast.unparse(child.returns)
                    except Exception:
                        pass

                if docstring:
                    # Check if partial (has docstring but missing args docs)
                    has_args_doc = any(
                        kw in docstring
                        for kw in ("Args:", "Parameters:", ":param", "@param")
                    )
                    if args and not has_args_doc:
                        status = DocStatus.PARTIAL
                    else:
                        status = DocStatus.DOCUMENTED
                else:
                    status = DocStatus.MISSING

                name = f"{class_name}.{child.name}" if class_name else child.name
                symbols.append(
                    SymbolDoc(
                        name=name,
                        symbol_type="method" if class_name else "function",
                        file_path=file_path,
                        line_number=child.lineno,
                        status=status,
                        existing_doc=docstring,
                        args=args,
                        return_type=return_type,
                    )
                )

    def analyze_directory(self, dir_path: str) -> ModuleInfo:
        """Analyze a Python module directory.

        Args:
            dir_path: Path to the directory.

        Returns:
            ModuleInfo with module metadata.
        """
        module_name = os.path.basename(dir_path.rstrip("/\\"))
        info = ModuleInfo(module_path=dir_path, name=module_name)

        if not os.path.isdir(dir_path):
            return info

        for entry in sorted(os.listdir(dir_path)):
            full_path = os.path.join(dir_path, entry)
            if os.path.isfile(full_path) and entry.endswith(".py"):
                info.files.append(entry)
                # Extract classes and functions
                try:
                    symbols = self.analyze_file(full_path)
                    for sym in symbols:
                        if sym.symbol_type == "class":
                            info.classes.append(sym.name)
                        elif sym.symbol_type == "function":
                            info.functions.append(sym.name)
                except Exception:
                    pass

                # Extract imports for dependencies
                try:
                    with open(full_path, encoding="utf-8") as f:
                        source = f.read()
                    tree = ast.parse(source)
                    for node in ast.iter_child_nodes(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                dep = alias.name.split(".")[0]
                                if dep not in info.dependencies:
                                    info.dependencies.append(dep)
                        elif isinstance(node, ast.ImportFrom) and node.module:
                            dep = node.module.split(".")[0]
                            if dep not in info.dependencies:
                                info.dependencies.append(dep)
                except Exception:
                    pass

            elif os.path.isdir(full_path):
                init_file = os.path.join(full_path, "__init__.py")
                if os.path.exists(init_file):
                    info.submodules.append(entry)

        # Try to extract description from __init__.py
        init_path = os.path.join(dir_path, "__init__.py")
        if os.path.isfile(init_path):
            try:
                with open(init_path, encoding="utf-8") as f:
                    source = f.read()
                tree = ast.parse(source)
                docstring = ast.get_docstring(tree)
                if docstring:
                    info.description = docstring.split("\n")[0]
            except Exception:
                pass

        return info


# ---------------------------------------------------------------------------
# Documentation Generator
# ---------------------------------------------------------------------------


class DocGenerator:
    """Generates documentation content from analyzed symbols."""

    def generate_docstring(
        self,
        symbol: SymbolDoc,
        fmt: DocFormat = DocFormat.GOOGLE,
    ) -> str:
        """Generate a docstring for a symbol.

        Args:
            symbol: The symbol to document.
            fmt: Output format.

        Returns:
            Generated docstring string.
        """
        if fmt == DocFormat.GOOGLE:
            return self._generate_google_docstring(symbol)
        elif fmt == DocFormat.NUMPY:
            return self._generate_numpy_docstring(symbol)
        elif fmt == DocFormat.SPHINX:
            return self._generate_sphinx_docstring(symbol)
        elif fmt == DocFormat.JSDOC:
            return self._generate_jsdoc(symbol)
        return self._generate_google_docstring(symbol)

    def _generate_google_docstring(self, symbol: SymbolDoc) -> str:
        """Generate Google-style docstring.

        We deliberately avoid emitting the ``TODO`` keyword: it leaks into user
        code and gets picked up by linters and TODO-trackers. Instead we emit
        an empty description slot so IDEs auto-suggest filling it in.
        """
        parts = [f"    {self._infer_description(symbol)}"]

        if symbol.args:
            parts.append("")
            parts.append("    Args:")
            for arg in symbol.args:
                parts.append(f"        {arg}: ")

        if symbol.return_type and symbol.return_type != "None":
            parts.append("")
            parts.append("    Returns:")
            parts.append(f"        {symbol.return_type}: ")

        docstring = '    """' + "\n".join(parts) + '\n    """'
        return docstring

    def _generate_numpy_docstring(self, symbol: SymbolDoc) -> str:
        """Generate NumPy-style docstring."""
        parts = [f"    {self._infer_description(symbol)}"]

        if symbol.args:
            parts.append("")
            parts.append("    Parameters")
            parts.append("    ----------")
            for arg in symbol.args:
                parts.append(f"    {arg}")
                parts.append(f"        Description of {arg}.")

        if symbol.return_type and symbol.return_type != "None":
            parts.append("")
            parts.append("    Returns")
            parts.append("    -------")
            parts.append(f"    {symbol.return_type}")
            parts.append("        ")

        docstring = '    """' + "\n".join(parts) + '\n    """'
        return docstring

    def _generate_sphinx_docstring(self, symbol: SymbolDoc) -> str:
        """Generate Sphinx-style docstring."""
        parts = [f"    {self._infer_description(symbol)}"]

        if symbol.args:
            parts.append("")
            for arg in symbol.args:
                parts.append(f"    :param {arg}: ")

        if symbol.return_type and symbol.return_type != "None":
            parts.append("    :returns: ")
            parts.append(f"    :rtype: {symbol.return_type}")

        docstring = '    """' + "\n".join(parts) + '\n    """'
        return docstring

    def _generate_jsdoc(self, symbol: SymbolDoc) -> str:
        """Generate JSDoc-style documentation."""
        parts = ["/**", f" * {self._infer_description(symbol)}"]
        if symbol.args:
            for arg in symbol.args:
                parts.append(f" * @param {{*}} {arg}")
        if symbol.return_type and symbol.return_type != "None":
            parts.append(f" * @returns {{{symbol.return_type}}}")
        parts.append(" */")
        return "\n".join(parts)

    @staticmethod
    def _infer_description(symbol: SymbolDoc) -> str:
        """Infer a description from the symbol name."""
        name = symbol.name.split(".")[-1]
        # Convert snake_case to words
        words = name.replace("_", " ").strip()
        if words.startswith("  "):
            words = words.lstrip()
        if not words:
            return "TODO — add description."
        return words.capitalize() + "."

    def generate_readme(self, module_info: ModuleInfo) -> str:
        """Generate a README.md for a module.

        Args:
            module_info: Analyzed module information.

        Returns:
            Markdown string for the README.
        """
        lines = [
            f"# {module_info.name}",
            "",
        ]

        if module_info.description:
            lines.append(module_info.description)
            lines.append("")

        lines.append("## Overview")
        lines.append("")
        lines.append(f"This module is located at `{module_info.module_path}`.")
        lines.append("")

        if module_info.files:
            lines.append("## Files")
            lines.append("")
            for f in module_info.files:
                lines.append(f"- `{f}`")
            lines.append("")

        if module_info.classes:
            lines.append("## Classes")
            lines.append("")
            for cls in module_info.classes:
                lines.append(f"- **`{cls}`**")
            lines.append("")

        if module_info.functions:
            lines.append("## Functions")
            lines.append("")
            for fn in module_info.functions:
                lines.append(f"- `{fn}()`")
            lines.append("")

        if module_info.submodules:
            lines.append("## Submodules")
            lines.append("")
            for sub in module_info.submodules:
                lines.append(f"- `{sub}/`")
            lines.append("")

        if module_info.dependencies:
            lines.append("## Dependencies")
            lines.append("")
            for dep in module_info.dependencies:
                lines.append(f"- `{dep}`")
            lines.append("")

        lines.append("---")
        lines.append(
            f"*Auto-generated by WorkPilot AI Documentation Agent on {datetime.now(timezone.utc).strftime('%Y-%m-%d')}*"
        )

        return "\n".join(lines)

    def generate_mermaid_class_diagram(self, symbols: list[SymbolDoc]) -> str:
        """Generate a Mermaid class diagram from analyzed symbols.

        Args:
            symbols: List of SymbolDoc objects.

        Returns:
            Mermaid diagram string.
        """
        lines = ["```mermaid", "classDiagram"]
        classes: dict[str, list[str]] = {}

        for sym in symbols:
            if sym.symbol_type == "class":
                classes.setdefault(sym.name, [])
            elif sym.symbol_type == "method" and "." in sym.name:
                cls_name, method = sym.name.split(".", 1)
                classes.setdefault(cls_name, [])
                args_str = ", ".join(sym.args) if sym.args else ""
                ret = f" {sym.return_type}" if sym.return_type else ""
                prefix = "+" if not method.startswith("_") else "-"
                classes[cls_name].append(
                    f"    {cls_name} : {prefix}{method}({args_str}){ret}"
                )

        for cls_name, methods in classes.items():
            lines.append(f"    class {cls_name}")
            for m in methods:
                lines.append(m)

        lines.append("```")
        return "\n".join(lines)

    def generate_mermaid_module_diagram(self, module_info: ModuleInfo) -> str:
        """Generate a Mermaid module dependency diagram.

        Args:
            module_info: Analyzed module information.

        Returns:
            Mermaid diagram string.
        """
        lines = ["```mermaid", "graph TD"]
        node_name = module_info.name.replace("-", "_")
        lines.append(f"    {node_name}[{module_info.name}]")

        for sub in module_info.submodules:
            sub_safe = sub.replace("-", "_")
            lines.append(f"    {node_name} --> {sub_safe}[{sub}]")

        for dep in module_info.dependencies[:10]:  # Limit to top 10
            dep_safe = dep.replace("-", "_").replace(".", "_")
            lines.append(f"    {node_name} -.-> {dep_safe}[{dep}]")

        lines.append("```")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Documentation Agent (main entry point)
# ---------------------------------------------------------------------------


class DocumentationAgent:
    """Autonomous documentation agent.

    Combines code analysis, docstring generation, README creation,
    and architecture diagram generation into a unified agent.
    """

    def __init__(
        self,
        llm_provider: Any | None = None,
        default_format: DocFormat = DocFormat.GOOGLE,
    ) -> None:
        self.llm_provider = llm_provider
        self.default_format = default_format
        self.analyzer = DocAnalyzer()
        self.generator = DocGenerator()
        self._history: list[DocGenerationResult] = []
        logger.info("DocumentationAgent initialized (format=%s)", default_format.value)

    # -- Docstring generation ------------------------------------------------

    def generate_docstrings(
        self,
        file_path: str | None = None,
        source: str | None = None,
        fmt: DocFormat | None = None,
    ) -> DocGenerationResult:
        """Generate docstrings for undocumented symbols in a file.

        Args:
            file_path: Path to the Python file.
            source: Source code string (alternative to file_path).
            fmt: Output format (defaults to instance default).

        Returns:
            DocGenerationResult with generated docstrings.
        """
        output_format = fmt or self.default_format

        if source:
            symbols = self.analyzer.analyze_source(source, file_path or "<source>")
        elif file_path:
            symbols = self.analyzer.analyze_file(file_path)
        else:
            return DocGenerationResult(source_path="<none>")

        result = DocGenerationResult(
            source_path=file_path or "<source>",
            symbols_analyzed=len(symbols),
            output_format=output_format,
        )

        for sym in symbols:
            if sym.status in (DocStatus.MISSING, DocStatus.PARTIAL):
                sym.generated_doc = self.generator.generate_docstring(
                    sym, output_format
                )
                result.symbols_documented += 1
            else:
                result.symbols_already_documented += 1
            result.generated_docs.append(sym)

        self._history.append(result)
        return result

    # -- README generation ---------------------------------------------------

    def generate_module_readme(
        self,
        dir_path: str,
    ) -> DocGenerationResult:
        """Generate a README.md for a module directory.

        Args:
            dir_path: Path to the module directory.

        Returns:
            DocGenerationResult with readme_content populated.
        """
        module_info = self.analyzer.analyze_directory(dir_path)
        readme = self.generator.generate_readme(module_info)
        diagram = self.generator.generate_mermaid_module_diagram(module_info)

        result = DocGenerationResult(
            source_path=dir_path,
            readme_content=readme,
            diagram_content=diagram,
        )
        self._history.append(result)
        return result

    # -- Architecture diagram ------------------------------------------------

    def generate_architecture_diagram(
        self,
        dir_path: str | None = None,
        file_path: str | None = None,
        source: str | None = None,
        diagram_type: DiagramType = DiagramType.CLASS_DIAGRAM,
    ) -> DocGenerationResult:
        """Generate an architecture diagram.

        Args:
            dir_path: Directory to analyze (for module diagrams).
            file_path: Single file to analyze (for class diagrams).
            source: Source code string (alternative).
            diagram_type: Type of diagram to generate.

        Returns:
            DocGenerationResult with diagram_content populated.
        """
        if diagram_type == DiagramType.MODULE_DEPENDENCY and dir_path:
            module_info = self.analyzer.analyze_directory(dir_path)
            diagram = self.generator.generate_mermaid_module_diagram(module_info)
        else:
            # Class diagram
            if source:
                symbols = self.analyzer.analyze_source(source, file_path or "<source>")
            elif file_path:
                symbols = self.analyzer.analyze_file(file_path)
            else:
                symbols = []
            diagram = self.generator.generate_mermaid_class_diagram(symbols)

        result = DocGenerationResult(
            source_path=dir_path or file_path or "<source>",
            diagram_content=diagram,
            symbols_analyzed=len(symbols)
            if diagram_type != DiagramType.MODULE_DEPENDENCY
            else 0,
        )
        self._history.append(result)
        return result

    # -- Documentation sync --------------------------------------------------

    def check_documentation_coverage(
        self,
        file_path: str | None = None,
        source: str | None = None,
    ) -> dict[str, Any]:
        """Check documentation coverage for a file.

        Args:
            file_path: Path to the Python file.
            source: Source code string.

        Returns:
            Dict with coverage statistics.
        """
        if source:
            symbols = self.analyzer.analyze_source(source, file_path or "<source>")
        elif file_path:
            symbols = self.analyzer.analyze_file(file_path)
        else:
            return {
                "total": 0,
                "documented": 0,
                "partial": 0,
                "missing": 0,
                "coverage_pct": 0.0,
            }

        documented = sum(1 for s in symbols if s.status == DocStatus.DOCUMENTED)
        partial = sum(1 for s in symbols if s.status == DocStatus.PARTIAL)
        missing = sum(1 for s in symbols if s.status == DocStatus.MISSING)
        total = len(symbols)
        coverage = (documented / total * 100) if total > 0 else 0.0

        return {
            "total": total,
            "documented": documented,
            "partial": partial,
            "missing": missing,
            "coverage_pct": round(coverage, 1),
            "symbols": [s.to_dict() for s in symbols],
        }

    # -- Query / Stats -------------------------------------------------------

    def get_history(self) -> list[DocGenerationResult]:
        """Get all generation results."""
        return list(self._history)

    def get_stats(self) -> dict[str, Any]:
        """Get overall documentation statistics."""
        return {
            "total_runs": len(self._history),
            "total_symbols_analyzed": sum(r.symbols_analyzed for r in self._history),
            "total_symbols_documented": sum(
                r.symbols_documented for r in self._history
            ),
            "total_readmes_generated": sum(
                1 for r in self._history if r.readme_content
            ),
            "total_diagrams_generated": sum(
                1 for r in self._history if r.diagram_content
            ),
        }
