"""Tests for Feature 9.4 — Global Keyboard Shortcuts.

40 tests covering:
- KeyboardShortcut: 3
- ShortcutConflict: 2
- Key normalization: 5
- Default shortcuts: 3
- Registration: 4
- Resolution: 5
- Execution: 3
- Customization (remap): 4
- Reset: 3
- Cheat sheet: 2
- Conflict detection: 2
- Export/Import: 2
- Stats: 2
"""

import pytest
from apps.backend.ui.keyboard_shortcuts import (
    DEFAULT_SHORTCUTS,
    KeyboardShortcut,
    ShortcutConflict,
    ShortcutManager,
    normalize_keys,
)


# ---------------------------------------------------------------------------
# KeyboardShortcut tests (3)
# ---------------------------------------------------------------------------

class TestKeyboardShortcut:
    def test_creation(self):
        s = KeyboardShortcut(keys="Ctrl+N", action_id="create_task")
        assert s.keys == "Ctrl+N"
        assert s.enabled is True
        assert s.is_custom is False

    def test_to_dict(self):
        s = KeyboardShortcut(keys="Ctrl+K", action_id="palette", category="general")
        d = s.to_dict()
        assert d["keys"] == "Ctrl+K"
        assert d["category"] == "general"

    def test_normalized_keys(self):
        s = KeyboardShortcut(keys="ctrl+shift+n")
        assert s.normalized_keys == "Ctrl+Shift+N"


# ---------------------------------------------------------------------------
# ShortcutConflict tests (2)
# ---------------------------------------------------------------------------

class TestShortcutConflict:
    def test_creation(self):
        c = ShortcutConflict(keys="Ctrl+N", existing_action="a", new_action="b")
        assert c.existing_action == "a"

    def test_to_dict(self):
        c = ShortcutConflict(keys="Ctrl+K", existing_action="x", new_action="y", scope="global")
        d = c.to_dict()
        assert d["scope"] == "global"


# ---------------------------------------------------------------------------
# Key normalization tests (5)
# ---------------------------------------------------------------------------

class TestNormalizeKeys:
    def test_basic(self):
        assert normalize_keys("Ctrl+N") == "Ctrl+N"

    def test_lowercase(self):
        assert normalize_keys("ctrl+n") == "Ctrl+N"

    def test_modifier_order(self):
        assert normalize_keys("Shift+Ctrl+N") == "Ctrl+Shift+N"

    def test_aliases(self):
        assert normalize_keys("cmd+k") == "Meta+K"
        assert normalize_keys("option+s") == "Alt+S"

    def test_special_keys(self):
        assert normalize_keys("ctrl+enter") == "Ctrl+Enter"
        assert normalize_keys("esc") == "Escape"


# ---------------------------------------------------------------------------
# Default shortcuts (3)
# ---------------------------------------------------------------------------

class TestDefaultShortcuts:
    def test_defaults_loaded(self):
        mgr = ShortcutManager()
        shortcuts = mgr.list_shortcuts()
        assert len(shortcuts) >= len(DEFAULT_SHORTCUTS)

    def test_ctrl_n_registered(self):
        mgr = ShortcutManager()
        s = mgr.get_shortcut_for_action("create_task")
        assert s is not None
        assert s.keys == "Ctrl+N"

    def test_ctrl_k_registered(self):
        mgr = ShortcutManager()
        s = mgr.get_shortcut_for_action("command_palette")
        assert s is not None
        assert s.keys == "Ctrl+K"


# ---------------------------------------------------------------------------
# Registration (4)
# ---------------------------------------------------------------------------

class TestRegistration:
    def test_register_new(self):
        mgr = ShortcutManager(load_defaults=False)
        s = mgr.register("Ctrl+M", "my_action", label="My Action")
        assert s.action_id == "my_action"
        assert s.keys == "Ctrl+M"

    def test_register_with_handler(self):
        mgr = ShortcutManager(load_defaults=False)
        mgr.register("Ctrl+M", "my_action", handler=lambda: "done")
        result = mgr.execute("Ctrl+M")
        assert result == "done"

    def test_register_conflict_raises(self):
        mgr = ShortcutManager(load_defaults=False)
        mgr.register("Ctrl+N", "action_a")
        with pytest.raises(ValueError, match="conflicts"):
            mgr.register("Ctrl+N", "action_b")

    def test_unregister(self):
        mgr = ShortcutManager(load_defaults=False)
        mgr.register("Ctrl+M", "my_action")
        s = mgr.get_shortcut_for_action("my_action")
        s.is_custom = True  # Only custom can be unregistered
        mgr.unregister("my_action")
        assert mgr.get_shortcut_for_action("my_action") is None


# ---------------------------------------------------------------------------
# Resolution (5)
# ---------------------------------------------------------------------------

class TestResolution:
    def test_resolve_global(self):
        mgr = ShortcutManager()
        action = mgr.resolve("Ctrl+N")
        assert action == "create_task"

    def test_resolve_scoped(self):
        mgr = ShortcutManager()
        action = mgr.resolve("Ctrl+Enter", current_scope="kanban")
        assert action == "run_agent"

    def test_resolve_global_from_any_scope(self):
        mgr = ShortcutManager()
        action = mgr.resolve("Ctrl+N", current_scope="kanban")
        assert action == "create_task"

    def test_resolve_unknown(self):
        mgr = ShortcutManager()
        action = mgr.resolve("Ctrl+Shift+Z")
        assert action is None

    def test_scope_priority_over_global(self):
        mgr = ShortcutManager(load_defaults=False)
        mgr.register("Ctrl+X", "global_action", scope="global")
        mgr.register("Ctrl+X", "kanban_action", scope="kanban")
        # Kanban scope should take priority
        action = mgr.resolve("Ctrl+X", current_scope="kanban")
        assert action == "kanban_action"


# ---------------------------------------------------------------------------
# Execution (3)
# ---------------------------------------------------------------------------

class TestExecution:
    def test_execute_with_handler(self):
        mgr = ShortcutManager(load_defaults=False)
        mgr.register("Ctrl+M", "my_action", handler=lambda: 42)
        result = mgr.execute("Ctrl+M")
        assert result == 42

    def test_execute_no_handler_returns_action_id(self):
        mgr = ShortcutManager(load_defaults=False)
        mgr.register("Ctrl+M", "my_action")
        result = mgr.execute("Ctrl+M")
        assert result == "my_action"

    def test_execute_unknown_returns_none(self):
        mgr = ShortcutManager()
        result = mgr.execute("Ctrl+Shift+Z")
        assert result is None


# ---------------------------------------------------------------------------
# Customization — remap (4)
# ---------------------------------------------------------------------------

class TestRemap:
    def test_remap_action(self):
        mgr = ShortcutManager()
        s = mgr.remap("create_task", "Ctrl+Shift+N")
        assert s.keys == "Ctrl+Shift+N"
        assert s.is_custom is True

    def test_remap_resolves_new_key(self):
        mgr = ShortcutManager()
        mgr.remap("create_task", "Ctrl+Shift+N")
        action = mgr.resolve("Ctrl+Shift+N")
        assert action == "create_task"

    def test_remap_unknown_action_raises(self):
        mgr = ShortcutManager()
        with pytest.raises(KeyError):
            mgr.remap("nonexistent", "Ctrl+Z")

    def test_remap_conflict_raises(self):
        mgr = ShortcutManager()
        with pytest.raises(ValueError, match="conflicts"):
            mgr.remap("create_task", "Ctrl+K")  # Already used by command_palette


# ---------------------------------------------------------------------------
# Reset (3)
# ---------------------------------------------------------------------------

class TestReset:
    def test_reset_single(self):
        mgr = ShortcutManager()
        mgr.remap("create_task", "Ctrl+Shift+N")
        s = mgr.reset_to_default("create_task")
        assert s.keys == "Ctrl+N"
        assert s.is_custom is False

    def test_reset_all(self):
        mgr = ShortcutManager()
        mgr.remap("create_task", "Ctrl+Shift+N")
        count = mgr.reset_all()
        assert count == 1
        s = mgr.get_shortcut_for_action("create_task")
        assert s.keys == "Ctrl+N"

    def test_reset_unknown_returns_none(self):
        mgr = ShortcutManager()
        result = mgr.reset_to_default("nonexistent")
        assert result is None


# ---------------------------------------------------------------------------
# Cheat sheet (2)
# ---------------------------------------------------------------------------

class TestCheatSheet:
    def test_cheat_sheet_structure(self):
        mgr = ShortcutManager()
        sheet = mgr.get_cheat_sheet()
        assert isinstance(sheet, dict)
        assert len(sheet) > 0
        for category, shortcuts in sheet.items():
            assert isinstance(shortcuts, list)
            for s in shortcuts:
                assert "keys" in s
                assert "label" in s

    def test_cheat_sheet_categories(self):
        mgr = ShortcutManager()
        sheet = mgr.get_cheat_sheet()
        assert "navigation" in sheet
        assert "general" in sheet


# ---------------------------------------------------------------------------
# Conflict detection (2)
# ---------------------------------------------------------------------------

class TestConflictDetection:
    def test_no_conflicts_in_defaults(self):
        mgr = ShortcutManager()
        conflicts = mgr.detect_conflicts()
        # Default shortcuts should not have conflicts within the same scope
        global_conflicts = [c for c in conflicts if c.scope == "global"]
        assert len(global_conflicts) == 0

    def test_detect_added_conflict(self):
        mgr = ShortcutManager(load_defaults=False)
        mgr.register("Ctrl+N", "action_a", scope="global")
        # Manually add a second shortcut with same keys (bypassing check)
        from apps.backend.ui.keyboard_shortcuts import KeyboardShortcut
        dup = KeyboardShortcut(keys="Ctrl+N", action_id="action_b", scope="global")
        mgr._shortcuts[dup.shortcut_id] = dup
        conflicts = mgr.detect_conflicts()
        assert len(conflicts) >= 1


# ---------------------------------------------------------------------------
# Export / Import (2)
# ---------------------------------------------------------------------------

class TestExportImport:
    def test_export_config(self):
        mgr = ShortcutManager()
        mgr.remap("create_task", "Ctrl+Shift+N")
        config = mgr.export_config()
        assert "custom_mappings" in config
        assert "create_task" in config["custom_mappings"]

    def test_import_config(self):
        mgr = ShortcutManager()
        config = {"custom_mappings": {"create_task": "Ctrl+Shift+N"}, "disabled": []}
        count = mgr.import_config(config)
        assert count >= 1
        s = mgr.get_shortcut_for_action("create_task")
        assert s.keys == "Ctrl+Shift+N"


# ---------------------------------------------------------------------------
# Stats (2)
# ---------------------------------------------------------------------------

class TestStats:
    def test_basic_stats(self):
        mgr = ShortcutManager(load_defaults=False)
        mgr.register("Ctrl+A", "action_a")
        mgr.register("Ctrl+B", "action_b")
        stats = mgr.get_stats()
        assert stats["total_shortcuts"] == 2
        assert stats["custom_shortcuts"] == 0

    def test_stats_after_remap(self):
        mgr = ShortcutManager()
        mgr.remap("create_task", "Ctrl+Shift+N")
        stats = mgr.get_stats()
        assert stats["custom_shortcuts"] == 1
