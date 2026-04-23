"""Regression tests for the BaseScanner / BaseScanReport migrations.

Covers the three agents that now sit on top of ``agents.scanner_base``:

- ``accessibility_agent.A11yReport`` — keeps its ``violations`` alias.
- ``i18n_agent.I18nReport`` — keeps ``issues`` + ``error_count`` aliases,
  overrides ``summary`` to group by issue type.
- ``flaky_test_detective.FlakyReport`` — keeps ``flaky_tests`` alias,
  uses a derived ``severity`` on the contained ``FlakyTest`` so the
  shared ``blocking_count`` / ``passed`` plumbing works without forcing
  a per-file scanner shape.

We specifically lock the back-compat aliases (same list object, not a
copy) so existing consumers that mutate them keep working.
"""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[2] / "apps" / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from accessibility_agent.accessibility_scanner import (  # noqa: E402
    A11yReport,
    A11ySeverity,
    AccessibilityScanner,
    WcagLevel,
)
from flaky_test_detective.flaky_analyzer import (  # noqa: E402
    FlakyAnalyzer,
    FlakyCause,
    FlakyConfidence,
    FlakyReport,
    FlakyTest,
    TestRun,
)
from i18n_agent.i18n_scanner import (  # noqa: E402
    I18nIssue,
    I18nIssueType,
    I18nReport,
    I18nScanner,
    I18nSeverity,
)

# ---------------------------------------------------------------------------
# AccessibilityScanner — already migrated in commit #1, re-tested here so
# the migration behaviour is locked alongside the i18n/flaky ones.
# ---------------------------------------------------------------------------


def test_a11y_violations_alias_is_same_object() -> None:
    report = A11yReport()
    assert report.violations is report.findings


def test_a11y_critical_count_tracks_blocking_count() -> None:
    report = A11yReport()
    report.findings.append(
        A11yViolation_factory(severity=A11ySeverity.CRITICAL),
    )
    report.findings.append(
        A11yViolation_factory(severity=A11ySeverity.SERIOUS),
    )
    assert report.critical_count == 1  # only CRITICAL blocks
    assert report.blocking_count == 1


def A11yViolation_factory(
    severity: A11ySeverity = A11ySeverity.MODERATE,
) -> object:
    from accessibility_agent.accessibility_scanner import A11yViolation

    return A11yViolation(
        rule_id="test",
        description="x",
        severity=severity,
        wcag_level=WcagLevel.AA,
    )


def test_a11y_scan_file_aggregation() -> None:
    scanner = AccessibilityScanner()
    report = scanner.scan_files({
        "a.html": "<img src='x.png'>",
        "b.html": "<html><head></head></html>",
    })
    # img-missing-alt is CRITICAL; html-missing-lang is SERIOUS.
    assert report.files_scanned == 2
    assert len(report.findings) >= 2
    # Both the alias and the base property reflect the same data.
    assert len(report.violations) == len(report.findings)


# ---------------------------------------------------------------------------
# I18nScanner.
# ---------------------------------------------------------------------------


def test_i18n_issues_alias_is_same_object() -> None:
    report = I18nReport()
    assert report.issues is report.findings


def test_i18n_scan_file_returns_report() -> None:
    scanner = I18nScanner()
    report = scanner.scan_file("App.tsx", "<button>Click me</button>")
    assert isinstance(report, I18nReport)
    assert len(report.findings) >= 1
    # Issues are warnings by default — not blocking.
    assert report.passed is True
    assert report.error_count == 0


def test_i18n_error_count_counts_only_errors() -> None:
    report = I18nReport()
    report.findings.extend(
        [
            I18nIssue(
                issue_type=I18nIssueType.MISSING_KEY,
                severity=I18nSeverity.ERROR,
                file="locale/fr.json",
            ),
            I18nIssue(
                issue_type=I18nIssueType.HARDCODED_STRING,
                severity=I18nSeverity.WARNING,
                file="App.tsx",
            ),
        ]
    )
    assert report.error_count == 1
    assert report.blocking_count == 1
    assert report.passed is False


def test_i18n_summary_groups_by_type_stably() -> None:
    scanner = I18nScanner()
    # Two hardcoded strings; single issue type — summary must be stable
    # regardless of file iteration order.
    first = scanner.scan_files(
        {
            "a.tsx": "<button>Hello World</button>",
            "b.tsx": "<span>Submit Form</span>",
        }
    ).summary
    second = scanner.scan_files(
        {
            "b.tsx": "<span>Submit Form</span>",
            "a.tsx": "<button>Hello World</button>",
        }
    ).summary
    assert first == second
    assert "hardcoded_string" in first


def test_i18n_scan_files_swallows_per_file_errors() -> None:
    """Inherited from BaseScanner: a bad file must not abort the whole run."""

    class _Boomer(I18nScanner):
        def scan_file(self, file_path, content):  # type: ignore[override]
            if "EXPLODE" in content:
                raise RuntimeError("boom")
            return super().scan_file(file_path, content)

    report = _Boomer().scan_files(
        {"ok.tsx": "<button>Hi</button>", "broken.tsx": "EXPLODE"}
    )
    # Broken file isn't counted; the other one still contributes.
    assert report.files_scanned == 1


# ---------------------------------------------------------------------------
# FlakyAnalyzer — analyser, not per-file scanner. Report rides on the
# same base via the HasSeverity protocol.
# ---------------------------------------------------------------------------


def test_flaky_tests_alias_is_same_object() -> None:
    report = FlakyReport()
    assert report.flaky_tests is report.findings


def test_flaky_test_exposes_severity_and_file_for_base_protocol() -> None:
    ft = FlakyTest(
        test_name="test_x",
        file_path="tests/foo.py",
        confidence=FlakyConfidence.HIGH,
    )
    assert ft.file == "tests/foo.py"
    assert ft.severity == "high"


def test_flaky_severity_maps_from_confidence() -> None:
    assert FlakyTest(test_name="a", confidence=FlakyConfidence.HIGH).severity == "high"
    assert (
        FlakyTest(test_name="a", confidence=FlakyConfidence.MEDIUM).severity
        == "medium"
    )
    assert FlakyTest(test_name="a", confidence=FlakyConfidence.LOW).severity == "low"


def _make_runs(name: str, pattern: list[bool], err: str = "") -> list[TestRun]:
    return [TestRun(name, passed=p, error_message=err if not p else "") for p in pattern]


def test_flaky_analyze_builds_typed_report() -> None:
    analyzer = FlakyAnalyzer()
    runs = _make_runs(
        "test_net", [True, True, False, True, False, True], err="connection refused"
    )
    report = analyzer.analyze(runs)
    assert isinstance(report, FlakyReport)
    assert report.total_tests_analysed == 1
    assert report.total_runs_analysed == 6
    # flaky_tests alias points at the same list the base maintains.
    assert report.flaky_tests is report.findings
    assert len(report.flaky_tests) == 1
    ft = report.flaky_tests[0]
    assert ft.test_name == "test_net"
    # Network cause classified correctly.
    assert ft.probable_cause == FlakyCause.NETWORK


def test_flaky_summary_groups_by_cause() -> None:
    analyzer = FlakyAnalyzer()
    runs = (
        _make_runs(
            "t_net",
            [True, True, False, True, False],
            err="ECONNREFUSED to host",
        )
        + _make_runs(
            "t_random",
            [True, True, False, True, False],
            err="Math.random returned unexpected seed",
        )
    )
    report = analyzer.analyze(runs)
    assert report.flaky_count == 2
    # Summary mentions both causes; ordering is stable (alphabetical).
    assert "network" in report.summary
    assert "randomness" in report.summary


def test_flaky_empty_summary() -> None:
    report = FlakyReport()
    assert report.summary == "No flaky tests detected"
    assert report.passed is True
    assert report.blocking_count == 0
