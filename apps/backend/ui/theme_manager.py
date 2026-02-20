"""Custom Theme Manager — Advanced theming with custom color editor, import/export, per-project themes.

Extends the existing 7-theme system with:
- Automatic system dark/light mode detection
- Custom theme creation with color picker values
- Import/export themes as JSON
- Per-project theme binding (different theme for each project)

Feature 9.1 — Mode sombre/clair automatique + thème custom.

Example:
    >>> from apps.backend.ui.theme_manager import ThemeManager
    >>> manager = ThemeManager()
    >>> theme = manager.create_custom_theme("My Theme", colors={"bg": "#1a1a2e", "accent": "#e94560"})
    >>> manager.set_project_theme("proj-1", theme.theme_id)
    >>> exported = manager.export_theme(theme.theme_id)
"""

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ThemeMode(str, Enum):
    """Appearance mode."""
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


class ThemeSource(str, Enum):
    """Origin of a theme."""
    BUILTIN = "builtin"
    CUSTOM = "custom"
    IMPORTED = "imported"


# ---------------------------------------------------------------------------
# Built-in themes (matching the existing 7 themes in the frontend)
# ---------------------------------------------------------------------------

BUILTIN_THEMES = [
    {
        "id": "default",
        "name": "Default",
        "description": "Oscura-inspired with pale yellow accent",
        "colors": {
            "bg": "#F2F2ED", "accent": "#E6E7A3",
            "darkBg": "#0B0B0F", "darkAccent": "#E6E7A3",
            "foreground": "#1a1a1a", "darkForeground": "#f0f0f0",
            "muted": "#6b7280", "darkMuted": "#9ca3af",
            "border": "#e5e7eb", "darkBorder": "#374151",
        },
    },
    {
        "id": "dusk",
        "name": "Dusk",
        "description": "Warmer variant with slightly lighter dark mode",
        "colors": {
            "bg": "#F5F5F0", "accent": "#E6E7A3",
            "darkBg": "#131419", "darkAccent": "#E6E7A3",
            "foreground": "#1a1a1a", "darkForeground": "#f0f0f0",
            "muted": "#6b7280", "darkMuted": "#9ca3af",
            "border": "#e5e7eb", "darkBorder": "#374151",
        },
    },
    {
        "id": "lime",
        "name": "Lime",
        "description": "Fresh, energetic lime with purple accents",
        "colors": {
            "bg": "#E8F5A3", "accent": "#7C3AED",
            "darkBg": "#0F0F1A", "darkAccent": "#A78BFA",
            "foreground": "#1a1a1a", "darkForeground": "#f0f0f0",
            "muted": "#6b7280", "darkMuted": "#9ca3af",
            "border": "#e5e7eb", "darkBorder": "#374151",
        },
    },
    {
        "id": "ocean",
        "name": "Ocean",
        "description": "Calm, professional blue tones",
        "colors": {
            "bg": "#E0F2FE", "accent": "#0284C7",
            "darkBg": "#082F49", "darkAccent": "#38BDF8",
            "foreground": "#1a1a1a", "darkForeground": "#f0f0f0",
            "muted": "#6b7280", "darkMuted": "#9ca3af",
            "border": "#e5e7eb", "darkBorder": "#374151",
        },
    },
    {
        "id": "retro",
        "name": "Retro",
        "description": "Warm, nostalgic amber vibes",
        "colors": {
            "bg": "#FEF3C7", "accent": "#D97706",
            "darkBg": "#1C1917", "darkAccent": "#FBBF24",
            "foreground": "#1a1a1a", "darkForeground": "#f0f0f0",
            "muted": "#6b7280", "darkMuted": "#9ca3af",
            "border": "#e5e7eb", "darkBorder": "#374151",
        },
    },
    {
        "id": "neo",
        "name": "Neo",
        "description": "Modern cyberpunk pink/magenta",
        "colors": {
            "bg": "#FDF4FF", "accent": "#D946EF",
            "darkBg": "#0F0720", "darkAccent": "#E879F9",
            "foreground": "#1a1a1a", "darkForeground": "#f0f0f0",
            "muted": "#6b7280", "darkMuted": "#9ca3af",
            "border": "#e5e7eb", "darkBorder": "#374151",
        },
    },
    {
        "id": "forest",
        "name": "Forest",
        "description": "Natural, earthy green tones",
        "colors": {
            "bg": "#DCFCE7", "accent": "#16A34A",
            "darkBg": "#052E16", "darkAccent": "#4ADE80",
            "foreground": "#1a1a1a", "darkForeground": "#f0f0f0",
            "muted": "#6b7280", "darkMuted": "#9ca3af",
            "border": "#e5e7eb", "darkBorder": "#374151",
        },
    },
]

# Required color keys for a valid theme
REQUIRED_COLOR_KEYS = {"bg", "accent", "darkBg", "darkAccent"}
OPTIONAL_COLOR_KEYS = {"foreground", "darkForeground", "muted", "darkMuted", "border", "darkBorder"}
ALL_COLOR_KEYS = REQUIRED_COLOR_KEYS | OPTIONAL_COLOR_KEYS

# CSS hex color pattern
HEX_COLOR_RE = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ThemeColors:
    """Color palette for a theme (light + dark variants)."""
    bg: str = "#FFFFFF"
    accent: str = "#3B82F6"
    darkBg: str = "#0F172A"
    darkAccent: str = "#60A5FA"
    foreground: str = "#1a1a1a"
    darkForeground: str = "#f0f0f0"
    muted: str = "#6b7280"
    darkMuted: str = "#9ca3af"
    border: str = "#e5e7eb"
    darkBorder: str = "#374151"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ThemeColors":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def validate(self) -> list[str]:
        """Validate all color values. Returns list of errors."""
        errors: list[str] = []
        for key in REQUIRED_COLOR_KEYS:
            value = getattr(self, key, None)
            if not value:
                errors.append(f"Missing required color: {key}")
            elif not HEX_COLOR_RE.match(value):
                errors.append(f"Invalid hex color for {key}: {value}")
        for key in OPTIONAL_COLOR_KEYS:
            value = getattr(self, key, None)
            if value and not HEX_COLOR_RE.match(value):
                errors.append(f"Invalid hex color for {key}: {value}")
        return errors


@dataclass
class CustomTheme:
    """A custom or imported theme definition."""
    theme_id: str
    name: str
    description: str = ""
    source: str = "custom"
    colors: ThemeColors = field(default_factory=ThemeColors)
    author: str = ""
    version: str = "1.0"
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "CustomTheme":
        colors_data = data.pop("colors", {})
        if isinstance(colors_data, dict):
            colors = ThemeColors.from_dict(colors_data)
        else:
            colors = ThemeColors()
        return cls(colors=colors, **{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ProjectThemeBinding:
    """Associates a project with a specific theme."""
    project_id: str
    theme_id: str
    mode: str = "system"  # light, dark, system
    bound_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Theme Manager
# ---------------------------------------------------------------------------

class ThemeManager:
    """Manages custom themes, per-project bindings, and import/export.

    Extends the existing 7-theme system with custom theme creation,
    system dark/light mode detection, and per-project theme binding.

    Attributes:
        _custom_themes: In-memory store of custom themes.
        _project_bindings: Project → theme bindings.
        _global_mode: The global appearance mode.
    """

    def __init__(self) -> None:
        self._custom_themes: dict[str, CustomTheme] = {}
        self._project_bindings: dict[str, ProjectThemeBinding] = {}
        self._global_mode: str = "system"
        self._counter = 0
        logger.info("ThemeManager initialised")

    # -- Mode management ----------------------------------------------------

    def get_mode(self) -> str:
        """Get the current global appearance mode."""
        return self._global_mode

    def set_mode(self, mode: str) -> str:
        """Set the global appearance mode (light/dark/system).

        Returns:
            The resolved effective mode.
        """
        if mode not in ("light", "dark", "system"):
            raise ValueError(f"Invalid mode: {mode}. Must be light, dark, or system.")
        self._global_mode = mode
        return self.resolve_mode(mode)

    def resolve_mode(self, mode: str, system_prefers_dark: bool = False) -> str:
        """Resolve 'system' mode to concrete light/dark.

        Args:
            mode: The mode setting.
            system_prefers_dark: Whether the OS is in dark mode.

        Returns:
            Either 'light' or 'dark'.
        """
        if mode == "system":
            return "dark" if system_prefers_dark else "light"
        return mode

    # -- Built-in themes ----------------------------------------------------

    def list_builtin_themes(self) -> list[dict]:
        """Return all built-in themes."""
        return [dict(t) for t in BUILTIN_THEMES]

    def get_builtin_theme(self, theme_id: str) -> Optional[dict]:
        """Get a built-in theme by ID."""
        for t in BUILTIN_THEMES:
            if t["id"] == theme_id:
                return dict(t)
        return None

    # -- Custom themes ------------------------------------------------------

    def create_custom_theme(
        self,
        name: str,
        colors: Optional[dict] = None,
        description: str = "",
        author: str = "",
    ) -> CustomTheme:
        """Create a new custom theme.

        Args:
            name: Theme display name.
            colors: Color palette dict (bg, accent, darkBg, darkAccent, ...).
            description: Optional description.
            author: Optional author name.

        Returns:
            The created ``CustomTheme``.

        Raises:
            ValueError: If color values are invalid.
        """
        self._counter += 1
        theme_id = f"custom-{self._counter:04d}"
        now = datetime.now(timezone.utc).isoformat()

        theme_colors = ThemeColors()
        if colors:
            theme_colors = ThemeColors(**{
                k: v for k, v in colors.items()
                if k in ThemeColors.__dataclass_fields__
            })

        errors = theme_colors.validate()
        if errors:
            raise ValueError(f"Invalid theme colors: {'; '.join(errors)}")

        theme = CustomTheme(
            theme_id=theme_id,
            name=name,
            description=description,
            source="custom",
            colors=theme_colors,
            author=author,
            created_at=now,
            updated_at=now,
        )

        self._custom_themes[theme_id] = theme
        logger.info("Created custom theme %s: %s", theme_id, name)
        return theme

    def get_custom_theme(self, theme_id: str) -> Optional[CustomTheme]:
        """Get a custom theme by ID."""
        return self._custom_themes.get(theme_id)

    def update_custom_theme(
        self,
        theme_id: str,
        name: Optional[str] = None,
        colors: Optional[dict] = None,
        description: Optional[str] = None,
    ) -> Optional[CustomTheme]:
        """Update an existing custom theme.

        Returns:
            The updated theme, or None if not found.
        """
        theme = self._custom_themes.get(theme_id)
        if not theme:
            return None

        if name is not None:
            theme.name = name
        if description is not None:
            theme.description = description
        if colors is not None:
            new_colors = ThemeColors(**{
                k: v for k, v in colors.items()
                if k in ThemeColors.__dataclass_fields__
            })
            errors = new_colors.validate()
            if errors:
                raise ValueError(f"Invalid theme colors: {'; '.join(errors)}")
            theme.colors = new_colors

        theme.updated_at = datetime.now(timezone.utc).isoformat()
        return theme

    def delete_custom_theme(self, theme_id: str) -> bool:
        """Delete a custom theme. Returns True if deleted."""
        if theme_id in self._custom_themes:
            del self._custom_themes[theme_id]
            # Remove any project bindings using this theme
            to_remove = [
                pid for pid, binding in self._project_bindings.items()
                if binding.theme_id == theme_id
            ]
            for pid in to_remove:
                del self._project_bindings[pid]
            return True
        return False

    def list_custom_themes(self) -> list[CustomTheme]:
        """List all custom themes."""
        return list(self._custom_themes.values())

    def list_all_themes(self) -> list[dict]:
        """List all themes (built-in + custom)."""
        themes: list[dict] = []
        for bt in BUILTIN_THEMES:
            themes.append({**bt, "source": "builtin"})
        for ct in self._custom_themes.values():
            themes.append(ct.to_dict())
        return themes

    # -- Per-project themes -------------------------------------------------

    def set_project_theme(
        self,
        project_id: str,
        theme_id: str,
        mode: str = "system",
    ) -> ProjectThemeBinding:
        """Bind a theme to a specific project.

        Args:
            project_id: The project identifier.
            theme_id: The theme to assign (builtin or custom ID).
            mode: Appearance mode for this project.

        Returns:
            The created ``ProjectThemeBinding``.
        """
        # Validate theme exists
        valid = (
            self.get_builtin_theme(theme_id) is not None
            or self.get_custom_theme(theme_id) is not None
        )
        if not valid:
            raise ValueError(f"Theme '{theme_id}' not found")

        binding = ProjectThemeBinding(
            project_id=project_id,
            theme_id=theme_id,
            mode=mode,
            bound_at=datetime.now(timezone.utc).isoformat(),
        )
        self._project_bindings[project_id] = binding
        logger.info("Bound theme %s to project %s", theme_id, project_id)
        return binding

    def get_project_theme(self, project_id: str) -> Optional[ProjectThemeBinding]:
        """Get the theme binding for a project."""
        return self._project_bindings.get(project_id)

    def remove_project_theme(self, project_id: str) -> bool:
        """Remove a project's theme binding (revert to global)."""
        if project_id in self._project_bindings:
            del self._project_bindings[project_id]
            return True
        return False

    def list_project_bindings(self) -> list[ProjectThemeBinding]:
        """List all project-theme bindings."""
        return list(self._project_bindings.values())

    # -- Import / Export ----------------------------------------------------

    def export_theme(self, theme_id: str) -> Optional[str]:
        """Export a theme (custom or builtin) as JSON string.

        Returns:
            JSON string, or None if theme not found.
        """
        # Check custom first
        custom = self.get_custom_theme(theme_id)
        if custom:
            export_data = custom.to_dict()
            export_data["_export_version"] = "1.0"
            export_data["_exported_at"] = datetime.now(timezone.utc).isoformat()
            return json.dumps(export_data, indent=2)

        # Check builtin
        builtin = self.get_builtin_theme(theme_id)
        if builtin:
            export_data = dict(builtin)
            export_data["_export_version"] = "1.0"
            export_data["_exported_at"] = datetime.now(timezone.utc).isoformat()
            return json.dumps(export_data, indent=2)

        return None

    def import_theme(self, data: str) -> CustomTheme:
        """Import a theme from JSON string.

        Args:
            data: JSON string with theme data.

        Returns:
            The imported ``CustomTheme``.

        Raises:
            ValueError: If the data is invalid.
        """
        try:
            theme_data = json.loads(data)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON: {exc}") from exc

        # Extract colors
        colors_data = theme_data.get("colors", {})
        name = theme_data.get("name", "Imported Theme")
        description = theme_data.get("description", "")
        author = theme_data.get("author", "")

        self._counter += 1
        theme_id = f"imported-{self._counter:04d}"
        now = datetime.now(timezone.utc).isoformat()

        theme_colors = ThemeColors.from_dict(colors_data) if isinstance(colors_data, dict) else ThemeColors()
        errors = theme_colors.validate()
        if errors:
            raise ValueError(f"Invalid theme colors: {'; '.join(errors)}")

        theme = CustomTheme(
            theme_id=theme_id,
            name=name,
            description=description,
            source="imported",
            colors=theme_colors,
            author=author,
            created_at=now,
            updated_at=now,
        )
        self._custom_themes[theme_id] = theme
        logger.info("Imported theme %s: %s", theme_id, name)
        return theme

    # -- CSS generation -----------------------------------------------------

    def generate_css_variables(self, theme_id: str, mode: str = "light") -> Optional[str]:
        """Generate CSS custom properties for a theme.

        Args:
            theme_id: Theme identifier.
            mode: 'light' or 'dark'.

        Returns:
            CSS string with custom properties, or None.
        """
        colors = None

        custom = self.get_custom_theme(theme_id)
        if custom:
            colors = custom.colors.to_dict()
        else:
            builtin = self.get_builtin_theme(theme_id)
            if builtin:
                colors = builtin["colors"]

        if not colors:
            return None

        is_dark = mode == "dark"

        css_vars = {
            "--theme-bg": colors.get("darkBg" if is_dark else "bg", "#ffffff"),
            "--theme-accent": colors.get("darkAccent" if is_dark else "accent", "#3b82f6"),
            "--theme-foreground": colors.get("darkForeground" if is_dark else "foreground", "#1a1a1a"),
            "--theme-muted": colors.get("darkMuted" if is_dark else "muted", "#6b7280"),
            "--theme-border": colors.get("darkBorder" if is_dark else "border", "#e5e7eb"),
        }

        lines = [":root {"]
        for var_name, value in css_vars.items():
            lines.append(f"  {var_name}: {value};")
        lines.append("}")

        return "\n".join(lines)

    # -- Statistics ---------------------------------------------------------

    def get_stats(self) -> dict:
        """Get theme manager statistics."""
        return {
            "builtin_themes": len(BUILTIN_THEMES),
            "custom_themes": len(self._custom_themes),
            "total_themes": len(BUILTIN_THEMES) + len(self._custom_themes),
            "project_bindings": len(self._project_bindings),
            "global_mode": self._global_mode,
        }
