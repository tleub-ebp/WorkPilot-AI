"""Tests for the Architecture Drift Detector."""

from __future__ import annotations

from pathlib import Path

import pytest
from architecture.models import ArchitectureReport, ArchitectureViolation
from architecture_drift import DriftDetector, DriftSeverity, detect_drift


def _violation(
    file: str,
    type_: str = "layer_violation",
    severity: str = "error",
    target: str = "forbidden_module",
    rule: str = "R-1",
    description: str = "imports a forbidden layer",
) -> ArchitectureViolation:
    return ArchitectureViolation(
        type=type_,
        severity=severity,
        file=file,
        line=10,
        import_target=target,
        rule=rule,
        description=description,
    )


def _report(
    violations: list[ArchitectureViolation] | None = None,
    warnings: list[ArchitectureViolation] | None = None,
) -> ArchitectureReport:
    return ArchitectureReport(
        violations=violations or [],
        warnings=warnings or [],
        passed=not (violations or []),
    )


class TestBaselinePersistence:
    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        detector = DriftDetector(project_dir=tmp_path)
        report = _report(
            violations=[_violation("a.py")],
            warnings=[_violation("b.py", severity="warning")],
        )
        path = detector.save_baseline(report)
        assert path.exists()

        loaded = detector.load_baseline()
        assert loaded is not None
        keys, deltas = loaded
        assert len(keys) == 2
        assert all(isinstance(d.fingerprint, str) for d in deltas.values())

    def test_load_returns_none_when_no_baseline(self, tmp_path: Path) -> None:
        detector = DriftDetector(project_dir=tmp_path)
        assert detector.load_baseline() is None

    def test_baseline_path_requires_project_dir(self) -> None:
        with pytest.raises(ValueError):
            DriftDetector(project_dir=None).baseline_path()

    def test_corrupt_baseline_returns_none(self, tmp_path: Path) -> None:
        detector = DriftDetector(project_dir=tmp_path)
        path = detector.baseline_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{ not json", encoding="utf-8")
        assert detector.load_baseline() is None


class TestDriftDetection:
    def test_no_baseline_means_no_drift_severity(self, tmp_path: Path) -> None:
        detector = DriftDetector(project_dir=tmp_path)
        current = _report(violations=[_violation("a.py")])
        report = detector.compare(current)
        assert report.has_baseline is False
        assert report.severity == DriftSeverity.NONE
        # Without a baseline, current violations are reported as "persistent"
        # so the user can see what's there, but it's not called drift.
        assert len(report.persistent_violations) == 1
        assert len(report.new_violations) == 0

    def test_no_change_means_no_drift(self, tmp_path: Path) -> None:
        detector = DriftDetector(project_dir=tmp_path)
        baseline = _report(violations=[_violation("a.py")])
        detector.save_baseline(baseline)
        report = detector.compare(_report(violations=[_violation("a.py")]))
        assert report.severity == DriftSeverity.NONE
        assert len(report.new_violations) == 0
        assert len(report.persistent_violations) == 1

    def test_one_new_warning_is_low_severity(self, tmp_path: Path) -> None:
        detector = DriftDetector(project_dir=tmp_path)
        detector.save_baseline(_report())
        current = _report(warnings=[_violation("a.py", severity="warning")])
        report = detector.compare(current)
        assert report.severity == DriftSeverity.LOW
        assert len(report.new_violations) == 1

    def test_one_new_error_is_medium(self, tmp_path: Path) -> None:
        detector = DriftDetector(project_dir=tmp_path)
        detector.save_baseline(_report())
        report = detector.compare(_report(violations=[_violation("a.py")]))
        assert report.severity == DriftSeverity.MEDIUM

    def test_three_new_errors_is_high(self, tmp_path: Path) -> None:
        detector = DriftDetector(project_dir=tmp_path)
        detector.save_baseline(_report())
        violations = [_violation(f"f{i}.py", target=f"mod_{i}") for i in range(3)]
        report = detector.compare(_report(violations=violations))
        assert report.severity == DriftSeverity.HIGH

    def test_ten_new_violations_is_critical(self, tmp_path: Path) -> None:
        detector = DriftDetector(project_dir=tmp_path)
        detector.save_baseline(_report())
        warnings = [
            _violation(f"f{i}.py", target=f"m{i}", severity="warning")
            for i in range(10)
        ]
        report = detector.compare(_report(warnings=warnings))
        assert report.severity == DriftSeverity.CRITICAL

    def test_resolved_violations_are_reported(self, tmp_path: Path) -> None:
        detector = DriftDetector(project_dir=tmp_path)
        baseline = _report(
            violations=[_violation("a.py"), _violation("b.py", target="other")]
        )
        detector.save_baseline(baseline)
        current = _report(violations=[_violation("a.py")])
        report = detector.compare(current)
        assert len(report.resolved_violations) == 1
        assert report.resolved_violations[0].file == "b.py"
        assert report.severity == DriftSeverity.NONE  # No new ones, only resolutions

    def test_line_shifts_do_not_create_false_drift(self, tmp_path: Path) -> None:
        detector = DriftDetector(project_dir=tmp_path)
        baseline = _report(violations=[_violation("a.py")])
        detector.save_baseline(baseline)
        # Same violation, just on a different line — fingerprint must match.
        moved = _violation("a.py")
        moved.line = 999
        report = detector.compare(_report(violations=[moved]))
        assert len(report.new_violations) == 0
        assert len(report.persistent_violations) == 1

    def test_summary_counts_errors_and_warnings_separately(
        self, tmp_path: Path
    ) -> None:
        detector = DriftDetector(project_dir=tmp_path)
        detector.save_baseline(_report())
        report = detector.compare(
            _report(
                violations=[_violation("a.py")],
                warnings=[_violation("b.py", target="other", severity="warning")],
            )
        )
        assert report.summary["new"] == 2
        assert report.summary["new_errors"] == 1
        assert report.summary["new_warnings"] == 1

    def test_to_dict_serialisable(self, tmp_path: Path) -> None:
        import json

        detector = DriftDetector(project_dir=tmp_path)
        detector.save_baseline(_report())
        report = detector.compare(_report(violations=[_violation("a.py")]))
        # Should round-trip cleanly through JSON.
        decoded = json.loads(json.dumps(report.to_dict()))
        assert decoded["severity"] in {s.value for s in DriftSeverity}


class TestConvenienceWrapper:
    def test_detect_drift_helper(self, tmp_path: Path) -> None:
        # Save baseline first via the detector, then use the helper.
        DriftDetector(project_dir=tmp_path).save_baseline(_report())
        report = detect_drift(tmp_path, _report(violations=[_violation("a.py")]))
        assert report.severity == DriftSeverity.MEDIUM


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
