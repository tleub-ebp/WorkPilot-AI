"""Documentation Analyzer - Detects coverage gaps and outdated documentation."""

import ast
import hashlib
import re
import uuid
from pathlib import Path

from .models import DocCoverage, DocSection, DocStatus, DocType

IGNORE_PATTERNS = {
    "node_modules",
    ".git",
    "__pycache__",
    "dist",
    "build",
    ".venv",
    ".next",
    "out",
    "coverage",
}

PYTHON_EXTENSIONS = {".py"}
JS_EXTENSIONS = {".js", ".ts", ".jsx", ".tsx", ".mjs"}


class DocumentationAnalyzer:
    """Analyzes a project's documentation coverage and freshness."""

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)

    def analyze_coverage(self) -> DocCoverage:
        """Scan Python/JS/TS files and measure documentation coverage."""
        coverage = DocCoverage()

        for file_path in self._get_source_files():
            try:
                if file_path.suffix == ".py":
                    symbols = self._extract_python_symbols(file_path)
                else:
                    symbols = self._extract_js_symbols(file_path)

                for sym in symbols:
                    rel_path = str(file_path.relative_to(self.project_dir))
                    qualified = f"{rel_path}:{sym['line']}:{sym['name']}"
                    if sym["kind"] == "function":
                        coverage.total_functions += 1
                        if sym["has_doc"]:
                            coverage.documented_functions += 1
                        else:
                            coverage.missing_docs.append(qualified)
                    elif sym["kind"] == "class":
                        coverage.total_classes += 1
                        if sym["has_doc"]:
                            coverage.documented_classes += 1
                        else:
                            coverage.missing_docs.append(qualified)
            except Exception:
                continue

        coverage.compute_coverage()
        return coverage

    def detect_outdated_docs(self) -> list[DocSection]:
        """Find documentation files whose related code has changed."""
        outdated = []
        doc_dirs = [
            self.project_dir / "docs",
            self.project_dir / "doc",
            self.project_dir / "documentation",
        ]
        doc_files = []
        for doc_dir in doc_dirs:
            if doc_dir.exists():
                doc_files.extend(doc_dir.rglob("*.md"))
        doc_files.extend(self.project_dir.glob("*.md"))

        for doc_file in doc_files:
            if self._is_ignoreable_path(doc_file):
                continue
            # Check modification time vs related code files
            try:
                doc_mtime = doc_file.stat().st_mtime
                rel_path = str(doc_file.relative_to(self.project_dir))

                # Find recently modified code files (newer than the doc)
                newer_code = self._find_newer_code_files(doc_mtime)
                if newer_code:
                    outdated.append(
                        DocSection(
                            section_id=str(uuid.uuid4())[:8],
                            file_path=rel_path,
                            doc_type=DocType.README,
                            title=doc_file.name,
                            status=DocStatus.OUTDATED,
                            related_code_file=newer_code[0],
                        )
                    )
            except Exception:
                continue

        return outdated

    def find_missing_docs(self) -> list[str]:
        """Return list of 'file:line:name' entries without documentation."""
        coverage = self.analyze_coverage()
        return coverage.missing_docs

    def analyze_readme(self) -> DocSection | None:
        """Check README quality and completeness."""
        readme_candidates = [
            self.project_dir / "README.md",
            self.project_dir / "readme.md",
            self.project_dir / "README.rst",
        ]
        for readme in readme_candidates:
            if readme.exists():
                try:
                    content = readme.read_text(encoding="utf-8", errors="ignore")
                    lines = content.count("\n")
                    status = (
                        DocStatus.UP_TO_DATE if lines > 20 else DocStatus.INCOMPLETE
                    )
                    return DocSection(
                        section_id=str(uuid.uuid4())[:8],
                        file_path=str(readme.relative_to(self.project_dir)),
                        doc_type=DocType.README,
                        title="README",
                        content=content[:2000],
                        status=status,
                        related_code_hash=self._compute_file_hash(readme),
                    )
                except Exception:
                    pass
        return DocSection(
            section_id=str(uuid.uuid4())[:8],
            file_path="README.md",
            doc_type=DocType.README,
            title="README",
            status=DocStatus.MISSING,
        )

    def analyze_api_docs(self) -> list[DocSection]:
        """Find API endpoints without documentation."""
        sections = []
        # FastAPI / Flask route patterns
        api_patterns = [
            re.compile(
                r'@(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*[\'"]([^\'"]+)[\'"]'
            ),
            re.compile(r'@(?:app|router)\.route\s*\(\s*[\'"]([^\'"]+)[\'"]'),
        ]

        for file_path in self._get_source_files([".py"]):
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            rel_path = str(file_path.relative_to(self.project_dir))

            for pattern in api_patterns:
                for m in pattern.finditer(content):
                    endpoint = (
                        m.group(2) if m.lastindex and m.lastindex >= 2 else m.group(1)
                    )
                    line = content[: m.start()].count("\n") + 1
                    sections.append(
                        DocSection(
                            section_id=str(uuid.uuid4())[:8],
                            file_path=rel_path,
                            doc_type=DocType.API_DOCS,
                            title=f"API: {endpoint}",
                            status=DocStatus.MISSING,
                            related_code_file=rel_path,
                        )
                    )

        return sections

    def _compute_file_hash(self, path: Path) -> str:
        """Compute MD5 hash of file content."""
        try:
            content = path.read_bytes()
            return hashlib.md5(content).hexdigest()
        except Exception:
            return ""

    def _extract_python_symbols(self, file_path: Path) -> list[dict]:
        """Extract Python functions/classes with docstring info using ast."""
        symbols = []
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    has_doc = (
                        (
                            isinstance(node.body[0], ast.Expr)
                            and isinstance(node.body[0].value, ast.Constant)
                            and isinstance(node.body[0].value.value, str)
                        )
                        if node.body
                        else False
                    )
                    symbols.append(
                        {
                            "name": node.name,
                            "kind": "function",
                            "line": node.lineno,
                            "has_doc": has_doc,
                        }
                    )
                elif isinstance(node, ast.ClassDef):
                    has_doc = (
                        (
                            isinstance(node.body[0], ast.Expr)
                            and isinstance(node.body[0].value, ast.Constant)
                            and isinstance(node.body[0].value.value, str)
                        )
                        if node.body
                        else False
                    )
                    symbols.append(
                        {
                            "name": node.name,
                            "kind": "class",
                            "line": node.lineno,
                            "has_doc": has_doc,
                        }
                    )
        except Exception:
            pass
        return symbols

    def _extract_js_symbols(self, file_path: Path) -> list[dict]:
        """Extract JS/TS functions/classes with JSDoc info."""
        symbols = []
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            lines = content.split("\n")

            func_pattern = re.compile(
                r"(?:export\s+)?(?:async\s+)?function\s+(\w+)|"
                r"(?:export\s+)?(?:const|let)\s+(\w+)\s*=\s*(?:async\s+)?\("
            )
            class_pattern = re.compile(r"(?:export\s+)?class\s+(\w+)")
            jsdoc_pattern = re.compile(r"/\*\*")

            for i, line in enumerate(lines):
                for m in func_pattern.finditer(line):
                    name = m.group(1) or m.group(2)
                    if not name:
                        continue
                    # Check if previous line has JSDoc
                    has_doc = i > 0 and "/**" in lines[max(0, i - 3) : i + 1]
                    symbols.append(
                        {
                            "name": name,
                            "kind": "function",
                            "line": i + 1,
                            "has_doc": has_doc,
                        }
                    )
                for m in class_pattern.finditer(line):
                    has_doc = i > 0 and "/**" in lines[max(0, i - 3) : i + 1]
                    symbols.append(
                        {
                            "name": m.group(1),
                            "kind": "class",
                            "line": i + 1,
                            "has_doc": has_doc,
                        }
                    )
        except Exception:
            pass
        return symbols

    def _find_newer_code_files(self, doc_mtime: float) -> list[str]:
        """Find code files modified more recently than doc_mtime."""
        newer = []
        for file_path in self._get_source_files():
            try:
                if file_path.stat().st_mtime > doc_mtime:
                    newer.append(str(file_path.relative_to(self.project_dir)))
                    if len(newer) >= 5:
                        break
            except Exception:
                continue
        return newer

    def _get_source_files(self, extensions: list[str] | None = None) -> list[Path]:
        """Return source files, excluding ignored paths."""
        if extensions is None:
            extensions = list(PYTHON_EXTENSIONS | JS_EXTENSIONS)
        ext_set = set(extensions)
        files = []
        for file_path in self.project_dir.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix not in ext_set:
                continue
            if self._is_ignoreable_path(file_path):
                continue
            files.append(file_path)
        return files

    def _is_ignoreable_path(self, path: Path) -> bool:
        return any(part in IGNORE_PATTERNS for part in path.parts)
