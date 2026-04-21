"""
Tech Debt Scanner.

Scans a project for signals of technical debt and scores each item with
a ROI = cost_if_kept / effort_to_fix heuristic so users can prioritize.

Provider-agnostic: this module is pure static analysis. The optional LLM
enrichment step (generate a spec from an item) is wired in a separate
runner that uses the project's multi-provider abstraction.

Signals detected:
  - todo_fixme:      TODO / FIXME / XXX / HACK comments
  - long_function:   Python/JS/TS function bodies > N lines
  - deep_complexity: nested loops/conditionals > N levels
  - duplication:     repeated >=6-line blocks across the project
  - stale_deps:      outdated dependencies from requirements.txt / package.json
  - low_coverage:    files in coverage.xml below threshold (optional)
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

DebtKind = Literal[
    "todo_fixme",
    "long_function",
    "deep_complexity",
    "duplication",
    "stale_deps",
    "low_coverage",
]

SCAN_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".cs"}
SKIP_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
    "__pycache__",
    ".next",
    ".turbo",
    "coverage",
    ".mypy_cache",
    ".pytest_cache",
    ".cache",
    "target",
    "out",
}

TODO_PATTERN = re.compile(
    r"(?://|#|/\*)\s*(TODO|FIXME|XXX|HACK)[:\s]?(.*)", re.IGNORECASE
)
FUNCTION_PATTERN = re.compile(
    r"^\s*(?:async\s+)?(?:def|function|fn|public|private|protected)\s+[\w$]+",
)
PACKAGE_JSON = "package.json"
REQUIREMENTS_TXT = "requirements.txt"


@dataclass
class DebtItem:
    id: str
    kind: DebtKind
    file_path: str
    line: int
    message: str
    cost: float  # estimated cost per week of ignoring (arbitrary units)
    effort: float  # estimated hours to fix
    roi: float  # cost / effort (higher = fix first)
    tags: list[str] = field(default_factory=list)
    context: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DebtTrendPoint:
    timestamp: float
    total_items: int
    total_cost: float
    avg_roi: float


@dataclass
class DebtReport:
    project_path: str
    scanned_at: float
    items: list[DebtItem]
    trend: list[DebtTrendPoint]
    summary: dict

    def to_dict(self) -> dict:
        return {
            "project_path": self.project_path,
            "scanned_at": self.scanned_at,
            "items": [i.to_dict() for i in self.items],
            "trend": [asdict(p) for p in self.trend],
            "summary": self.summary,
        }


def _iter_source_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SCAN_EXTS:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def _make_id(kind: str, file_path: str, line: int, msg: str) -> str:
    key = f"{kind}|{file_path}|{line}|{msg}".encode()
    return hashlib.sha1(key).hexdigest()[:12]  # nosec: B324 - SHA1 used for ID generation, not security


def score_roi(cost: float, effort: float) -> float:
    """ROI = cost per week / effort hours. Never divide by zero."""
    if effort <= 0:
        return cost * 10
    return round(cost / effort, 3)


def _scan_todos(root: Path) -> list[DebtItem]:
    items: list[DebtItem] = []
    for path in _iter_source_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for idx, line in enumerate(text.splitlines(), start=1):
            m = TODO_PATTERN.search(line)
            if not m:
                continue
            tag = m.group(1).upper()
            message = (m.group(2) or "").strip() or f"{tag} comment"
            cost = 2.0 if tag in ("FIXME", "XXX", "HACK") else 1.0
            effort = 0.5
            rel = str(path.relative_to(root))
            items.append(
                DebtItem(
                    id=_make_id("todo_fixme", rel, idx, message),
                    kind="todo_fixme",
                    file_path=rel,
                    line=idx,
                    message=message,
                    cost=cost,
                    effort=effort,
                    roi=score_roi(cost, effort),
                    tags=[tag.lower()],
                    context=line.strip()[:200],
                )
            )
    return items


def _scan_long_functions(root: Path, threshold: int = 60) -> list[DebtItem]:
    items: list[DebtItem] = []
    for path in _iter_source_files(root):
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        in_func = False
        func_start = 0
        func_name = ""
        indent = 0
        for idx, line in enumerate(lines, start=1):
            stripped = line.lstrip()
            cur_indent = len(line) - len(stripped)
            if FUNCTION_PATTERN.match(line):
                if in_func and (idx - func_start) > threshold:
                    rel = str(path.relative_to(root))
                    length = idx - func_start
                    cost = float(length) / 20.0
                    effort = max(1.0, length / 30.0)
                    items.append(
                        DebtItem(
                            id=_make_id("long_function", rel, func_start, func_name),
                            kind="long_function",
                            file_path=rel,
                            line=func_start,
                            message=f"{func_name or 'function'} is {length} lines (>{threshold})",
                            cost=cost,
                            effort=effort,
                            roi=score_roi(cost, effort),
                            tags=["maintainability"],
                        )
                    )
                in_func = True
                func_start = idx
                func_name = stripped.split("(")[0][:80]
                indent = cur_indent
            elif (
                in_func
                and stripped
                and cur_indent <= indent
                and not stripped.startswith(("@", "//", "#"))
            ):
                # left the function body
                if (idx - func_start) > threshold:
                    rel = str(path.relative_to(root))
                    length = idx - func_start
                    cost = float(length) / 20.0
                    effort = max(1.0, length / 30.0)
                    items.append(
                        DebtItem(
                            id=_make_id("long_function", rel, func_start, func_name),
                            kind="long_function",
                            file_path=rel,
                            line=func_start,
                            message=f"{func_name or 'function'} is {length} lines (>{threshold})",
                            cost=cost,
                            effort=effort,
                            roi=score_roi(cost, effort),
                            tags=["maintainability"],
                        )
                    )
                in_func = False
        # flush trailing function if the file ends mid-body
        if in_func and (len(lines) - func_start) > threshold:
            rel = str(path.relative_to(root))
            length = len(lines) - func_start
            cost = float(length) / 20.0
            effort = max(1.0, length / 30.0)
            items.append(
                DebtItem(
                    id=_make_id("long_function", rel, func_start, func_name),
                    kind="long_function",
                    file_path=rel,
                    line=func_start,
                    message=f"{func_name or 'function'} is {length} lines (>{threshold})",
                    cost=cost,
                    effort=effort,
                    roi=score_roi(cost, effort),
                    tags=["maintainability"],
                )
            )
    return items


def _scan_deep_complexity(root: Path, threshold: int = 5) -> list[DebtItem]:
    """Detect blocks with high indentation depth — proxy for cyclomatic complexity."""
    items: list[DebtItem] = []
    for path in _iter_source_files(root):
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        rel = str(path.relative_to(root))
        for idx, line in enumerate(lines, start=1):
            stripped = line.lstrip()
            if not stripped or stripped.startswith(("#", "//", "/*", "*")):
                continue
            depth = (len(line) - len(stripped)) // 4
            if depth > threshold and any(
                kw in stripped for kw in ("if ", "for ", "while ", "switch ", "case ")
            ):
                cost = float(depth - threshold) * 1.5
                effort = 2.0
                items.append(
                    DebtItem(
                        id=_make_id("deep_complexity", rel, idx, stripped[:40]),
                        kind="deep_complexity",
                        file_path=rel,
                        line=idx,
                        message=f"Nesting depth {depth} (>{threshold})",
                        cost=cost,
                        effort=effort,
                        roi=score_roi(cost, effort),
                        tags=["complexity"],
                        context=stripped[:200],
                    )
                )
    return items


def _scan_duplication(root: Path, block_size: int = 6) -> list[DebtItem]:
    """Detect identical code blocks of N lines across files."""
    blocks: dict[str, list[tuple[str, int]]] = {}
    for path in _iter_source_files(root):
        try:
            lines = [
                ln.strip()
                for ln in path.read_text(encoding="utf-8", errors="ignore").splitlines()
            ]
        except OSError:
            continue
        rel = str(path.relative_to(root))
        for i in range(len(lines) - block_size):
            block_lines = [
                ln
                for ln in lines[i : i + block_size]
                if ln and not ln.startswith(("#", "//"))
            ]
            if len(block_lines) < block_size - 1:
                continue
            key = hashlib.sha1("\n".join(block_lines).encode("utf-8")).hexdigest()  # nosec: B324 - SHA1 used for deduplication, not security
            blocks.setdefault(key, []).append((rel, i + 1))

    items: list[DebtItem] = []
    for key, locations in blocks.items():
        if len(locations) < 2:
            continue
        first_file, first_line = locations[0]
        cost = 1.0 * len(locations)
        effort = 1.5
        items.append(
            DebtItem(
                id=_make_id("duplication", first_file, first_line, key),
                kind="duplication",
                file_path=first_file,
                line=first_line,
                message=f"Block duplicated in {len(locations)} locations",
                cost=cost,
                effort=effort,
                roi=score_roi(cost, effort),
                tags=["duplication"],
                context=json.dumps(
                    [f"{f}:{line_num}" for f, line_num in locations[:5]]
                ),
            )
        )
    return items


def _scan_stale_deps(root: Path) -> list[DebtItem]:
    items: list[DebtItem] = []
    pkg_json = root / PACKAGE_JSON
    if pkg_json.exists():
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        for name, version in deps.items():
            if isinstance(version, str) and ("^0." in version or "~0." in version):
                items.append(
                    DebtItem(
                        id=_make_id("stale_deps", PACKAGE_JSON, 0, name),
                        kind="stale_deps",
                        file_path=PACKAGE_JSON,
                        line=0,
                        message=f"{name}@{version} is pre-1.0 (unstable)",
                        cost=1.5,
                        effort=1.0,
                        roi=score_roi(1.5, 1.0),
                        tags=["dependencies"],
                    )
                )
    req = root / REQUIREMENTS_TXT
    if req.exists():
        try:
            for idx, line in enumerate(
                req.read_text(encoding="utf-8").splitlines(), start=1
            ):
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                if "==" not in s and ">=" not in s:
                    items.append(
                        DebtItem(
                            id=_make_id("stale_deps", REQUIREMENTS_TXT, idx, s),
                            kind="stale_deps",
                            file_path=REQUIREMENTS_TXT,
                            line=idx,
                            message=f"{s} is unpinned",
                            cost=1.0,
                            effort=0.5,
                            roi=score_roi(1.0, 0.5),
                            tags=["dependencies", "unpinned"],
                        )
                    )
        except OSError:
            pass
    return items


def _load_trend(trend_file: Path) -> list[DebtTrendPoint]:
    if not trend_file.exists():
        return []
    try:
        payload = json.loads(trend_file.read_text(encoding="utf-8"))
        return [DebtTrendPoint(**p) for p in payload]
    except (OSError, ValueError, TypeError):
        return []


def _persist_trend(
    trend_file: Path, new_point: DebtTrendPoint, max_points: int = 60
) -> list[DebtTrendPoint]:
    existing = _load_trend(trend_file)
    existing.append(new_point)
    existing = existing[-max_points:]
    trend_file.parent.mkdir(parents=True, exist_ok=True)
    trend_file.write_text(
        json.dumps([asdict(p) for p in existing], indent=2), encoding="utf-8"
    )
    return existing


def scan_project(
    project_path: str | Path,
    kinds: list[DebtKind] | None = None,
    persist: bool = True,
) -> DebtReport:
    """Run all enabled scanners and produce a report with ROI scores."""
    import time

    root = Path(project_path).resolve()
    if not root.exists():
        raise ValueError(f"project_path does not exist: {root}")

    enabled = set(
        kinds
        or [
            "todo_fixme",
            "long_function",
            "deep_complexity",
            "duplication",
            "stale_deps",
        ]
    )
    items: list[DebtItem] = []
    if "todo_fixme" in enabled:
        items.extend(_scan_todos(root))
    if "long_function" in enabled:
        items.extend(_scan_long_functions(root))
    if "deep_complexity" in enabled:
        items.extend(_scan_deep_complexity(root))
    if "duplication" in enabled:
        items.extend(_scan_duplication(root))
    if "stale_deps" in enabled:
        items.extend(_scan_stale_deps(root))

    items.sort(key=lambda i: i.roi, reverse=True)

    summary = {
        "total": len(items),
        "by_kind": {
            k: sum(1 for i in items if i.kind == k) for k in {i.kind for i in items}
        },
        "total_cost": round(sum(i.cost for i in items), 2),
        "total_effort": round(sum(i.effort for i in items), 2),
        "avg_roi": round(sum(i.roi for i in items) / len(items), 3) if items else 0.0,
    }

    now = time.time()
    trend_file = root / ".workpilot" / "tech_debt" / "trend.json"
    point = DebtTrendPoint(
        timestamp=now,
        total_items=summary["total"],
        total_cost=float(summary["total_cost"]),
        avg_roi=float(summary["avg_roi"]),
    )
    trend = _persist_trend(trend_file, point) if persist else []

    report = DebtReport(
        project_path=str(root),
        scanned_at=now,
        items=items,
        trend=trend,
        summary=summary,
    )
    if persist:
        snapshot_dir = root / ".workpilot" / "tech_debt"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        (snapshot_dir / "last_report.json").write_text(
            json.dumps(report.to_dict(), indent=2), encoding="utf-8"
        )
    return report
