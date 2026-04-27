"""Tests for the Generational Test Archive."""

from __future__ import annotations

from pathlib import Path

import pytest
from generational_tests import (
    Generation,
    GenerationalArchive,
    TestOutcome,
    TestStatus,
    parse_junit_xml,
)

JUNIT_BASELINE = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="suite_a" tests="3" failures="0" errors="0" skipped="0" time="0.5">
    <testcase classname="auth.TestLogin" name="test_valid_credentials" time="0.05"/>
    <testcase classname="auth.TestLogin" name="test_invalid_password" time="0.04"/>
    <testcase classname="orders.TestCart" name="test_add_item" time="0.30"/>
  </testsuite>
</testsuites>
"""


def _outcome(
    test_id: str,
    status: TestStatus = TestStatus.PASSED,
    duration: float = 0.1,
    failure_message: str = "",
) -> TestOutcome:
    name = test_id.split("::")[-1]
    classname = test_id.split("::")[0] if "::" in test_id else ""
    return TestOutcome(
        test_id=test_id,
        name=name,
        classname=classname,
        status=status,
        duration_seconds=duration,
        failure_message=failure_message,
    )


# ----------------------------------------------------------------------
# JUnit parsing


class TestJUnitParser:
    def test_parses_passing_tests(self) -> None:
        outcomes = parse_junit_xml(JUNIT_BASELINE)
        assert len(outcomes) == 3
        assert all(o.status == TestStatus.PASSED for o in outcomes)
        assert outcomes[0].test_id == "auth.TestLogin::test_valid_credentials"

    def test_parses_failure(self) -> None:
        xml = """<?xml version="1.0"?>
        <testsuite>
          <testcase classname="x" name="boom" time="0.01">
            <failure message="AssertionError: expected 1, got 2"/>
          </testcase>
        </testsuite>"""
        outcomes = parse_junit_xml(xml)
        assert outcomes[0].status == TestStatus.FAILED
        assert "AssertionError" in outcomes[0].failure_message

    def test_parses_error(self) -> None:
        xml = """<?xml version="1.0"?>
        <testsuite>
          <testcase classname="x" name="oops" time="0.01">
            <error message="ImportError: no module named foo"/>
          </testcase>
        </testsuite>"""
        outcomes = parse_junit_xml(xml)
        assert outcomes[0].status == TestStatus.ERROR

    def test_parses_skipped(self) -> None:
        xml = """<?xml version="1.0"?>
        <testsuite>
          <testcase classname="x" name="skip" time="0">
            <skipped/>
          </testcase>
        </testsuite>"""
        outcomes = parse_junit_xml(xml)
        assert outcomes[0].status == TestStatus.SKIPPED

    def test_invalid_xml_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_junit_xml("not xml at all")

    def test_unexpected_root_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_junit_xml("<wrong/>")

    def test_accepts_path(self, tmp_path: Path) -> None:
        f = tmp_path / "junit.xml"
        f.write_text(JUNIT_BASELINE, encoding="utf-8")
        outcomes = parse_junit_xml(f)
        assert len(outcomes) == 3


# ----------------------------------------------------------------------
# Capture / load


class TestCapture:
    def test_capture_from_outcomes(self, tmp_path: Path) -> None:
        archive = GenerationalArchive(project_dir=tmp_path)
        gen = archive.capture("v1", outcomes=[_outcome("a::test_x")])
        assert gen.label == "v1"
        assert len(gen.outcomes) == 1

        loaded = archive.load("v1")
        assert loaded is not None
        assert loaded.outcomes[0].test_id == "a::test_x"

    def test_capture_from_xml(self, tmp_path: Path) -> None:
        archive = GenerationalArchive(project_dir=tmp_path)
        gen = archive.capture("v1", junit_xml=JUNIT_BASELINE)
        assert len(gen.outcomes) == 3
        assert gen.junit_source.startswith("junit-xml-sha256:")

    def test_capture_requires_input(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            GenerationalArchive(project_dir=tmp_path).capture("v1")

    def test_invalid_label_rejected(self, tmp_path: Path) -> None:
        archive = GenerationalArchive(project_dir=tmp_path)
        with pytest.raises(ValueError):
            archive.capture("../escape", outcomes=[_outcome("a::t")])
        with pytest.raises(ValueError):
            archive.capture("with spaces", outcomes=[_outcome("a::t")])

    def test_load_missing_returns_none(self, tmp_path: Path) -> None:
        assert GenerationalArchive(project_dir=tmp_path).load("ghost") is None

    def test_list_and_delete(self, tmp_path: Path) -> None:
        archive = GenerationalArchive(project_dir=tmp_path)
        archive.capture("v1", outcomes=[_outcome("a::t")])
        archive.capture("v2", outcomes=[_outcome("a::t")])
        assert set(archive.list_generations()) == {"v1", "v2"}
        assert archive.delete("v1") is True
        assert archive.delete("v1") is False
        assert archive.list_generations() == ["v2"]


# ----------------------------------------------------------------------
# Compare / regression detection


class TestCompare:
    def _seed(self, archive: GenerationalArchive) -> Generation:
        return archive.capture(
            "baseline",
            outcomes=[
                _outcome("auth::test_login", duration=0.05),
                _outcome("auth::test_logout", duration=0.04),
                _outcome("orders::test_cart", duration=0.30),
            ],
        )

    def test_no_change_means_no_regression(self, tmp_path: Path) -> None:
        archive = GenerationalArchive(project_dir=tmp_path)
        self._seed(archive)
        report = archive.compare(
            "baseline",
            current_outcomes=[
                _outcome("auth::test_login", duration=0.05),
                _outcome("auth::test_logout", duration=0.04),
                _outcome("orders::test_cart", duration=0.30),
            ],
        )
        assert report.summary["regressed"] == 0
        assert report.summary["vanished"] == 0
        assert report.summary["added"] == 0
        assert report.regressions == []

    def test_regression_detected(self, tmp_path: Path) -> None:
        archive = GenerationalArchive(project_dir=tmp_path)
        self._seed(archive)
        report = archive.compare(
            "baseline",
            current_outcomes=[
                _outcome(
                    "auth::test_login",
                    status=TestStatus.FAILED,
                    failure_message="boom",
                ),
                _outcome("auth::test_logout"),
                _outcome("orders::test_cart"),
            ],
        )
        assert len(report.regressions) == 1
        assert report.regressions[0].test_id == "auth::test_login"
        assert report.regressions[0].current_status == "failed"
        assert "boom" in report.regressions[0].detail

    def test_vanished_test_flagged(self, tmp_path: Path) -> None:
        archive = GenerationalArchive(project_dir=tmp_path)
        self._seed(archive)
        report = archive.compare(
            "baseline",
            current_outcomes=[
                _outcome("auth::test_login"),
                _outcome("auth::test_logout"),
                # orders::test_cart is gone
            ],
        )
        assert report.summary["vanished"] == 1
        vanished = [i for i in report.items if i.kind == "vanished"]
        assert vanished[0].test_id == "orders::test_cart"

    def test_added_test_recorded(self, tmp_path: Path) -> None:
        archive = GenerationalArchive(project_dir=tmp_path)
        self._seed(archive)
        report = archive.compare(
            "baseline",
            current_outcomes=[
                _outcome("auth::test_login"),
                _outcome("auth::test_logout"),
                _outcome("orders::test_cart"),
                _outcome("orders::test_checkout"),
            ],
        )
        assert report.summary["added"] == 1
        added = [i for i in report.items if i.kind == "added"]
        assert added[0].test_id == "orders::test_checkout"

    def test_new_failure_recorded(self, tmp_path: Path) -> None:
        archive = GenerationalArchive(project_dir=tmp_path)
        self._seed(archive)
        report = archive.compare(
            "baseline",
            current_outcomes=[
                _outcome("auth::test_login"),
                _outcome("auth::test_logout"),
                _outcome("orders::test_cart"),
                _outcome(
                    "orders::test_new_thing",
                    status=TestStatus.FAILED,
                    failure_message="not implemented",
                ),
            ],
        )
        assert report.summary["new_failure"] == 1

    def test_slowdown_detected(self, tmp_path: Path) -> None:
        archive = GenerationalArchive(project_dir=tmp_path)
        self._seed(archive)
        # orders::test_cart was 0.30s in baseline; bump to 1.5s = 5x slower
        # and the absolute delta (>= 0.2s) is met → must flag.
        report = archive.compare(
            "baseline",
            current_outcomes=[
                _outcome("auth::test_login", duration=0.05),
                _outcome("auth::test_logout", duration=0.04),
                _outcome("orders::test_cart", duration=1.5),
            ],
        )
        assert report.summary["slowed_down"] == 1
        slow = [i for i in report.items if i.kind == "slowed_down"]
        assert slow[0].test_id == "orders::test_cart"
        assert "slower" in slow[0].detail

    def test_tiny_slowdown_below_abs_threshold_ignored(self, tmp_path: Path) -> None:
        archive = GenerationalArchive(project_dir=tmp_path)
        # 1ms baseline → even doubling stays under the 0.2s noise floor.
        archive.capture(
            "baseline",
            outcomes=[_outcome("ping::test_ping", duration=0.001)],
        )
        report = archive.compare(
            "baseline",
            current_outcomes=[_outcome("ping::test_ping", duration=0.005)],
        )
        assert report.summary["slowed_down"] == 0

    def test_compare_with_unknown_baseline_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            GenerationalArchive(project_dir=tmp_path).compare(
                "ghost", current_outcomes=[_outcome("a::t")]
            )

    def test_to_dict_serialisable(self, tmp_path: Path) -> None:
        import json

        archive = GenerationalArchive(project_dir=tmp_path)
        self._seed(archive)
        report = archive.compare(
            "baseline",
            current_outcomes=[
                _outcome("auth::test_login", status=TestStatus.FAILED),
                _outcome("auth::test_logout"),
                _outcome("orders::test_cart"),
            ],
        )
        # Must round-trip cleanly through JSON.
        decoded = json.loads(json.dumps(report.to_dict()))
        assert decoded["regression_count"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
