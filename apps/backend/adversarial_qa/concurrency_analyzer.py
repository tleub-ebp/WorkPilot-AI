"""
Concurrency Analyzer — Detect race conditions and deadlocks.

Analyzes code patterns for concurrency issues.  Identifies shared
mutable state, missing locks, and potential deadlock ordering.

100% algorithmic — no LLM dependency.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ConcurrencyIssueType(str, Enum):
    RACE_CONDITION = "race_condition"
    DEADLOCK_RISK = "deadlock_risk"
    MISSING_LOCK = "missing_lock"
    SHARED_MUTABLE_STATE = "shared_mutable_state"
    UNSAFE_SINGLETON = "unsafe_singleton"


@dataclass
class RaceCondition:
    """Describes a potential race condition."""

    resource: str
    description: str
    location: str = ""  # file:line or function name
    severity: str = "high"
    suggestion: str = ""


@dataclass
class ConcurrencyFinding:
    """A single concurrency analysis finding."""

    issue_type: ConcurrencyIssueType
    description: str
    location: str = ""
    severity: str = "high"
    code_snippet: str = ""
    suggestion: str = ""


class ConcurrencyAnalyzer:
    """Analyze code for concurrency issues.

    Usage::

        analyzer = ConcurrencyAnalyzer()
        findings = analyzer.analyze_python_code(source_code)
        for f in findings:
            print(f"{f.issue_type}: {f.description}")
    """

    def analyze_python_code(self, code: str, filename: str = "") -> list[ConcurrencyFinding]:
        """Analyze Python source code for concurrency issues."""
        findings: list[ConcurrencyFinding] = []
        findings.extend(self._check_shared_mutable_state(code, filename))
        findings.extend(self._check_missing_locks(code, filename))
        findings.extend(self._check_deadlock_patterns(code, filename))
        findings.extend(self._check_unsafe_globals(code, filename))
        return findings

    def detect_race_conditions(
        self,
        shared_resources: list[str],
        access_patterns: list[dict[str, Any]],
    ) -> list[RaceCondition]:
        """Detect potential race conditions from access patterns.

        Args:
            shared_resources: Names of shared resources.
            access_patterns: List of dicts with keys: "resource", "operation" (read/write), "thread".
        """
        races: list[RaceCondition] = []

        # Group by resource
        resource_accesses: dict[str, list[dict[str, Any]]] = {}
        for access in access_patterns:
            res = access.get("resource", "")
            if res in shared_resources:
                resource_accesses.setdefault(res, []).append(access)

        for resource, accesses in resource_accesses.items():
            threads = {a.get("thread", "") for a in accesses}
            has_write = any(a.get("operation") == "write" for a in accesses)
            has_read = any(a.get("operation") == "read" for a in accesses)

            if len(threads) > 1 and has_write:
                race_type = "read-write" if has_read else "write-write"
                races.append(RaceCondition(
                    resource=resource,
                    description=f"Potential {race_type} race on '{resource}' across {len(threads)} threads",
                    severity="critical" if race_type == "write-write" else "high",
                    suggestion=f"Protect '{resource}' with a lock or use thread-safe data structure.",
                ))

        return races

    def _check_shared_mutable_state(
        self, code: str, filename: str
    ) -> list[ConcurrencyFinding]:
        """Check for module-level mutable state that could be shared."""
        findings: list[ConcurrencyFinding] = []
        lines = code.split("\n")

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            # Module-level dict or list assignment (not inside function/class)
            if not stripped.startswith(" ") and not stripped.startswith("\t"):
                if re.match(r"^\w+\s*[:=]\s*(\{|\[|dict\(|list\(|set\()", stripped):
                    # Skip if it's a constant (ALL_CAPS)
                    var_name = stripped.split("=")[0].split(":")[0].strip()
                    if not var_name.isupper() and not var_name.startswith("_"):
                        findings.append(ConcurrencyFinding(
                            issue_type=ConcurrencyIssueType.SHARED_MUTABLE_STATE,
                            description=f"Module-level mutable variable '{var_name}'",
                            location=f"{filename}:{i}" if filename else f"line {i}",
                            severity="medium",
                            code_snippet=stripped,
                            suggestion=f"Consider making '{var_name}' thread-local or protecting with a lock.",
                        ))

        return findings

    def _check_missing_locks(
        self, code: str, filename: str
    ) -> list[ConcurrencyFinding]:
        """Check for thread usage without apparent lock protection."""
        findings: list[ConcurrencyFinding] = []

        has_threading = "import threading" in code or "from threading" in code
        has_asyncio = "import asyncio" in code or "async def" in code
        has_lock = "Lock()" in code or "RLock()" in code or "Semaphore(" in code

        if has_threading and not has_lock:
            findings.append(ConcurrencyFinding(
                issue_type=ConcurrencyIssueType.MISSING_LOCK,
                description="Threading used without any Lock/RLock/Semaphore",
                location=filename or "module",
                severity="high",
                suggestion="Add locks to protect shared state accessed from threads.",
            ))

        if has_asyncio and not has_lock and "asyncio.Lock()" not in code:
            # Check for shared state modification in async code
            if re.search(r"self\.\w+\s*[+\-*/]?=", code) and "async def" in code:
                findings.append(ConcurrencyFinding(
                    issue_type=ConcurrencyIssueType.MISSING_LOCK,
                    description="Async code modifies instance state without asyncio.Lock",
                    location=filename or "module",
                    severity="medium",
                    suggestion="Use asyncio.Lock() to protect shared state in async code.",
                ))

        return findings

    def _check_deadlock_patterns(
        self, code: str, filename: str
    ) -> list[ConcurrencyFinding]:
        """Check for potential deadlock patterns (nested lock acquisition)."""
        findings: list[ConcurrencyFinding] = []

        # Simple heuristic: multiple lock.acquire() or `with lock` in the same function
        lock_pattern = re.compile(r"(with\s+self\._\w*lock|\.acquire\(\))")
        functions = re.split(r"\ndef\s+", code)

        for func in functions:
            matches = lock_pattern.findall(func)
            if len(matches) >= 2:
                func_name = func.split("(")[0].strip() if "(" in func else "unknown"
                findings.append(ConcurrencyFinding(
                    issue_type=ConcurrencyIssueType.DEADLOCK_RISK,
                    description=f"Multiple lock acquisitions in '{func_name}'",
                    location=f"{filename}:{func_name}" if filename else func_name,
                    severity="high",
                    suggestion="Ensure consistent lock ordering or use a single coarser lock.",
                ))

        return findings

    def _check_unsafe_globals(
        self, code: str, filename: str
    ) -> list[ConcurrencyFinding]:
        """Check for unsafe global keyword usage."""
        findings: list[ConcurrencyFinding] = []
        lines = code.split("\n")

        for i, line in enumerate(lines, 1):
            if re.match(r"\s+global\s+\w+", line):
                var = line.strip().replace("global ", "")
                findings.append(ConcurrencyFinding(
                    issue_type=ConcurrencyIssueType.SHARED_MUTABLE_STATE,
                    description=f"'global {var}' used — shared mutable state risk",
                    location=f"{filename}:{i}" if filename else f"line {i}",
                    severity="medium",
                    suggestion="Avoid global mutable state. Use dependency injection or thread-local storage.",
                ))

        return findings
