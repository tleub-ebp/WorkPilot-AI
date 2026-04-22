"""Regression guards for critical dependency version pins.

These tests exist to make accidental loosening of our minimum-version
constraints fail loudly, rather than silently breaking runtime behavior.
Every constant here corresponds to a comment in ``requirements.txt``
explaining *why* the floor exists — keep them in sync.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REQUIREMENTS_PATH = (
    Path(__file__).resolve().parents[2] / "apps" / "backend" / "requirements.txt"
)


# Minimum versions with a recorded reason (see requirements.txt comments).
# (package, minimum_version, rationale)
_CRITICAL_PINS: tuple[tuple[str, str, str], ...] = (
    (
        "claude-agent-sdk",
        "0.1.25",
        "0.1.25+ required for improved tool_use concurrency handling "
        "(earlier versions raised 400 errors on partial tool_use failures).",
    ),
    (
        "httpx",
        "0.27.0",
        "0.27.0+ required for Timeout(connect=...) and HTTP/2 with h2 extra.",
    ),
    (
        "pydantic",
        "2.0.0",
        "Pydantic v2 API is used throughout the backend.",
    ),
    (
        "fastapi",
        "0.100.0",
        "0.100+ required for Pydantic v2 integration.",
    ),
)


_LINE_PATTERN = re.compile(
    r"^(?P<name>[A-Za-z0-9_\-\.]+)\s*(?:\[[^\]]+\])?\s*>=\s*(?P<version>[\w\.\-]+)"
)


def _parse_requirements() -> dict[str, str]:
    """Return a mapping of package name -> declared minimum version."""
    result: dict[str, str] = {}
    for raw_line in _REQUIREMENTS_PATH.read_text(encoding="utf-8").splitlines():
        # Drop comments / inline comments / markers (``; python_version ...``).
        line = raw_line.split("#", 1)[0].split(";", 1)[0].strip()
        if not line:
            continue
        match = _LINE_PATTERN.match(line)
        if match:
            result[match.group("name").lower()] = match.group("version")
    return result


def _version_tuple(version: str) -> tuple[int, ...]:
    """Best-effort version parse — we only need ordering for ``>=`` compares."""
    parts: list[int] = []
    for chunk in version.split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


@pytest.mark.parametrize(("package", "minimum", "rationale"), _CRITICAL_PINS)
def test_minimum_version_is_pinned(
    package: str, minimum: str, rationale: str
) -> None:
    """Fail if ``requirements.txt`` loosens below the documented floor.

    The rationale is surfaced in the failure message so the maintainer
    lowering the bound sees *why* the pin existed in the first place.
    """
    pins = _parse_requirements()
    declared = pins.get(package.lower())
    assert declared is not None, (
        f"{package} is no longer listed in requirements.txt. "
        f"If it was intentionally removed, drop it from _CRITICAL_PINS as well."
    )
    assert _version_tuple(declared) >= _version_tuple(minimum), (
        f"{package} is pinned at >={declared} in requirements.txt but must be "
        f">={minimum}. Reason: {rationale}"
    )
