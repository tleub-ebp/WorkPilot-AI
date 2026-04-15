"""
Git Surgeon Runner

Analyses git history for large blobs, sensitive data, and messy commits,
and returns a surgery plan.

Output protocol (one JSON object per line, prefixed):
    GIT_SURGEON_EVENT:{"type": "progress", "data": {"status": "..."}}
    GIT_SURGEON_RESULT:{...plan dict...}
    GIT_SURGEON_ERROR:<message>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from git_surgeon.history_analyzer import (  # noqa: E402
    HistoryAnalyzer,
    SurgeryPlan,
)


def _emit(prefix: str, payload: Any) -> None:
    print(f"{prefix}:{json.dumps(payload, default=str)}", flush=True)


def _emit_event(event_type: str, data: dict[str, Any]) -> None:
    _emit("GIT_SURGEON_EVENT", {"type": event_type, "data": data})


def _plan_to_dict(plan: SurgeryPlan) -> dict[str, Any]:
    return {
        "issues": [
            {
                "issueType": issue.issue_type.value,
                "severity": issue.severity,
                "description": issue.description,
                "commitSha": issue.commit_sha,
                "filePath": issue.file_path,
                "sizeBytes": issue.size_bytes,
                "suggestedAction": issue.suggested_action.value,
            }
            for issue in plan.issues
        ],
        "actions": [
            {"action": action.value, "description": description}
            for action, description in plan.actions
        ],
        "estimatedSizeSavingsMb": plan.estimated_size_savings_mb,
        "requiresForcePush": plan.requires_force_push,
        "summary": plan.summary,
    }


def run_scan(project_path: Path, max_commits: int) -> dict[str, Any]:
    if not (project_path / ".git").exists():
        return {
            "issues": [],
            "actions": [],
            "estimatedSizeSavingsMb": 0.0,
            "requiresForcePush": False,
            "summary": "Project is not a git repository",
        }

    _emit_event("start", {"status": "Analyzing git history..."})
    analyzer = HistoryAnalyzer(repo_root=project_path)
    plan = analyzer.analyze(max_commits=max_commits)
    _emit_event(
        "complete",
        {"issues": len(plan.issues), "savingsMb": plan.estimated_size_savings_mb},
    )
    return _plan_to_dict(plan)


def main() -> None:
    parser = argparse.ArgumentParser(description="Git Surgeon Runner")
    parser.add_argument("--project-path", required=True, help="Project root path")
    parser.add_argument(
        "--max-commits",
        type=int,
        default=500,
        help="Maximum commits to analyse",
    )
    args = parser.parse_args()

    project_path = Path(args.project_path)
    if not project_path.exists():
        _emit("GIT_SURGEON_ERROR", f"Project path does not exist: {project_path}")
        sys.exit(1)

    try:
        result = run_scan(project_path, args.max_commits)
        _emit("GIT_SURGEON_RESULT", result)
    except Exception as exc:  # noqa: BLE001
        _emit("GIT_SURGEON_ERROR", str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
