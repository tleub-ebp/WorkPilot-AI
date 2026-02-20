"""Tests for Feature 9.5 — Command Palette (type VSCode).

40 tests covering:
- PaletteCommand: 3
- SearchResult: 2
- CommandExecution: 2
- Fuzzy matching: 5
- Built-in commands: 3
- Command registration: 4
- Search: 6
- Execution: 4
- History: 3
- Recent commands: 3
- Stats: 2
- Scope filtering: 3
"""

import pytest
from apps.backend.ui.command_palette import (
    BUILTIN_COMMANDS,
    CommandExecution,
    CommandPalette,
    PaletteCommand,
    SearchResult,
    fuzzy_match,
)


# ---------------------------------------------------------------------------
# PaletteCommand tests (3)
# ---------------------------------------------------------------------------

class TestPaletteCommand:
    def test_creation(self):
        cmd = PaletteCommand(command_id="test", label="Test Command")
        assert cmd.command_id == "test"
        assert cmd.enabled is True

    def test_to_dict(self):
        cmd = PaletteCommand(command_id="x", label="X", category="tasks")
        d = cmd.to_dict()
        assert d["category"] == "tasks"

    def test_searchable_text(self):
        cmd = PaletteCommand(
            label="Create Task",
            description="Make a new task",
            category="tasks",
            keywords=["add", "new"],
        )
        text = cmd.searchable_text
        assert "create task" in text
        assert "add" in text
        assert "tasks" in text


# ---------------------------------------------------------------------------
# SearchResult tests (2)
# ---------------------------------------------------------------------------

class TestSearchResult:
    def test_creation(self):
        r = SearchResult(command_id="test", label="Test", score=85.0)
        assert r.score == 85.0

    def test_to_dict(self):
        r = SearchResult(command_id="x", category="nav")
        d = r.to_dict()
        assert d["category"] == "nav"


# ---------------------------------------------------------------------------
# CommandExecution tests (2)
# ---------------------------------------------------------------------------

class TestCommandExecution:
    def test_creation(self):
        e = CommandExecution(command_id="test")
        assert e.success is True
        assert e.execution_id

    def test_to_dict(self):
        e = CommandExecution(command_id="test", success=False, error="fail")
        d = e.to_dict()
        assert d["success"] is False
        assert d["error"] == "fail"


# ---------------------------------------------------------------------------
# Fuzzy matching tests (5)
# ---------------------------------------------------------------------------

class TestFuzzyMatch:
    def test_exact_match(self):
        score, positions = fuzzy_match("create", "Create Task")
        assert score > 0
        assert len(positions) > 0

    def test_substring_match(self):
        score, positions = fuzzy_match("task", "Create Task")
        assert score > 0

    def test_fuzzy_characters(self):
        score, positions = fuzzy_match("ct", "Create Task")
        assert score > 0

    def test_no_match(self):
        score, positions = fuzzy_match("xyz", "Create Task")
        assert score == 0.0

    def test_empty_query(self):
        score, positions = fuzzy_match("", "Create Task")
        assert score > 0  # Empty query matches everything


# ---------------------------------------------------------------------------
# Built-in commands (3)
# ---------------------------------------------------------------------------

class TestBuiltinCommands:
    def test_builtins_loaded(self):
        palette = CommandPalette()
        cmds = palette.list_commands()
        assert len(cmds) >= len(BUILTIN_COMMANDS)

    def test_create_task_exists(self):
        palette = CommandPalette()
        cmd = palette.get_command("create_task")
        assert cmd.label == "Create Task"
        assert cmd.shortcut == "Ctrl+N"

    def test_command_palette_command_exists(self):
        palette = CommandPalette()
        cmd = palette.get_command("run_agent")
        assert cmd.label == "Run Agent"


# ---------------------------------------------------------------------------
# Command registration (4)
# ---------------------------------------------------------------------------

class TestCommandRegistration:
    def test_register_command(self):
        palette = CommandPalette()
        cmd = palette.register_command("my_cmd", "My Command", category="tasks")
        assert cmd.command_id == "my_cmd"
        assert palette.get_command("my_cmd").label == "My Command"

    def test_register_with_handler(self):
        palette = CommandPalette()
        palette.register_command("my_cmd", "My Cmd", handler=lambda: "done")
        result = palette.execute("my_cmd")
        assert result.result == "done"

    def test_unregister_command(self):
        palette = CommandPalette()
        palette.register_command("temp", "Temp")
        palette.unregister_command("temp")
        with pytest.raises(KeyError):
            palette.get_command("temp")

    def test_get_unknown_command_raises(self):
        palette = CommandPalette()
        with pytest.raises(KeyError):
            palette.get_command("nonexistent")


# ---------------------------------------------------------------------------
# Search tests (6)
# ---------------------------------------------------------------------------

class TestSearch:
    def test_exact_search(self):
        palette = CommandPalette()
        results = palette.search("Create Task")
        assert len(results) > 0
        assert results[0].command_id == "create_task"

    def test_fuzzy_search(self):
        palette = CommandPalette()
        results = palette.search("creat tsk")
        assert len(results) > 0

    def test_search_by_keyword(self):
        palette = CommandPalette()
        results = palette.search("terminal")
        ids = [r.command_id for r in results]
        assert "new_terminal" in ids

    def test_empty_query_returns_defaults(self):
        palette = CommandPalette()
        results = palette.search("")
        assert len(results) > 0

    def test_search_limit(self):
        palette = CommandPalette()
        results = palette.search("go", limit=3)
        assert len(results) <= 3

    def test_search_results_sorted_by_score(self):
        palette = CommandPalette()
        results = palette.search("task")
        if len(results) >= 2:
            assert results[0].score >= results[1].score


# ---------------------------------------------------------------------------
# Execution tests (4)
# ---------------------------------------------------------------------------

class TestExecution:
    def test_execute_command(self):
        palette = CommandPalette()
        result = palette.execute("create_task")
        assert result.success is True
        assert result.command_id == "create_task"

    def test_execute_with_handler(self):
        palette = CommandPalette()
        palette.register_handler("create_task", lambda: {"created": True})
        result = palette.execute("create_task")
        assert result.result == {"created": True}

    def test_execute_handler_error(self):
        palette = CommandPalette()
        palette.register_handler("create_task", lambda: 1 / 0)
        result = palette.execute("create_task")
        assert result.success is False
        assert result.error is not None

    def test_execute_unknown_raises(self):
        palette = CommandPalette()
        with pytest.raises(KeyError):
            palette.execute("nonexistent")


# ---------------------------------------------------------------------------
# History tests (3)
# ---------------------------------------------------------------------------

class TestHistory:
    def test_execution_recorded(self):
        palette = CommandPalette()
        palette.execute("create_task")
        history = palette.get_history()
        assert len(history) == 1
        assert history[0].command_id == "create_task"

    def test_history_order(self):
        palette = CommandPalette()
        palette.execute("create_task")
        palette.execute("run_agent")
        history = palette.get_history()
        assert history[0].command_id == "run_agent"
        assert history[1].command_id == "create_task"

    def test_history_limit(self):
        palette = CommandPalette(max_history=5)
        for i in range(10):
            palette.register_command(f"cmd_{i}", f"Cmd {i}")
            palette.execute(f"cmd_{i}")
        history = palette.get_history()
        assert len(history) <= 5


# ---------------------------------------------------------------------------
# Recent commands (3)
# ---------------------------------------------------------------------------

class TestRecentCommands:
    def test_recent_updated_on_execute(self):
        palette = CommandPalette()
        palette.execute("create_task")
        recent = palette.get_recent_commands()
        assert len(recent) == 1
        assert recent[0].command_id == "create_task"

    def test_recent_order(self):
        palette = CommandPalette()
        palette.execute("create_task")
        palette.execute("run_agent")
        recent = palette.get_recent_commands()
        assert recent[0].command_id == "run_agent"

    def test_recent_boosted_in_search(self):
        palette = CommandPalette()
        palette.execute("export_report")
        results = palette.search("export")
        ids = [r.command_id for r in results]
        assert "export_report" in ids


# ---------------------------------------------------------------------------
# Stats (2)
# ---------------------------------------------------------------------------

class TestStats:
    def test_basic_stats(self):
        palette = CommandPalette()
        stats = palette.get_stats()
        assert stats["total_commands"] >= len(BUILTIN_COMMANDS)
        assert stats["total_executions"] == 0

    def test_stats_after_executions(self):
        palette = CommandPalette()
        palette.execute("create_task")
        palette.execute("create_task")
        palette.execute("run_agent")
        stats = palette.get_stats()
        assert stats["total_executions"] == 3
        assert stats["successful_executions"] == 3


# ---------------------------------------------------------------------------
# Scope filtering (3)
# ---------------------------------------------------------------------------

class TestScopeFiltering:
    def test_list_commands_by_category(self):
        palette = CommandPalette()
        nav = palette.list_commands(category="navigation")
        assert all(c.category == "navigation" for c in nav)

    def test_search_with_scope(self):
        palette = CommandPalette()
        palette.register_command("kanban_only", "Kanban Only", scope="kanban")
        results = palette.search("Kanban Only", scope="kanban")
        assert len(results) > 0

    def test_global_commands_available_in_all_scopes(self):
        palette = CommandPalette()
        results = palette.search("Create Task", scope="kanban")
        ids = [r.command_id for r in results]
        assert "create_task" in ids
