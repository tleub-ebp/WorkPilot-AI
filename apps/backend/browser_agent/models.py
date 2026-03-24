"""
Browser Agent Models
=====================

Data models for the Built-in Browser Agent feature.
"""

from dataclasses import dataclass, field
from enum import Enum


class BrowserAgentTab(str, Enum):
    BROWSER = "browser"
    VISUAL_REGRESSION = "visual-regression"
    TEST_RUNNER = "test-runner"


class TestStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class ComparisonResult:
    """Result of comparing a screenshot against its baseline."""

    name: str
    baseline_path: str
    current_path: str
    diff_image_path: str | None
    match_percentage: float
    diff_pixels: int
    passed: bool
    threshold: float

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "baselinePath": self.baseline_path,
            "currentPath": self.current_path,
            "diffImagePath": self.diff_image_path,
            "matchPercentage": self.match_percentage,
            "diffPixels": self.diff_pixels,
            "passed": self.passed,
            "threshold": self.threshold,
        }


@dataclass
class BaselineInfo:
    """Metadata about a stored visual baseline."""

    name: str
    path: str
    created_at: str
    width: int
    height: int

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "createdAt": self.created_at,
            "width": self.width,
            "height": self.height,
        }


@dataclass
class ScreenshotInfo:
    """Metadata about a captured screenshot."""

    name: str
    path: str
    url: str
    timestamp: str
    width: int
    height: int

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "url": self.url,
            "timestamp": self.timestamp,
            "width": self.width,
            "height": self.height,
        }


@dataclass
class TestInfo:
    """Metadata about a discovered test file."""

    name: str
    path: str
    type: str  # 'playwright' | 'pytest' | 'custom'

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "type": self.type,
        }


@dataclass
class TestResult:
    """Result of a single test execution."""

    name: str
    path: str
    status: str
    duration_ms: float
    error_message: str | None = None
    screenshot_path: str | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "status": self.status,
            "durationMs": self.duration_ms,
            "errorMessage": self.error_message,
            "screenshotPath": self.screenshot_path,
        }


@dataclass
class TestRunResult:
    """Aggregated result of a test run."""

    total: int
    passed: int
    failed: int
    skipped: int
    duration_ms: float
    results: list[TestResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "durationMs": self.duration_ms,
            "results": [r.to_dict() for r in self.results],
        }


@dataclass
class BrowserAgentStats:
    """Dashboard statistics for the Browser Agent."""

    total_tests: int = 0
    pass_rate: float = 0.0
    screenshots_captured: int = 0
    regressions_detected: int = 0

    def to_dict(self) -> dict:
        return {
            "totalTests": self.total_tests,
            "passRate": self.pass_rate,
            "screenshotsCaptured": self.screenshots_captured,
            "regressionsDetected": self.regressions_detected,
        }
