"""Real registry resolvers for the license scanner.

The base scanner (`license_governance.scanner`) takes an injectable
resolver: a callable `(DependencyRecord) -> str | None` that returns the
declared licence for a dep. This module ships two real resolvers that
hit the npm and PyPI registries over HTTPS, plus a small in-process
cache so we don't hammer the registries.

Both resolvers degrade silently to `None` on network failure: the
scanner then classifies the dep as `UNKNOWN` rather than crashing.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

from .scanner import DependencyRecord

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cache


class _TtlCache:
    """Tiny thread-safe TTL cache. Process-local, no eviction beyond TTL."""

    def __init__(self, ttl_seconds: int = 24 * 3600) -> None:
        self.ttl = ttl_seconds
        self._lock = threading.Lock()
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return _MISS
            ts, value = entry
            if time.time() - ts > self.ttl:
                self._store.pop(key, None)
                return _MISS
            return value

    def put(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = (time.time(), value)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


_MISS = object()
_cache = _TtlCache()


# ---------------------------------------------------------------------------
# HTTP


_USER_AGENT = "WorkPilotAI-license-scanner/1.0"
_TIMEOUT = 5.0


def _http_get_json(url: str) -> dict | None:
    """Fetch + parse JSON. Returns None on any failure (logged at DEBUG)."""
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": _USER_AGENT, "Accept": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:  # noqa: S310 — explicit https URLs
            if resp.status >= 400:
                return None
            payload = resp.read()
            if not payload:
                return None
            return json.loads(payload.decode("utf-8"))
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        json.JSONDecodeError,
        TimeoutError,
    ) as e:
        logger.debug("Registry fetch failed for %s: %s", url, e)
        return None
    except OSError as e:
        # Catches ConnectionResetError, gaierror, etc. on Windows.
        logger.debug("Registry network error for %s: %s", url, e)
        return None


# ---------------------------------------------------------------------------
# npm


def _normalise_license_field(value: Any) -> str | None:
    """npm `license` field can be a string, an object, or a list."""
    if value is None:
        return None
    if isinstance(value, str):
        return value or None
    if isinstance(value, dict):
        return value.get("type") or value.get("name") or None
    if isinstance(value, list):
        # Older packages: list of `{type, url}` dicts.
        names = [_normalise_license_field(v) for v in value]
        names = [n for n in names if n]
        if not names:
            return None
        # Combine with " OR " — the classifier picks the most permissive.
        return " OR ".join(names)
    return None


def npm_resolver(dep: DependencyRecord) -> str | None:
    """Look up a package's licence on the npm registry."""
    if dep.ecosystem != "npm" or not dep.name:
        return None

    cached = _cache.get(f"npm:{dep.name}")
    if cached is not _MISS:
        return cached

    # The /-/v1/ endpoints are heavier; the package root is enough for the
    # `license` field on the latest version.
    url = f"https://registry.npmjs.org/{urllib.parse.quote(dep.name, safe='@/')}"
    payload = _http_get_json(url)
    if payload is None:
        return None

    # Latest version's license is the most relevant — fall back to the
    # top-level `license` field if `dist-tags.latest` is missing.
    license_value: str | None = None
    versions = payload.get("versions") or {}
    latest_tag = (payload.get("dist-tags") or {}).get("latest")
    if latest_tag and isinstance(versions, dict):
        latest_pkg = versions.get(latest_tag) or {}
        license_value = _normalise_license_field(latest_pkg.get("license"))
    if not license_value:
        license_value = _normalise_license_field(payload.get("license"))

    _cache.put(f"npm:{dep.name}", license_value)
    return license_value


# ---------------------------------------------------------------------------
# PyPI


def pypi_resolver(dep: DependencyRecord) -> str | None:
    """Look up a package's licence on the PyPI registry."""
    if dep.ecosystem != "pypi" or not dep.name:
        return None

    cached = _cache.get(f"pypi:{dep.name}")
    if cached is not _MISS:
        return cached

    url = f"https://pypi.org/pypi/{urllib.parse.quote(dep.name, safe='')}/json"
    payload = _http_get_json(url)
    if payload is None:
        return None

    info = payload.get("info") or {}
    # PyPI fills `license` with the SPDX name OR the full text. Many newer
    # packages prefer classifiers like "License :: OSI Approved :: MIT License".
    license_value: str | None = info.get("license") or None

    if not license_value:
        for classifier in info.get("classifiers") or []:
            if isinstance(classifier, str) and classifier.startswith("License :: "):
                # Take the leaf — the part after the last "::".
                license_value = classifier.split("::")[-1].strip()
                if license_value:
                    break

    # Some packages ship a 2 KB licence text instead of an SPDX id. We
    # only forward short values to the classifier — anything > 200 chars
    # is almost certainly a full licence text and won't classify cleanly.
    if license_value and len(license_value) > 200:
        license_value = None

    _cache.put(f"pypi:{dep.name}", license_value)
    return license_value


# ---------------------------------------------------------------------------
# Composition


def make_registry_resolver(
    *,
    enable_npm: bool = True,
    enable_pypi: bool = True,
    fallback: Callable[[DependencyRecord], str | None] | None = None,
) -> Callable[[DependencyRecord], str | None]:
    """Build a resolver that picks the right registry based on `ecosystem`.

    Args:
        enable_npm: route `npm` deps to the npm registry.
        enable_pypi: route `pypi` deps to PyPI.
        fallback: called for anything we can't resolve (cargo / go / unknown
            ecosystems). Defaults to `dep.declared_license` (the manifest value).
    """
    if fallback is None:
        fallback = lambda dep: dep.declared_license  # noqa: E731

    def _resolve(dep: DependencyRecord) -> str | None:
        if enable_npm and dep.ecosystem == "npm":
            value = npm_resolver(dep)
            if value:
                return value
        if enable_pypi and dep.ecosystem == "pypi":
            value = pypi_resolver(dep)
            if value:
                return value
        return fallback(dep)

    return _resolve


def reset_cache_for_tests() -> None:
    _cache.clear()
