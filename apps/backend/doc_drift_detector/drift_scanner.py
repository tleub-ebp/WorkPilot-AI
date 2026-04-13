"""
Documentation Drift Detector — Detect when docs diverge from code.

Compares README, API docs, inline docstrings, and configuration
examples against the actual codebase to flag stale documentation.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class DriftType(str, Enum):
    STALE_REFERENCE = "stale_reference"
    MISSING_FUNCTION = "missing_function"
    OUTDATED_EXAMPLE = "outdated_example"
    MISSING_DOCS = "missing_docs"
    CONFIG_MISMATCH = "config_mismatch"


class DriftSeverity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class DriftIssue:
    """A single documentation drift issue."""

    drift_type: DriftType
    severity: DriftSeverity
    doc_file: str
    doc_line: int = 0
    message: str = ""
    referenced_symbol: str = ""
    suggestion: str = ""


@dataclass
class DriftReport:
    """Documentation drift analysis report."""

    issues: list[DriftIssue] = field(default_factory=list)
    docs_scanned: int = 0
    source_files_scanned: int = 0

    @property
    def high_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == DriftSeverity.HIGH)

    @property
    def summary(self) -> str:
        by_type = {}
        for issue in self.issues:
            by_type[issue.drift_type.value] = by_type.get(issue.drift_type.value, 0) + 1
        parts = [f"{count} {t}" for t, count in by_type.items()]
        return ", ".join(parts) or "No drift detected"


# Patterns to extract code references from documentation
_CODE_REF_PATTERN = re.compile(r"`([a-zA-Z_]\w*(?:\.\w+)*)\(`")
_FILE_REF_PATTERN = re.compile(r"`([a-zA-Z0-9_/\\.-]+\.\w{1,5})`")
_IMPORT_REF_PATTERN = re.compile(r"(?:from|import)\s+`?([a-zA-Z_]\w*(?:\.\w+)*)`?")


class DriftScanner:
    """Scan documentation for drift from the actual codebase.

    Usage::

        scanner = DriftScanner()
        report = scanner.scan(doc_files, source_symbols)
    """

    def scan(
        self,
        doc_files: dict[str, str],
        source_symbols: set[str],
        source_files: set[str] | None = None,
    ) -> DriftReport:
        """Scan doc files for references to symbols/files that no longer exist."""
        report = DriftReport(
            docs_scanned=len(doc_files),
            source_files_scanned=len(source_files or set()),
        )

        for doc_path, content in doc_files.items():
            report.issues.extend(
                self._check_code_references(doc_path, content, source_symbols)
            )
            if source_files:
                report.issues.extend(
                    self._check_file_references(doc_path, content, source_files)
                )

        return report

    def _check_code_references(
        self, doc_path: str, content: str, symbols: set[str]
    ) -> list[DriftIssue]:
        issues: list[DriftIssue] = []
        lines = content.splitlines()

        for i, line in enumerate(lines, 1):
            for match in _CODE_REF_PATTERN.finditer(line):
                ref = match.group(1)
                if ref not in symbols and not _is_common_builtin(ref):
                    issues.append(DriftIssue(
                        drift_type=DriftType.MISSING_FUNCTION,
                        severity=DriftSeverity.HIGH,
                        doc_file=doc_path,
                        doc_line=i,
                        referenced_symbol=ref,
                        message=f"Function '{ref}' referenced in docs not found in codebase",
                        suggestion=f"Update or remove reference to '{ref}'",
                    ))

        return issues

    def _check_file_references(
        self, doc_path: str, content: str, files: set[str]
    ) -> list[DriftIssue]:
        issues: list[DriftIssue] = []
        lines = content.splitlines()

        for i, line in enumerate(lines, 1):
            for match in _FILE_REF_PATTERN.finditer(line):
                ref = match.group(1)
                # Normalise path separators
                normalised = ref.replace("\\", "/")
                if normalised not in files and not _is_url_or_extension(ref):
                    issues.append(DriftIssue(
                        drift_type=DriftType.STALE_REFERENCE,
                        severity=DriftSeverity.MEDIUM,
                        doc_file=doc_path,
                        doc_line=i,
                        referenced_symbol=ref,
                        message=f"File '{ref}' referenced in docs not found in codebase",
                        suggestion=f"Update the file reference '{ref}' or remove it",
                    ))

        return issues


def _is_common_builtin(name: str) -> bool:
    builtins = {"print", "len", "str", "int", "float", "list", "dict", "set",
                "True", "False", "None", "self", "cls", "console", "log",
                "require", "import", "export", "return", "async", "await"}
    return name in builtins


def _is_url_or_extension(ref: str) -> bool:
    return ref.startswith("http") or ref.startswith(".") or "/" not in ref
