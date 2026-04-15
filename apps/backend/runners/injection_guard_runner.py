"""
Injection Guard Runner

Scans persisted prompt payloads under ``<project>/.workpilot/prompts/*.{txt,md,json}``
for prompt injection attempts using the ``InjectionScanner``.

For JSON files, the runner looks for a ``text`` or ``content`` field. Plain
``.txt`` and ``.md`` files are scanned as-is.

Output protocol (one JSON object per line, prefixed):
    INJECTION_GUARD_EVENT:{"type": "progress", "data": {"status": "..."}}
    INJECTION_GUARD_RESULT:{"results": [...]}
    INJECTION_GUARD_ERROR:<message>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from injection_guard import InjectionScanner, ScanResult  # noqa: E402

PROMPTS_SUBDIR = Path(".workpilot") / "prompts"
SCANNED_EXTENSIONS = {".txt", ".md", ".json"}


def _emit(prefix: str, payload: Any) -> None:
    print(f"{prefix}:{json.dumps(payload, default=str)}", flush=True)


def _emit_event(event_type: str, data: dict[str, Any]) -> None:
    _emit("INJECTION_GUARD_EVENT", {"type": event_type, "data": data})


def _result_to_dict(result: ScanResult) -> dict[str, Any]:
    return {
        "threatLevel": result.threat_level.value,
        "findings": [
            {
                "layer": f.layer,
                "description": f.description,
                "severity": f.severity,
                "confidence": f.confidence,
            }
            for f in result.findings
        ],
        "scannedText": result.scanned_text,
        "source": result.source,
        "decodedContent": result.decoded_content,
        "timestamp": result.timestamp,
    }


def _discover_prompts(project_path: Path) -> list[Path]:
    prompts_dir = project_path / PROMPTS_SUBDIR
    if not prompts_dir.exists():
        return []
    return sorted(
        p
        for p in prompts_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in SCANNED_EXTENSIONS
    )


def _extract_text(file_path: Path) -> str:
    raw = file_path.read_text(encoding="utf-8", errors="ignore")
    if file_path.suffix.lower() == ".json":
        try:
            payload = json.loads(raw)
        except ValueError:
            return raw
        if isinstance(payload, dict):
            for key in ("text", "content", "prompt", "input"):
                value = payload.get(key)
                if isinstance(value, str):
                    return value
            return json.dumps(payload)
        if isinstance(payload, list):
            return "\n".join(str(item) for item in payload)
        return raw
    return raw


def run_scan(project_path: Path) -> dict[str, Any]:
    _emit_event("start", {"status": "Discovering prompt payloads..."})
    prompt_files = _discover_prompts(project_path)

    if not prompt_files:
        _emit_event("complete", {"status": "No prompts found", "results": 0})
        return {"results": []}

    _emit_event(
        "progress",
        {"status": f"Scanning {len(prompt_files)} prompt(s)..."},
    )

    scanner = InjectionScanner()
    results: list[dict[str, Any]] = []
    for file_path in prompt_files:
        try:
            text = _extract_text(file_path)
        except OSError as exc:
            _emit_event("progress", {"status": f"Skipped {file_path.name}: {exc}"})
            continue

        scan = scanner.scan(
            text,
            source=str(file_path.relative_to(project_path)),
        )
        results.append(_result_to_dict(scan))

    _emit_event("complete", {"results": len(results)})
    return {"results": results}


def main() -> None:
    parser = argparse.ArgumentParser(description="Injection Guard Runner")
    parser.add_argument("--project-path", required=True, help="Project root path")
    args = parser.parse_args()

    project_path = Path(args.project_path)
    if not project_path.exists():
        _emit(
            "INJECTION_GUARD_ERROR",
            f"Project path does not exist: {project_path}",
        )
        sys.exit(1)

    try:
        result = run_scan(project_path)
        _emit("INJECTION_GUARD_RESULT", result)
    except Exception as exc:  # noqa: BLE001
        _emit("INJECTION_GUARD_ERROR", str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
