"""
Dependency Graph Cache
=======================

Persists the dependency graph to .workpilot/dependency_graph.json.
Invalidates when the project file set changes (hash of sorted file paths + mtimes).
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

from .builder import _JS_TS_EXTS, _PYTHON_EXTS, _SKIP_DIRS, DependencyGraphBuilder
from .models import DependencyGraph

logger = logging.getLogger(__name__)

_CACHE_FILE = "dependency_graph.json"
_SUPPORTED_EXTS = _PYTHON_EXTS | _JS_TS_EXTS


class DependencyGraphCache:
    """
    Manages a cached DependencyGraph for a project.

    The cache is invalidated whenever the set of source files or their
    modification timestamps change.
    """

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir).resolve()
        self._cache_path = self.project_dir / ".workpilot" / _CACHE_FILE

    # ── Public API ─────────────────────────────────────────────────────────

    def get_or_build(self, force_rebuild: bool = False) -> DependencyGraph:
        """
        Return the cached graph if up-to-date, otherwise rebuild and cache it.

        Args:
            force_rebuild: Skip cache check and always rebuild

        Returns:
            Up-to-date DependencyGraph
        """
        current_hash = self._compute_fingerprint()

        if not force_rebuild:
            cached = self._load_cache()
            if cached is not None:
                cached_hash = cached.get("fingerprint", "")
                if cached_hash == current_hash:
                    return DependencyGraph.from_dict(cached)

        # Build fresh graph
        builder = DependencyGraphBuilder(self.project_dir)
        graph = builder.build()
        self._save_cache(graph, current_hash)
        return graph

    def invalidate(self) -> None:
        """Remove the cache file, forcing a rebuild on next access."""
        if self._cache_path.exists():
            self._cache_path.unlink()

    # ── Fingerprinting ─────────────────────────────────────────────────────

    def _compute_fingerprint(self) -> str:
        """
        Compute a hash of all source file paths and their modification times.
        Changes when files are added, removed, or modified.
        """
        entries: list[str] = []
        for path in sorted(self.project_dir.rglob("*")):
            if not path.is_file():
                continue
            if any(part in _SKIP_DIRS for part in path.parts):
                continue
            if path.suffix.lower() not in _SUPPORTED_EXTS:
                continue
            rel = str(path.relative_to(self.project_dir)).replace("\\", "/")
            mtime = path.stat().st_mtime_ns
            entries.append(f"{rel}:{mtime}")

        content = "\n".join(entries)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    # ── Persistence ────────────────────────────────────────────────────────

    def _load_cache(self) -> dict | None:
        if not self._cache_path.exists():
            return None
        try:
            with open(self._cache_path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

    def _save_cache(self, graph: DependencyGraph, fingerprint: str) -> None:
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        data = graph.to_dict()
        data["fingerprint"] = fingerprint
        try:
            with open(self._cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except OSError:
            logger.debug("Dependency graph cache write failed at %s", self._cache_path, exc_info=True)
