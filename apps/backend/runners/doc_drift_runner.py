"""
Doc Drift Runner

Scans a project for documentation that drifts from the actual code.
Compares references in markdown / RST docs against symbols and files
discovered in the source tree.

Output protocol (one JSON object per line, prefixed):
    DOC_DRIFT_EVENT:{"type": "progress", "data": {"status": "..."}}
    DOC_DRIFT_RESULT:{...full report dict...}
    DOC_DRIFT_ERROR:<message>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from doc_drift_detector.drift_scanner import DriftScanner  # noqa: E402

DOC_EXTENSIONS = {".md", ".mdx", ".rst", ".txt"}
SOURCE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte"}
DEFAULT_IGNORES = {
    "node_modules",
    ".git",
    "dist",
    "build",
    ".next",
    "__pycache__",
    ".venv",
    "venv",
    ".workpilot",
    "out",
    "coverage",
}

_PY_SYMBOL = re.compile(r"^\s*(?:def|class)\s+([A-Za-z_]\w*)", re.MULTILINE)
_JS_SYMBOL = re.compile(
    r"(?:export\s+)?(?:async\s+)?(?:function|class|const|let|var)\s+([A-Za-z_$][\w$]*)",
)


def _emit(prefix: str, payload: Any) -> None:
    print(f"{prefix}:{json.dumps(payload, default=str)}", flush=True)


def _emit_event(event_type: str, data: dict[str, Any]) -> None:
    _emit("DOC_DRIFT_EVENT", {"type": event_type, "data": data})


def _iter_files(root: Path, extensions: set[str]) -> list[Path]:
    out: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in extensions:
            continue
        if any(part in DEFAULT_IGNORES for part in path.parts):
            continue
        out.append(path)
    return out


def _extract_symbols(content: str, suffix: str) -> set[str]:
    pattern = _PY_SYMBOL if suffix == ".py" else _JS_SYMBOL
    return {m.group(1) for m in pattern.finditer(content)}


def _issue_to_dict(issue: Any) -> dict[str, Any]:
    return {
        "driftType": issue.drift_type.value,
        "severity": issue.severity.value,
        "docFile": issue.doc_file,
        "docLine": issue.doc_line,
        "referencedSymbol": issue.referenced_symbol,
        "message": issue.message,
        "suggestion": issue.suggestion,
    }


def run_scan(project_path: Path) -> dict[str, Any]:
    _emit_event("start", {"status": "Discovering documentation files..."})
    doc_paths = _iter_files(project_path, DOC_EXTENSIONS)
    _emit_event(
        "progress",
        {"status": f"Indexing source code ({len(doc_paths)} docs found)..."},
    )

    source_paths = _iter_files(project_path, SOURCE_EXTENSIONS)
    symbols: set[str] = set()
    source_files: set[str] = set()
    for path in source_paths:
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        symbols.update(_extract_symbols(content, path.suffix.lower()))
        source_files.add(str(path.relative_to(project_path)).replace("\\", "/"))

    doc_files: dict[str, str] = {}
    for path in doc_paths:
        try:
            doc_files[str(path.relative_to(project_path))] = path.read_text(
                encoding="utf-8", errors="ignore"
            )
        except OSError:
            continue

    _emit_event(
        "progress",
        {
            "status": f"Comparing {len(doc_files)} docs against {len(symbols)} symbols..."
        },
    )

    scanner = DriftScanner()
    report = scanner.scan(doc_files, symbols, source_files)

    result = {
        "docsScanned": report.docs_scanned,
        "codeFilesIndexed": report.source_files_scanned,
        "issues": [_issue_to_dict(i) for i in report.issues],
        "summary": report.summary,
    }
    _emit_event(
        "complete",
        {"issues": len(report.issues), "docsScanned": report.docs_scanned},
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Doc Drift Runner")
    parser.add_argument("--project-path", required=True, help="Project root path")
    args = parser.parse_args()

    project_path = Path(args.project_path)
    if not project_path.exists():
        _emit("DOC_DRIFT_ERROR", f"Project path does not exist: {project_path}")
        sys.exit(1)

    try:
        result = run_scan(project_path)
        _emit("DOC_DRIFT_RESULT", result)
    except Exception as exc:  # noqa: BLE001
        _emit("DOC_DRIFT_ERROR", str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
