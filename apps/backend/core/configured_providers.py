"""Single-source-of-truth loader for ``config/configured_providers.json``.

Both the Python backend and the Electron/TypeScript frontend read the
same JSON file. On the TS side a generated module
(``apps/frontend/src/shared/types/providers.generated.ts``) gives the
renderer a typed view — see ``scripts/generate-provider-types.js``.

This module gives the Python backend an equivalent typed surface:

* ``ConfiguredProvider`` — typed dataclass matching the JSON shape.
* ``load_configured_providers()`` — cached read + validation.
* ``is_known_provider(name)`` — O(1) membership check.

The JSON is validated at load time so a malformed entry fails loudly
instead of propagating empty strings deep into provider setup code.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

# The JSON lives at the repository root. ``apps/backend/core/<this file>``
# → ``../../../config/configured_providers.json``.
_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT = _THIS_FILE.parents[3]
_DEFAULT_PATH = _REPO_ROOT / "config" / "configured_providers.json"


@dataclass(frozen=True)
class ConfiguredProvider:
    """Typed view of an entry in ``configured_providers.json``."""

    name: str
    label: str
    description: str


def _validate_entry(index: int, raw: object) -> ConfiguredProvider:
    if not isinstance(raw, dict):
        raise ValueError(
            f"configured_providers[{index}] must be an object, got {type(raw).__name__}"
        )
    missing = [field for field in ("name", "label", "description") if field not in raw]
    if missing:
        raise ValueError(
            f"configured_providers[{index}] is missing required field(s): {missing}"
        )
    for field in ("name", "label", "description"):
        value = raw[field]
        if not isinstance(value, str) or not value:
            raise ValueError(
                f"configured_providers[{index}].{field} must be a non-empty string"
            )
    return ConfiguredProvider(
        name=raw["name"], label=raw["label"], description=raw["description"]
    )


@lru_cache(maxsize=1)
def load_configured_providers(
    path: Path | None = None,
) -> tuple[ConfiguredProvider, ...]:
    """Load, validate and cache the provider list.

    The result is cached on the default path; passing an explicit ``path``
    (e.g. for tests) bypasses the cache for that call.
    """
    resolved = path or _DEFAULT_PATH
    try:
        raw = json.loads(resolved.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.warning("configured_providers.json not found at %s", resolved)
        return ()
    except json.JSONDecodeError:
        logger.exception("configured_providers.json is not valid JSON (%s)", resolved)
        raise

    providers_raw = raw.get("providers") if isinstance(raw, dict) else None
    if not isinstance(providers_raw, list):
        raise ValueError(
            f"{resolved}: expected top-level {{'providers': [...]}}, got "
            f"{type(providers_raw).__name__}"
        )
    return tuple(_validate_entry(i, entry) for i, entry in enumerate(providers_raw))


def get_provider_names() -> frozenset[str]:
    """Return the set of known provider IDs."""
    return frozenset(p.name for p in load_configured_providers())


def is_known_provider(name: str) -> bool:
    """O(1) membership check against the canonical provider list."""
    return name in get_provider_names()
