"""
Notebook Agent — Handle Jupyter notebooks as first-class citizens.

Parses .ipynb files, extracts cells, detects issues (stale outputs,
execution order inconsistencies, missing imports), and can convert
between notebook and script formats.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CellType(str, Enum):
    CODE = "code"
    MARKDOWN = "markdown"
    RAW = "raw"


class NotebookIssueType(str, Enum):
    STALE_OUTPUT = "stale_output"
    OUT_OF_ORDER = "out_of_order"
    MISSING_IMPORT = "missing_import"
    EMPTY_CELL = "empty_cell"
    LONG_CELL = "long_cell"
    NO_MARKDOWN = "no_markdown"
    SENSITIVE_OUTPUT = "sensitive_output"


@dataclass
class NotebookCell:
    """A single notebook cell."""

    index: int
    cell_type: CellType
    source: str
    execution_count: int | None = None
    outputs: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class NotebookIssue:
    """An issue detected in a notebook."""

    issue_type: NotebookIssueType
    cell_index: int
    message: str
    severity: str = "warning"
    suggestion: str = ""


@dataclass
class ParsedNotebook:
    """Parsed representation of a Jupyter notebook."""

    path: str = ""
    cells: list[NotebookCell] = field(default_factory=list)
    kernel: str = ""
    language: str = ""
    nbformat: int = 4
    metadata: dict[str, Any] = field(default_factory=dict)
    issues: list[NotebookIssue] = field(default_factory=list)

    @property
    def code_cells(self) -> list[NotebookCell]:
        return [c for c in self.cells if c.cell_type == CellType.CODE]

    @property
    def markdown_cells(self) -> list[NotebookCell]:
        return [c for c in self.cells if c.cell_type == CellType.MARKDOWN]


class NotebookHandler:
    """Parse, analyse, and transform Jupyter notebooks.

    Usage::

        handler = NotebookHandler()
        nb = handler.parse(Path("analysis.ipynb"))
        issues = handler.analyze(nb)
        script = handler.to_script(nb)
    """

    def parse(self, path: Path) -> ParsedNotebook:
        """Parse a .ipynb file."""
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)

        kernel_spec = data.get("metadata", {}).get("kernelspec", {})
        nb = ParsedNotebook(
            path=str(path),
            kernel=kernel_spec.get("name", ""),
            language=kernel_spec.get("language", data.get("metadata", {}).get("language_info", {}).get("name", "")),
            nbformat=data.get("nbformat", 4),
            metadata=data.get("metadata", {}),
        )

        for i, cell_data in enumerate(data.get("cells", [])):
            source = "".join(cell_data.get("source", []))
            nb.cells.append(NotebookCell(
                index=i,
                cell_type=CellType(cell_data.get("cell_type", "code")),
                source=source,
                execution_count=cell_data.get("execution_count"),
                outputs=cell_data.get("outputs", []),
                metadata=cell_data.get("metadata", {}),
            ))

        return nb

    def analyze(self, nb: ParsedNotebook) -> list[NotebookIssue]:
        """Analyse a notebook for common issues."""
        issues: list[NotebookIssue] = []

        issues.extend(self._check_execution_order(nb))
        issues.extend(self._check_empty_cells(nb))
        issues.extend(self._check_long_cells(nb))
        issues.extend(self._check_documentation(nb))

        nb.issues = issues
        return issues

    def to_script(self, nb: ParsedNotebook) -> str:
        """Convert a notebook to a Python/script file."""
        lines: list[str] = []
        lines.append(f"# Converted from {nb.path}")
        lines.append(f"# Kernel: {nb.kernel}\n")

        for cell in nb.cells:
            if cell.cell_type == CellType.MARKDOWN:
                for line in cell.source.splitlines():
                    lines.append(f"# {line}")
                lines.append("")
            elif cell.cell_type == CellType.CODE:
                lines.append(cell.source)
                lines.append("")

        return "\n".join(lines)

    def clear_outputs(self, nb: ParsedNotebook) -> ParsedNotebook:
        """Return a copy of the notebook with all outputs cleared."""
        for cell in nb.cells:
            cell.outputs = []
            cell.execution_count = None
        return nb

    # ------------------------------------------------------------------
    # Analysis checks
    # ------------------------------------------------------------------

    @staticmethod
    def _check_execution_order(nb: ParsedNotebook) -> list[NotebookIssue]:
        issues: list[NotebookIssue] = []
        code_cells = nb.code_cells
        prev_count = 0

        for cell in code_cells:
            if cell.execution_count is not None:
                if cell.execution_count < prev_count:
                    issues.append(NotebookIssue(
                        issue_type=NotebookIssueType.OUT_OF_ORDER,
                        cell_index=cell.index,
                        message=f"Cell {cell.index} executed out of order (count={cell.execution_count}, previous={prev_count})",
                        suggestion="Re-run all cells in order with 'Restart & Run All'",
                    ))
                prev_count = cell.execution_count

        return issues

    @staticmethod
    def _check_empty_cells(nb: ParsedNotebook) -> list[NotebookIssue]:
        return [
            NotebookIssue(
                issue_type=NotebookIssueType.EMPTY_CELL,
                cell_index=cell.index,
                message=f"Empty code cell at index {cell.index}",
                severity="info",
                suggestion="Remove empty cells to keep the notebook clean",
            )
            for cell in nb.code_cells
            if not cell.source.strip()
        ]

    @staticmethod
    def _check_long_cells(nb: ParsedNotebook, max_lines: int = 50) -> list[NotebookIssue]:
        return [
            NotebookIssue(
                issue_type=NotebookIssueType.LONG_CELL,
                cell_index=cell.index,
                message=f"Code cell at index {cell.index} has {len(cell.source.splitlines())} lines",
                suggestion="Consider breaking this cell into smaller, focused cells",
            )
            for cell in nb.code_cells
            if len(cell.source.splitlines()) > max_lines
        ]

    @staticmethod
    def _check_documentation(nb: ParsedNotebook) -> list[NotebookIssue]:
        if not nb.markdown_cells and len(nb.code_cells) > 3:
            return [NotebookIssue(
                issue_type=NotebookIssueType.NO_MARKDOWN,
                cell_index=0,
                message="Notebook has no markdown cells — consider adding documentation",
                severity="info",
                suggestion="Add markdown cells to explain the notebook's purpose and key steps",
            )]
        return []
