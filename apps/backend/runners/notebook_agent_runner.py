"""
Notebook Agent Runner

Discovers .ipynb files in a project, parses them, and reports common issues
(stale outputs, out-of-order execution, empty cells, long cells, missing
documentation).

Output protocol (one JSON object per line, prefixed):
    NOTEBOOK_EVENT:{"type": "progress", "data": {"status": "..."}}
    NOTEBOOK_RESULT:{"notebooks": [...]}
    NOTEBOOK_ERROR:<message>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from notebook_agent.notebook_handler import (  # noqa: E402
    NotebookHandler,
    ParsedNotebook,
)

EXCLUDED_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".ipynb_checkpoints"}


def _emit(prefix: str, payload: Any) -> None:
    print(f"{prefix}:{json.dumps(payload, default=str)}", flush=True)


def _emit_event(event_type: str, data: dict[str, Any]) -> None:
    _emit("NOTEBOOK_EVENT", {"type": event_type, "data": data})


def _is_excluded(path: Path, root: Path) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return True
    return any(part in EXCLUDED_DIRS for part in rel.parts)


def _discover_notebooks(project_path: Path) -> list[Path]:
    found: list[Path] = []
    for p in project_path.glob("**/*.ipynb"):
        if p.is_file() and not _is_excluded(p, project_path):
            found.append(p)
    return sorted(found)


def _notebook_to_dict(nb: ParsedNotebook, project_root: Path) -> dict[str, Any]:
    try:
        rel_path = str(Path(nb.path).relative_to(project_root))
    except ValueError:
        rel_path = nb.path
    return {
        "path": rel_path,
        "kernel": nb.kernel,
        "language": nb.language,
        "totalCells": len(nb.cells),
        "codeCells": len(nb.code_cells),
        "markdownCells": len(nb.markdown_cells),
        "issues": [
            {
                "issueType": issue.issue_type.value,
                "cellIndex": issue.cell_index,
                "message": issue.message,
                "severity": issue.severity,
                "suggestion": issue.suggestion,
            }
            for issue in nb.issues
        ],
    }


def run_scan(project_path: Path) -> dict[str, Any]:
    _emit_event("start", {"status": "Discovering notebooks..."})
    notebook_paths = _discover_notebooks(project_path)

    if not notebook_paths:
        _emit_event("complete", {"status": "No notebooks found"})
        return {"notebooks": []}

    _emit_event(
        "progress",
        {"status": f"Found {len(notebook_paths)} notebook(s), analyzing..."},
    )

    handler = NotebookHandler()
    notebooks: list[dict[str, Any]] = []
    for path in notebook_paths:
        try:
            nb = handler.parse(path)
            handler.analyze(nb)
            notebooks.append(_notebook_to_dict(nb, project_path))
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            _emit_event(
                "progress", {"status": f"Failed to parse {path.name}: {exc}"}
            )

    total_issues = sum(len(nb["issues"]) for nb in notebooks)
    _emit_event(
        "complete",
        {"notebooks": len(notebooks), "issues": total_issues},
    )
    return {"notebooks": notebooks}


def main() -> None:
    parser = argparse.ArgumentParser(description="Notebook Agent Runner")
    parser.add_argument("--project-path", required=True, help="Project root path")
    args = parser.parse_args()

    project_path = Path(args.project_path)
    if not project_path.exists():
        _emit("NOTEBOOK_ERROR", f"Project path does not exist: {project_path}")
        sys.exit(1)

    try:
        result = run_scan(project_path)
        _emit("NOTEBOOK_RESULT", result)
    except Exception as exc:  # noqa: BLE001
        _emit("NOTEBOOK_ERROR", str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
