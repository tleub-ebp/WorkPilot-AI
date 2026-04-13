"""
Flaky Test Detective — Identify and classify flaky tests.

Analyses test run history, categorises root causes (timing, ordering,
shared state, network, randomness), and suggests targeted fixes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class FlakyCause(str, Enum):
    TIMING = "timing"
    TEST_ORDER = "test_order"
    SHARED_STATE = "shared_state"
    NETWORK = "network"
    RANDOMNESS = "randomness"
    RESOURCE_LEAK = "resource_leak"
    CONCURRENCY = "concurrency"
    ENVIRONMENT = "environment"
    UNKNOWN = "unknown"


class FlakyConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class TestRun:
    """A single test execution result."""

    test_name: str
    passed: bool
    duration_ms: float = 0.0
    error_message: str = ""
    run_id: str = ""
    timestamp: float = 0.0


@dataclass
class FlakyTest:
    """A test identified as flaky."""

    test_name: str
    file_path: str = ""
    total_runs: int = 0
    failures: int = 0
    flakiness_rate: float = 0.0
    probable_cause: FlakyCause = FlakyCause.UNKNOWN
    confidence: FlakyConfidence = FlakyConfidence.LOW
    error_patterns: list[str] = field(default_factory=list)
    suggested_fix: str = ""


@dataclass
class FlakyReport:
    """Report of flaky test analysis."""

    flaky_tests: list[FlakyTest] = field(default_factory=list)
    total_tests_analysed: int = 0
    total_runs_analysed: int = 0

    @property
    def flaky_count(self) -> int:
        return len(self.flaky_tests)

    @property
    def summary(self) -> str:
        if not self.flaky_tests:
            return "No flaky tests detected"
        by_cause = {}
        for ft in self.flaky_tests:
            by_cause[ft.probable_cause.value] = (
                by_cause.get(ft.probable_cause.value, 0) + 1
            )
        parts = [f"{count} {cause}" for cause, count in by_cause.items()]
        return f"{self.flaky_count} flaky tests: {', '.join(parts)}"


_CAUSE_PATTERNS: dict[FlakyCause, list[str]] = {
    FlakyCause.TIMING: ["timeout", "timed out", "sleep", "delay", "slow", "deadline"],
    FlakyCause.NETWORK: [
        "connection refused",
        "ECONNREFUSED",
        "socket",
        "dns",
        "fetch failed",
    ],
    FlakyCause.SHARED_STATE: [
        "already exists",
        "duplicate key",
        "state",
        "setUp",
        "tearDown",
    ],
    FlakyCause.CONCURRENCY: ["race", "deadlock", "lock", "concurrent", "thread"],
    FlakyCause.RESOURCE_LEAK: [
        "too many open files",
        "memory",
        "ENOMEM",
        "file descriptor",
    ],
    FlakyCause.RANDOMNESS: ["random", "seed", "uuid", "nonce", "Math.random"],
}

_CAUSE_FIXES: dict[FlakyCause, str] = {
    FlakyCause.TIMING: "Replace sleep/timeout with explicit waits or polling. Increase timeout thresholds.",
    FlakyCause.TEST_ORDER: "Ensure each test sets up and tears down its own state. Use test isolation fixtures.",
    FlakyCause.SHARED_STATE: "Isolate shared state per test. Use fresh DB transactions or in-memory stores.",
    FlakyCause.NETWORK: "Mock external network calls. Use WireMock/nock/responses for HTTP stubs.",
    FlakyCause.RANDOMNESS: "Seed random generators in tests. Use deterministic UUIDs/timestamps.",
    FlakyCause.RESOURCE_LEAK: "Ensure proper cleanup in tearDown/afterEach. Close file handles and connections.",
    FlakyCause.CONCURRENCY: "Add synchronisation primitives. Use thread-safe assertions.",
    FlakyCause.ENVIRONMENT: "Pin environment variables and system deps in CI. Use containers for consistency.",
    FlakyCause.UNKNOWN: "Run the test in isolation to confirm flakiness. Add verbose logging.",
}


class FlakyAnalyzer:
    """Analyse test run history to detect and classify flaky tests.

    Usage::

        analyzer = FlakyAnalyzer(flakiness_threshold=0.05)
        report = analyzer.analyze(test_runs)
    """

    def __init__(self, flakiness_threshold: float = 0.05, min_runs: int = 5) -> None:
        self._threshold = flakiness_threshold
        self._min_runs = min_runs

    def analyze(self, runs: list[TestRun]) -> FlakyReport:
        """Analyse test runs and detect flaky tests."""
        grouped: dict[str, list[TestRun]] = {}
        for run in runs:
            grouped.setdefault(run.test_name, []).append(run)

        report = FlakyReport(
            total_tests_analysed=len(grouped),
            total_runs_analysed=len(runs),
        )

        for test_name, test_runs in grouped.items():
            if len(test_runs) < self._min_runs:
                continue

            failures = sum(1 for r in test_runs if not r.passed)
            passes = sum(1 for r in test_runs if r.passed)

            # Flaky = sometimes passes, sometimes fails
            if failures == 0 or passes == 0:
                continue

            rate = failures / len(test_runs)
            if rate < self._threshold:
                continue

            errors = [r.error_message for r in test_runs if r.error_message]
            cause = self._classify_cause(errors)

            report.flaky_tests.append(
                FlakyTest(
                    test_name=test_name,
                    total_runs=len(test_runs),
                    failures=failures,
                    flakiness_rate=rate,
                    probable_cause=cause,
                    confidence=self._assess_confidence(cause, errors),
                    error_patterns=list(set(errors))[:5],
                    suggested_fix=_CAUSE_FIXES.get(cause, ""),
                )
            )

        report.flaky_tests.sort(key=lambda ft: ft.flakiness_rate, reverse=True)
        return report

    @staticmethod
    def _classify_cause(errors: list[str]) -> FlakyCause:
        """Classify the probable cause from error messages."""
        all_errors = " ".join(errors).lower()
        best_cause = FlakyCause.UNKNOWN
        best_score = 0

        for cause, patterns in _CAUSE_PATTERNS.items():
            score = sum(1 for p in patterns if p.lower() in all_errors)
            if score > best_score:
                best_score = score
                best_cause = cause

        return best_cause

    @staticmethod
    def _assess_confidence(cause: FlakyCause, errors: list[str]) -> FlakyConfidence:
        if cause == FlakyCause.UNKNOWN:
            return FlakyConfidence.LOW
        all_errors = " ".join(errors).lower()
        matches = sum(
            1 for p in _CAUSE_PATTERNS.get(cause, []) if p.lower() in all_errors
        )
        if matches >= 3:
            return FlakyConfidence.HIGH
        if matches >= 1:
            return FlakyConfidence.MEDIUM
        return FlakyConfidence.LOW
