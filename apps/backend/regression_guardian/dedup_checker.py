"""
Dedup Checker — Detect if a similar regression test already exists.

Uses text similarity and function-name matching to avoid creating
duplicate tests for the same incident pattern.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from .incident_parser import Incident

logger = logging.getLogger(__name__)


@dataclass
class DedupResult:
    """Result of a deduplication check."""

    is_duplicate: bool
    similar_test_path: str = ""
    similarity_score: float = 0.0
    recommendation: str = ""


class DedupChecker:
    """Check for existing tests that cover the same incident.

    Usage::

        checker = DedupChecker(test_dirs=[Path("tests/")])
        result = checker.check(incident)
        if result.is_duplicate:
            print(f"Already covered by {result.similar_test_path}")
    """

    def __init__(
        self,
        test_dirs: list[Path] | None = None,
        similarity_threshold: float = 0.7,
    ) -> None:
        self._test_dirs = test_dirs or []
        self._threshold = similarity_threshold

    def check(self, incident: Incident) -> DedupResult:
        """Check whether a regression test already exists for this incident."""
        target_func = incident.faulting_function or ""
        target_file = incident.faulting_file or ""
        exc_type = incident.exception_type or ""

        if not target_func and not exc_type:
            return DedupResult(is_duplicate=False, recommendation="No target to deduplicate against")

        best_score = 0.0
        best_path = ""

        for test_dir in self._test_dirs:
            if not test_dir.exists():
                continue
            for test_file in test_dir.rglob("*"):
                if not test_file.is_file():
                    continue
                if not _is_test_file(test_file.name):
                    continue

                try:
                    content = test_file.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue

                score = self._compute_similarity(
                    content, target_func, target_file, exc_type
                )
                if score > best_score:
                    best_score = score
                    best_path = str(test_file)

        if best_score >= self._threshold:
            return DedupResult(
                is_duplicate=True,
                similar_test_path=best_path,
                similarity_score=best_score,
                recommendation=f"Existing test at {best_path} (score={best_score:.2f}) — consider enriching it instead of creating a new one.",
            )

        return DedupResult(
            is_duplicate=False,
            similarity_score=best_score,
            similar_test_path=best_path,
            recommendation="No sufficiently similar test found.",
        )

    @staticmethod
    def _compute_similarity(
        content: str, target_func: str, target_file: str, exc_type: str
    ) -> float:
        """Compute a similarity score between existing test content and an incident."""
        score = 0.0
        content_lower = content.lower()

        if target_func:
            func_lower = target_func.lower()
            if func_lower in content_lower:
                score += 0.5
            elif _fuzzy_match(func_lower, content_lower):
                score += 0.3

        if target_file:
            file_base = Path(target_file).stem.lower()
            if file_base in content_lower:
                score += 0.2

        if exc_type:
            if exc_type.lower() in content_lower:
                score += 0.3

        return min(score, 1.0)


def _is_test_file(filename: str) -> bool:
    name = filename.lower()
    return (
        name.startswith("test_")
        or name.endswith("_test.py")
        or name.endswith(".test.ts")
        or name.endswith(".test.js")
        or name.endswith(".test.tsx")
        or name.endswith(".spec.ts")
        or name.endswith(".spec.js")
        or name.endswith("test.java")
        or name.endswith("_test.go")
        or name.endswith("tests.cs")
    )


def _fuzzy_match(needle: str, haystack: str) -> bool:
    """Simple fuzzy match: check if parts of the needle appear in the haystack."""
    parts = re.split(r"[_\-.]", needle)
    matched = sum(1 for p in parts if p and p in haystack)
    return matched >= len(parts) * 0.6 if parts else False
