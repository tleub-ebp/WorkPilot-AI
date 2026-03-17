"""
Browser Agent Module
=====================

Built-in Chromium browser agent for testing, scraping, and visual validation.
Provides headless browser control, visual regression testing, and E2E test execution.
"""

from .browser_controller import BrowserController
from .models import (
    BaselineInfo,
    BrowserAgentStats,
    ComparisonResult,
    ScreenshotInfo,
    TestInfo,
    TestResult,
    TestRunResult,
)
from .test_executor import TestExecutor
from .visual_regression import VisualRegressionEngine

__all__ = [
    "BrowserController",
    "VisualRegressionEngine",
    "TestExecutor",
    "BaselineInfo",
    "BrowserAgentStats",
    "ComparisonResult",
    "ScreenshotInfo",
    "TestInfo",
    "TestResult",
    "TestRunResult",
]
