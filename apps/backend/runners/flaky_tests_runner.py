"""
Flaky Tests Runner

Discovers JUnit-format XML test reports in a project, builds a TestRun
history, and runs the FlakyAnalyzer to identify flaky tests.

Output protocol (one JSON object per line, prefixed):
    FLAKY_EVENT:{"type": "progress", "data": {"status": "..."}}
    FLAKY_RESULT:{...full report dict...}
    FLAKY_ERROR:<message>
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from flaky_test_detective.flaky_analyzer import (  # noqa: E402
    FlakyAnalyzer,
    TestRun,
)

REPORT_GLOBS = [
    "**/test-results/**/*.xml",
    "**/junit*.xml",
    "**/TEST-*.xml",
    "**/*.junit.xml",
    "**/build/test-results/**/*.xml",
    "**/target/surefire-reports/*.xml",
    "**/reports/junit/*.xml",
]
DEFAULT_IGNORES = {"node_modules", ".git", ".venv", "venv", "__pycache__"}


def _emit(prefix: str, payload: Any) -> None:
    print(f"{prefix}:{json.dumps(payload, default=str)}", flush=True)


def _emit_event(event_type: str, data: dict[str, Any]) -> None:
    _emit("FLAKY_EVENT", {"type": event_type, "data": data})


def _discover_reports(root: Path) -> list[Path]:
    found: set[Path] = set()
    for pattern in REPORT_GLOBS:
        for path in root.glob(pattern):
            if path.is_file() and not any(
                part in DEFAULT_IGNORES for part in path.parts
            ):
                found.add(path)
    return sorted(found)


def _testcase_full_name(case: ET.Element) -> str:
    name = case.attrib.get("name", "")
    classname = case.attrib.get("classname", "")
    return f"{classname}::{name}" if classname else name


def _testcase_duration(case: ET.Element) -> float:
    try:
        return float(case.attrib.get("time", "0")) * 1000
    except ValueError:
        return 0.0


def _testcase_error_message(case: ET.Element) -> tuple[bool, str]:
    """Return (passed, error_message). Skipped tests yield (True, "")."""
    failure = case.find("failure")
    error = case.find("error")
    if failure is not None:
        return False, failure.attrib.get("message", "") or (failure.text or "")
    if error is not None:
        return False, error.attrib.get("message", "") or (error.text or "")
    return True, ""


def _parse_junit_file(path: Path, run_id: str) -> list[TestRun]:
    runs: list[TestRun] = []
    try:
        tree = ET.parse(path)  # noqa: S314
    except (ET.ParseError, OSError):
        return runs

    root = tree.getroot()
    timestamp = path.stat().st_mtime

    for case in root.iter("testcase"):
        if case.find("skipped") is not None:
            continue
        passed, error_message = _testcase_error_message(case)
        runs.append(
            TestRun(
                test_name=_testcase_full_name(case),
                passed=passed,
                duration_ms=_testcase_duration(case),
                error_message=error_message[:500],
                run_id=run_id,
                timestamp=timestamp,
            )
        )
    return runs


def _flaky_test_to_dict(test: Any) -> dict[str, Any]:
    return {
        "testName": test.test_name,
        "totalRuns": test.total_runs,
        "failures": test.failures,
        "flakinessRate": test.flakiness_rate,
        "probableCause": test.probable_cause.value,
        "confidence": test.confidence.value,
        "errorPatterns": test.error_patterns,
        "suggestedFix": test.suggested_fix,
    }


def run_scan(project_path: Path, threshold: float, min_runs: int) -> dict[str, Any]:
    _emit_event("start", {"status": "Discovering test reports..."})
    report_files = _discover_reports(project_path)
    _emit_event(
        "progress",
        {"status": f"Parsing {len(report_files)} JUnit reports..."},
    )

    runs: list[TestRun] = []
    for idx, file in enumerate(report_files):
        runs.extend(_parse_junit_file(file, run_id=f"{file.name}-{idx}"))

    if not runs:
        _emit_event("complete", {"flakyCount": 0, "totalTests": 0})
        return {
            "totalTests": 0,
            "flakyCount": 0,
            "flakyTests": [],
            "summary": "No JUnit reports found. Configure your test runner to emit XML reports.",
        }

    _emit_event(
        "progress",
        {"status": f"Analysing {len(runs)} test runs..."},
    )
    analyzer = FlakyAnalyzer(flakiness_threshold=threshold, min_runs=min_runs)
    report = analyzer.analyze(runs)

    result = {
        "totalTests": report.total_tests_analysed,
        "flakyCount": report.flaky_count,
        "flakyTests": [_flaky_test_to_dict(t) for t in report.flaky_tests],
        "summary": report.summary,
    }
    _emit_event(
        "complete",
        {"flakyCount": report.flaky_count, "totalTests": report.total_tests_analysed},
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Flaky Tests Runner")
    parser.add_argument("--project-path", required=True, help="Project root path")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.05,
        help="Flakiness rate threshold (0.0-1.0)",
    )
    parser.add_argument(
        "--min-runs",
        type=int,
        default=2,
        help="Minimum runs needed to assess flakiness",
    )
    args = parser.parse_args()

    project_path = Path(args.project_path)
    if not project_path.exists():
        _emit("FLAKY_ERROR", f"Project path does not exist: {project_path}")
        sys.exit(1)

    try:
        result = run_scan(project_path, args.threshold, args.min_runs)
        _emit("FLAKY_RESULT", result)
    except Exception as exc:  # noqa: BLE001
        _emit("FLAKY_ERROR", str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
