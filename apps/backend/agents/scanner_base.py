"""Shared base classes for "scanner-style" agent modules.

A large number of modules under ``apps/backend/*_agent`` / ``apps/backend/*_detector``
share the same skeleton:

* a ``Severity`` enum,
* a ``Finding`` dataclass (violation / issue / drift / …),
* a ``Report`` dataclass with ``findings`` + ``files_scanned`` +
  severity-count properties + ``summary``,
* a ``Scanner`` class with ``scan_file(path, content) -> Report`` and
  ``scan_files(files_map) -> Report``.

This module provides a minimal, typed base that new or migrated modules
can extend, eliminating the boilerplate without forcing a big-bang
migration of the 40+ existing modules.

Design notes
------------

* The base is **generic** over ``FindingT``: each concrete agent keeps
  its own ``Finding`` dataclass with agent-specific fields
  (``rule_id``, ``wcag_criteria``, ``drift_type``, …). We only require
  that every ``Finding`` exposes ``severity`` and ``file`` attributes.
* ``BaseScanReport`` aggregates findings and surfaces common counters.
  Subclasses are free to add agent-specific properties.
* ``BaseScanner`` owns the iteration logic (``scan_files``) so subclasses
  only implement ``scan_file``.
* Nothing here imports from agent-specific modules — it is safe to import
  from ``agents/scanner_base.py`` in any of the scanner agents.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Generic, Protocol, TypeVar, runtime_checkable

logger = logging.getLogger(__name__)


class Severity(str, Enum):
    """Generic severity levels shared across scanners.

    Concrete agents may define their own enum when they need a different
    vocabulary (e.g. ``WcagLevel``, ``DriftSeverity``). ``BaseScanReport``
    only requires that the ``severity`` field has a ``.value`` that can be
    compared with :data:`BLOCKING_SEVERITIES`.
    """

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


# Findings at these severities should block CI/QA by default. Concrete
# reports are free to override ``blocking_severities`` when they use a
# different vocabulary.
BLOCKING_SEVERITIES: frozenset[str] = frozenset({"critical", "high"})


@runtime_checkable
class HasSeverity(Protocol):
    """Minimum contract for objects stored in a :class:`BaseScanReport`."""

    severity: object  # str | Enum — duck-typed via .value below
    file: str


FindingT = TypeVar("FindingT", bound=HasSeverity)


def _severity_value(finding: HasSeverity) -> str:
    """Return the string form of a finding's severity, tolerating str or Enum."""
    sev = finding.severity
    # ``Enum`` instances expose ``.value``; plain strings are used as-is.
    return getattr(sev, "value", sev) if sev is not None else ""


@dataclass
class BaseScanReport(Generic[FindingT]):
    """Aggregate report emitted by a scanner.

    Subclasses typically don't need to override anything — they just
    parameterize ``FindingT`` with their own dataclass.
    """

    findings: list[FindingT] = field(default_factory=list)
    files_scanned: int = 0

    # Overridable: a concrete subclass may extend this with its own
    # vocabulary (e.g. {"critical", "serious"} for a11y).
    blocking_severities: frozenset[str] = field(
        default_factory=lambda: BLOCKING_SEVERITIES
    )

    @property
    def count_by_severity(self) -> dict[str, int]:
        """Return ``{severity: count}`` over all findings."""
        by_sev: dict[str, int] = {}
        for finding in self.findings:
            key = _severity_value(finding)
            by_sev[key] = by_sev.get(key, 0) + 1
        return by_sev

    @property
    def blocking_count(self) -> int:
        """Number of findings whose severity is in ``blocking_severities``."""
        return sum(
            1 for f in self.findings if _severity_value(f) in self.blocking_severities
        )

    @property
    def passed(self) -> bool:
        """True when no finding reaches a blocking severity."""
        return self.blocking_count == 0

    @property
    def summary(self) -> str:
        """One-line human-readable summary."""
        counts = self.count_by_severity
        if not counts:
            return "No findings"
        # Stable ordering so snapshots don't flap between runs.
        ordered = sorted(counts.items(), key=lambda kv: kv[0])
        return ", ".join(f"{count} {sev}" for sev, count in ordered)


ReportT = TypeVar("ReportT", bound=BaseScanReport)


class BaseScanner(Generic[FindingT, ReportT]):
    """Template for scanner agents.

    Subclasses must implement :meth:`scan_file`. :meth:`scan_files`
    iterates over ``{path: content}`` and aggregates results into a
    single report.

    The class is intentionally tiny: the win here is consistency of
    interface across the ~20 scanner agents, not premature abstraction.
    """

    #: Subclasses set this so :meth:`_new_report` can instantiate the
    #: concrete report subclass without requiring the caller to pass it.
    report_cls: type[ReportT]

    def scan_file(self, file_path: str, content: str) -> ReportT:
        """Scan a single file. Must be implemented by subclasses."""
        raise NotImplementedError

    def scan_files(self, files: dict[str, str]) -> ReportT:
        """Scan multiple files and aggregate their findings.

        Args:
            files: mapping of file path -> file content.
        """
        report = self._new_report()
        for path, content in files.items():
            try:
                sub = self.scan_file(path, content)
            except Exception:
                # One bad file must not abort the whole run — this matches
                # the existing behavior of several scanners that used
                # try/except per file.
                logger.exception("scan_file failed for %s", path)
                continue
            report.findings.extend(sub.findings)
            report.files_scanned += 1
        return report

    def _new_report(self) -> ReportT:
        """Hook for subclasses that need to pass extra kwargs to their report."""
        return self.report_cls()
