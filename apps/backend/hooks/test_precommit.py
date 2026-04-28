"""Tests for the pre-commit hooks."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from hooks.precommit import (
    HOOK_EXIT_INFRASTRUCTURE_ERROR,
    HOOK_EXIT_OK,
    HOOK_EXIT_VIOLATION,
    main,
    run_drift_check,
    run_gen_tests_check,
    run_license_check,
)

# ---------------------------------------------------------------------------
# license-check


class TestRunLicenseCheck:
    def test_unresolved_deps_block_under_strict_policy(
        self, tmp_path: Path, capsys
    ) -> None:
        # `react` has no declared license in the manifest itself, and the
        # scanner has no network resolver — so under permissive_only it
        # ends up Unknown → conflict. Hook must surface this as VIOLATION
        # (not OK), with a useful message.
        (tmp_path / "package.json").write_text(
            json.dumps(
                {
                    "name": "demo",
                    "license": "MIT",
                    "dependencies": {"react": "^18.0.0"},
                }
            ),
            encoding="utf-8",
        )
        rc = run_license_check(tmp_path)
        assert rc == HOOK_EXIT_VIOLATION
        out = capsys.readouterr()
        assert "BLOCKED" in out.err
        assert "react" in out.err

    def test_unknown_policy_returns_infra_error(self, tmp_path: Path) -> None:
        err = io.StringIO()
        rc = run_license_check(tmp_path, policy="not_a_policy", stderr=err)
        assert rc == HOOK_EXIT_INFRASTRUCTURE_ERROR
        assert "unknown policy" in err.getvalue()

    def test_empty_project_passes_silently(self, tmp_path: Path) -> None:
        # No manifest → scanner finds nothing → no conflicts → pass.
        rc = run_license_check(tmp_path)
        assert rc == HOOK_EXIT_OK


# ---------------------------------------------------------------------------
# drift-check


class TestRunDriftCheck:
    def test_no_baseline_skips(self, tmp_path: Path, capsys) -> None:
        rc = run_drift_check(tmp_path)
        assert rc == HOOK_EXIT_OK
        captured = capsys.readouterr()
        assert "no baseline" in captured.out

    def test_no_current_report_skips(self, tmp_path: Path, capsys) -> None:
        # Seed a baseline so the function gets past the first guard.
        baseline_dir = tmp_path / ".workpilot" / "architecture"
        baseline_dir.mkdir(parents=True)
        (baseline_dir / "baseline.json").write_text(
            json.dumps({"violations": []}), encoding="utf-8"
        )
        rc = run_drift_check(tmp_path)
        assert rc == HOOK_EXIT_OK
        assert "no current architecture report" in capsys.readouterr().out

    def test_invalid_block_on_falls_back_to_high(self, tmp_path: Path) -> None:
        # Internal helper falls back gracefully — no crash.
        from architecture_drift import DriftSeverity
        from hooks.precommit import _drift_levels_at_or_above

        levels = _drift_levels_at_or_above("garbage", DriftSeverity)
        # "high" cutoff = HIGH + CRITICAL.
        assert any(s.value == "high" for s in levels)
        assert any(s.value == "critical" for s in levels)
        assert not any(s.value == "low" for s in levels)


# ---------------------------------------------------------------------------
# gen-tests-check


class TestRunGenTestsCheck:
    def test_no_junit_xml_skips(self, tmp_path: Path, capsys) -> None:
        rc = run_gen_tests_check(tmp_path)
        assert rc == HOOK_EXIT_OK
        assert "no JUnit XML" in capsys.readouterr().out

    def test_no_prior_generation_skips(self, tmp_path: Path, capsys) -> None:
        junit = tmp_path / "junit.xml"
        junit.write_text(
            '<?xml version="1.0"?><testsuites>'
            '<testsuite name="s"><testcase classname="x" name="ok" time="0.01"/>'
            "</testsuite></testsuites>",
            encoding="utf-8",
        )
        rc = run_gen_tests_check(tmp_path, junit_xml=junit)
        assert rc == HOOK_EXIT_OK
        assert "no prior generation" in capsys.readouterr().out

    def test_clean_run_against_baseline_passes(self, tmp_path: Path) -> None:
        # Capture a baseline, then re-run the same outcomes → no regressions.
        from generational_tests import GenerationalArchive

        junit = tmp_path / "junit.xml"
        junit.write_text(
            '<?xml version="1.0"?><testsuites>'
            '<testsuite name="s">'
            '<testcase classname="x" name="ok" time="0.01"/>'
            "</testsuite></testsuites>",
            encoding="utf-8",
        )
        archive = GenerationalArchive(project_dir=tmp_path)
        archive.capture("v1", junit_xml=junit)
        rc = run_gen_tests_check(tmp_path, junit_xml=junit)
        assert rc == HOOK_EXIT_OK

    def test_regression_blocks(self, tmp_path: Path, capsys) -> None:
        from generational_tests import GenerationalArchive

        # Baseline: test passes.
        baseline_xml = tmp_path / "baseline.xml"
        baseline_xml.write_text(
            '<?xml version="1.0"?><testsuites>'
            '<testsuite name="s">'
            '<testcase classname="x" name="t1" time="0.01"/>'
            "</testsuite></testsuites>",
            encoding="utf-8",
        )
        archive = GenerationalArchive(project_dir=tmp_path)
        archive.capture("v1", junit_xml=baseline_xml)

        # Current run: same test fails.
        current_xml = tmp_path / "current.xml"
        current_xml.write_text(
            '<?xml version="1.0"?><testsuites>'
            '<testsuite name="s">'
            '<testcase classname="x" name="t1" time="0.01">'
            "<failure>boom</failure></testcase>"
            "</testsuite></testsuites>",
            encoding="utf-8",
        )
        rc = run_gen_tests_check(tmp_path, junit_xml=current_xml)
        assert rc == HOOK_EXIT_VIOLATION
        out = capsys.readouterr()
        # Block message lands on stderr.
        assert "BLOCKED" in out.err
        # GenerationalArchive uses "::" as the classname/test separator.
        assert "x::t1" in out.err

    def test_corrupt_junit_xml_returns_infra_error(self, tmp_path: Path) -> None:
        junit = tmp_path / "bad.xml"
        junit.write_text("not xml", encoding="utf-8")
        # Need a baseline so we get past the early-exit.
        from generational_tests import GenerationalArchive

        baseline = tmp_path / "good.xml"
        baseline.write_text(
            '<?xml version="1.0"?><testsuites>'
            '<testsuite name="s">'
            '<testcase classname="x" name="ok" time="0.01"/>'
            "</testsuite></testsuites>",
            encoding="utf-8",
        )
        GenerationalArchive(project_dir=tmp_path).capture("v1", junit_xml=baseline)
        rc = run_gen_tests_check(tmp_path, junit_xml=junit)
        assert rc == HOOK_EXIT_INFRASTRUCTURE_ERROR


# ---------------------------------------------------------------------------
# CLI entrypoint


class TestMain:
    def test_unknown_project_dir_errors(self) -> None:
        rc = main(["license-check", "--project-dir", "/this/does/not/exist"])
        assert rc == HOOK_EXIT_INFRASTRUCTURE_ERROR

    def test_clean_license_via_cli(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(
            json.dumps({"name": "x", "license": "MIT"}), encoding="utf-8"
        )
        rc = main(["license-check", "--project-dir", str(tmp_path)])
        assert rc == HOOK_EXIT_OK

    def test_drift_check_with_no_baseline_via_cli(self, tmp_path: Path) -> None:
        rc = main(["drift-check", "--project-dir", str(tmp_path)])
        assert rc == HOOK_EXIT_OK

    def test_gen_tests_with_no_data_via_cli(self, tmp_path: Path) -> None:
        rc = main(["gen-tests-check", "--project-dir", str(tmp_path)])
        assert rc == HOOK_EXIT_OK


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
