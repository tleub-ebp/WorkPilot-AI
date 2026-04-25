"""Auto-Licensing & Dependency Governance.

Pipeline
--------

1. **Discover** dependencies in the project — parse package.json,
   requirements.txt, pyproject.toml, Cargo.toml, go.mod.
2. **Resolve licences** — for each dependency, look up its declared
   licence (best-effort; we don't go online by default — callers can
   inject a registry resolver).
3. **Classify** each licence as permissive / weak_copyleft / strong_copyleft
   / network_copyleft / commercial / unknown.
4. **Apply policy** — given a `LicensePolicy` (a list of categories the
   project is allowed to consume), emit `LicenseConflict`s for every
   violation, with a one-line remediation hint.

The classification table covers ~30 SPDX ids that account for >95% of
real-world OSS dependencies.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class LicenseCategory(str, Enum):
    PERMISSIVE = "permissive"  # MIT, BSD, Apache-2.0, ISC, …
    WEAK_COPYLEFT = "weak_copyleft"  # LGPL, MPL-2.0, EPL — lib-level copyleft
    STRONG_COPYLEFT = "strong_copyleft"  # GPL-2.0/-3.0 — viral
    NETWORK_COPYLEFT = "network_copyleft"  # AGPL — viral over the network
    PUBLIC_DOMAIN = "public_domain"  # CC0, Unlicense, WTFPL
    COMMERCIAL = "commercial"  # proprietary / EULA
    UNKNOWN = "unknown"  # not declared / not in our table


# Curated SPDX → category map. Permissive entries are the long tail.
_LICENSE_TABLE: dict[str, LicenseCategory] = {
    # Permissive
    "mit": LicenseCategory.PERMISSIVE,
    "mit license": LicenseCategory.PERMISSIVE,
    "isc": LicenseCategory.PERMISSIVE,
    "apache-2.0": LicenseCategory.PERMISSIVE,
    "apache 2.0": LicenseCategory.PERMISSIVE,
    "apache-2": LicenseCategory.PERMISSIVE,
    "asl-2.0": LicenseCategory.PERMISSIVE,
    "bsd": LicenseCategory.PERMISSIVE,
    "bsd-2-clause": LicenseCategory.PERMISSIVE,
    "bsd-3-clause": LicenseCategory.PERMISSIVE,
    "bsd 3-clause": LicenseCategory.PERMISSIVE,
    "0bsd": LicenseCategory.PERMISSIVE,
    "zlib": LicenseCategory.PERMISSIVE,
    "x11": LicenseCategory.PERMISSIVE,
    "python-2.0": LicenseCategory.PERMISSIVE,
    "psf-2.0": LicenseCategory.PERMISSIVE,
    "boost software license 1.0": LicenseCategory.PERMISSIVE,
    "bsl-1.0": LicenseCategory.PERMISSIVE,
    # Weak copyleft (library boundary)
    "lgpl-2.1": LicenseCategory.WEAK_COPYLEFT,
    "lgpl-2.1-only": LicenseCategory.WEAK_COPYLEFT,
    "lgpl-2.1-or-later": LicenseCategory.WEAK_COPYLEFT,
    "lgpl-3.0": LicenseCategory.WEAK_COPYLEFT,
    "lgpl-3.0-only": LicenseCategory.WEAK_COPYLEFT,
    "lgpl-3.0-or-later": LicenseCategory.WEAK_COPYLEFT,
    "mpl-2.0": LicenseCategory.WEAK_COPYLEFT,
    "epl-1.0": LicenseCategory.WEAK_COPYLEFT,
    "epl-2.0": LicenseCategory.WEAK_COPYLEFT,
    "cddl-1.0": LicenseCategory.WEAK_COPYLEFT,
    "cddl-1.1": LicenseCategory.WEAK_COPYLEFT,
    # Strong copyleft (whole-program copyleft)
    "gpl-2.0": LicenseCategory.STRONG_COPYLEFT,
    "gpl-2.0-only": LicenseCategory.STRONG_COPYLEFT,
    "gpl-2.0-or-later": LicenseCategory.STRONG_COPYLEFT,
    "gpl-3.0": LicenseCategory.STRONG_COPYLEFT,
    "gpl-3.0-only": LicenseCategory.STRONG_COPYLEFT,
    "gpl-3.0-or-later": LicenseCategory.STRONG_COPYLEFT,
    # Network copyleft (SaaS-killer)
    "agpl-3.0": LicenseCategory.NETWORK_COPYLEFT,
    "agpl-3.0-only": LicenseCategory.NETWORK_COPYLEFT,
    "agpl-3.0-or-later": LicenseCategory.NETWORK_COPYLEFT,
    # Public-domain-equivalent
    "cc0-1.0": LicenseCategory.PUBLIC_DOMAIN,
    "unlicense": LicenseCategory.PUBLIC_DOMAIN,
    "wtfpl": LicenseCategory.PUBLIC_DOMAIN,
    # Common commercial markers
    "commercial": LicenseCategory.COMMERCIAL,
    "proprietary": LicenseCategory.COMMERCIAL,
    "see eula": LicenseCategory.COMMERCIAL,
    "see license": LicenseCategory.COMMERCIAL,
}

# Default suggestion table — when a category is forbidden, what to do.
_REMEDIATION_HINT = {
    LicenseCategory.STRONG_COPYLEFT: (
        "Replace with a permissive alternative or wall it off behind an IPC boundary."
    ),
    LicenseCategory.NETWORK_COPYLEFT: (
        "AGPL contaminates SaaS deployments — find an MIT/Apache replacement."
    ),
    LicenseCategory.WEAK_COPYLEFT: (
        "Acceptable if linked dynamically; review legal exposure."
    ),
    LicenseCategory.COMMERCIAL: (
        "Confirm a paid licence covers your usage; track renewals."
    ),
    LicenseCategory.UNKNOWN: ("Look up the upstream licence and add it to the policy."),
}


def classify_license(raw: str | None) -> LicenseCategory:
    """Map a free-form licence string to a category.

    Handles SPDX-like ``MIT OR Apache-2.0`` expressions by taking the
    most-permissive match (a permissive option in an OR expression
    means the project can pick the permissive one).
    """
    if not raw:
        return LicenseCategory.UNKNOWN
    text = raw.strip().lower()

    # Split SPDX-style "X OR Y" into the most-permissive of the two.
    # We classify each part and pick the highest-ranked (most permissive).
    rank = {
        LicenseCategory.PUBLIC_DOMAIN: 0,
        LicenseCategory.PERMISSIVE: 1,
        LicenseCategory.WEAK_COPYLEFT: 2,
        LicenseCategory.STRONG_COPYLEFT: 3,
        LicenseCategory.NETWORK_COPYLEFT: 4,
        LicenseCategory.COMMERCIAL: 5,
        LicenseCategory.UNKNOWN: 6,
    }
    parts = re.split(r"\s+(?:or|/)\s+", text)
    best: LicenseCategory | None = None
    for part in parts:
        cleaned = part.strip().strip("()")
        cat = _LICENSE_TABLE.get(cleaned, LicenseCategory.UNKNOWN)
        if best is None or rank[cat] < rank[best]:
            best = cat
    return best or LicenseCategory.UNKNOWN


# ----------------------------------------------------------------------
# Data models


@dataclass(frozen=True)
class DependencyRecord:
    name: str
    version: str
    ecosystem: str  # npm | pypi | cargo | go
    declared_license: str | None = None
    is_direct: bool = True

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "ecosystem": self.ecosystem,
            "declared_license": self.declared_license,
            "is_direct": self.is_direct,
        }


@dataclass
class LicenseConflict:
    dependency: DependencyRecord
    category: LicenseCategory
    reason: str
    remediation: str

    def to_dict(self) -> dict:
        return {
            "dependency": self.dependency.to_dict(),
            "category": self.category.value,
            "reason": self.reason,
            "remediation": self.remediation,
        }


@dataclass
class LicensePolicy:
    """A set of allowed categories. Anything else triggers a conflict."""

    allowed: frozenset[LicenseCategory] = frozenset(
        {LicenseCategory.PERMISSIVE, LicenseCategory.PUBLIC_DOMAIN}
    )

    @classmethod
    def permissive_only(cls) -> LicensePolicy:
        return cls(
            allowed=frozenset(
                {LicenseCategory.PERMISSIVE, LicenseCategory.PUBLIC_DOMAIN}
            )
        )

    @classmethod
    def open_source_friendly(cls) -> LicensePolicy:
        """Permissive + weak copyleft — typical for an internal tool."""
        return cls(
            allowed=frozenset(
                {
                    LicenseCategory.PERMISSIVE,
                    LicenseCategory.PUBLIC_DOMAIN,
                    LicenseCategory.WEAK_COPYLEFT,
                }
            )
        )

    @classmethod
    def saas_safe(cls) -> LicensePolicy:
        """Same as permissive_only — explicitly excludes AGPL."""
        return cls.permissive_only()


@dataclass
class LicenseReport:
    dependencies: list[DependencyRecord] = field(default_factory=list)
    conflicts: list[LicenseConflict] = field(default_factory=list)
    by_category: dict[str, int] = field(default_factory=dict)
    summary: dict = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return not self.conflicts

    def to_dict(self) -> dict:
        return {
            "dependencies": [d.to_dict() for d in self.dependencies],
            "conflicts": [c.to_dict() for c in self.conflicts],
            "by_category": self.by_category,
            "summary": self.summary,
            "passed": self.passed,
        }


# ----------------------------------------------------------------------
# Manifest parsers


def _parse_package_json(path: Path) -> list[DependencyRecord]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    deps: list[DependencyRecord] = []
    for is_direct, key in ((True, "dependencies"), (False, "devDependencies")):
        block = data.get(key) or {}
        for name, version in block.items():
            deps.append(
                DependencyRecord(
                    name=name,
                    version=str(version),
                    ecosystem="npm",
                    is_direct=is_direct,
                )
            )
    return deps


_REQ_LINE_RE = re.compile(
    r"^([A-Za-z0-9._-]+)\s*(?:\[[^\]]+\])?\s*([<>=!~]=?[^;#\s]*)?"
)


def _parse_requirements_txt(path: Path) -> list[DependencyRecord]:
    deps: list[DependencyRecord] = []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        m = _REQ_LINE_RE.match(line)
        if not m:
            continue
        name, version = m.group(1), (m.group(2) or "").strip()
        deps.append(
            DependencyRecord(
                name=name, version=version, ecosystem="pypi", is_direct=True
            )
        )
    return deps


def _parse_pyproject_toml(path: Path) -> list[DependencyRecord]:
    """Parse PEP 621 dependencies. Falls back gracefully without `tomllib`."""
    try:
        import tomllib  # type: ignore[import-not-found]
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[import-not-found]
        except ImportError:
            return []
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, ValueError):
        return []
    project = data.get("project", {})
    raw_deps: list[str] = project.get("dependencies", []) or []
    deps: list[DependencyRecord] = []
    for entry in raw_deps:
        m = _REQ_LINE_RE.match(entry.strip())
        if not m:
            continue
        deps.append(
            DependencyRecord(
                name=m.group(1),
                version=(m.group(2) or "").strip(),
                ecosystem="pypi",
                is_direct=True,
            )
        )
    return deps


def _parse_cargo_toml(path: Path) -> list[DependencyRecord]:
    try:
        import tomllib  # type: ignore[import-not-found]
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[import-not-found]
        except ImportError:
            return []
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, ValueError):
        return []
    deps: list[DependencyRecord] = []
    for is_direct, key in ((True, "dependencies"), (False, "dev-dependencies")):
        block = data.get(key) or {}
        for name, value in block.items():
            version = value if isinstance(value, str) else (value.get("version") or "")
            deps.append(
                DependencyRecord(
                    name=name,
                    version=str(version),
                    ecosystem="cargo",
                    is_direct=is_direct,
                )
            )
    return deps


def _parse_go_mod(path: Path) -> list[DependencyRecord]:
    deps: list[DependencyRecord] = []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    in_block = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("require ("):
            in_block = True
            continue
        if in_block and stripped == ")":
            in_block = False
            continue
        if in_block:
            parts = stripped.split()
            if len(parts) >= 2:
                deps.append(
                    DependencyRecord(
                        name=parts[0], version=parts[1], ecosystem="go", is_direct=True
                    )
                )
        elif stripped.startswith("require "):
            parts = stripped.split()
            if len(parts) >= 3:
                deps.append(
                    DependencyRecord(
                        name=parts[1], version=parts[2], ecosystem="go", is_direct=True
                    )
                )
    return deps


_PARSERS: list[tuple[str, Callable[[Path], list[DependencyRecord]]]] = [
    ("package.json", _parse_package_json),
    ("requirements.txt", _parse_requirements_txt),
    ("pyproject.toml", _parse_pyproject_toml),
    ("Cargo.toml", _parse_cargo_toml),
    ("go.mod", _parse_go_mod),
]


# ----------------------------------------------------------------------
# Scanner


# A LicenseResolver maps a (ecosystem, name, version) → declared licence
# string. Default = "look in the manifest" (npm package.json's "license"
# field). For the others we'd need to query the registry; the resolver
# hook lets callers inject that.
LicenseResolver = Callable[[DependencyRecord], str | None]


def _default_resolver(dep: DependencyRecord) -> str | None:
    """No-op resolver — returns whatever the manifest already declared."""
    return dep.declared_license


class LicenseScanner:
    """Scan a project tree, classify licences, apply a policy."""

    def __init__(
        self,
        project_dir: Path | str,
        policy: LicensePolicy | None = None,
        resolver: LicenseResolver | None = None,
    ) -> None:
        self.project_dir = Path(project_dir)
        self.policy = policy or LicensePolicy.permissive_only()
        self.resolver = resolver or _default_resolver

    def discover(self) -> list[DependencyRecord]:
        """Walk the project tree and parse every supported manifest."""
        all_deps: list[DependencyRecord] = []
        seen: set[tuple[str, str, str]] = set()
        for filename, parser in _PARSERS:
            for path in self.project_dir.rglob(filename):
                if any(
                    p in {"node_modules", ".venv", "venv", "vendor"} for p in path.parts
                ):
                    continue
                # If this is package.json itself: pull "license" too.
                license_field: str | None = None
                if filename == "package.json":
                    try:
                        license_field = json.loads(
                            path.read_text(encoding="utf-8")
                        ).get("license")
                    except (OSError, json.JSONDecodeError):
                        license_field = None
                for dep in parser(path):
                    key = (dep.ecosystem, dep.name, dep.version)
                    if key in seen:
                        continue
                    seen.add(key)
                    if filename == "package.json" and dep.declared_license is None:
                        # The host project itself may have a license field but
                        # individual deps in package.json don't carry one.
                        # We leave declared_license=None — the resolver hook
                        # is responsible for filling it from the registry.
                        pass
                    all_deps.append(dep)
                # Note: we don't propagate the host's license_field to its deps;
                # it just means we *could* read the host's own licence later.
                _ = license_field
        return all_deps

    def scan(self) -> LicenseReport:
        deps = self.discover()
        # Resolve licences via the injected resolver.
        resolved: list[DependencyRecord] = []
        for dep in deps:
            declared = self.resolver(dep)
            resolved.append(
                DependencyRecord(
                    name=dep.name,
                    version=dep.version,
                    ecosystem=dep.ecosystem,
                    declared_license=declared,
                    is_direct=dep.is_direct,
                )
            )

        conflicts: list[LicenseConflict] = []
        category_counts: dict[str, int] = {}
        for dep in resolved:
            cat = classify_license(dep.declared_license)
            category_counts[cat.value] = category_counts.get(cat.value, 0) + 1
            if cat not in self.policy.allowed:
                conflicts.append(
                    LicenseConflict(
                        dependency=dep,
                        category=cat,
                        reason=(
                            f"License {dep.declared_license!r} (category={cat.value}) "
                            "is not in the project's allowed set."
                        ),
                        remediation=_REMEDIATION_HINT.get(
                            cat, "Review and update the project policy if intentional."
                        ),
                    )
                )

        summary = {
            "total_dependencies": len(resolved),
            "by_ecosystem": _count(resolved, lambda d: d.ecosystem),
            "direct": sum(1 for d in resolved if d.is_direct),
            "transitive": sum(1 for d in resolved if not d.is_direct),
            "conflict_count": len(conflicts),
            "policy_allowed": sorted(c.value for c in self.policy.allowed),
        }

        return LicenseReport(
            dependencies=resolved,
            conflicts=conflicts,
            by_category=category_counts,
            summary=summary,
        )


def _count(
    items: list[DependencyRecord], key: Callable[[DependencyRecord], str]
) -> dict[str, int]:
    out: dict[str, int] = {}
    for it in items:
        k = key(it)
        out[k] = out.get(k, 0) + 1
    return out
