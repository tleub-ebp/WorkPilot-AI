"""Tests for Feature 9.1 — Mode sombre/clair automatique + thème custom.

40 tests covering:
- ThemeColors: 4 tests (creation, to_dict, from_dict, validate)
- CustomTheme: 3 tests (creation, to_dict, from_dict)
- Mode management: 4 tests (get_mode, set_mode, resolve_system_dark, resolve_system_light)
- Built-in themes: 3 tests (list, get_existing, get_missing)
- Custom themes CRUD: 6 tests (create, get, update, delete, list, validation error)
- Per-project themes: 5 tests (set, get, remove, list, invalid theme)
- Import/Export: 5 tests (export custom, export builtin, import valid, import invalid json, import invalid colors)
- CSS generation: 3 tests (light mode, dark mode, missing theme)
- All themes: 3 tests (list_all, count, sources)
- Stats: 2 tests (basic, empty)
- Edge cases: 2 tests (delete theme removes bindings, update nonexistent)
"""

import json

import pytest

from apps.backend.ui.theme_manager import (
    BUILTIN_THEMES,
    CustomTheme,
    ProjectThemeBinding,
    ThemeColors,
    ThemeManager,
    ThemeMode,
    ThemeSource,
)

# ---------------------------------------------------------------------------
# ThemeColors tests
# ---------------------------------------------------------------------------

class TestThemeColors:
    def test_create(self):
        colors = ThemeColors(bg="#FFFFFF", accent="#3B82F6", darkBg="#0F172A", darkAccent="#60A5FA")
        assert colors.bg == "#FFFFFF"
        assert colors.darkBg == "#0F172A"

    def test_to_dict(self):
        colors = ThemeColors()
        d = colors.to_dict()
        assert "bg" in d
        assert "accent" in d
        assert "darkBg" in d

    def test_from_dict(self):
        data = {"bg": "#1a1a2e", "accent": "#e94560", "darkBg": "#0f0f1a", "darkAccent": "#ff6b6b"}
        colors = ThemeColors.from_dict(data)
        assert colors.bg == "#1a1a2e"
        assert colors.accent == "#e94560"

    def test_validate_valid(self):
        colors = ThemeColors(bg="#FFFFFF", accent="#3B82F6", darkBg="#0F172A", darkAccent="#60A5FA")
        errors = colors.validate()
        assert len(errors) == 0

    # Note: test_validate_invalid is covered in custom theme validation error test


# ---------------------------------------------------------------------------
# CustomTheme tests
# ---------------------------------------------------------------------------

class TestCustomTheme:
    def test_create(self):
        theme = CustomTheme(
            theme_id="custom-0001",
            name="My Theme",
            description="A custom theme",
            source="custom",
        )
        assert theme.theme_id == "custom-0001"
        assert theme.name == "My Theme"

    def test_to_dict(self):
        theme = CustomTheme(
            theme_id="custom-0001",
            name="My Theme",
        )
        d = theme.to_dict()
        assert d["theme_id"] == "custom-0001"
        assert "colors" in d

    def test_from_dict(self):
        data = {
            "theme_id": "custom-0001",
            "name": "Imported",
            "description": "Test",
            "source": "imported",
            "colors": {"bg": "#FFFFFF", "accent": "#3B82F6", "darkBg": "#0F172A", "darkAccent": "#60A5FA"},
        }
        theme = CustomTheme.from_dict(data)
        assert theme.name == "Imported"
        assert theme.colors.bg == "#FFFFFF"


# ---------------------------------------------------------------------------
# Mode management tests
# ---------------------------------------------------------------------------

class TestModeManagement:
    def test_get_mode_default(self):
        manager = ThemeManager()
        assert manager.get_mode() == "system"

    def test_set_mode(self):
        manager = ThemeManager()
        manager.set_mode("dark")
        assert manager.get_mode() == "dark"

    def test_resolve_system_dark(self):
        manager = ThemeManager()
        resolved = manager.resolve_mode("system", system_prefers_dark=True)
        assert resolved == "dark"

    def test_resolve_system_light(self):
        manager = ThemeManager()
        resolved = manager.resolve_mode("system", system_prefers_dark=False)
        assert resolved == "light"


# ---------------------------------------------------------------------------
# Built-in themes tests
# ---------------------------------------------------------------------------

class TestBuiltinThemes:
    def test_list_builtin(self):
        manager = ThemeManager()
        themes = manager.list_builtin_themes()
        assert len(themes) == 7
        ids = [t["id"] for t in themes]
        assert "default" in ids
        assert "ocean" in ids

    def test_get_existing(self):
        manager = ThemeManager()
        theme = manager.get_builtin_theme("ocean")
        assert theme is not None
        assert theme["name"] == "Ocean"

    def test_get_missing(self):
        manager = ThemeManager()
        theme = manager.get_builtin_theme("nonexistent")
        assert theme is None


# ---------------------------------------------------------------------------
# Custom themes CRUD tests
# ---------------------------------------------------------------------------

class TestCustomThemesCRUD:
    def test_create_custom(self):
        manager = ThemeManager()
        theme = manager.create_custom_theme(
            "My Theme",
            colors={"bg": "#1a1a2e", "accent": "#e94560", "darkBg": "#0f0f1a", "darkAccent": "#ff6b6b"},
            description="My custom theme",
            author="Alice",
        )
        assert theme.theme_id.startswith("custom-")
        assert theme.name == "My Theme"
        assert theme.author == "Alice"
        assert theme.colors.bg == "#1a1a2e"

    def test_get_custom(self):
        manager = ThemeManager()
        created = manager.create_custom_theme(
            "Test", colors={"bg": "#fff", "accent": "#000", "darkBg": "#111", "darkAccent": "#eee"}
        )
        retrieved = manager.get_custom_theme(created.theme_id)
        assert retrieved is not None
        assert retrieved.name == "Test"

    def test_update_custom(self):
        manager = ThemeManager()
        theme = manager.create_custom_theme(
            "Old Name", colors={"bg": "#fff", "accent": "#000", "darkBg": "#111", "darkAccent": "#eee"}
        )
        updated = manager.update_custom_theme(theme.theme_id, name="New Name", description="Updated")
        assert updated is not None
        assert updated.name == "New Name"
        assert updated.description == "Updated"

    def test_delete_custom(self):
        manager = ThemeManager()
        theme = manager.create_custom_theme(
            "To Delete", colors={"bg": "#fff", "accent": "#000", "darkBg": "#111", "darkAccent": "#eee"}
        )
        assert manager.delete_custom_theme(theme.theme_id) is True
        assert manager.get_custom_theme(theme.theme_id) is None

    def test_list_custom(self):
        manager = ThemeManager()
        manager.create_custom_theme("A", colors={"bg": "#fff", "accent": "#000", "darkBg": "#111", "darkAccent": "#eee"})
        manager.create_custom_theme("B", colors={"bg": "#fff", "accent": "#000", "darkBg": "#111", "darkAccent": "#eee"})
        assert len(manager.list_custom_themes()) == 2

    def test_validation_error(self):
        manager = ThemeManager()
        with pytest.raises(ValueError, match="Invalid"):
            manager.create_custom_theme(
                "Bad Theme",
                colors={"bg": "not-a-color", "accent": "#000", "darkBg": "#111", "darkAccent": "#eee"},
            )


# ---------------------------------------------------------------------------
# Per-project themes tests
# ---------------------------------------------------------------------------

class TestProjectThemes:
    def test_set_project_theme(self):
        manager = ThemeManager()
        binding = manager.set_project_theme("proj-1", "ocean", mode="dark")
        assert binding.project_id == "proj-1"
        assert binding.theme_id == "ocean"
        assert binding.mode == "dark"

    def test_get_project_theme(self):
        manager = ThemeManager()
        manager.set_project_theme("proj-1", "default")
        binding = manager.get_project_theme("proj-1")
        assert binding is not None
        assert binding.theme_id == "default"

    def test_remove_project_theme(self):
        manager = ThemeManager()
        manager.set_project_theme("proj-1", "ocean")
        assert manager.remove_project_theme("proj-1") is True
        assert manager.get_project_theme("proj-1") is None

    def test_list_bindings(self):
        manager = ThemeManager()
        manager.set_project_theme("proj-1", "ocean")
        manager.set_project_theme("proj-2", "retro")
        bindings = manager.list_project_bindings()
        assert len(bindings) == 2

    def test_invalid_theme(self):
        manager = ThemeManager()
        with pytest.raises(ValueError, match="not found"):
            manager.set_project_theme("proj-1", "nonexistent-theme-id")


# ---------------------------------------------------------------------------
# Import / Export tests
# ---------------------------------------------------------------------------

class TestImportExport:
    def test_export_custom(self):
        manager = ThemeManager()
        theme = manager.create_custom_theme(
            "Export Me",
            colors={"bg": "#1a1a2e", "accent": "#e94560", "darkBg": "#0f0f1a", "darkAccent": "#ff6b6b"},
        )
        exported = manager.export_theme(theme.theme_id)
        assert exported is not None
        data = json.loads(exported)
        assert data["name"] == "Export Me"
        assert "_export_version" in data

    def test_export_builtin(self):
        manager = ThemeManager()
        exported = manager.export_theme("ocean")
        assert exported is not None
        data = json.loads(exported)
        assert data["name"] == "Ocean"

    def test_import_valid(self):
        manager = ThemeManager()
        theme_data = {
            "name": "Imported Theme",
            "description": "From another instance",
            "colors": {
                "bg": "#1a1a2e", "accent": "#e94560",
                "darkBg": "#0f0f1a", "darkAccent": "#ff6b6b",
            },
            "author": "Bob",
        }
        imported = manager.import_theme(json.dumps(theme_data))
        assert imported.name == "Imported Theme"
        assert imported.source == "imported"
        assert imported.author == "Bob"

    def test_import_invalid_json(self):
        manager = ThemeManager()
        with pytest.raises(ValueError, match="Invalid JSON"):
            manager.import_theme("not valid json {{{")

    def test_import_invalid_colors(self):
        manager = ThemeManager()
        theme_data = {
            "name": "Bad Import",
            "colors": {"bg": "xyz", "accent": "abc", "darkBg": "def", "darkAccent": "ghi"},
        }
        with pytest.raises(ValueError, match="Invalid"):
            manager.import_theme(json.dumps(theme_data))


# ---------------------------------------------------------------------------
# CSS generation tests
# ---------------------------------------------------------------------------

class TestCSSGeneration:
    def test_light_mode(self):
        manager = ThemeManager()
        css = manager.generate_css_variables("ocean", mode="light")
        assert css is not None
        assert "--theme-bg" in css
        assert "#E0F2FE" in css  # Ocean light bg

    def test_dark_mode(self):
        manager = ThemeManager()
        css = manager.generate_css_variables("ocean", mode="dark")
        assert css is not None
        assert "--theme-bg" in css
        assert "#082F49" in css  # Ocean dark bg

    def test_missing_theme(self):
        manager = ThemeManager()
        css = manager.generate_css_variables("nonexistent")
        assert css is None


# ---------------------------------------------------------------------------
# All themes tests
# ---------------------------------------------------------------------------

class TestAllThemes:
    def test_list_all(self):
        manager = ThemeManager()
        manager.create_custom_theme("Custom", colors={"bg": "#fff", "accent": "#000", "darkBg": "#111", "darkAccent": "#eee"})
        all_themes = manager.list_all_themes()
        assert len(all_themes) == 8  # 7 builtin + 1 custom

    def test_count(self):
        manager = ThemeManager()
        all_themes = manager.list_all_themes()
        assert len(all_themes) == 7  # Only builtins

    def test_sources(self):
        manager = ThemeManager()
        manager.create_custom_theme("Custom", colors={"bg": "#fff", "accent": "#000", "darkBg": "#111", "darkAccent": "#eee"})
        all_themes = manager.list_all_themes()
        sources = {t.get("source") for t in all_themes}
        assert "builtin" in sources
        assert "custom" in sources


# ---------------------------------------------------------------------------
# Stats tests
# ---------------------------------------------------------------------------

class TestStats:
    def test_stats_basic(self):
        manager = ThemeManager()
        manager.create_custom_theme("A", colors={"bg": "#fff", "accent": "#000", "darkBg": "#111", "darkAccent": "#eee"})
        manager.set_project_theme("proj-1", "ocean")
        stats = manager.get_stats()
        assert stats["builtin_themes"] == 7
        assert stats["custom_themes"] == 1
        assert stats["total_themes"] == 8
        assert stats["project_bindings"] == 1

    def test_stats_empty(self):
        manager = ThemeManager()
        stats = manager.get_stats()
        assert stats["custom_themes"] == 0
        assert stats["project_bindings"] == 0


# ---------------------------------------------------------------------------
# Edge cases tests
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_delete_theme_removes_bindings(self):
        manager = ThemeManager()
        theme = manager.create_custom_theme("Temp", colors={"bg": "#fff", "accent": "#000", "darkBg": "#111", "darkAccent": "#eee"})
        manager.set_project_theme("proj-1", theme.theme_id)
        assert manager.get_project_theme("proj-1") is not None
        manager.delete_custom_theme(theme.theme_id)
        assert manager.get_project_theme("proj-1") is None

    def test_update_nonexistent(self):
        manager = ThemeManager()
        result = manager.update_custom_theme("nonexistent", name="Nope")
        assert result is None
