"""i18n Auto-Scaling.

Reference workflow
------------------

1. **Diff** a target locale against the source — what keys are missing,
   what keys are obsolete (present in target but not source), and what
   keys are present in both with stale values.
2. **Generate** the missing-key skeleton: same shape as the source but
   values replaced by a placeholder (``[FR] Hello``).
3. **Coverage** report per locale: how complete is each, and which keys
   are still placeholders vs. real translations.

The default placeholder strategy uses ``[<LANG>]`` prefixes so missing
translations are immediately visible in the running app — better than
silent fallback to English.

Storage convention assumed
--------------------------

Each locale is one JSON file (or many JSON files in a folder), nested or
flat. We support both. Discovery layout matches WorkPilot's existing
``apps/frontend/src/shared/i18n/locales/<lang>/<namespace>.json``.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Helpers


def flatten(data: dict[str, Any], prefix: str = "") -> dict[str, str]:
    """Flatten a nested locale dict into ``{"a.b.c": "value"}``.

    Non-string leaves are coerced via ``str()``. Lists are turned into
    indexed paths (``a.0``, ``a.1``…).
    """
    out: dict[str, str] = {}
    for key, value in data.items():
        sub_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            out.update(flatten(value, sub_key))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    out.update(flatten(item, f"{sub_key}.{i}"))
                else:
                    out[f"{sub_key}.{i}"] = str(item)
        else:
            out[sub_key] = "" if value is None else str(value)
    return out


def unflatten(flat: dict[str, str]) -> dict[str, Any]:
    """Inverse of `flatten` — build back a nested dict from dotted keys."""
    root: dict[str, Any] = {}
    for key, value in flat.items():
        parts = key.split(".")
        cursor: Any = root
        for i, part in enumerate(parts):
            is_last = i == len(parts) - 1
            if is_last:
                cursor[part] = value
            else:
                if part not in cursor or not isinstance(cursor[part], dict):
                    cursor[part] = {}
                cursor = cursor[part]
    return root


_INTERPOLATION_RE = re.compile(r"\{\{?\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}?\}")


def _extract_placeholders(value: str) -> set[str]:
    """Return the set of ``{var}`` / ``{{var}}`` placeholder names in a string."""
    return set(_INTERPOLATION_RE.findall(value))


# ----------------------------------------------------------------------
# Models


class PlaceholderStrategy(str, Enum):
    """How to mark untranslated values in the generated locale skeleton."""

    LANG_PREFIX = "lang_prefix"  # "[FR] Hello"
    EMPTY = "empty"  # ""
    SOURCE_VALUE = "source_value"  # copy the source value verbatim
    MARKER = "marker"  # "__TRANSLATE_ME__"


@dataclass
class LocaleDiff:
    source_locale: str
    target_locale: str
    missing_keys: list[str] = field(default_factory=list)
    obsolete_keys: list[str] = field(default_factory=list)
    placeholder_mismatches: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "source_locale": self.source_locale,
            "target_locale": self.target_locale,
            "missing_keys": self.missing_keys,
            "obsolete_keys": self.obsolete_keys,
            "placeholder_mismatches": self.placeholder_mismatches,
            "totals": {
                "missing": len(self.missing_keys),
                "obsolete": len(self.obsolete_keys),
                "placeholder_mismatches": len(self.placeholder_mismatches),
            },
        }


@dataclass
class LocaleCoverage:
    locale: str
    total_keys: int
    translated_keys: int
    placeholder_keys: int

    @property
    def coverage_ratio(self) -> float:
        if self.total_keys == 0:
            return 0.0
        return self.translated_keys / self.total_keys

    def to_dict(self) -> dict:
        return {
            "locale": self.locale,
            "total_keys": self.total_keys,
            "translated_keys": self.translated_keys,
            "placeholder_keys": self.placeholder_keys,
            "coverage_ratio": round(self.coverage_ratio, 4),
        }


@dataclass
class ScalingReport:
    source_locale: str
    diffs: list[LocaleDiff] = field(default_factory=list)
    coverage: list[LocaleCoverage] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "source_locale": self.source_locale,
            "diffs": [d.to_dict() for d in self.diffs],
            "coverage": [c.to_dict() for c in self.coverage],
        }


# ----------------------------------------------------------------------
# Scaler


class I18nAutoScaler:
    """Diff, scaffold and report on multi-locale translation files."""

    def __init__(
        self,
        placeholder_strategy: PlaceholderStrategy = PlaceholderStrategy.LANG_PREFIX,
        marker: str = "__TRANSLATE_ME__",
    ) -> None:
        self.placeholder_strategy = placeholder_strategy
        self.marker = marker

    # ------------------------------------------------------------------
    # Diff

    def diff(
        self,
        source: dict[str, Any],
        target: dict[str, Any],
        source_locale: str = "en",
        target_locale: str = "fr",
    ) -> LocaleDiff:
        """Compare a target locale dict against the source."""
        src_flat = flatten(source)
        tgt_flat = flatten(target)
        src_keys = set(src_flat.keys())
        tgt_keys = set(tgt_flat.keys())

        missing = sorted(src_keys - tgt_keys)
        obsolete = sorted(tgt_keys - src_keys)

        # Placeholder consistency: if EN says "Hello {name}" and FR says
        # "Bonjour {nom}" the variable names diverge — flag it.
        placeholder_mismatches = []
        for key in sorted(src_keys & tgt_keys):
            src_vars = _extract_placeholders(src_flat[key])
            tgt_vars = _extract_placeholders(tgt_flat[key])
            if src_vars != tgt_vars:
                placeholder_mismatches.append(key)

        return LocaleDiff(
            source_locale=source_locale,
            target_locale=target_locale,
            missing_keys=missing,
            obsolete_keys=obsolete,
            placeholder_mismatches=placeholder_mismatches,
        )

    # ------------------------------------------------------------------
    # Skeleton generation

    def generate_skeleton(
        self,
        source: dict[str, Any],
        target_locale: str,
        existing_target: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build a complete target locale dict with placeholders for new keys.

        Existing translated values in `existing_target` are preserved as-is.
        """
        src_flat = flatten(source)
        existing_flat = flatten(existing_target) if existing_target else {}
        out_flat: dict[str, str] = {}

        for key, src_value in src_flat.items():
            if key in existing_flat:
                out_flat[key] = existing_flat[key]
            else:
                out_flat[key] = self._make_placeholder(src_value, target_locale)

        return unflatten(out_flat)

    def _make_placeholder(self, source_value: str, target_locale: str) -> str:
        if self.placeholder_strategy == PlaceholderStrategy.LANG_PREFIX:
            return f"[{target_locale.upper()}] {source_value}"
        if self.placeholder_strategy == PlaceholderStrategy.EMPTY:
            return ""
        if self.placeholder_strategy == PlaceholderStrategy.SOURCE_VALUE:
            return source_value
        return self.marker

    # ------------------------------------------------------------------
    # Coverage

    def coverage(
        self,
        source: dict[str, Any],
        targets: dict[str, dict[str, Any]],
    ) -> list[LocaleCoverage]:
        """Compute coverage per target locale.

        A value counts as `translated` when (a) the key exists in the target
        AND (b) the value is not the placeholder we'd otherwise generate.
        """
        src_flat = flatten(source)
        result: list[LocaleCoverage] = []
        for locale, target in sorted(targets.items()):
            tgt_flat = flatten(target)
            translated = 0
            placeholder = 0
            for key, src_value in src_flat.items():
                if key not in tgt_flat:
                    continue
                if self._looks_like_placeholder(tgt_flat[key], src_value, locale):
                    placeholder += 1
                else:
                    translated += 1
            result.append(
                LocaleCoverage(
                    locale=locale,
                    total_keys=len(src_flat),
                    translated_keys=translated,
                    placeholder_keys=placeholder,
                )
            )
        return result

    def _looks_like_placeholder(
        self, value: str, source_value: str, target_locale: str
    ) -> bool:
        if not value:
            return True
        if value == self.marker:
            return True
        # `[FR] ...` style placeholders we generate.
        if re.match(rf"^\[{re.escape(target_locale.upper())}\]\s", value):
            return True
        # source_value strategy → identical value = untranslated heuristic.
        if (
            self.placeholder_strategy == PlaceholderStrategy.SOURCE_VALUE
            and value == source_value
        ):
            return True
        return False

    # ------------------------------------------------------------------
    # Filesystem helpers

    def discover_locale_dir(self, locales_dir: Path | str) -> dict[str, dict[str, Any]]:
        """Load every locale directory under `locales_dir`.

        Layout:  ``<locales_dir>/<lang>/*.json`` — typical i18next layout.
        Each language is the merged content of all its namespace files,
        keyed by the namespace stem.
        """
        root = Path(locales_dir)
        if not root.is_dir():
            raise ValueError(f"Not a directory: {root}")

        out: dict[str, dict[str, Any]] = {}
        for lang_dir in sorted(p for p in root.iterdir() if p.is_dir()):
            merged: dict[str, Any] = {}
            for ns_file in sorted(lang_dir.glob("*.json")):
                try:
                    payload = json.loads(ns_file.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as e:
                    logger.warning("Skipping %s: %s", ns_file, e)
                    continue
                merged[ns_file.stem] = payload
            out[lang_dir.name] = merged
        return out

    def write_skeleton_to_dir(
        self,
        skeleton: dict[str, Any],
        locale_dir: Path | str,
        namespaces: Iterable[str] | None = None,
    ) -> list[Path]:
        """Write a skeleton dict to disk as ``<locale_dir>/<ns>.json`` files.

        Only writes files for top-level keys present in `namespaces`
        (default: every top-level key).
        """
        target = Path(locale_dir)
        target.mkdir(parents=True, exist_ok=True)
        ns_filter = set(namespaces) if namespaces is not None else None
        written: list[Path] = []
        for ns, payload in skeleton.items():
            if ns_filter is not None and ns not in ns_filter:
                continue
            path = target / f"{ns}.json"
            path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            written.append(path)
        return written

    # ------------------------------------------------------------------
    # All-in-one

    def report(
        self,
        source_locale: str,
        locales: dict[str, dict[str, Any]],
    ) -> ScalingReport:
        """Compute a full diff + coverage report."""
        if source_locale not in locales:
            raise ValueError(f"Source locale {source_locale!r} not in locales")
        source = locales[source_locale]

        diffs = [
            self.diff(source, target, source_locale=source_locale, target_locale=lang)
            for lang, target in sorted(locales.items())
            if lang != source_locale
        ]
        coverage = self.coverage(
            source,
            {lang: t for lang, t in locales.items() if lang != source_locale},
        )
        return ScalingReport(
            source_locale=source_locale, diffs=diffs, coverage=coverage
        )
