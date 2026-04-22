"""Tests for the Python loader of ``config/configured_providers.json``.

We validate both the happy path (loader produces the expected shape)
and the error path (malformed JSON surfaces a clear exception rather
than silently returning empty strings).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[2] / "apps" / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from core.configured_providers import (  # noqa: E402
    ConfiguredProvider,
    load_configured_providers,
)


def _write_providers(tmp_path: Path, payload: object) -> Path:
    path = tmp_path / "configured_providers.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_default_path_loads_canonical_list() -> None:
    """The loader works against the real file at the repo root."""
    providers = load_configured_providers()
    assert len(providers) >= 1
    # All entries have the expected shape.
    assert all(isinstance(p, ConfiguredProvider) for p in providers)
    assert all(p.name and p.label and p.description for p in providers)
    # Names are unique.
    names = [p.name for p in providers]
    assert len(names) == len(set(names))


def test_valid_custom_file_round_trips(tmp_path: Path) -> None:
    path = _write_providers(
        tmp_path,
        {
            "providers": [
                {"name": "foo", "label": "Foo", "description": "demo provider"},
            ]
        },
    )
    providers = load_configured_providers(path)
    assert providers == (
        ConfiguredProvider(name="foo", label="Foo", description="demo provider"),
    )


def test_missing_file_returns_empty_tuple(tmp_path: Path) -> None:
    """Not blowing up lets callers default to an empty registry."""
    result = load_configured_providers(tmp_path / "does-not-exist.json")
    assert result == ()


def test_invalid_json_raises(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{not: json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        load_configured_providers(path)


def test_missing_top_level_providers_key(tmp_path: Path) -> None:
    path = _write_providers(tmp_path, {"other": []})
    with pytest.raises(ValueError, match="providers"):
        load_configured_providers(path)


@pytest.mark.parametrize(
    "bad_entry",
    [
        {"label": "No name", "description": "x"},
        {"name": "nolabel", "description": "x"},
        {"name": "x", "label": "x"},
        {"name": "", "label": "x", "description": "x"},  # empty name
        {"name": "x", "label": "x", "description": 42},  # wrong type
    ],
)
def test_invalid_entry_is_rejected(
    tmp_path: Path, bad_entry: dict[str, object]
) -> None:
    path = _write_providers(tmp_path, {"providers": [bad_entry]})
    with pytest.raises(ValueError):
        load_configured_providers(path)
