"""
Flaky Test Detective — Identify, classify, and fix flaky tests.

Analyses test run history to detect intermittent failures,
classifies root causes, and suggests targeted fixes.
"""

from .flaky_analyzer import (
    FlakyAnalyzer,
    FlakyCause,
    FlakyConfidence,
    FlakyReport,
    FlakyTest,
    TestRun,
)

__all__ = [
    "FlakyAnalyzer",
    "FlakyReport",
    "FlakyTest",
    "FlakyCause",
    "FlakyConfidence",
    "TestRun",
]
