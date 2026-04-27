"""Generational Test Archive — snapshot, compare, regress.

Workflow
--------

1. **Capture a generation** — at a clean point in history, parse the test
   run output (JUnit XML) and persist it as a generation.

       archive = GenerationalArchive(project_dir=Path("./my-app"))
       gen = archive.capture(label="release-1.2.0", junit_xml=xml_path)

2. **Compare a fresh run against a baseline** — later, after refactoring
   or upgrading deps, parse the new test output and diff against the
   stored generation.

       report = archive.compare(
           baseline_label="release-1.2.0",
           current_junit_xml=new_xml,
       )

3. **React to the regression report** — `report.regressions` lists tests
   that were passing in the baseline and now fail (or got slow).

Storage layout: `.workpilot/generational_tests/<label>.json`. Each
generation is a flat list of `TestOutcome` records with stable IDs.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class TestStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


# Tell pytest these aren't test classes despite the "Test" prefix.
TestStatus.__test__ = False  # type: ignore[attr-defined]


@dataclass(frozen=True)
class TestOutcome:
    """A single test result inside a generation."""

    __test__ = False  # noqa: PT013

    test_id: str  # stable identifier: "<classname>::<name>"
    name: str
    classname: str
    status: TestStatus
    duration_seconds: float
    failure_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> TestOutcome:
        return cls(
            test_id=raw["test_id"],
            name=raw["name"],
            classname=raw["classname"],
            status=TestStatus(raw["status"]),
            duration_seconds=float(raw["duration_seconds"]),
            failure_message=raw.get("failure_message", ""),
        )


@dataclass
class Generation:
    label: str
    captured_at: float  # unix timestamp
    junit_source: str  # path / hash for traceability
    outcomes: list[TestOutcome] = field(default_factory=list)

    def by_id(self) -> dict[str, TestOutcome]:
        return {o.test_id: o for o in self.outcomes}

    @property
    def passing_ids(self) -> set[str]:
        return {o.test_id for o in self.outcomes if o.status == TestStatus.PASSED}

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "captured_at": self.captured_at,
            "junit_source": self.junit_source,
            "outcomes": [o.to_dict() for o in self.outcomes],
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Generation:
        return cls(
            label=raw["label"],
            captured_at=float(raw["captured_at"]),
            junit_source=raw.get("junit_source", ""),
            outcomes=[TestOutcome.from_dict(o) for o in raw.get("outcomes", [])],
        )


@dataclass
class RegressionItem:
    test_id: str
    kind: str  # "regressed" | "new_failure" | "vanished" | "added" | "slowed_down"
    baseline_status: str | None
    current_status: str | None
    baseline_duration: float | None
    current_duration: float | None
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RegressionReport:
    baseline_label: str
    current_captured_at: float
    items: list[RegressionItem] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)

    @property
    def regressions(self) -> list[RegressionItem]:
        """Tests that were passing and now don't (the actionable subset)."""
        return [i for i in self.items if i.kind == "regressed"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline_label": self.baseline_label,
            "current_captured_at": self.current_captured_at,
            "items": [i.to_dict() for i in self.items],
            "summary": self.summary,
            "regression_count": len(self.regressions),
        }


# ---------------------------------------------------------------------------
# JUnit XML parsing


# Some reporters (jest, vitest) include a leading time-stamp in the testcase
# name; trim it so the test_id stays stable across runs.
_TS_PREFIX = re.compile(r"^\d+ms\s+")


def _make_test_id(classname: str, name: str) -> str:
    cleaned_name = _TS_PREFIX.sub("", name).strip()
    return f"{classname}::{cleaned_name}" if classname else cleaned_name


def parse_junit_xml(xml_text: str | bytes | Path) -> list[TestOutcome]:
    """Parse a JUnit XML report into TestOutcomes.

    Accepts a path, a bytes object, or a string. Tolerant to both
    `<testsuites>` and bare `<testsuite>` roots.
    """
    if isinstance(xml_text, Path):
        xml_text = xml_text.read_bytes()

    try:
        root = ET.fromstring(xml_text)  # noqa: S314 - JUnit XML is trusted local
    except ET.ParseError as e:
        raise ValueError(f"Invalid JUnit XML: {e}") from e

    suites: Iterable[ET.Element]
    if root.tag == "testsuites":
        suites = root.findall("testsuite")
    elif root.tag == "testsuite":
        suites = [root]
    else:
        raise ValueError(f"Unexpected root element <{root.tag}>")

    outcomes: list[TestOutcome] = []
    for suite in suites:
        for tc in suite.findall("testcase"):
            classname = tc.get("classname", "") or ""
            name = tc.get("name", "") or ""
            duration = float(tc.get("time", "0") or 0.0)

            if tc.find("failure") is not None:
                node = tc.find("failure")
                status = TestStatus.FAILED
                failure_msg = (
                    (node.get("message") or "")[:500] if node is not None else ""
                )
            elif tc.find("error") is not None:
                node = tc.find("error")
                status = TestStatus.ERROR
                failure_msg = (
                    (node.get("message") or "")[:500] if node is not None else ""
                )
            elif tc.find("skipped") is not None:
                status = TestStatus.SKIPPED
                failure_msg = ""
            else:
                status = TestStatus.PASSED
                failure_msg = ""

            outcomes.append(
                TestOutcome(
                    test_id=_make_test_id(classname, name),
                    name=name,
                    classname=classname,
                    status=status,
                    duration_seconds=duration,
                    failure_message=failure_msg,
                )
            )
    return outcomes


# ---------------------------------------------------------------------------
# Archive


_LABEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class GenerationalArchive:
    """Persists test generations under `.workpilot/generational_tests/`."""

    # How much slower a test must get to count as a "slowdown" — 50% by default,
    # but only if the absolute extra time is meaningful (>= 0.2s) so we don't
    # bark at noise on millisecond-tier tests.
    SLOWDOWN_RATIO = 1.5
    SLOWDOWN_MIN_ABS_SECONDS = 0.2

    DEFAULT_SUBDIR = Path(".workpilot") / "generational_tests"

    def __init__(self, project_dir: Path | str) -> None:
        self.project_dir = Path(project_dir)

    # ------------------------------------------------------------------
    # Storage helpers

    def _validate_label(self, label: str) -> str:
        if not isinstance(label, str) or not _LABEL_RE.fullmatch(label):
            raise ValueError(
                f"Invalid generation label {label!r}: must match {_LABEL_RE.pattern}"
            )
        return label

    def _path_for(self, label: str) -> Path:
        return (
            self.project_dir
            / self.DEFAULT_SUBDIR
            / f"{self._validate_label(label)}.json"
        )

    def list_generations(self) -> list[str]:
        target_dir = self.project_dir / self.DEFAULT_SUBDIR
        if not target_dir.exists():
            return []
        return sorted(p.stem for p in target_dir.glob("*.json"))

    def load(self, label: str) -> Generation | None:
        path = self._path_for(label)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Could not load generation %s: %s", label, e)
            return None
        return Generation.from_dict(data)

    def delete(self, label: str) -> bool:
        path = self._path_for(label)
        if not path.exists():
            return False
        path.unlink()
        return True

    # ------------------------------------------------------------------
    # Capture & compare

    def capture(
        self,
        label: str,
        outcomes: list[TestOutcome] | None = None,
        junit_xml: str | bytes | Path | None = None,
        junit_source: str = "",
    ) -> Generation:
        """Persist a new generation. Provide either `outcomes` or `junit_xml`."""
        if outcomes is None and junit_xml is None:
            raise ValueError("Provide either outcomes or junit_xml")
        parsed = outcomes if outcomes is not None else parse_junit_xml(junit_xml)
        if junit_source == "" and isinstance(junit_xml, Path):
            junit_source = str(junit_xml)
        elif junit_source == "" and junit_xml is not None:
            junit_source = (
                "junit-xml-sha256:"
                + hashlib.sha256(
                    junit_xml.encode() if isinstance(junit_xml, str) else junit_xml
                ).hexdigest()[:16]
            )

        gen = Generation(
            label=self._validate_label(label),
            captured_at=time.time(),
            junit_source=junit_source,
            outcomes=parsed,
        )

        path = self._path_for(label)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(gen.to_dict(), indent=2), encoding="utf-8")
        return gen

    def compare(
        self,
        baseline_label: str,
        current_outcomes: list[TestOutcome] | None = None,
        current_junit_xml: str | bytes | Path | None = None,
    ) -> RegressionReport:
        """Diff a fresh test run against a baseline generation."""
        baseline = self.load(baseline_label)
        if baseline is None:
            raise ValueError(f"No generation named {baseline_label!r}")

        if current_outcomes is None and current_junit_xml is None:
            raise ValueError("Provide either current_outcomes or current_junit_xml")
        current_list = (
            current_outcomes
            if current_outcomes is not None
            else parse_junit_xml(current_junit_xml)
        )

        baseline_by_id = baseline.by_id()
        current_by_id = {o.test_id: o for o in current_list}

        items: list[RegressionItem] = []

        # 1. Regressions (was passing, now isn't)
        for tid in baseline.passing_ids:
            cur = current_by_id.get(tid)
            if cur is None:
                items.append(
                    RegressionItem(
                        test_id=tid,
                        kind="vanished",
                        baseline_status=baseline_by_id[tid].status.value,
                        current_status=None,
                        baseline_duration=baseline_by_id[tid].duration_seconds,
                        current_duration=None,
                        detail="Test present in baseline, missing in current run",
                    )
                )
            elif cur.status != TestStatus.PASSED:
                items.append(
                    RegressionItem(
                        test_id=tid,
                        kind="regressed",
                        baseline_status="passed",
                        current_status=cur.status.value,
                        baseline_duration=baseline_by_id[tid].duration_seconds,
                        current_duration=cur.duration_seconds,
                        detail=cur.failure_message[:200],
                    )
                )
            else:
                # Both passed — check for slowdown.
                base_dur = baseline_by_id[tid].duration_seconds
                if (
                    base_dur > 0
                    and cur.duration_seconds >= base_dur * self.SLOWDOWN_RATIO
                    and cur.duration_seconds - base_dur >= self.SLOWDOWN_MIN_ABS_SECONDS
                ):
                    items.append(
                        RegressionItem(
                            test_id=tid,
                            kind="slowed_down",
                            baseline_status="passed",
                            current_status="passed",
                            baseline_duration=base_dur,
                            current_duration=cur.duration_seconds,
                            detail=f"{cur.duration_seconds / base_dur:.1f}× slower",
                        )
                    )

        # 2. New failures: tests that exist in current but weren't passing in
        # baseline (either not present at all, or already failing). We only
        # surface tests that didn't exist before — already-failing tests are
        # not new news.
        for tid, cur in current_by_id.items():
            if tid in baseline_by_id:
                continue
            kind = "new_failure" if cur.status != TestStatus.PASSED else "added"
            items.append(
                RegressionItem(
                    test_id=tid,
                    kind=kind,
                    baseline_status=None,
                    current_status=cur.status.value,
                    baseline_duration=None,
                    current_duration=cur.duration_seconds,
                    detail=cur.failure_message[:200] if cur.failure_message else "",
                )
            )

        summary = {
            "regressed": sum(1 for i in items if i.kind == "regressed"),
            "vanished": sum(1 for i in items if i.kind == "vanished"),
            "slowed_down": sum(1 for i in items if i.kind == "slowed_down"),
            "new_failure": sum(1 for i in items if i.kind == "new_failure"),
            "added": sum(1 for i in items if i.kind == "added"),
        }

        return RegressionReport(
            baseline_label=baseline.label,
            current_captured_at=time.time(),
            items=items,
            summary=summary,
        )
