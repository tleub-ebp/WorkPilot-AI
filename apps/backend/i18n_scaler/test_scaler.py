"""Tests for the i18n Auto-Scaler."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from i18n_scaler import (
    I18nAutoScaler,
    PlaceholderStrategy,
    flatten,
    unflatten,
)

# ----------------------------------------------------------------------
# flatten / unflatten


class TestFlatten:
    def test_flatten_simple(self) -> None:
        assert flatten({"a": "x"}) == {"a": "x"}

    def test_flatten_nested(self) -> None:
        assert flatten({"a": {"b": {"c": "x"}}}) == {"a.b.c": "x"}

    def test_flatten_with_list(self) -> None:
        out = flatten({"items": ["a", "b"]})
        assert out == {"items.0": "a", "items.1": "b"}

    def test_flatten_with_list_of_dicts(self) -> None:
        out = flatten({"items": [{"name": "a"}, {"name": "b"}]})
        assert out == {"items.0.name": "a", "items.1.name": "b"}

    def test_unflatten_round_trip(self) -> None:
        original = {"a": {"b": {"c": "x"}}, "d": "y"}
        flat = flatten(original)
        assert unflatten(flat) == original

    def test_unflatten_handles_dotted_keys(self) -> None:
        flat = {"a.b": "1", "a.c": "2"}
        assert unflatten(flat) == {"a": {"b": "1", "c": "2"}}


# ----------------------------------------------------------------------
# Diff


class TestDiff:
    def test_identical_locales_have_no_diff(self) -> None:
        src = {"hello": "Hi"}
        diff = I18nAutoScaler().diff(src, src.copy(), "en", "en")
        assert diff.missing_keys == []
        assert diff.obsolete_keys == []

    def test_missing_keys_detected(self) -> None:
        src = {"hello": "Hi", "bye": "Bye"}
        tgt = {"hello": "Bonjour"}
        diff = I18nAutoScaler().diff(src, tgt, "en", "fr")
        assert diff.missing_keys == ["bye"]

    def test_obsolete_keys_detected(self) -> None:
        src = {"hello": "Hi"}
        tgt = {"hello": "Bonjour", "ancien": "Old"}
        diff = I18nAutoScaler().diff(src, tgt, "en", "fr")
        assert diff.obsolete_keys == ["ancien"]

    def test_placeholder_mismatch_detected(self) -> None:
        src = {"greet": "Hello {name}"}
        tgt = {"greet": "Bonjour {nom}"}
        diff = I18nAutoScaler().diff(src, tgt, "en", "fr")
        assert "greet" in diff.placeholder_mismatches

    def test_placeholder_match_not_flagged(self) -> None:
        src = {"greet": "Hello {name}"}
        tgt = {"greet": "Bonjour {name}"}
        diff = I18nAutoScaler().diff(src, tgt, "en", "fr")
        assert diff.placeholder_mismatches == []

    def test_double_brace_placeholders(self) -> None:
        # i18next uses {{var}} — must match identical regardless of brace style
        src = {"greet": "Hello {{name}}"}
        tgt = {"greet": "Bonjour {{name}}"}
        diff = I18nAutoScaler().diff(src, tgt, "en", "fr")
        assert diff.placeholder_mismatches == []


# ----------------------------------------------------------------------
# Skeleton generation


class TestSkeleton:
    def test_lang_prefix_strategy(self) -> None:
        scaler = I18nAutoScaler(PlaceholderStrategy.LANG_PREFIX)
        out = scaler.generate_skeleton({"hello": "Hi"}, target_locale="fr")
        assert out == {"hello": "[FR] Hi"}

    def test_empty_strategy(self) -> None:
        scaler = I18nAutoScaler(PlaceholderStrategy.EMPTY)
        out = scaler.generate_skeleton({"hello": "Hi"}, target_locale="fr")
        assert out == {"hello": ""}

    def test_source_value_strategy(self) -> None:
        scaler = I18nAutoScaler(PlaceholderStrategy.SOURCE_VALUE)
        out = scaler.generate_skeleton({"hello": "Hi"}, target_locale="fr")
        assert out == {"hello": "Hi"}

    def test_marker_strategy(self) -> None:
        scaler = I18nAutoScaler(PlaceholderStrategy.MARKER)
        out = scaler.generate_skeleton({"hello": "Hi"}, target_locale="fr")
        assert out == {"hello": "__TRANSLATE_ME__"}

    def test_existing_translations_preserved(self) -> None:
        scaler = I18nAutoScaler(PlaceholderStrategy.LANG_PREFIX)
        out = scaler.generate_skeleton(
            {"hello": "Hi", "bye": "Bye"},
            target_locale="fr",
            existing_target={"hello": "Salut"},
        )
        assert out == {"hello": "Salut", "bye": "[FR] Bye"}

    def test_nested_structure_preserved(self) -> None:
        scaler = I18nAutoScaler(PlaceholderStrategy.LANG_PREFIX)
        out = scaler.generate_skeleton(
            {"nav": {"home": "Home", "settings": "Settings"}},
            target_locale="fr",
        )
        assert out == {"nav": {"home": "[FR] Home", "settings": "[FR] Settings"}}


# ----------------------------------------------------------------------
# Coverage


class TestCoverage:
    def test_full_translation_is_100_percent(self) -> None:
        src = {"a": "A", "b": "B"}
        tgt = {"a": "Ah", "b": "Beh"}
        cov = I18nAutoScaler().coverage(src, {"de": tgt})
        assert cov[0].coverage_ratio == 1.0
        assert cov[0].placeholder_keys == 0

    def test_placeholder_counted_separately(self) -> None:
        src = {"a": "A", "b": "B"}
        tgt = {"a": "Ah", "b": "[DE] B"}
        cov = I18nAutoScaler().coverage(src, {"de": tgt})
        assert cov[0].translated_keys == 1
        assert cov[0].placeholder_keys == 1
        assert cov[0].coverage_ratio == 0.5

    def test_missing_keys_dont_count_as_placeholder_or_translated(self) -> None:
        src = {"a": "A", "b": "B"}
        tgt = {"a": "Ah"}
        cov = I18nAutoScaler().coverage(src, {"de": tgt})
        assert cov[0].translated_keys == 1
        assert cov[0].placeholder_keys == 0
        assert cov[0].total_keys == 2  # the source has 2 keys

    def test_marker_strategy_detects_marker_as_placeholder(self) -> None:
        src = {"a": "A"}
        tgt = {"a": "__TRANSLATE_ME__"}
        cov = I18nAutoScaler(PlaceholderStrategy.MARKER).coverage(src, {"de": tgt})
        assert cov[0].placeholder_keys == 1
        assert cov[0].translated_keys == 0


# ----------------------------------------------------------------------
# Discovery & writing


class TestFilesystemHelpers:
    def _write_locale(self, root: Path, lang: str, files: dict[str, dict]) -> None:
        d = root / lang
        d.mkdir(parents=True, exist_ok=True)
        for ns, payload in files.items():
            (d / f"{ns}.json").write_text(json.dumps(payload), encoding="utf-8")

    def test_discover_locales(self, tmp_path: Path) -> None:
        self._write_locale(tmp_path, "en", {"common": {"hello": "Hi"}})
        self._write_locale(tmp_path, "fr", {"common": {"hello": "Bonjour"}})
        out = I18nAutoScaler().discover_locale_dir(tmp_path)
        assert set(out.keys()) == {"en", "fr"}
        assert out["en"]["common"]["hello"] == "Hi"

    def test_discover_skips_corrupt_files(self, tmp_path: Path) -> None:
        self._write_locale(tmp_path, "en", {"common": {"hello": "Hi"}})
        # Drop a broken JSON file in fr
        (tmp_path / "fr").mkdir()
        (tmp_path / "fr" / "broken.json").write_text("{ not json")
        out = I18nAutoScaler().discover_locale_dir(tmp_path)
        # fr exists with no namespaces (the broken file is silently skipped).
        assert "fr" in out
        assert out["fr"] == {}

    def test_discover_rejects_non_directory(self, tmp_path: Path) -> None:
        ghost = tmp_path / "missing"
        with pytest.raises(ValueError):
            I18nAutoScaler().discover_locale_dir(ghost)

    def test_write_skeleton_creates_files(self, tmp_path: Path) -> None:
        skeleton = {"common": {"hello": "[FR] Hi"}, "errors": {"e": "[FR] err"}}
        written = I18nAutoScaler().write_skeleton_to_dir(skeleton, tmp_path / "fr")
        assert len(written) == 2
        for p in written:
            assert p.exists()
            payload = json.loads(p.read_text(encoding="utf-8"))
            assert payload  # non-empty

    def test_write_skeleton_with_namespace_filter(self, tmp_path: Path) -> None:
        skeleton = {"common": {"x": "y"}, "errors": {"e": "f"}}
        written = I18nAutoScaler().write_skeleton_to_dir(
            skeleton, tmp_path / "fr", namespaces=["common"]
        )
        assert len(written) == 1
        assert written[0].name == "common.json"


# ----------------------------------------------------------------------
# Report


class TestReport:
    def test_full_report(self) -> None:
        scaler = I18nAutoScaler()
        locales = {
            "en": {"hello": "Hi", "bye": "Bye"},
            "fr": {"hello": "Bonjour"},
            "de": {"hello": "Hallo", "bye": "Tschüss"},
        }
        report = scaler.report("en", locales)
        assert {d.target_locale for d in report.diffs} == {"fr", "de"}
        fr = next(d for d in report.diffs if d.target_locale == "fr")
        assert fr.missing_keys == ["bye"]
        de = next(d for d in report.diffs if d.target_locale == "de")
        assert de.missing_keys == []

    def test_report_rejects_unknown_source(self) -> None:
        with pytest.raises(ValueError):
            I18nAutoScaler().report("xx", {"en": {}})

    def test_to_dict_serialisable(self) -> None:
        scaler = I18nAutoScaler()
        locales = {"en": {"a": "A"}, "fr": {"a": "[FR] A"}}
        report = scaler.report("en", locales)
        decoded = json.loads(json.dumps(report.to_dict()))
        assert decoded["source_locale"] == "en"
        assert "diffs" in decoded
        assert "coverage" in decoded


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
