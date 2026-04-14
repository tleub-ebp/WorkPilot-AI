"""
i18n Runner

Scans a project tree for internationalisation issues: hardcoded
user-facing strings, missing translation keys, locale file
inconsistencies, and translation coverage per locale.

Output protocol (one JSON object per line, prefixed):
    I18N_EVENT:{"type": "progress", "data": {"status": "..."}}
    I18N_RESULT:{...full report dict...}
    I18N_ERROR:<message>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from i18n_agent.i18n_scanner import I18nScanner  # noqa: E402

SCAN_EXTENSIONS = {".jsx", ".tsx", ".vue", ".svelte", ".py", ".html", ".htm"}
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
    _emit("I18N_EVENT", {"type": event_type, "data": data})


def _iter_source_files(root: Path) -> list[Path]:
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


def _discover_locales(root: Path) -> dict[str, dict[str, Any]]:
    """Find {locale: merged_dict} from common i18n folder layouts."""
    locales: dict[str, dict[str, Any]] = {}
    candidates = [
        root / "src" / "shared" / "i18n" / "locales",
        root / "apps" / "frontend" / "src" / "shared" / "i18n" / "locales",
        root / "src" / "i18n" / "locales",
        root / "locales",
        root / "i18n",
    ]
    locales_root: Path | None = None
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            locales_root = candidate
            break
    if locales_root is None:
        return locales

    for locale_dir in sorted(locales_root.iterdir()):
        if not locale_dir.is_dir():
            continue
        merged: dict[str, Any] = {}
        for json_file in sorted(locale_dir.glob("*.json")):
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    merged[json_file.stem] = data
            except (OSError, json.JSONDecodeError):
                continue
        if merged:
            locales[locale_dir.name] = merged
    return locales


def _issue_to_dict(issue: Any) -> dict[str, Any]:
    return {
        "issueType": issue.issue_type.value,
        "severity": issue.severity.value,
        "file": issue.file,
        "line": issue.line,
        "key": issue.key,
        "locale": issue.locale,
        "message": issue.message,
        "suggestion": issue.suggestion,
    }


def run_scan(project_path: Path, reference_locale: str) -> dict[str, Any]:
    _emit_event("start", {"status": "Discovering source files..."})
    files = _iter_source_files(project_path)
    _emit_event(
        "progress", {"status": f"Scanning {len(files)} files for hardcoded strings..."}
    )

    scanner = I18nScanner(reference_locale=reference_locale)
    issues: list[Any] = []
    for file in files:
        try:
            content = file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = str(file.relative_to(project_path))
        issues.extend(scanner.scan_file_for_hardcoded(rel, content))

    _emit_event("progress", {"status": "Comparing locale files..."})
    locales = _discover_locales(project_path)
    coverage: dict[str, float] = {}
    locale_names = sorted(locales.keys())

    if reference_locale in locales and len(locales) > 1:
        ref_data = locales[reference_locale]
        for locale_name, locale_data in locales.items():
            if locale_name == reference_locale:
                continue
            issues.extend(
                scanner.compare_locale_files(ref_data, locale_data, locale_name)
            )
        coverage_raw = scanner.compute_coverage(ref_data, locales)
        coverage = {k: round(v * 100, 1) for k, v in coverage_raw.items()}

    by_type: dict[str, int] = {}
    for issue in issues:
        by_type[issue.issue_type.value] = by_type.get(issue.issue_type.value, 0) + 1
    summary = ", ".join(f"{c} {t}" for t, c in by_type.items()) or "No issues"

    result = {
        "filesScanned": len(files),
        "localesCompared": locale_names,
        "issues": [_issue_to_dict(i) for i in issues],
        "coverageByLocale": coverage,
        "summary": summary,
    }
    _emit_event(
        "complete",
        {"issues": len(issues), "filesScanned": len(files)},
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="i18n Runner")
    parser.add_argument("--project-path", required=True, help="Project root path")
    parser.add_argument(
        "--reference-locale",
        default="en",
        help="Reference locale to compare other locales against",
    )
    args = parser.parse_args()

    project_path = Path(args.project_path)
    if not project_path.exists():
        _emit("I18N_ERROR", f"Project path does not exist: {project_path}")
        sys.exit(1)

    try:
        result = run_scan(project_path, args.reference_locale)
        _emit("I18N_RESULT", result)
    except Exception as exc:  # noqa: BLE001
        _emit("I18N_ERROR", str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
