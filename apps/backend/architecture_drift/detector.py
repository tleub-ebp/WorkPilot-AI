"""Architecture Drift Detector.

Compares a fresh `ArchitectureReport` to a stored baseline and surfaces:
* **new violations**   — appeared since the baseline (drift!)
* **resolved**         — present in baseline, absent now (improvement)
* **persistent**       — still present in both (known debt)

The baseline itself is just a serialised `ArchitectureReport` written to
`.workpilot/architecture/baseline.json`.

A `DriftSeverity` is computed from the magnitude of new violations:
the more *errors* (vs warnings) we accumulate, the worse the drift.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from architecture.models import ArchitectureReport, ArchitectureViolation

logger = logging.getLogger(__name__)


class DriftSeverity(str, Enum):
    NONE = "none"  # 0 new violations
    LOW = "low"  # 1–3 new warnings, 0 new errors
    MEDIUM = "medium"  # ≥ 4 new warnings OR 1–2 new errors
    HIGH = "high"  # 3+ new errors
    CRITICAL = "critical"  # ≥ 10 new violations or > 5 new errors


@dataclass
class ViolationDelta:
    """A single violation that changed status between baseline and current."""

    fingerprint: str
    type: str
    severity: str
    file: str
    line: int | None
    description: str

    @classmethod
    def from_violation(cls, v: ArchitectureViolation) -> ViolationDelta:
        return cls(
            fingerprint=_fingerprint(v),
            type=v.type,
            severity=v.severity,
            file=v.file,
            line=v.line,
            description=v.description,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DriftReport:
    has_baseline: bool
    severity: DriftSeverity
    new_violations: list[ViolationDelta] = field(default_factory=list)
    resolved_violations: list[ViolationDelta] = field(default_factory=list)
    persistent_violations: list[ViolationDelta] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "has_baseline": self.has_baseline,
            "severity": self.severity.value,
            "new_violations": [v.to_dict() for v in self.new_violations],
            "resolved_violations": [v.to_dict() for v in self.resolved_violations],
            "persistent_violations": [v.to_dict() for v in self.persistent_violations],
            "summary": self.summary,
        }


class DriftDetector:
    """Compare current vs baseline architecture reports."""

    DEFAULT_BASELINE_RELATIVE = Path(".workpilot") / "architecture" / "baseline.json"

    def __init__(self, project_dir: Path | str | None = None) -> None:
        self.project_dir = Path(project_dir) if project_dir else None

    # ------------------------------------------------------------------
    # Baseline persistence

    def baseline_path(self, override: Path | None = None) -> Path:
        if override is not None:
            return override
        if self.project_dir is None:
            raise ValueError(
                "DriftDetector needs either project_dir or an explicit override path"
            )
        return self.project_dir / self.DEFAULT_BASELINE_RELATIVE

    def save_baseline(
        self, report: ArchitectureReport, path: Path | None = None
    ) -> Path:
        """Write the current report as the new baseline."""
        target = self.baseline_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        # Serialise both errors and warnings — drift cares about both.
        payload = {
            "violations": [v.to_dict() for v in report.violations],
            "warnings": [w.to_dict() for w in report.warnings],
        }
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return target

    def load_baseline(
        self, path: Path | None = None
    ) -> tuple[set[str], dict[str, ViolationDelta]] | None:
        """Load baseline fingerprints. Returns None if no baseline exists."""
        target = self.baseline_path(path)
        if not target.exists():
            return None
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Could not read baseline at %s: %s", target, e)
            return None

        deltas: dict[str, ViolationDelta] = {}
        for raw in payload.get("violations", []) + payload.get("warnings", []):
            v = _violation_from_dict(raw)
            d = ViolationDelta.from_violation(v)
            deltas[d.fingerprint] = d
        return set(deltas.keys()), deltas

    # ------------------------------------------------------------------
    # Drift computation

    def compare(
        self,
        current: ArchitectureReport,
        baseline_path: Path | None = None,
    ) -> DriftReport:
        """Compute drift between `current` and the baseline on disk."""
        baseline_loaded = self.load_baseline(baseline_path)

        current_deltas: dict[str, ViolationDelta] = {}
        for v in current.violations + current.warnings:
            d = ViolationDelta.from_violation(v)
            current_deltas[d.fingerprint] = d
        current_keys = set(current_deltas.keys())

        if baseline_loaded is None:
            # No baseline yet — every current violation is "persistent" (we
            # can't tell if it's drift). Severity = NONE because we have no
            # reference point to call it drift.
            return DriftReport(
                has_baseline=False,
                severity=DriftSeverity.NONE,
                persistent_violations=list(current_deltas.values()),
                summary={
                    "message": "No baseline yet — call save_baseline() to start tracking drift.",
                    "current_violations": len(current_deltas),
                },
            )

        baseline_keys, baseline_deltas = baseline_loaded
        new_keys = current_keys - baseline_keys
        resolved_keys = baseline_keys - current_keys
        persistent_keys = current_keys & baseline_keys

        new_list = [current_deltas[k] for k in new_keys]
        resolved_list = [baseline_deltas[k] for k in resolved_keys]
        persistent_list = [current_deltas[k] for k in persistent_keys]

        severity = _classify_severity(new_list)

        return DriftReport(
            has_baseline=True,
            severity=severity,
            new_violations=new_list,
            resolved_violations=resolved_list,
            persistent_violations=persistent_list,
            summary={
                "new": len(new_list),
                "resolved": len(resolved_list),
                "persistent": len(persistent_list),
                "new_errors": sum(1 for v in new_list if v.severity == "error"),
                "new_warnings": sum(1 for v in new_list if v.severity == "warning"),
            },
        )


def detect_drift(
    project_dir: Path | str,
    current: ArchitectureReport,
    baseline_path: Path | None = None,
) -> DriftReport:
    """Convenience wrapper: compare `current` against the project's baseline."""
    detector = DriftDetector(project_dir=project_dir)
    return detector.compare(current, baseline_path=baseline_path)


# ----------------------------------------------------------------------
# Helpers


def _fingerprint(v: ArchitectureViolation) -> str:
    """A stable identity for a violation, robust to line shifts within a file.

    We include type + file + import_target + rule but NOT the line number,
    because adding/removing lines above a violation shouldn't make the same
    violation look "new". Description is included as a tiebreaker.
    """
    parts = [
        v.type or "",
        v.file or "",
        v.import_target or "",
        v.rule or "",
        v.description or "",
    ]
    return "|".join(parts)


def _violation_from_dict(raw: dict[str, Any]) -> ArchitectureViolation:
    return ArchitectureViolation(
        type=raw.get("type", ""),
        severity=raw.get("severity", "warning"),
        file=raw.get("file", ""),
        line=raw.get("line"),
        import_target=raw.get("import_target", ""),
        rule=raw.get("rule", ""),
        description=raw.get("description", ""),
        suggestion=raw.get("suggestion", ""),
    )


def _classify_severity(new: list[ViolationDelta]) -> DriftSeverity:
    if not new:
        return DriftSeverity.NONE

    new_errors = sum(1 for v in new if v.severity == "error")
    new_warnings = sum(1 for v in new if v.severity == "warning")
    total = len(new)

    if total >= 10 or new_errors > 5:
        return DriftSeverity.CRITICAL
    if new_errors >= 3:
        return DriftSeverity.HIGH
    if new_errors >= 1 or new_warnings >= 4:
        return DriftSeverity.MEDIUM
    return DriftSeverity.LOW
