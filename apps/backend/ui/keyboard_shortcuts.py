"""Global Keyboard Shortcuts — Complete keyboard navigation for power users.

Provides a centralized shortcut manager that registers, resolves, and tracks
keyboard shortcuts across the application.  Supports multi-key combos,
scope-based filtering (global vs view-specific), customization, conflict
detection, and cheat-sheet generation.

Feature 9.4 — Raccourcis clavier globaux.

Example:
    >>> from apps.backend.ui.keyboard_shortcuts import ShortcutManager
    >>> manager = ShortcutManager()
    >>> manager.register("Ctrl+N", "create_task", scope="global")
    >>> action = manager.resolve("Ctrl+N", current_scope="kanban")
    >>> print(action)  # "create_task"
"""

import logging
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ShortcutScope(str, Enum):
    """Scope where a shortcut is active."""

    GLOBAL = "global"
    KANBAN = "kanban"
    TERMINAL = "terminal"
    INSIGHTS = "insights"
    SETTINGS = "settings"
    CODE_REVIEW = "code_review"
    PAIR_PROGRAMMING = "pair_programming"
    DIALOG = "dialog"


class ShortcutCategory(str, Enum):
    """Category for organizing shortcuts in the cheat sheet."""

    NAVIGATION = "navigation"
    TASKS = "tasks"
    AGENTS = "agents"
    TERMINAL = "terminal"
    GENERAL = "general"
    EDITING = "editing"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class KeyboardShortcut:
    """A registered keyboard shortcut."""

    shortcut_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    keys: str = ""
    action_id: str = ""
    label: str = ""
    description: str = ""
    scope: str = "global"
    category: str = "general"
    enabled: bool = True
    is_custom: bool = False
    default_keys: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def normalized_keys(self) -> str:
        """Normalize key combo for consistent comparison."""
        return normalize_keys(self.keys)


@dataclass
class ShortcutConflict:
    """A conflict between two shortcuts."""

    keys: str = ""
    existing_action: str = ""
    new_action: str = ""
    scope: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ShortcutUsage:
    """Record of a shortcut being used."""

    action_id: str = ""
    keys: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    scope: str = ""


# ---------------------------------------------------------------------------
# Key normalization
# ---------------------------------------------------------------------------

MODIFIER_ORDER = ["Ctrl", "Alt", "Shift", "Meta"]
KEY_ALIASES = {
    "cmd": "Meta",
    "command": "Meta",
    "ctrl": "Ctrl",
    "control": "Ctrl",
    "alt": "Alt",
    "option": "Alt",
    "shift": "Shift",
    "enter": "Enter",
    "return": "Enter",
    "esc": "Escape",
    "escape": "Escape",
    "del": "Delete",
    "delete": "Delete",
    "backspace": "Backspace",
    "tab": "Tab",
    "space": "Space",
}


def normalize_keys(combo: str) -> str:
    """Normalize a key combination string for consistent matching."""
    parts = [p.strip() for p in combo.replace("+", " + ").split("+")]
    parts = [p.strip() for p in parts if p.strip()]

    normalized: list[str] = []
    for part in parts:
        lower = part.lower()
        if lower in KEY_ALIASES:
            normalized.append(KEY_ALIASES[lower])
        elif len(part) == 1:
            normalized.append(part.upper())
        else:
            normalized.append(part.capitalize())

    # Sort modifiers first, then key
    modifiers = [k for k in normalized if k in MODIFIER_ORDER]
    keys = [k for k in normalized if k not in MODIFIER_ORDER]
    modifiers.sort(key=lambda m: MODIFIER_ORDER.index(m))

    return "+".join(modifiers + keys)


# ---------------------------------------------------------------------------
# Built-in shortcuts
# ---------------------------------------------------------------------------

DEFAULT_SHORTCUTS = [
    KeyboardShortcut(
        keys="Ctrl+N",
        action_id="create_task",
        label="New Task",
        description="Create a new task",
        scope="global",
        category="tasks",
        default_keys="Ctrl+N",
    ),
    KeyboardShortcut(
        keys="Ctrl+K",
        action_id="command_palette",
        label="Command Palette",
        description="Open the command palette",
        scope="global",
        category="general",
        default_keys="Ctrl+K",
    ),
    KeyboardShortcut(
        keys="Ctrl+Shift+T",
        action_id="new_terminal",
        label="New Terminal",
        description="Open a new terminal session",
        scope="global",
        category="terminal",
        default_keys="Ctrl+Shift+T",
    ),
    KeyboardShortcut(
        keys="Ctrl+1",
        action_id="go_kanban",
        label="Go to Kanban",
        description="Navigate to Kanban board",
        scope="global",
        category="navigation",
        default_keys="Ctrl+1",
    ),
    KeyboardShortcut(
        keys="Ctrl+2",
        action_id="go_terminals",
        label="Go to Terminals",
        description="Navigate to Terminals view",
        scope="global",
        category="navigation",
        default_keys="Ctrl+2",
    ),
    KeyboardShortcut(
        keys="Ctrl+3",
        action_id="go_insights",
        label="Go to Insights",
        description="Navigate to Insights dashboard",
        scope="global",
        category="navigation",
        default_keys="Ctrl+3",
    ),
    KeyboardShortcut(
        keys="Ctrl+4",
        action_id="go_code_review",
        label="Go to Code Review",
        description="Navigate to Code Review",
        scope="global",
        category="navigation",
        default_keys="Ctrl+4",
    ),
    KeyboardShortcut(
        keys="Ctrl+5",
        action_id="go_settings",
        label="Go to Settings",
        description="Open Settings",
        scope="global",
        category="navigation",
        default_keys="Ctrl+5",
    ),
    KeyboardShortcut(
        keys="Ctrl+Enter",
        action_id="run_agent",
        label="Run Agent",
        description="Launch agent on selected task",
        scope="kanban",
        category="agents",
        default_keys="Ctrl+Enter",
    ),
    KeyboardShortcut(
        keys="/",
        action_id="search_tasks",
        label="Quick Search",
        description="Search tasks in Kanban",
        scope="kanban",
        category="tasks",
        default_keys="/",
    ),
    KeyboardShortcut(
        keys="Escape",
        action_id="close_dialog",
        label="Close",
        description="Close dialog or palette",
        scope="dialog",
        category="general",
        default_keys="Escape",
    ),
    KeyboardShortcut(
        keys="Ctrl+/",
        action_id="keyboard_shortcuts",
        label="Keyboard Shortcuts",
        description="Show keyboard shortcuts cheat sheet",
        scope="global",
        category="general",
        default_keys="Ctrl+/",
    ),
    KeyboardShortcut(
        keys="Ctrl+Shift+D",
        action_id="open_dependency_graph",
        label="Dependency Graph",
        description="Open task dependency graph",
        scope="global",
        category="tasks",
        default_keys="Ctrl+Shift+D",
    ),
    KeyboardShortcut(
        keys="Ctrl+Shift+P",
        action_id="open_pair_programming",
        label="Pair Programming",
        description="Start pair programming on selected task",
        scope="kanban",
        category="agents",
        default_keys="Ctrl+Shift+P",
    ),
    KeyboardShortcut(
        keys="Ctrl+Shift+E",
        action_id="export_report",
        label="Export Report",
        description="Export current report",
        scope="insights",
        category="general",
        default_keys="Ctrl+Shift+E",
    ),
]


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class ShortcutManager:
    """Centralized keyboard shortcut manager.

    Registers, resolves, and tracks keyboard shortcuts with support for
    scoping, customization, conflict detection, and usage analytics.
    """

    def __init__(self, load_defaults: bool = True) -> None:
        self._shortcuts: dict[str, KeyboardShortcut] = {}
        self._handlers: dict[str, Callable] = {}
        self._usage: list[ShortcutUsage] = []
        self._custom_mappings: dict[str, str] = {}

        if load_defaults:
            for shortcut in DEFAULT_SHORTCUTS:
                self._shortcuts[shortcut.shortcut_id] = shortcut

    # -- Registration --------------------------------------------------------

    def register(
        self,
        keys: str,
        action_id: str,
        label: str = "",
        description: str = "",
        scope: str = "global",
        category: str = "general",
        handler: Callable | None = None,
    ) -> KeyboardShortcut:
        """Register a new keyboard shortcut."""
        normalized = normalize_keys(keys)
        conflict = self._check_conflict(normalized, action_id, scope)
        if conflict:
            raise ValueError(
                f"Shortcut '{keys}' conflicts with '{conflict.existing_action}' in scope '{scope}'"
            )

        shortcut = KeyboardShortcut(
            keys=normalized,
            action_id=action_id,
            label=label or action_id,
            description=description,
            scope=scope,
            category=category,
            default_keys=normalized,
        )
        self._shortcuts[shortcut.shortcut_id] = shortcut
        if handler:
            self._handlers[action_id] = handler
        return shortcut

    def unregister(self, action_id: str) -> None:
        """Remove all shortcuts for an action."""
        to_remove = [
            sid
            for sid, s in self._shortcuts.items()
            if s.action_id == action_id and s.is_custom
        ]
        for sid in to_remove:
            del self._shortcuts[sid]

    def register_handler(self, action_id: str, handler: Callable) -> None:
        """Register an execution handler for an action."""
        self._handlers[action_id] = handler

    # -- Resolution ----------------------------------------------------------

    def resolve(self, keys: str, current_scope: str = "global") -> str | None:
        """Resolve a key combination to an action ID.

        Checks scope-specific shortcuts first, then global ones.
        Returns None if no matching shortcut is found.
        """
        normalized = normalize_keys(keys)

        # Check scope-specific first
        for shortcut in self._shortcuts.values():
            if not shortcut.enabled:
                continue
            if (
                shortcut.normalized_keys == normalized
                and shortcut.scope == current_scope
            ):
                self._record_usage(shortcut, current_scope)
                return shortcut.action_id

        # Then check global
        for shortcut in self._shortcuts.values():
            if not shortcut.enabled:
                continue
            if shortcut.normalized_keys == normalized and shortcut.scope == "global":
                self._record_usage(shortcut, current_scope)
                return shortcut.action_id

        return None

    def execute(
        self, keys: str, current_scope: str = "global", **kwargs: Any
    ) -> Any | None:
        """Resolve and execute a shortcut. Returns the handler result or None."""
        action_id = self.resolve(keys, current_scope)
        if not action_id:
            return None
        handler = self._handlers.get(action_id)
        if handler:
            return handler(**kwargs)
        return action_id

    # -- Customization -------------------------------------------------------

    def remap(self, action_id: str, new_keys: str) -> KeyboardShortcut:
        """Remap an existing action to new keys."""
        normalized = normalize_keys(new_keys)

        # Find the existing shortcut
        target = None
        for shortcut in self._shortcuts.values():
            if shortcut.action_id == action_id:
                target = shortcut
                break
        if not target:
            raise KeyError(f"No shortcut found for action '{action_id}'")

        # Check for conflicts
        conflict = self._check_conflict(normalized, action_id, target.scope)
        if conflict:
            raise ValueError(
                f"Key '{new_keys}' conflicts with '{conflict.existing_action}' in scope '{target.scope}'"
            )

        target.keys = normalized
        target.is_custom = True
        self._custom_mappings[action_id] = normalized
        return target

    def reset_to_default(self, action_id: str) -> KeyboardShortcut | None:
        """Reset a shortcut to its default keys."""
        for shortcut in self._shortcuts.values():
            if shortcut.action_id == action_id and shortcut.default_keys:
                shortcut.keys = shortcut.default_keys
                shortcut.is_custom = False
                self._custom_mappings.pop(action_id, None)
                return shortcut
        return None

    def reset_all(self) -> int:
        """Reset all shortcuts to defaults. Returns count of reset shortcuts."""
        count = 0
        for shortcut in self._shortcuts.values():
            if shortcut.is_custom and shortcut.default_keys:
                shortcut.keys = shortcut.default_keys
                shortcut.is_custom = False
                count += 1
        self._custom_mappings.clear()
        return count

    # -- Queries -------------------------------------------------------------

    def get_shortcut_for_action(self, action_id: str) -> KeyboardShortcut | None:
        """Get the shortcut assigned to an action."""
        for shortcut in self._shortcuts.values():
            if shortcut.action_id == action_id:
                return shortcut
        return None

    def list_shortcuts(
        self,
        scope: str | None = None,
        category: str | None = None,
    ) -> list[KeyboardShortcut]:
        """List all shortcuts, optionally filtered."""
        shortcuts = list(self._shortcuts.values())
        if scope:
            shortcuts = [s for s in shortcuts if s.scope in (scope, "global")]
        if category:
            shortcuts = [s for s in shortcuts if s.category == category]
        return shortcuts

    def get_cheat_sheet(self) -> dict[str, list[dict[str, str]]]:
        """Generate a cheat sheet grouped by category."""
        sheet: dict[str, list[dict[str, str]]] = {}
        for shortcut in sorted(self._shortcuts.values(), key=lambda s: s.category):
            if not shortcut.enabled:
                continue
            cat = shortcut.category
            if cat not in sheet:
                sheet[cat] = []
            sheet[cat].append(
                {
                    "keys": shortcut.keys,
                    "label": shortcut.label,
                    "description": shortcut.description,
                    "scope": shortcut.scope,
                }
            )
        return sheet

    def detect_conflicts(self) -> list[ShortcutConflict]:
        """Detect all conflicts among registered shortcuts."""
        conflicts: list[ShortcutConflict] = []
        shortcuts_list = list(self._shortcuts.values())
        seen: set[str] = set()

        for i, s1 in enumerate(shortcuts_list):
            for s2 in shortcuts_list[i + 1 :]:
                if s1.normalized_keys == s2.normalized_keys:
                    # Same scope or one is global
                    if (
                        s1.scope == s2.scope
                        or s1.scope == "global"
                        or s2.scope == "global"
                    ):
                        key = f"{s1.action_id}-{s2.action_id}"
                        if key not in seen:
                            conflicts.append(
                                ShortcutConflict(
                                    keys=s1.keys,
                                    existing_action=s1.action_id,
                                    new_action=s2.action_id,
                                    scope=s1.scope,
                                )
                            )
                            seen.add(key)

        return conflicts

    # -- Export/Import -------------------------------------------------------

    def export_config(self) -> dict[str, Any]:
        """Export custom shortcuts config."""
        return {
            "custom_mappings": dict(self._custom_mappings),
            "disabled": [
                s.action_id for s in self._shortcuts.values() if not s.enabled
            ],
        }

    def import_config(self, config: dict[str, Any]) -> int:
        """Import custom shortcuts config. Returns count of applied changes."""
        count = 0
        for action_id, keys in config.get("custom_mappings", {}).items():
            try:
                self.remap(action_id, keys)
                count += 1
            except (KeyError, ValueError) as exc:
                logger.warning(
                    "Could not import remap %s -> %s: %s", action_id, keys, exc
                )

        for action_id in config.get("disabled", []):
            for shortcut in self._shortcuts.values():
                if shortcut.action_id == action_id:
                    shortcut.enabled = False
                    count += 1
        return count

    # -- Stats ---------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Get shortcut usage statistics."""
        action_counts: dict[str, int] = {}
        for u in self._usage:
            action_counts[u.action_id] = action_counts.get(u.action_id, 0) + 1

        return {
            "total_shortcuts": len(self._shortcuts),
            "custom_shortcuts": sum(1 for s in self._shortcuts.values() if s.is_custom),
            "disabled_shortcuts": sum(
                1 for s in self._shortcuts.values() if not s.enabled
            ),
            "total_usages": len(self._usage),
            "usage_by_action": action_counts,
            "most_used": sorted(
                action_counts.items(), key=lambda x: x[1], reverse=True
            )[:5],
        }

    # -- Internal helpers ----------------------------------------------------

    def _check_conflict(
        self,
        normalized_keys: str,
        action_id: str,
        scope: str,
    ) -> ShortcutConflict | None:
        for shortcut in self._shortcuts.values():
            if shortcut.action_id == action_id:
                continue
            if shortcut.normalized_keys == normalized_keys:
                # Same scope = conflict.  Both global = conflict.
                # But a scoped shortcut is allowed to shadow a global one.
                if shortcut.scope == scope:
                    return ShortcutConflict(
                        keys=normalized_keys,
                        existing_action=shortcut.action_id,
                        new_action=action_id,
                        scope=scope,
                    )
                if shortcut.scope == "global" and scope == "global":
                    return ShortcutConflict(
                        keys=normalized_keys,
                        existing_action=shortcut.action_id,
                        new_action=action_id,
                        scope=scope,
                    )
        return None

    def _record_usage(self, shortcut: KeyboardShortcut, scope: str) -> None:
        self._usage.append(
            ShortcutUsage(
                action_id=shortcut.action_id,
                keys=shortcut.keys,
                scope=scope,
            )
        )
