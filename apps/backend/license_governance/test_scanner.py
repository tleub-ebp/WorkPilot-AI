"""Tests for the License Scanner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from license_governance import (
    DependencyRecord,
    LicenseCategory,
    LicensePolicy,
    LicenseScanner,
    classify_license,
)

# ----------------------------------------------------------------------
# classify_license


class TestClassifier:
    def test_unknown_when_empty(self) -> None:
        assert classify_license(None) == LicenseCategory.UNKNOWN
        assert classify_license("") == LicenseCategory.UNKNOWN
        assert classify_license("   ") == LicenseCategory.UNKNOWN

    def test_mit_is_permissive(self) -> None:
        assert classify_license("MIT") == LicenseCategory.PERMISSIVE
        assert classify_license("mit") == LicenseCategory.PERMISSIVE
        assert classify_license("MIT License") == LicenseCategory.PERMISSIVE

    def test_apache_variants(self) -> None:
        for v in ("Apache-2.0", "Apache 2.0", "ASL-2.0", "apache-2"):
            assert classify_license(v) == LicenseCategory.PERMISSIVE

    def test_gpl_strong_copyleft(self) -> None:
        assert classify_license("GPL-3.0") == LicenseCategory.STRONG_COPYLEFT
        assert classify_license("GPL-3.0-or-later") == LicenseCategory.STRONG_COPYLEFT

    def test_lgpl_weak_copyleft(self) -> None:
        assert classify_license("LGPL-2.1") == LicenseCategory.WEAK_COPYLEFT
        assert classify_license("MPL-2.0") == LicenseCategory.WEAK_COPYLEFT

    def test_agpl_network_copyleft(self) -> None:
        assert classify_license("AGPL-3.0") == LicenseCategory.NETWORK_COPYLEFT

    def test_public_domain(self) -> None:
        assert classify_license("CC0-1.0") == LicenseCategory.PUBLIC_DOMAIN
        assert classify_license("Unlicense") == LicenseCategory.PUBLIC_DOMAIN

    def test_commercial_marker(self) -> None:
        assert classify_license("Proprietary") == LicenseCategory.COMMERCIAL
        assert classify_license("see EULA") == LicenseCategory.COMMERCIAL

    def test_dual_license_picks_most_permissive(self) -> None:
        # "MIT OR GPL-3.0" should classify as permissive (we can pick MIT).
        assert classify_license("MIT OR GPL-3.0") == LicenseCategory.PERMISSIVE

    def test_unknown_falls_through(self) -> None:
        assert classify_license("WeirdLicense-1.0") == LicenseCategory.UNKNOWN


# ----------------------------------------------------------------------
# Manifest discovery


class TestManifestDiscovery:
    def test_package_json_dependencies(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(
            json.dumps(
                {
                    "name": "demo",
                    "license": "MIT",
                    "dependencies": {"react": "^18.0.0", "left-pad": "1.3.0"},
                    "devDependencies": {"vitest": "^1.0.0"},
                }
            )
        )
        deps = LicenseScanner(project_dir=tmp_path).discover()
        names = {(d.name, d.is_direct) for d in deps}
        assert ("react", True) in names
        assert ("left-pad", True) in names
        assert ("vitest", False) in names

    def test_requirements_txt_strips_comments_and_options(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text(
            "# top comment\n"
            "fastapi==0.110.0\n"
            "pydantic[email]>=2.0\n"
            "-e ./local-pkg  # editable install — should be skipped\n"
            "\n"
        )
        deps = LicenseScanner(project_dir=tmp_path).discover()
        names = {d.name for d in deps}
        assert names == {"fastapi", "pydantic"}

    def test_go_mod_block_form(self, tmp_path: Path) -> None:
        (tmp_path / "go.mod").write_text(
            "module example.com/x\n"
            "go 1.22\n"
            "require (\n"
            "  github.com/foo/bar v1.2.3\n"
            "  github.com/baz/quux v0.0.1\n"
            ")\n"
        )
        deps = LicenseScanner(project_dir=tmp_path).discover()
        names = {d.name for d in deps}
        assert "github.com/foo/bar" in names
        assert "github.com/baz/quux" in names

    def test_node_modules_skipped(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(
            json.dumps({"name": "demo", "dependencies": {"a": "1.0.0"}})
        )
        nested = tmp_path / "node_modules" / "junk"
        nested.mkdir(parents=True)
        (nested / "package.json").write_text(
            json.dumps({"name": "junk", "dependencies": {"transitively-bad": "0.0.1"}})
        )
        deps = LicenseScanner(project_dir=tmp_path).discover()
        names = {d.name for d in deps}
        assert "a" in names
        assert "transitively-bad" not in names  # node_modules pruned

    def test_dedup_same_dep_in_multiple_files(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("fastapi==0.110.0\n")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "requirements.txt").write_text("fastapi==0.110.0\n")
        deps = LicenseScanner(project_dir=tmp_path).discover()
        # Same (ecosystem, name, version) appears twice in the tree but
        # the scanner dedups.
        assert sum(1 for d in deps if d.name == "fastapi") == 1

    def test_corrupt_manifest_does_not_crash(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text("{ not valid json")
        # Should silently return [] for the broken manifest.
        deps = LicenseScanner(project_dir=tmp_path).discover()
        assert deps == []


# ----------------------------------------------------------------------
# Policy evaluation


class TestPolicy:
    def _scanner_with_licenses(
        self, tmp_path: Path, licenses: dict[str, str]
    ) -> LicenseScanner:
        (tmp_path / "package.json").write_text(
            json.dumps(
                {
                    "name": "host",
                    "dependencies": dict.fromkeys(licenses, "1.0.0"),
                }
            )
        )

        def resolver(dep: DependencyRecord) -> str | None:
            return licenses.get(dep.name)

        return LicenseScanner(
            project_dir=tmp_path,
            policy=LicensePolicy.permissive_only(),
            resolver=resolver,
        )

    def test_all_permissive_passes(self, tmp_path: Path) -> None:
        scanner = self._scanner_with_licenses(tmp_path, {"a": "MIT", "b": "Apache-2.0"})
        report = scanner.scan()
        assert report.passed is True
        assert report.summary["conflict_count"] == 0

    def test_gpl_dep_fails_default_policy(self, tmp_path: Path) -> None:
        scanner = self._scanner_with_licenses(
            tmp_path, {"good": "MIT", "bad": "GPL-3.0"}
        )
        report = scanner.scan()
        assert report.passed is False
        assert any(
            c.dependency.name == "bad" and c.category == LicenseCategory.STRONG_COPYLEFT
            for c in report.conflicts
        )

    def test_open_source_friendly_allows_lgpl(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(
            json.dumps({"name": "h", "dependencies": {"x": "1.0.0"}})
        )

        def resolver(dep: DependencyRecord) -> str | None:
            return "LGPL-2.1"

        scanner = LicenseScanner(
            project_dir=tmp_path,
            policy=LicensePolicy.open_source_friendly(),
            resolver=resolver,
        )
        report = scanner.scan()
        assert report.passed is True

    def test_unknown_license_blocked_under_strict_policy(self, tmp_path: Path) -> None:
        scanner = self._scanner_with_licenses(tmp_path, {"mystery": "WeirdLicense-1.0"})
        report = scanner.scan()
        assert report.passed is False
        assert report.conflicts[0].category == LicenseCategory.UNKNOWN

    def test_conflict_carries_remediation(self, tmp_path: Path) -> None:
        scanner = self._scanner_with_licenses(tmp_path, {"x": "AGPL-3.0"})
        report = scanner.scan()
        assert "AGPL" in report.conflicts[0].remediation

    def test_summary_counts(self, tmp_path: Path) -> None:
        scanner = self._scanner_with_licenses(
            tmp_path, {"a": "MIT", "b": "MIT", "c": "GPL-3.0"}
        )
        report = scanner.scan()
        assert report.summary["total_dependencies"] == 3
        assert report.summary["conflict_count"] == 1
        assert report.by_category["permissive"] == 2
        assert report.by_category["strong_copyleft"] == 1


class TestSerialisation:
    def test_to_dict_roundtrips(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(
            json.dumps({"name": "h", "dependencies": {"x": "1.0.0"}})
        )

        def resolver(_dep: DependencyRecord) -> str | None:
            return "GPL-3.0"

        scanner = LicenseScanner(project_dir=tmp_path, resolver=resolver)
        report = scanner.scan()
        decoded = json.loads(json.dumps(report.to_dict()))
        assert decoded["passed"] is False
        assert decoded["conflicts"][0]["category"] == "strong_copyleft"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
