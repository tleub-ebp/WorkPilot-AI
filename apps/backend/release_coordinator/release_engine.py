"""
Release Train Coordinator — Orchestrate multi-service releases.

Manages semantic versioning, changelog generation, dependency ordering,
release branch creation, and go/no-go gate checks across multiple
services in a monorepo or multi-repo setup.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class BumpType(str, Enum):
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    NONE = "none"


class ReleaseStatus(str, Enum):
    PLANNING = "planning"
    STAGING = "staging"
    GATE_CHECK = "gate_check"
    RELEASING = "releasing"
    RELEASED = "released"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class GateStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    PENDING = "pending"
    SKIPPED = "skipped"


@dataclass
class SemVer:
    """Semantic version."""

    major: int = 0
    minor: int = 0
    patch: int = 0
    prerelease: str = ""

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        return f"{base}-{self.prerelease}" if self.prerelease else base

    def bump(self, bump_type: BumpType) -> SemVer:
        if bump_type == BumpType.MAJOR:
            return SemVer(self.major + 1, 0, 0)
        if bump_type == BumpType.MINOR:
            return SemVer(self.major, self.minor + 1, 0)
        if bump_type == BumpType.PATCH:
            return SemVer(self.major, self.minor, self.patch + 1)
        return SemVer(self.major, self.minor, self.patch)

    @classmethod
    def parse(cls, version_str: str) -> SemVer:
        match = re.match(r"v?(\d+)\.(\d+)\.(\d+)(?:-(.+))?", version_str)
        if not match:
            return cls()
        return cls(
            major=int(match.group(1)),
            minor=int(match.group(2)),
            patch=int(match.group(3)),
            prerelease=match.group(4) or "",
        )


@dataclass
class ServiceRelease:
    """Release plan for a single service."""

    name: str
    current_version: SemVer = field(default_factory=SemVer)
    next_version: SemVer = field(default_factory=SemVer)
    bump_type: BumpType = BumpType.NONE
    changelog_entries: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    gates: dict[str, GateStatus] = field(default_factory=dict)


@dataclass
class GateCheck:
    """A release gate check result."""

    name: str
    status: GateStatus = GateStatus.PENDING
    message: str = ""


@dataclass
class ReleaseTrainPlan:
    """A coordinated release plan across services."""

    id: str = ""
    services: list[ServiceRelease] = field(default_factory=list)
    status: ReleaseStatus = ReleaseStatus.PLANNING
    gates: list[GateCheck] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    @property
    def all_gates_passed(self) -> bool:
        return all(g.status == GateStatus.PASSED for g in self.gates)

    @property
    def summary(self) -> str:
        service_parts = [f"{s.name}: {s.current_version} → {s.next_version}" for s in self.services if s.bump_type != BumpType.NONE]
        return ", ".join(service_parts) or "No version changes"


_CONVENTIONAL_COMMIT_PATTERN = re.compile(
    r"^(?P<type>feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
    r"(?:\((?P<scope>[^)]+)\))?!?:\s*(?P<description>.+)$",
    re.MULTILINE,
)


class ReleaseEngine:
    """Coordinate multi-service releases.

    Usage::

        engine = ReleaseEngine()
        plan = engine.plan_release(commits, services)
        engine.run_gates(plan)
    """

    def determine_bump(self, commits: list[str]) -> BumpType:
        """Determine version bump from conventional commit messages."""
        has_breaking = any("!" in c.split(":")[0] or "BREAKING CHANGE" in c for c in commits)
        has_feat = any(c.startswith("feat") for c in commits)
        has_fix = any(c.startswith("fix") for c in commits)

        if has_breaking:
            return BumpType.MAJOR
        if has_feat:
            return BumpType.MINOR
        if has_fix:
            return BumpType.PATCH
        return BumpType.NONE

    def generate_changelog(self, commits: list[str]) -> list[str]:
        """Generate changelog entries from conventional commits."""
        entries: list[str] = []
        for commit in commits:
            match = _CONVENTIONAL_COMMIT_PATTERN.match(commit)
            if match:
                ctype = match.group("type")
                scope = match.group("scope") or ""
                desc = match.group("description")
                prefix = f"**{scope}:** " if scope else ""
                entries.append(f"- {prefix}{desc} ({ctype})")
        return entries

    def plan_release(
        self,
        services: list[ServiceRelease],
        default_gates: list[str] | None = None,
    ) -> ReleaseTrainPlan:
        """Create a coordinated release plan."""
        plan = ReleaseTrainPlan(
            id=f"release-{int(time.time())}",
            services=services,
        )

        gate_names = default_gates or ["ci_pass", "qa_review", "security_scan", "staging_deploy"]
        plan.gates = [GateCheck(name=g) for g in gate_names]

        # Topological order by dependencies
        plan.services = self._order_by_deps(services)
        return plan

    def run_gate(self, plan: ReleaseTrainPlan, gate_name: str, passed: bool, message: str = "") -> None:
        """Update a gate check result."""
        for gate in plan.gates:
            if gate.name == gate_name:
                gate.status = GateStatus.PASSED if passed else GateStatus.FAILED
                gate.message = message
                break

        if plan.all_gates_passed:
            plan.status = ReleaseStatus.RELEASING

    @staticmethod
    def _order_by_deps(services: list[ServiceRelease]) -> list[ServiceRelease]:
        """Simple topological sort by dependencies."""
        name_map = {s.name: s for s in services}
        ordered: list[ServiceRelease] = []
        visited: set[str] = set()

        def visit(name: str) -> None:
            if name in visited or name not in name_map:
                return
            visited.add(name)
            for dep in name_map[name].dependencies:
                visit(dep)
            ordered.append(name_map[name])

        for s in services:
            visit(s.name)
        return ordered
