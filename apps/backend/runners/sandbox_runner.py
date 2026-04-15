"""
Sandbox Runner

Produces a dry-run simulation report for a project by diffing the current
working tree against ``HEAD`` via ``git diff``. The result is a
``SimulationResult`` with no executed steps and a list of predicted file
diffs, letting users preview uncommitted changes before they commit.

Output protocol (one JSON object per line, prefixed):
    SANDBOX_EVENT:{"type": "progress", "data": {"status": "..."}}
    SANDBOX_RESULT:{"result": {...}}
    SANDBOX_ERROR:<message>
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _emit(prefix: str, payload: Any) -> None:
    print(f"{prefix}:{json.dumps(payload, default=str)}", flush=True)


def _emit_event(event_type: str, data: dict[str, Any]) -> None:
    _emit("SANDBOX_EVENT", {"type": event_type, "data": data})


def _run_git(project_path: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(project_path),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def _parse_diff(diff_text: str) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    current_hunk: dict[str, Any] | None = None
    pending_lines: list[str] = []

    def flush_hunk() -> None:
        nonlocal current_hunk, pending_lines
        if current_hunk is not None and current is not None:
            current_hunk["content"] = "\n".join(pending_lines)
            current["hunks"].append(current_hunk)
        current_hunk = None
        pending_lines = []

    def flush_file() -> None:
        nonlocal current
        flush_hunk()
        if current is not None:
            files.append(current)
        current = None

    lines = diff_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("diff --git"):
            flush_file()
            match = re.search(r" a/(.+) b/(.+)$", line)
            path = match.group(2) if match else ""
            current = {
                "filePath": path,
                "changeType": "modified",
                "additions": 0,
                "deletions": 0,
                "hunks": [],
            }
        elif current is not None and line.startswith("new file"):
            current["changeType"] = "added"
        elif current is not None and line.startswith("deleted file"):
            current["changeType"] = "deleted"
        elif current is not None and line.startswith("rename "):
            current["changeType"] = "renamed"
        elif line.startswith("@@"):
            flush_hunk()
            m = HUNK_HEADER.match(line)
            if m and current is not None:
                current_hunk = {
                    "oldStart": int(m.group(1)),
                    "oldCount": int(m.group(2) or 1),
                    "newStart": int(m.group(3)),
                    "newCount": int(m.group(4) or 1),
                    "content": "",
                }
                pending_lines = []
        elif current_hunk is not None and current is not None:
            pending_lines.append(line)
            if line.startswith("+") and not line.startswith("+++"):
                current["additions"] += 1
            elif line.startswith("-") and not line.startswith("---"):
                current["deletions"] += 1
        i += 1

    flush_file()
    return files


def run_scan(project_path: Path, spec_id: str) -> dict[str, Any]:
    _emit_event("start", {"status": "Checking git status..."})

    if not (project_path / ".git").exists():
        raise RuntimeError("Project is not a git repository")

    start = time.time()
    _emit_event("progress", {"status": "Running git diff against HEAD..."})
    diff_text = _run_git(project_path, "diff", "HEAD")
    diffs = _parse_diff(diff_text)

    total_additions = sum(d["additions"] for d in diffs)
    total_deletions = sum(d["deletions"] for d in diffs)
    duration_ms = int((time.time() - start) * 1000)

    result = {
        "id": str(uuid.uuid4()),
        "specId": spec_id,
        "phase": "awaiting_approval" if diffs else "complete",
        "steps": [],
        "diffs": diffs,
        "totalTokensUsed": 0,
        "estimatedCostUsd": 0.0,
        "estimatedRealCostUsd": 0.0,
        "durationMs": duration_ms,
        "successCount": 0,
        "warningCount": 0,
        "errorCount": 0,
        "createdAt": datetime.now(tz=timezone.utc).isoformat(),
    }

    _emit_event(
        "complete",
        {
            "files": len(diffs),
            "additions": total_additions,
            "deletions": total_deletions,
        },
    )
    return {"result": result}


def main() -> None:
    parser = argparse.ArgumentParser(description="Sandbox Runner")
    parser.add_argument("--project-path", required=True, help="Project root path")
    parser.add_argument("--spec-id", default="dry-run", help="Spec identifier label")
    args = parser.parse_args()

    project_path = Path(args.project_path)
    if not project_path.exists():
        _emit("SANDBOX_ERROR", f"Project path does not exist: {project_path}")
        sys.exit(1)

    try:
        result = run_scan(project_path, args.spec_id)
        _emit("SANDBOX_RESULT", result)
    except Exception as exc:  # noqa: BLE001
        _emit("SANDBOX_ERROR", str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
