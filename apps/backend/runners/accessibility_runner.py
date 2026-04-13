"""
Accessibility Runner

Scans a project tree for WCAG accessibility violations and emits a
structured report. Designed to be invoked by the Electron frontend
via the accessibility IPC handler.

Output protocol (one JSON object per line, prefixed):
    A11Y_EVENT:{"type": "progress", "data": {"status": "..."}}
    A11Y_RESULT:{...full report dict...}
    A11Y_ERROR:<message>
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from accessibility_agent.accessibility_scanner import (  # noqa: E402
    A11yReport,
    AccessibilityScanner,
    WcagLevel,
)

SCAN_EXTENSIONS = {".html", ".htm", ".jsx", ".tsx", ".vue", ".svelte"}
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


def _emit(prefix: str, payload: Any) -> None:
    print(f"{prefix}:{json.dumps(payload, default=str)}", flush=True)


def _emit_event(event_type: str, data: dict[str, Any]) -> None:
    _emit("A11Y_EVENT", {"type": event_type, "data": data})


def _iter_target_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SCAN_EXTENSIONS:
            continue
        if any(part in DEFAULT_IGNORES for part in path.parts):
            continue
        files.append(path)
    return files


def _report_to_dict(report: A11yReport) -> dict[str, Any]:
    return {
        "filesScanned": report.files_scanned,
        "targetLevel": report.target_level.value,
        "violations": [
            {
                "ruleId": v.rule_id,
                "description": v.description,
                "severity": v.severity.value,
                "wcagLevel": v.wcag_level.value,
                "wcagCriteria": v.wcag_criteria,
                "file": v.file,
                "line": v.line,
                "element": v.element,
                "suggestion": v.suggestion,
            }
            for v in report.violations
        ],
        "passedRules": [],
        "summary": report.summary,
    }


def run_scan(project_path: Path, target_level: WcagLevel) -> dict[str, Any]:
    _emit_event("start", {"status": "Discovering files..."})
    files = _iter_target_files(project_path)
    _emit_event("progress", {"status": f"Scanning {len(files)} files..."})

    scanner = AccessibilityScanner(target_level=target_level)
    contents: dict[str, str] = {}
    for file in files:
        try:
            contents[str(file.relative_to(project_path))] = file.read_text(
                encoding="utf-8", errors="ignore"
            )
        except OSError:
            continue

    report = scanner.scan_files(contents)
    result = _report_to_dict(report)
    _emit_event(
        "complete",
        {"violations": len(report.violations), "filesScanned": report.files_scanned},
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Accessibility Runner")
    parser.add_argument("--project-path", required=True, help="Project root path")
    parser.add_argument(
        "--target-level",
        default="AA",
        choices=["A", "AA", "AAA"],
        help="WCAG conformance level to enforce",
    )
    args = parser.parse_args()

    project_path = Path(args.project_path)
    if not project_path.exists():
        _emit("A11Y_ERROR", f"Project path does not exist: {project_path}")
        sys.exit(1)

    try:
        result = run_scan(project_path, WcagLevel(args.target_level))
        _emit("A11Y_RESULT", result)
    except Exception as exc:  # noqa: BLE001
        _emit("A11Y_ERROR", str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
