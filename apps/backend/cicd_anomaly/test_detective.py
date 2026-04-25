"""Tests for the CI/CD Anomaly Detective."""

from __future__ import annotations

import pytest
from cicd_anomaly import (
    AnomalyDetective,
    AnomalyKind,
    Severity,
)


class TestSingleLogScan:
    def test_empty_log_returns_no_signals(self) -> None:
        assert AnomalyDetective().scan("") == []

    def test_none_log_does_not_crash(self) -> None:
        assert AnomalyDetective().scan(None) == []  # type: ignore[arg-type]

    def test_clean_log_returns_no_signals(self) -> None:
        log = "All tests passed.\nBuild successful.\n"
        assert AnomalyDetective().scan(log) == []

    def test_timeout_pattern_detected(self) -> None:
        log = "Step 1: Running...\nError: timeout after 600s\n"
        signals = AnomalyDetective().scan(log)
        assert len(signals) == 1
        assert signals[0].kind == AnomalyKind.TIMEOUT
        assert signals[0].severity == Severity.HIGH
        assert "timeout" in signals[0].matching_line.lower()
        assert "increase" in signals[0].suggested_fix.lower()

    def test_oom_critical(self) -> None:
        log = "running tests\nKilled (OOM)\n"
        signals = AnomalyDetective().scan(log)
        assert any(s.kind == AnomalyKind.OOM for s in signals)
        assert all(
            s.severity == Severity.CRITICAL
            for s in signals
            if s.kind == AnomalyKind.OOM
        )

    def test_javascript_oom_specific_message(self) -> None:
        log = "JavaScript heap out of memory\n"
        signals = AnomalyDetective().scan(log)
        assert any("NODE_OPTIONS" in s.suggested_fix for s in signals)

    def test_dependency_conflict_detected(self) -> None:
        log = "npm ERR! ERESOLVE could not resolve\n"
        signals = AnomalyDetective().scan(log)
        assert any(s.kind == AnomalyKind.DEPENDENCY_CONFLICT for s in signals)

    def test_network_failure_detected(self) -> None:
        log = "fatal: unable to access 'https://github.com/...': Could not resolve host: github.com\n"
        signals = AnomalyDetective().scan(log)
        assert any(s.kind == AnomalyKind.NETWORK_FAILURE for s in signals)

    def test_disk_full_critical(self) -> None:
        log = "tar: Cannot write: No space left on device\n"
        signals = AnomalyDetective().scan(log)
        kinds = {s.kind for s in signals}
        assert AnomalyKind.DISK_FULL in kinds
        disk_sigs = [s for s in signals if s.kind == AnomalyKind.DISK_FULL]
        assert all(s.severity == Severity.CRITICAL for s in disk_sigs)

    def test_rate_limited_detected(self) -> None:
        log = "HTTP 429: Too Many Requests\n"
        signals = AnomalyDetective().scan(log)
        assert any(s.kind == AnomalyKind.RATE_LIMITED for s in signals)

    def test_auth_failure_detected(self) -> None:
        log = "remote: HTTP 403: Forbidden\n"
        signals = AnomalyDetective().scan(log)
        assert any(s.kind == AnomalyKind.AUTH_FAILURE for s in signals)

    def test_docker_daemon_flake(self) -> None:
        log = "Cannot connect to the Docker daemon\n"
        signals = AnomalyDetective().scan(log)
        assert any(s.kind == AnomalyKind.INFRASTRUCTURE_FLAKE for s in signals)

    def test_case_insensitive_match(self) -> None:
        log = "ERROR: Connection Refused\n"
        signals = AnomalyDetective().scan(log)
        assert any(s.kind == AnomalyKind.NETWORK_FAILURE for s in signals)

    def test_line_numbers_are_one_based(self) -> None:
        log = "fine\nfine\nKilled (OOM)\n"
        signals = AnomalyDetective().scan(log)
        oom = [s for s in signals if s.kind == AnomalyKind.OOM][0]
        assert oom.line_number == 3

    def test_log_label_propagated(self) -> None:
        signals = AnomalyDetective().scan(
            "no space left on device", log_label="build-42"
        )
        assert all(s.log_label == "build-42" for s in signals)

    def test_oversize_log_truncated(self) -> None:
        # 9 MB of 'safe' lines + a poison line at the end. Truncation
        # should occur and we shouldn't crash.
        log = ("ok\n" * (3_000_000)) + "OOM!\n"
        # The poison line is past 8MB — should be truncated and missed.
        signals = AnomalyDetective().scan(log)
        assert all(s.kind != AnomalyKind.OOM for s in signals)


class TestRecurringDetection:
    def test_recurring_kind_flagged(self) -> None:
        # Same OOM in 3 distinct builds = recurring.
        d = AnomalyDetective()
        report = d.analyse(
            [
                ("build-1", "OOM-killed\n"),
                ("build-2", "OOM-killed\n"),
                ("build-3", "OOM-killed\n"),
            ]
        )
        assert AnomalyKind.OOM.value in report.recurring_kinds

    def test_one_off_signal_not_recurring(self) -> None:
        d = AnomalyDetective()
        report = d.analyse(
            [
                ("build-1", "OOM-killed\n"),
                ("build-2", "all good\n"),
                ("build-3", "all good\n"),
            ]
        )
        assert AnomalyKind.OOM.value not in report.recurring_kinds

    def test_single_log_string_input(self) -> None:
        d = AnomalyDetective()
        report = d.analyse("OOM-killed\n")
        assert report.summary["samples"] == 1
        assert report.summary["total_signals"] >= 1

    def test_summary_counts_by_kind_and_severity(self) -> None:
        d = AnomalyDetective()
        report = d.analyse(
            [
                ("a", "OOM-killed\nNo space left on device\n"),
                ("b", "OOM-killed\n"),
            ]
        )
        assert report.summary["samples"] == 2
        assert report.summary["by_kind"]["oom"] == 2
        assert report.summary["by_kind"]["disk_full"] == 1
        assert report.summary["by_severity"]["critical"] == 3

    def test_recurring_recommendations_prefixed(self) -> None:
        d = AnomalyDetective()
        report = d.analyse(
            [
                ("build-1", "OOM-killed\n"),
                ("build-2", "OOM-killed\n"),
            ]
        )
        # Aggregated recs: at least one starts with [recurring]
        assert any(r.startswith("[recurring]") for r in report.fix_recommendations)


class TestReport:
    def test_has_critical_true_when_any_critical(self) -> None:
        report = AnomalyDetective().analyse("OOM-killed\n")
        assert report.has_critical is True

    def test_has_critical_false_when_none(self) -> None:
        report = AnomalyDetective().analyse("HTTP 429: too many requests\n")
        assert report.has_critical is False

    def test_to_dict_serialisable(self) -> None:
        import json

        report = AnomalyDetective().analyse("OOM-killed\n")
        decoded = json.loads(json.dumps(report.to_dict()))
        assert decoded["has_critical"] is True
        assert isinstance(decoded["signals"], list)

    def test_no_recommendations_when_clean(self) -> None:
        report = AnomalyDetective().analyse("everything is fine\n")
        assert report.fix_recommendations == []

    def test_dedup_within_kind_per_line(self) -> None:
        # The disk-full pattern matches several aliases — ensure we don't
        # emit two signals from the same line.
        log = "ENOSPC: no space left on device\n"
        signals = AnomalyDetective().scan(log)
        disk_sigs = [s for s in signals if s.kind == AnomalyKind.DISK_FULL]
        assert len(disk_sigs) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
