"""
Notebook Agent — First-class Jupyter notebook support.

Parses .ipynb files, detects stale outputs, execution order issues,
missing imports, and converts between notebook and script formats.
"""

from .notebook_handler import (
    CellType,
    NotebookCell,
    NotebookHandler,
    NotebookIssue,
    NotebookIssueType,
    ParsedNotebook,
)

__all__ = [
    "NotebookHandler",
    "ParsedNotebook",
    "NotebookCell",
    "NotebookIssue",
    "NotebookIssueType",
    "CellType",
]
