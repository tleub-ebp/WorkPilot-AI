"""Tests for the registry resolvers (npm + PyPI).

We don't hit the network — `_http_get_json` is monkey-patched per test.
"""

from __future__ import annotations

import pytest
from license_governance import (
    DependencyRecord,
    make_registry_resolver,
    npm_resolver,
    pypi_resolver,
)
from license_governance.resolvers import _normalise_license_field, reset_cache_for_tests


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    reset_cache_for_tests()
    yield
    reset_cache_for_tests()


def _dep(name: str, ecosystem: str, declared: str | None = None) -> DependencyRecord:
    return DependencyRecord(
        name=name, version="1.0.0", ecosystem=ecosystem, declared_license=declared
    )


# ----------------------------------------------------------------------
# Pure helpers


class TestNormaliseLicenseField:
    def test_string(self) -> None:
        assert _normalise_license_field("MIT") == "MIT"

    def test_empty_string(self) -> None:
        assert _normalise_license_field("") is None

    def test_none(self) -> None:
        assert _normalise_license_field(None) is None

    def test_dict_with_type(self) -> None:
        assert _normalise_license_field({"type": "MIT", "url": "..."}) == "MIT"

    def test_dict_with_name_fallback(self) -> None:
        assert _normalise_license_field({"name": "Apache-2.0"}) == "Apache-2.0"

    def test_list_combines_with_or(self) -> None:
        out = _normalise_license_field([{"type": "MIT"}, {"type": "Apache-2.0"}])
        assert out == "MIT OR Apache-2.0"

    def test_unknown_shape(self) -> None:
        assert _normalise_license_field(42) is None


# ----------------------------------------------------------------------
# npm


class TestNpmResolver:
    def test_skips_non_npm_eco(self, monkeypatch: pytest.MonkeyPatch) -> None:
        called = []

        def fake_get(url):
            called.append(url)
            return {}

        monkeypatch.setattr("license_governance.resolvers._http_get_json", fake_get)
        assert npm_resolver(_dep("foo", "pypi")) is None
        assert called == []

    def test_resolves_via_latest_version(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload = {
            "dist-tags": {"latest": "2.0.0"},
            "versions": {
                "1.0.0": {"license": "GPL-3.0"},  # ignored — not latest
                "2.0.0": {"license": "MIT"},
            },
            "license": "Apache-2.0",  # ignored — versions hit first
        }
        monkeypatch.setattr(
            "license_governance.resolvers._http_get_json",
            lambda url: payload,
        )
        assert npm_resolver(_dep("react", "npm")) == "MIT"

    def test_falls_back_to_top_level_license(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        payload = {"license": "ISC"}
        monkeypatch.setattr(
            "license_governance.resolvers._http_get_json",
            lambda url: payload,
        )
        assert npm_resolver(_dep("legacy", "npm")) == "ISC"

    def test_returns_none_on_network_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "license_governance.resolvers._http_get_json", lambda url: None
        )
        assert npm_resolver(_dep("any", "npm")) is None

    def test_caches_lookups(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[str] = []

        def fake_get(url):
            calls.append(url)
            return {"license": "MIT"}

        monkeypatch.setattr("license_governance.resolvers._http_get_json", fake_get)
        assert npm_resolver(_dep("react", "npm")) == "MIT"
        assert npm_resolver(_dep("react", "npm")) == "MIT"
        assert len(calls) == 1


# ----------------------------------------------------------------------
# PyPI


class TestPypiResolver:
    def test_resolves_from_info_license(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "license_governance.resolvers._http_get_json",
            lambda url: {"info": {"license": "Apache-2.0"}},
        )
        assert pypi_resolver(_dep("requests", "pypi")) == "Apache-2.0"

    def test_falls_back_to_classifiers(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "license_governance.resolvers._http_get_json",
            lambda url: {
                "info": {
                    "license": "",
                    "classifiers": [
                        "Programming Language :: Python :: 3",
                        "License :: OSI Approved :: BSD License",
                    ],
                }
            },
        )
        assert pypi_resolver(_dep("any", "pypi")) == "BSD License"

    def test_long_license_text_treated_as_unresolved(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "license_governance.resolvers._http_get_json",
            lambda url: {"info": {"license": "x" * 500}},
        )
        # 500 chars > 200 cap → treated as None so the classifier flags UNKNOWN
        assert pypi_resolver(_dep("verbose", "pypi")) is None

    def test_skips_non_pypi_eco(self) -> None:
        assert pypi_resolver(_dep("foo", "npm")) is None


# ----------------------------------------------------------------------
# Composition


class TestMakeRegistryResolver:
    def test_routes_npm_to_npm_resolver(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "license_governance.resolvers._http_get_json",
            lambda url: {"license": "MIT"} if "registry.npmjs.org" in url else None,
        )
        resolve = make_registry_resolver()
        assert resolve(_dep("react", "npm")) == "MIT"

    def test_routes_pypi_to_pypi_resolver(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "license_governance.resolvers._http_get_json",
            lambda url: (
                {"info": {"license": "Apache-2.0"}} if "pypi.org" in url else None
            ),
        )
        resolve = make_registry_resolver()
        assert resolve(_dep("requests", "pypi")) == "Apache-2.0"

    def test_falls_back_to_declared_for_other_eco(self) -> None:
        resolve = make_registry_resolver()
        assert resolve(_dep("foo", "cargo", declared="MIT")) == "MIT"

    def test_custom_fallback(self) -> None:
        resolve = make_registry_resolver(
            enable_npm=False,
            enable_pypi=False,
            fallback=lambda dep: "FORCED",
        )
        assert resolve(_dep("anything", "npm")) == "FORCED"

    def test_npm_fetch_failure_falls_through(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "license_governance.resolvers._http_get_json", lambda url: None
        )
        resolve = make_registry_resolver(
            fallback=lambda dep: dep.declared_license or "FALLBACK"
        )
        assert resolve(_dep("react", "npm", declared="MIT-DECLARED")) == "MIT-DECLARED"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
