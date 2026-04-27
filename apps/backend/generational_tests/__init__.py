"""Generational Test Archive.

Snapshots a test run as a generation, then compares future runs against
that snapshot to surface regressions:
  * tests that were passing and now fail
  * tests that got significantly slower
  * tests that disappeared (deleted? renamed?)
  * brand-new tests that didn't exist in the baseline

Different from `flaky_test_detective/` which looks for *intermittent*
failures across many runs of the same revision. This module looks for
*regression* between revisions.

Format-agnostic ingestion: we accept JUnit XML (pytest, jest, gradle,
mocha-junit-reporter, etc.) which is the lowest common denominator.
"""

from .archive import (
    Generation,
    GenerationalArchive,
    RegressionReport,
    TestOutcome,
    TestStatus,
    parse_junit_xml,
)

__all__ = [
    "GenerationalArchive",
    "Generation",
    "RegressionReport",
    "TestOutcome",
    "TestStatus",
    "parse_junit_xml",
]
