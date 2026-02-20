"""Command Palette — Universal command bar with fuzzy search (VSCode-style).

Provides a searchable command palette accessible via Ctrl+K / Cmd+K that
lets users search tasks, specs, files, settings, and execute commands like
"Create task", "Switch provider", "Open terminal".  Supports fuzzy matching,
command history, contextual actions, and extensible command registration.

Feature 9.5 — Command Palette (type VSCode).

Example:
    >>> from apps.backend.ui.command_palette import CommandPalette
    >>> palette = CommandPalette()
    >>> palette.register_command("create_task", "Create Task", category="tasks")
    >>> results = palette.search("creat task")
    >>> palette.execute("create_task")
"""

import logging
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CommandCategory(str, Enum):
    """Categories for palette commands."""
    TASKS = "tasks"
    NAVIGATION = "navigation"
    AGENTS = "agents"
    SETTINGS = "settings"
    PROVIDERS = "providers"
    FILES = "files"
    TERMINAL = "terminal"
    HELP = "help"
    RECENT = "recent"


class CommandScope(str, Enum):
    """Scope where a command is available."""
    GLOBAL = "global"
    KANBAN = "kanban"
    TERMINAL = "terminal"
    INSIGHTS = "insights"
    SETTINGS = "settings"
    CODE_REVIEW = "code_review"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class PaletteCommand:
    """A command registered in the palette."""
    command_id: str = ""
    label: str = ""
    description: str = ""
    category: str = "navigation"
    icon: str = ""
    shortcut: str = ""
    scope: str = "global"
    keywords: List[str] = field(default_factory=list)
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def searchable_text(self) -> str:
        parts = [self.label, self.description, self.category]
        parts.extend(self.keywords)
        return " ".join(parts).lower()


@dataclass
class SearchResult:
    """A search result from the palette."""
    command_id: str = ""
    label: str = ""
    description: str = ""
    category: str = ""
    icon: str = ""
    shortcut: str = ""
    score: float = 0.0
    match_positions: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CommandExecution:
    """Record of a command execution."""
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    command_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    success: bool = True
    result: Any = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "command_id": self.command_id,
            "timestamp": self.timestamp,
            "success": self.success,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Fuzzy matching
# ---------------------------------------------------------------------------

def fuzzy_match(query: str, text: str) -> tuple:
    """Fuzzy match a query against text. Returns (score, match_positions).

    Score is 0 if no match. Higher is better.
    """
    query_lower = query.lower()
    text_lower = text.lower()

    if not query_lower:
        return (1.0, [])

    # Exact substring match — highest score
    if query_lower in text_lower:
        start = text_lower.index(query_lower)
        positions = list(range(start, start + len(query_lower)))
        # Bonus for match at start
        bonus = 20.0 if start == 0 else 0.0
        return (100.0 + bonus, positions)

    # Word-start matching
    words = text_lower.split()
    word_starts = []
    pos = 0
    for w in words:
        idx = text_lower.index(w, pos)
        word_starts.append(idx)
        pos = idx + len(w)

    # Fuzzy character-by-character matching
    qi = 0
    positions: List[int] = []
    score = 0.0
    prev_match = -2

    for ti in range(len(text_lower)):
        if qi >= len(query_lower):
            break
        if text_lower[ti] == query_lower[qi]:
            positions.append(ti)
            # Consecutive match bonus
            if ti == prev_match + 1:
                score += 8.0
            # Word start bonus
            elif ti in word_starts:
                score += 6.0
            else:
                score += 4.0
            prev_match = ti
            qi += 1

    if qi < len(query_lower):
        return (0.0, [])

    # Length penalty
    score = score * (len(query_lower) / max(len(text_lower), 1))

    return (score, positions)


# ---------------------------------------------------------------------------
# Built-in commands
# ---------------------------------------------------------------------------

BUILTIN_COMMANDS = [
    PaletteCommand(
        command_id="create_task",
        label="Create Task",
        description="Create a new task in the Kanban board",
        category="tasks",
        icon="plus-circle",
        shortcut="Ctrl+N",
        keywords=["new", "add", "task", "create"],
    ),
    PaletteCommand(
        command_id="search_tasks",
        label="Search Tasks",
        description="Search existing tasks by name or ID",
        category="tasks",
        icon="search",
        shortcut="/",
        keywords=["find", "filter", "task"],
    ),
    PaletteCommand(
        command_id="go_kanban",
        label="Go to Kanban",
        description="Navigate to the Kanban board view",
        category="navigation",
        icon="layout",
        shortcut="Ctrl+1",
        keywords=["board", "kanban", "tasks"],
    ),
    PaletteCommand(
        command_id="go_terminals",
        label="Go to Terminals",
        description="Navigate to the Terminals view",
        category="navigation",
        icon="terminal",
        shortcut="Ctrl+2",
        keywords=["terminal", "console", "shell"],
    ),
    PaletteCommand(
        command_id="go_insights",
        label="Go to Insights",
        description="Navigate to the Insights dashboard",
        category="navigation",
        icon="bar-chart",
        shortcut="Ctrl+3",
        keywords=["dashboard", "metrics", "analytics", "insights"],
    ),
    PaletteCommand(
        command_id="go_code_review",
        label="Go to Code Review",
        description="Navigate to the Code Review view",
        category="navigation",
        icon="eye",
        shortcut="Ctrl+4",
        keywords=["review", "code", "diff"],
    ),
    PaletteCommand(
        command_id="go_settings",
        label="Go to Settings",
        description="Open application settings",
        category="navigation",
        icon="settings",
        shortcut="Ctrl+5",
        keywords=["settings", "config", "preferences"],
    ),
    PaletteCommand(
        command_id="new_terminal",
        label="New Terminal",
        description="Open a new terminal session",
        category="terminal",
        icon="terminal",
        shortcut="Ctrl+Shift+T",
        keywords=["terminal", "shell", "console", "new"],
    ),
    PaletteCommand(
        command_id="run_agent",
        label="Run Agent",
        description="Launch the agent on the selected task",
        category="agents",
        icon="play",
        shortcut="Ctrl+Enter",
        keywords=["run", "agent", "execute", "start", "launch"],
    ),
    PaletteCommand(
        command_id="switch_provider",
        label="Switch LLM Provider",
        description="Change the active LLM provider",
        category="providers",
        icon="cpu",
        keywords=["provider", "llm", "model", "switch", "change"],
    ),
    PaletteCommand(
        command_id="toggle_theme",
        label="Toggle Theme",
        description="Switch between light and dark theme",
        category="settings",
        icon="sun",
        keywords=["theme", "dark", "light", "appearance"],
    ),
    PaletteCommand(
        command_id="go_roadmap",
        label="Go to Roadmap",
        description="Navigate to the project roadmap",
        category="navigation",
        icon="map",
        shortcut="Ctrl+4",
        keywords=["roadmap", "plan", "timeline"],
    ),
    PaletteCommand(
        command_id="go_ideation",
        label="Go to Ideation",
        description="Navigate to the ideation view",
        category="navigation",
        icon="lightbulb",
        keywords=["ideation", "brainstorm", "ideas"],
    ),
    PaletteCommand(
        command_id="go_context",
        label="Go to Context",
        description="Navigate to the context view",
        category="navigation",
        icon="book-open",
        keywords=["context", "memory", "knowledge"],
    ),
    PaletteCommand(
        command_id="go_agent_tools",
        label="Go to Agent Tools",
        description="Navigate to agent tools configuration",
        category="navigation",
        icon="wrench",
        keywords=["tools", "agent", "mcp"],
    ),
    PaletteCommand(
        command_id="go_changelog",
        label="Go to Changelog",
        description="Navigate to the changelog",
        category="navigation",
        icon="file-text",
        keywords=["changelog", "updates", "history"],
    ),
    PaletteCommand(
        command_id="go_worktrees",
        label="Go to Worktrees",
        description="Navigate to Git worktrees",
        category="navigation",
        icon="git-branch",
        keywords=["worktrees", "git", "branches"],
    ),
    PaletteCommand(
        command_id="go_dashboard",
        label="Go to Dashboard",
        description="View project metrics, KPIs, and analytics",
        category="navigation",
        icon="bar-chart-3",
        keywords=["dashboard", "metrics", "kpi", "analytics", "stats"],
    ),
    PaletteCommand(
        command_id="go_refactoring",
        label="Go to Refactoring",
        description="Detect code smells and get refactoring proposals",
        category="navigation",
        icon="wand-2",
        keywords=["refactor", "smells", "clean", "code"],
    ),
    PaletteCommand(
        command_id="go_documentation",
        label="Go to Documentation",
        description="Check coverage and generate docstrings",
        category="navigation",
        icon="book-open-check",
        keywords=["docs", "documentation", "docstring", "readme"],
    ),
    PaletteCommand(
        command_id="go_cost_estimator",
        label="Go to Cost Estimator",
        description="View LLM usage costs and budgets",
        category="navigation",
        icon="coins",
        keywords=["cost", "budget", "spending", "tokens", "money"],
    ),
    PaletteCommand(
        command_id="go_session_history",
        label="Go to Session History",
        description="Track agent session performance and costs",
        category="navigation",
        icon="history",
        keywords=["sessions", "history", "timeline", "past"],
    ),
    PaletteCommand(
        command_id="go_migration",
        label="Go to Migration",
        description="Framework migration wizard",
        category="navigation",
        icon="download",
        keywords=["migration", "framework", "upgrade", "wizard"],
    ),
    PaletteCommand(
        command_id="go_visual_programming",
        label="Go to Visual Programming",
        description="Visual node-based programming interface",
        category="navigation",
        icon="sparkles",
        keywords=["visual", "programming", "nodes", "flow"],
    ),
    PaletteCommand(
        command_id="go_github_issues",
        label="Go to GitHub Issues",
        description="View and manage GitHub issues",
        category="navigation",
        icon="github",
        keywords=["github", "issues", "bugs", "tickets"],
    ),
    PaletteCommand(
        command_id="go_github_prs",
        label="Go to GitHub PRs",
        description="View and review GitHub pull requests",
        category="navigation",
        icon="git-pull-request",
        keywords=["github", "pull", "requests", "prs", "review"],
    ),
    PaletteCommand(
        command_id="go_gitlab_issues",
        label="Go to GitLab Issues",
        description="View and manage GitLab issues",
        category="navigation",
        icon="git-merge",
        keywords=["gitlab", "issues", "bugs", "tickets"],
    ),
    PaletteCommand(
        command_id="go_gitlab_merge_requests",
        label="Go to GitLab Merge Requests",
        description="View and review GitLab merge requests",
        category="navigation",
        icon="git-merge",
        keywords=["gitlab", "merge", "requests", "mrs", "review"],
    ),
    PaletteCommand(
        command_id="open_pair_programming",
        label="Start Pair Programming",
        description="Start a pair programming session on the selected task",
        category="agents",
        icon="users",
        keywords=["pair", "programming", "interactive", "collaborate"],
    ),
    PaletteCommand(
        command_id="export_report",
        label="Export Report",
        description="Export dashboard report as JSON or CSV",
        category="tasks",
        icon="download",
        keywords=["export", "report", "csv", "json", "download"],
    ),
    PaletteCommand(
        command_id="open_dependency_graph",
        label="Open Dependency Graph",
        description="View task dependency graph visualization",
        category="navigation",
        icon="git-branch",
        keywords=["graph", "dependency", "dag", "dependencies"],
    ),
    PaletteCommand(
        command_id="keyboard_shortcuts",
        label="Keyboard Shortcuts",
        description="View all available keyboard shortcuts",
        category="help",
        icon="keyboard",
        shortcut="Ctrl+/",
        keywords=["shortcuts", "keyboard", "keys", "help", "hotkeys"],
    ),
]


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class CommandPalette:
    """Universal command palette with fuzzy search and command execution.

    Manages a registry of commands, supports fuzzy search, tracks execution
    history, and provides contextual filtering based on the active view.

    Args:
        max_history: Maximum number of recent commands to keep.
    """

    def __init__(self, max_history: int = 50) -> None:
        self._commands: Dict[str, PaletteCommand] = {}
        self._handlers: Dict[str, Callable] = {}
        self._history: List[CommandExecution] = []
        self._max_history = max_history
        self._recent_command_ids: List[str] = []

        # Register built-in commands
        for cmd in BUILTIN_COMMANDS:
            self._commands[cmd.command_id] = cmd

    # -- Command registration ------------------------------------------------

    def register_command(
        self,
        command_id: str,
        label: str,
        description: str = "",
        category: str = "navigation",
        icon: str = "",
        shortcut: str = "",
        scope: str = "global",
        keywords: Optional[List[str]] = None,
        handler: Optional[Callable] = None,
    ) -> PaletteCommand:
        """Register a new command in the palette."""
        cmd = PaletteCommand(
            command_id=command_id,
            label=label,
            description=description,
            category=category,
            icon=icon,
            shortcut=shortcut,
            scope=scope,
            keywords=keywords or [],
        )
        self._commands[command_id] = cmd
        if handler:
            self._handlers[command_id] = handler
        return cmd

    def unregister_command(self, command_id: str) -> None:
        """Remove a command from the palette."""
        self._commands.pop(command_id, None)
        self._handlers.pop(command_id, None)

    def register_handler(self, command_id: str, handler: Callable) -> None:
        """Register an execution handler for a command."""
        self._handlers[command_id] = handler

    def get_command(self, command_id: str) -> PaletteCommand:
        """Get a command by ID."""
        if command_id not in self._commands:
            raise KeyError(f"Command '{command_id}' not found")
        return self._commands[command_id]

    def list_commands(
        self,
        category: Optional[str] = None,
        scope: Optional[str] = None,
    ) -> List[PaletteCommand]:
        """List all registered commands, optionally filtered."""
        cmds = list(self._commands.values())
        if category:
            cmds = [c for c in cmds if c.category == category]
        if scope:
            cmds = [c for c in cmds if c.scope in (scope, "global")]
        return cmds

    # -- Search --------------------------------------------------------------

    def search(
        self,
        query: str,
        scope: Optional[str] = None,
        limit: int = 10,
    ) -> List[SearchResult]:
        """Fuzzy search commands. Returns results sorted by relevance."""
        if not query.strip():
            return self._get_default_results(scope, limit)

        results: List[SearchResult] = []
        for cmd in self._commands.values():
            if not cmd.enabled:
                continue
            if scope and cmd.scope not in (scope, "global"):
                continue

            score, positions = fuzzy_match(query, cmd.searchable_text)
            if score > 0:
                # Boost recently used commands
                recency_boost = 0.0
                if cmd.command_id in self._recent_command_ids:
                    idx = self._recent_command_ids.index(cmd.command_id)
                    recency_boost = max(0, 10 - idx)

                results.append(SearchResult(
                    command_id=cmd.command_id,
                    label=cmd.label,
                    description=cmd.description,
                    category=cmd.category,
                    icon=cmd.icon,
                    shortcut=cmd.shortcut,
                    score=score + recency_boost,
                    match_positions=positions,
                ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    # -- Execution -----------------------------------------------------------

    def execute(self, command_id: str, **kwargs: Any) -> CommandExecution:
        """Execute a command by ID."""
        if command_id not in self._commands:
            raise KeyError(f"Command '{command_id}' not found")

        execution = CommandExecution(command_id=command_id)

        handler = self._handlers.get(command_id)
        if handler:
            try:
                result = handler(**kwargs)
                execution.result = result
                execution.success = True
            except Exception as exc:
                execution.success = False
                execution.error = str(exc)
                logger.error("Command '%s' failed: %s", command_id, exc)
        else:
            execution.success = True
            execution.result = "no_handler"

        self._history.append(execution)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        # Update recent commands
        if command_id in self._recent_command_ids:
            self._recent_command_ids.remove(command_id)
        self._recent_command_ids.insert(0, command_id)
        self._recent_command_ids = self._recent_command_ids[:20]

        return execution

    # -- History -------------------------------------------------------------

    def get_history(self, limit: int = 20) -> List[CommandExecution]:
        """Get recent command execution history."""
        return list(reversed(self._history[-limit:]))

    def get_recent_commands(self, limit: int = 5) -> List[PaletteCommand]:
        """Get recently used commands."""
        result: List[PaletteCommand] = []
        for cid in self._recent_command_ids[:limit]:
            if cid in self._commands:
                result.append(self._commands[cid])
        return result

    # -- Stats ---------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get palette statistics."""
        category_counts: Dict[str, int] = {}
        for cmd in self._commands.values():
            category_counts[cmd.category] = category_counts.get(cmd.category, 0) + 1

        execution_counts: Dict[str, int] = {}
        for ex in self._history:
            execution_counts[ex.command_id] = execution_counts.get(ex.command_id, 0) + 1

        return {
            "total_commands": len(self._commands),
            "category_counts": category_counts,
            "total_executions": len(self._history),
            "successful_executions": sum(1 for e in self._history if e.success),
            "failed_executions": sum(1 for e in self._history if not e.success),
            "most_used": sorted(execution_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            "recent_commands_count": len(self._recent_command_ids),
        }

    # -- Internal helpers ----------------------------------------------------

    def _get_default_results(self, scope: Optional[str], limit: int) -> List[SearchResult]:
        """Return default results when query is empty (recent + popular)."""
        results: List[SearchResult] = []

        # Add recent commands first
        for cid in self._recent_command_ids:
            if cid in self._commands:
                cmd = self._commands[cid]
                if scope and cmd.scope not in (scope, "global"):
                    continue
                results.append(SearchResult(
                    command_id=cmd.command_id,
                    label=cmd.label,
                    description=cmd.description,
                    category="recent",
                    icon=cmd.icon,
                    shortcut=cmd.shortcut,
                    score=100.0,
                ))

        # Fill with navigation commands
        for cmd in self._commands.values():
            if cmd.command_id in self._recent_command_ids:
                continue
            if scope and cmd.scope not in (scope, "global"):
                continue
            if cmd.category == "navigation":
                results.append(SearchResult(
                    command_id=cmd.command_id,
                    label=cmd.label,
                    description=cmd.description,
                    category=cmd.category,
                    icon=cmd.icon,
                    shortcut=cmd.shortcut,
                    score=50.0,
                ))

        return results[:limit]
