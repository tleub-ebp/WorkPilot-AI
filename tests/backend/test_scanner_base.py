"""Tests for ``agents/scanner_base.py``.

The scanner base is the abstraction that the ``accessibility_agent``
migration now sits on top of. These tests lock down its contract so
future migrations can rely on the behavior.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[2] / "apps" / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from agents.scanner_base import (  # noqa: E402
    BaseScanner,
    BaseScanReport,
)


@dataclass
class _Finding:
    severity: str
    file: str
    message: str = ""


@dataclass
class _Report(BaseScanReport[_Finding]):
    pass


class _Scanner(BaseScanner[_Finding, _Report]):
    report_cls = _Report

    def scan_file(self, file_path: str, content: str) -> _Report:
        report = _Report(files_scanned=1)
        if "BAD" in content:
            report.findings.append(_Finding(severity="critical", file=file_path))
        if "WARN" in content:
            report.findings.append(_Finding(severity="medium", file=file_path))
        return report


def test_scan_files_aggregates_across_files() -> None:
    scanner = _Scanner()
    report = scanner.scan_files({
        "a.py": "BAD code",
        "b.py": "WARN something",
        "c.py": "nothing wrong here",
    })
    assert report.files_scanned == 3
    assert len(report.findings) == 2
    assert report.count_by_severity == {"critical": 1, "medium": 1}


def test_passed_reflects_blocking_severities() -> None:
    scanner = _Scanner()
    report = scanner.scan_files({"a.py": "WARN only"})
    assert report.passed is True  # medium is not blocking by default

    report = scanner.scan_files({"a.py": "BAD stuff"})
    assert report.passed is False  # critical is blocking
    assert report.blocking_count == 1


def test_summary_is_stable_across_runs() -> None:
    """Sorting the summary keeps snapshot tests from flapping."""
    scanner = _Scanner()
    first = scanner.scan_files({"a.py": "BAD", "b.py": "WARN"}).summary
    second = scanner.scan_files({"b.py": "WARN", "a.py": "BAD"}).summary
    assert first == second
    assert "critical" in first
    assert "medium" in first


def test_scan_files_swallows_per_file_errors() -> None:
    """One bad file must not abort the whole run."""

    @dataclass
    class _ExplodingReport(BaseScanReport[_Finding]):
        pass

    class _ExplodingScanner(BaseScanner[_Finding, _ExplodingReport]):
        report_cls = _ExplodingReport

        def scan_file(self, file_path: str, content: str) -> _ExplodingReport:
            if "EXPLODE" in content:
                raise RuntimeError("boom")
            report = _ExplodingReport(files_scanned=1)
            if "BAD" in content:
                report.findings.append(_Finding(severity="critical", file=file_path))
            return report

    report = _ExplodingScanner().scan_files({
        "ok.py": "BAD",
        "broken.py": "EXPLODE",
        "also_ok.py": "",
    })
    # Broken file is not counted; the other two still contribute.
    assert report.files_scanned == 2
    assert len(report.findings) == 1


def test_empty_report_has_no_findings_summary() -> None:
    report: _Report = _Scanner().scan_files({})
    assert report.findings == []
    assert report.files_scanned == 0
    assert report.summary == "No findings"
    assert report.passed is True
