"""CI/CD Anomaly Detective — pattern-based log analysis.

Each `AnomalySignal` corresponds to a known infrastructure failure
pattern. Detection is regex-based on log lines so we can run it on every
CI build with negligible overhead.

History-aware mode: when callers pass multiple log samples (one per
recent build), the detective also flags patterns that **recur** across
runs, which is the actually-actionable signal — a single timeout might
be noise, the same timeout 3 builds in a row is a thing to fix.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class AnomalyKind(str, Enum):
    TIMEOUT = "timeout"  # global step/job timeout hit
    OOM = "oom"  # out of memory killed
    DEPENDENCY_CONFLICT = "dependency_conflict"  # package resolver failed
    NETWORK_FAILURE = "network_failure"  # DNS/conn refused/timeout to remote
    DISK_FULL = "disk_full"  # ENOSPC / no space left
    RATE_LIMITED = "rate_limited"  # 429 from registry/API
    AUTH_FAILURE = "auth_failure"  # 401/403, token expired
    INFRASTRUCTURE_FLAKE = "infrastructure_flake"  # docker daemon down, SSH refused
    SLOW_BUILD = "slow_build"  # build duration >> baseline


class Severity(str, Enum):
    CRITICAL = "critical"  # blocks merge / wastes infra
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class _PatternSpec:
    """Describes how to detect one anomaly kind."""

    kind: AnomalyKind
    severity: Severity
    # Each pattern is a tuple (compiled regex, suggested fix).
    patterns: tuple[tuple[re.Pattern[str], str], ...]


# Precompile all patterns once at module load. Lines are matched
# case-insensitive because CI runners shout in mixed case.
def _p(rx: str) -> re.Pattern[str]:
    return re.compile(rx, re.IGNORECASE)


_PATTERN_SPECS: tuple[_PatternSpec, ...] = (
    _PatternSpec(
        kind=AnomalyKind.TIMEOUT,
        severity=Severity.HIGH,
        patterns=(
            (
                _p(r"\berror\b.*\btimeout\b|the operation was canceled"),
                "Increase the job timeout or split into smaller steps.",
            ),
            (_p(r"timed out after \d+"), "Increase the relevant per-step timeout."),
            (
                _p(r"hang|stuck|no output for \d+"),
                "Add a heartbeat log or kill on inactivity.",
            ),
        ),
    ),
    _PatternSpec(
        kind=AnomalyKind.OOM,
        severity=Severity.CRITICAL,
        patterns=(
            # Specific patterns first — once one matches we break out, so
            # the JS/JVM-specific suggestions only fire when their tell
            # is in the line.
            (
                _p(r"javascript heap out of memory"),
                "Set NODE_OPTIONS=--max-old-space-size=… or shard the build.",
            ),
            (
                _p(r"java\.lang\.OutOfMemoryError"),
                "Bump the JVM heap (-Xmx) or split tests into shards.",
            ),
            (
                _p(r"\boom-killed\b|killed.*oom|out of memory|memorykiller"),
                "Bump the runner memory or split the workload.",
            ),
        ),
    ),
    _PatternSpec(
        kind=AnomalyKind.DEPENDENCY_CONFLICT,
        severity=Severity.HIGH,
        patterns=(
            (
                _p(r"\bERESOLVE\b|peer dep(endency)? conflict"),
                "Pin the conflicting peer dep, or use --legacy-peer-deps as a temporary patch.",
            ),
            (
                _p(r"\bdependency_resolution_failed\b|could not resolve dependencies"),
                "Inspect the resolver output; pin transitives in the lockfile.",
            ),
            (
                _p(r"version conflict for"),
                "Pin the offending dep at a single version across the workspace.",
            ),
            (
                _p(r"\bConflictingDependencies\b"),
                "Audit lockfile for ambiguous transitives.",
            ),
        ),
    ),
    _PatternSpec(
        kind=AnomalyKind.NETWORK_FAILURE,
        severity=Severity.MEDIUM,
        patterns=(
            (
                _p(
                    r"could not resolve host|getaddrinfo (failed|enotfound)|name or service not known"
                ),
                "Add DNS retry / cache the resolution at runner start.",
            ),
            (
                _p(r"connection (refused|reset by peer|timed out)"),
                "Wrap the network call in a retry-with-backoff; check upstream status.",
            ),
            (
                _p(r"ssl handshake (failed|error)"),
                "Check the registry's TLS cert / clock skew on the runner.",
            ),
        ),
    ),
    _PatternSpec(
        kind=AnomalyKind.DISK_FULL,
        severity=Severity.CRITICAL,
        patterns=(
            (
                _p(r"no space left on device|enospc|disk quota exceeded"),
                "Add a `df -h` step + cleanup of /tmp + docker prune before the failing step.",
            ),
        ),
    ),
    _PatternSpec(
        kind=AnomalyKind.RATE_LIMITED,
        severity=Severity.MEDIUM,
        patterns=(
            (
                _p(r"\b429\b|too many requests|rate limit (exceeded|reached)"),
                "Add backoff + jitter; or authenticate to a higher-quota tier.",
            ),
        ),
    ),
    _PatternSpec(
        kind=AnomalyKind.AUTH_FAILURE,
        severity=Severity.HIGH,
        patterns=(
            (
                _p(
                    r"\b(401|403)\b|unauthorized|forbidden|invalid (credentials|token)|authentication required"
                ),
                "Rotate the CI token; ensure the secret is exposed to the failing job.",
            ),
            (
                _p(r"bad credentials|permission denied \(publickey\)"),
                "Refresh the SSH key or PAT used by the runner.",
            ),
        ),
    ),
    _PatternSpec(
        kind=AnomalyKind.INFRASTRUCTURE_FLAKE,
        severity=Severity.HIGH,
        patterns=(
            (
                _p(
                    r"docker daemon (is )?not (running|responding)|cannot connect to the docker daemon"
                ),
                "Restart docker / use a fresh runner image.",
            ),
            (
                _p(r"runner offline|host unreachable|broken pipe"),
                "Mark the runner as offline; switch to a healthy pool.",
            ),
            (
                _p(r"received signal\s*15|terminated by sigterm"),
                "The runner was preempted; mark the build as retryable.",
            ),
        ),
    ),
)


@dataclass
class AnomalySignal:
    """A single detected anomaly inside one log sample."""

    kind: AnomalyKind
    severity: Severity
    matching_line: str
    line_number: int
    suggested_fix: str
    log_label: str = ""  # which sample matched (e.g. "build-1234")

    def to_dict(self) -> dict:
        return {
            "kind": self.kind.value,
            "severity": self.severity.value,
            "matching_line": self.matching_line[:300],
            "line_number": self.line_number,
            "suggested_fix": self.suggested_fix,
            "log_label": self.log_label,
        }


@dataclass
class AnomalyReport:
    signals: list[AnomalySignal] = field(default_factory=list)
    recurring_kinds: list[str] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)
    fix_recommendations: list[str] = field(default_factory=list)

    @property
    def has_critical(self) -> bool:
        return any(s.severity == Severity.CRITICAL for s in self.signals)

    def to_dict(self) -> dict:
        return {
            "signals": [s.to_dict() for s in self.signals],
            "recurring_kinds": self.recurring_kinds,
            "summary": self.summary,
            "fix_recommendations": self.fix_recommendations,
            "has_critical": self.has_critical,
        }


class AnomalyDetective:
    """Scan one or many CI log samples for known failure patterns."""

    # An anomaly is "recurring" if it appears in this many distinct
    # log samples (history mode).
    RECURRING_THRESHOLD = 2

    # Hard cap on log size we'll scan to keep this O(N) and prevent
    # accidental DoS by huge artefacts. Roughly 8 MB.
    MAX_LOG_BYTES = 8 * 1024 * 1024

    def scan(self, log: str, log_label: str = "") -> list[AnomalySignal]:
        """Scan a single log blob and return all matching signals."""
        if log is None:
            return []
        if len(log) > self.MAX_LOG_BYTES:
            log = log[: self.MAX_LOG_BYTES]
            logger.warning("Log truncated to %d bytes for scan", self.MAX_LOG_BYTES)

        signals: list[AnomalySignal] = []
        # Track (kind, line) we already emitted to avoid double-counting
        # the same line matching multiple regexes for the same kind.
        seen: set[tuple[AnomalyKind, int]] = set()

        lines = log.splitlines()
        for spec in _PATTERN_SPECS:
            for line_no, line in enumerate(lines, start=1):
                for pattern, suggestion in spec.patterns:
                    if pattern.search(line):
                        key = (spec.kind, line_no)
                        if key in seen:
                            continue
                        seen.add(key)
                        signals.append(
                            AnomalySignal(
                                kind=spec.kind,
                                severity=spec.severity,
                                matching_line=line.strip(),
                                line_number=line_no,
                                suggested_fix=suggestion,
                                log_label=log_label,
                            )
                        )
                        break  # one match per line per kind is enough
        return signals

    def analyse(
        self,
        logs: Iterable[tuple[str, str]] | str,
    ) -> AnomalyReport:
        """Scan one or several log samples and produce a report.

        Args:
            logs: either a single log string, or an iterable of
                ``(label, log_text)`` tuples for history-aware analysis.
        """
        if isinstance(logs, str):
            samples = [("", logs)]
        else:
            samples = list(logs)

        all_signals: list[AnomalySignal] = []
        per_label_kinds: dict[str, set[AnomalyKind]] = {}

        for label, text in samples:
            sigs = self.scan(text, log_label=label)
            all_signals.extend(sigs)
            per_label_kinds[label] = {s.kind for s in sigs}

        # Recurring = same kind appears in ≥ THRESHOLD distinct labels.
        kind_label_counts: Counter[AnomalyKind] = Counter()
        for kinds in per_label_kinds.values():
            for k in kinds:
                kind_label_counts[k] += 1
        recurring = [
            k.value
            for k, c in kind_label_counts.items()
            if c >= self.RECURRING_THRESHOLD
        ]

        summary = {
            "samples": len(samples),
            "total_signals": len(all_signals),
            "by_kind": dict(Counter(s.kind.value for s in all_signals)),
            "by_severity": dict(Counter(s.severity.value for s in all_signals)),
        }

        fix_recommendations = self._aggregate_recommendations(all_signals, recurring)

        return AnomalyReport(
            signals=all_signals,
            recurring_kinds=recurring,
            summary=summary,
            fix_recommendations=fix_recommendations,
        )

    # ------------------------------------------------------------------
    # Internals

    def _aggregate_recommendations(
        self, signals: list[AnomalySignal], recurring: list[str]
    ) -> list[str]:
        """Pick one fix per *kind*, prioritising recurring ones."""
        seen_kinds: set[str] = set()
        ordered: list[str] = []

        # Recurring kinds first.
        recurring_set = set(recurring)
        for s in signals:
            if s.kind.value in recurring_set and s.kind.value not in seen_kinds:
                ordered.append(f"[recurring] {s.suggested_fix}")
                seen_kinds.add(s.kind.value)

        # Then the rest, by severity.
        sev_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
        }
        for s in sorted(signals, key=lambda x: sev_order[x.severity]):
            if s.kind.value not in seen_kinds:
                ordered.append(s.suggested_fix)
                seen_kinds.add(s.kind.value)

        return ordered


# Convenience helpers for callers who just want a one-shot.
def scan_log(log: str) -> list[dict]:
    """One-shot helper: scan one log, return dicts."""
    return [s.to_dict() for s in AnomalyDetective().scan(log)]
