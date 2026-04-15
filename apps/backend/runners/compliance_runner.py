"""
Compliance Runner

Walks a project to collect evidence for a compliance framework (SOC2
or ISO 27001), mapping discovered artifacts to control types.

Output protocol (one JSON object per line, prefixed):
    COMPLIANCE_EVENT:{"type": "progress", "data": {"status": "..."}}
    COMPLIANCE_RESULT:{...full report dict...}
    COMPLIANCE_ERROR:<message>
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from compliance_collector.evidence_collector import (  # noqa: E402
    ComplianceFramework,
    EvidenceCollector,
    EvidenceType,
)

FRAMEWORK_ALIASES = {
    "SOC2": ComplianceFramework.SOC2,
    "ISO_27001": ComplianceFramework.ISO_27001,
    "HIPAA": ComplianceFramework.HIPAA,
    "PCI_DSS": ComplianceFramework.PCI_DSS,
    "GDPR": ComplianceFramework.GDPR,
    "CCPA": ComplianceFramework.CCPA,
}


def _emit(prefix: str, payload: Any) -> None:
    print(f"{prefix}:{json.dumps(payload, default=str)}", flush=True)


def _emit_event(event_type: str, data: dict[str, Any]) -> None:
    _emit("COMPLIANCE_EVENT", {"type": event_type, "data": data})


def _discover_files(root: Path, patterns: list[str]) -> list[Path]:
    found: list[Path] = []
    for pattern in patterns:
        for path in root.glob(pattern):
            if path.is_file():
                found.append(path)
    return found


def _evidence_entry(source: str, description: str) -> dict[str, Any]:
    return {"source": source, "description": description}


def _collect_sources(project_path: Path) -> dict[EvidenceType, list[dict[str, Any]]]:
    sources: dict[EvidenceType, list[dict[str, Any]]] = {}

    code_reviews = _discover_files(
        project_path,
        [".github/CODEOWNERS", ".github/pull_request_template.md", "CODE_REVIEW*.md"],
    )
    if code_reviews:
        sources[EvidenceType.CODE_REVIEW] = [
            _evidence_entry(str(p.relative_to(project_path)), "Code review artifact")
            for p in code_reviews
        ]

    security_scans = _discover_files(
        project_path,
        [
            "**/dependabot.yml",
            ".github/dependabot.yml",
            "**/.snyk",
            "**/trivy*.yaml",
            "**/.semgrep*",
            "SECURITY.md",
        ],
    )
    if security_scans:
        sources[EvidenceType.SECURITY_SCAN] = [
            _evidence_entry(str(p.relative_to(project_path)), "Security scan config")
            for p in security_scans
        ]

    access_logs = _discover_files(
        project_path,
        [".github/CODEOWNERS", ".github/workflows/*.yml", "docs/access*.md"],
    )
    if access_logs:
        sources[EvidenceType.ACCESS_LOG] = [
            _evidence_entry(str(p.relative_to(project_path)), "Access policy artifact")
            for p in access_logs
        ]

    change_logs = _discover_files(
        project_path,
        ["CHANGELOG.md", "CHANGES.md", "CHANGELOG.txt", "docs/changelog*.md"],
    )
    if not change_logs and (project_path / ".git").exists():
        try:
            out = subprocess.run(  # noqa: S603
                ["git", "log", "--oneline", "-20"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if out.returncode == 0 and out.stdout.strip():
                sources[EvidenceType.CHANGE_LOG] = [
                    _evidence_entry("git-log", "Recent commit history"),
                ]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    elif change_logs:
        sources[EvidenceType.CHANGE_LOG] = [
            _evidence_entry(str(p.relative_to(project_path)), "Changelog")
            for p in change_logs
        ]

    policies = _discover_files(
        project_path,
        [
            "SECURITY.md",
            "PRIVACY.md",
            "TERMS.md",
            "LICENSE",
            "docs/policies/*.md",
            "docs/security/*.md",
        ],
    )
    if policies:
        sources[EvidenceType.POLICY_DOCUMENT] = [
            _evidence_entry(str(p.relative_to(project_path)), "Policy document")
            for p in policies
        ]

    deploys = _discover_files(
        project_path,
        [
            ".github/workflows/deploy*.yml",
            ".github/workflows/release*.yml",
            ".gitlab-ci.yml",
            "Dockerfile",
        ],
    )
    if deploys:
        sources[EvidenceType.DEPLOYMENT_LOG] = [
            _evidence_entry(str(p.relative_to(project_path)), "Deployment config")
            for p in deploys
        ]

    return sources


def _normalize_evidence_type(raw: str) -> str:
    """Map backend evidence type values to frontend-expected values."""
    mapping = {
        "code_review": "code_review",
        "test_results": "test_result",
        "security_scan": "security_scan",
        "access_log": "access_log",
        "change_log": "git_log",
        "approval_record": "code_review",
        "deployment_log": "ci_cd_log",
        "policy_document": "policy_file",
        "training_record": "policy_file",
    }
    return mapping.get(raw, raw)


def _evidence_to_dict(ev: Any, framework_ui: str) -> dict[str, Any]:
    return {
        "id": ev.id,
        "evidenceType": _normalize_evidence_type(ev.evidence_type.value),
        "framework": framework_ui,
        "controlId": ev.control_id,
        "title": ev.title,
        "description": ev.description,
        "status": ev.status.value,
        "source": ev.source,
    }


def run_scan(project_path: Path, framework_ui: str) -> dict[str, Any]:
    framework = FRAMEWORK_ALIASES.get(framework_ui, ComplianceFramework.SOC2)
    _emit_event("start", {"status": f"Collecting {framework_ui} evidence..."})

    sources = _collect_sources(project_path)
    _emit_event(
        "progress",
        {"status": f"Found {sum(len(v) for v in sources.values())} evidence artifacts"},
    )

    collector = EvidenceCollector()
    report = collector.collect(framework, sources)

    result = {
        "framework": framework_ui,
        "evidence": [_evidence_to_dict(e, framework_ui) for e in report.evidence],
        "coveragePercent": round(report.coverage * 100, 1),
        "missingControls": report.missing_controls,
        "collectedCount": report.collected_count,
        "generatedAt": datetime.fromtimestamp(
            report.generated_at, tz=timezone.utc
        ).isoformat(),
        "summary": report.summary,
    }
    _emit_event(
        "complete",
        {"collected": report.collected_count, "missing": len(report.missing_controls)},
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Compliance Runner")
    parser.add_argument("--project-path", required=True, help="Project root path")
    parser.add_argument(
        "--framework",
        default="SOC2",
        choices=list(FRAMEWORK_ALIASES.keys()),
        help="Compliance framework to evaluate",
    )
    args = parser.parse_args()

    project_path = Path(args.project_path)
    if not project_path.exists():
        _emit("COMPLIANCE_ERROR", f"Project path does not exist: {project_path}")
        sys.exit(1)

    try:
        result = run_scan(project_path, args.framework)
        _emit("COMPLIANCE_RESULT", result)
    except Exception as exc:  # noqa: BLE001
        _emit("COMPLIANCE_ERROR", str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
