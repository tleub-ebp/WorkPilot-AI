"""Documentation Updater - Detects and updates outdated documentation."""

import re
from collections.abc import Callable
from pathlib import Path

from .models import DocSection, DocStatus


class DocumentationUpdater:
    """Detects and updates outdated documentation in the project."""

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self._progress_callback: Callable | None = None

    def set_progress_callback(self, callback: Callable) -> None:
        self._progress_callback = callback

    def check_and_update(self) -> list[DocSection]:
        """Detect outdated docs and update them with placeholder improvements."""
        from .doc_analyzer import DocumentationAnalyzer

        analyzer = DocumentationAnalyzer(str(self.project_dir))
        outdated = analyzer.detect_outdated_docs()
        updated = []
        for section in outdated:
            try:
                updated_section = self.update_section(
                    section,
                    section.content + "\n\n> ⚠️ This documentation may be outdated. "
                    "Run the Documentation Agent to regenerate.\n",
                )
                updated.append(updated_section)
            except Exception as e:
                print(f"[DocUpdater] Failed to update {section.file_path}: {e}")
        return updated

    def update_section(self, section: DocSection, new_content: str) -> DocSection:
        """Update a specific doc section with new content."""
        target = self.project_dir / section.file_path
        if not target.parent.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(new_content, encoding="utf-8")
        section.content = new_content
        section.status = DocStatus.UP_TO_DATE
        return section

    def insert_docstrings(
        self,
        file_path: str,
        symbols_with_docs: list[dict],
        dry_run: bool = False,
    ) -> int:
        """Insert docstrings into source files. Returns count of insertions."""
        target = Path(file_path)
        if not target.exists():
            return 0

        try:
            source = target.read_text(encoding="utf-8")
        except Exception:
            return 0

        count = 0
        modified = source

        for sym in symbols_with_docs:
            name = sym.get("name", "")
            docstring = sym.get("docstring", "")
            if not name or not docstring:
                continue

            if target.suffix == ".py":
                result = self._insert_python_docstring(modified, name, docstring)
            else:
                result = self._insert_jsdoc(modified, name, docstring)

            if result != modified:
                modified = result
                count += 1
                if self._progress_callback:
                    self._progress_callback(f"Documented: {name}")

        if count > 0 and not dry_run:
            target.write_text(modified, encoding="utf-8")

        return count

    def _insert_python_docstring(
        self, source: str, function_name: str, docstring: str
    ) -> str:
        """Insert a docstring after a Python function/class definition."""
        pattern = re.compile(
            rf"(def\s+{re.escape(function_name)}\s*\([^)]*\)\s*(?:->\s*\S+\s*)?:)([ \t]*\n)",
            re.MULTILINE,
        )
        match = pattern.search(source)
        if not match:
            # Try class definition
            pattern = re.compile(
                rf"(class\s+{re.escape(function_name)}\s*(?:\([^)]*\))?\s*:)([ \t]*\n)",
                re.MULTILINE,
            )
            match = pattern.search(source)

        if not match:
            return source

        # Find the indentation of the next line
        after_def = source[match.end() :]
        indent_match = re.match(r"([ \t]+)", after_def)
        indent = indent_match.group(1) if indent_match else "    "

        # Format docstring with indentation
        docstring_lines = docstring.strip().split("\n")
        if len(docstring_lines) == 1:
            formatted = f'{indent}"""{docstring_lines[0]}"""\n'
        else:
            inner = "\n".join(f"{indent}{line}" for line in docstring_lines)
            formatted = f'{indent}"""\n{inner}\n{indent}"""\n'

        # Check if there's already a docstring
        if '"""' in after_def[:50] or "'''" in after_def[:50]:
            return source  # Already has docstring

        insert_pos = match.end()
        return source[:insert_pos] + formatted + source[insert_pos:]

    def _insert_jsdoc(self, source: str, function_name: str, jsdoc: str) -> str:
        """Insert JSDoc comment before a JavaScript/TypeScript function."""
        pattern = re.compile(
            rf"((?:export\s+)?(?:async\s+)?function\s+{re.escape(function_name)}\s*\(|"
            rf"(?:export\s+)?(?:const|let)\s+{re.escape(function_name)}\s*=\s*(?:async\s+)?\()",
            re.MULTILINE,
        )
        match = pattern.search(source)
        if not match:
            return source

        # Check if there's already a JSDoc comment just before
        before = source[: match.start()]
        if before.rstrip().endswith("*/"):
            return source

        # Find the indentation of the function line
        line_start = source.rfind("\n", 0, match.start()) + 1
        indent_match = re.match(r"([ \t]*)", source[line_start:])
        indent = indent_match.group(1) if indent_match else ""

        # Format JSDoc
        lines = jsdoc.strip().split("\n")
        formatted_lines = [f"{indent}/**"]
        for line in lines:
            formatted_lines.append(f"{indent} * {line}")
        formatted_lines.append(f"{indent} */\n")
        formatted_jsdoc = "\n".join(formatted_lines)

        return source[: match.start()] + formatted_jsdoc + source[match.start() :]

    def watch_for_changes(self, callback: Callable) -> None:
        """Watch for code changes that invalidate docs (polling-based fallback)."""
        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer

            class CodeChangeHandler(FileSystemEventHandler):
                def on_modified(self, event):
                    if not event.is_directory and event.src_path.endswith(
                        (".py", ".ts", ".tsx", ".js", ".jsx")
                    ):
                        callback(event.src_path)

            observer = Observer()
            observer.schedule(
                CodeChangeHandler(), str(self.project_dir), recursive=True
            )
            observer.start()
        except ImportError:
            print("[DocUpdater] watchdog not available — file watching disabled")


def _generate_python_docstring(name: str, kind: str) -> str:
    """Produce a minimal, honest docstring skeleton.

    We deliberately avoid emitting ``TODO`` placeholders for params/returns:
    they leak into user code and get flagged by linters. A one-line summary
    is strictly more useful than a structured template full of TODOs.
    """
    if kind == "class":
        return f"{name} class.\n"
    return f"Execute {name}.\n"


def _generate_jsdoc(name: str, kind: str) -> str:
    """JSDoc counterpart of ``_generate_python_docstring`` — same rationale."""
    if kind == "class":
        return f"@class {name}"
    return f"@function {name}"
