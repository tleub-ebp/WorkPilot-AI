"""Task Templates System — Reusable templates for task creation.

Provides a library of predefined and custom task templates with variable
substitution, YAML import/export, and cross-project sharing.

Feature 3.2 — Système de templates de tâches.

Example:
    >>> from apps.backend.scheduling.task_templates import TaskTemplateManager
    >>> manager = TaskTemplateManager()
    >>> manager.load_builtin_templates()
    >>> tpl = manager.get_template("feature")
    >>> task = tpl.render(component="LoginPage", endpoint="/api/auth/login")
    >>> print(task["title"])
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# YAML is optional — graceful degradation if not installed
try:
    import yaml  # type: ignore[import-untyped]

    HAS_YAML = True
except ImportError:
    HAS_YAML = False


class TemplateCategory(Enum):
    """Categories of task templates."""

    FEATURE = "feature"
    BUGFIX = "bugfix"
    REFACTORING = "refactoring"
    MIGRATION = "migration"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    SECURITY = "security"
    PERFORMANCE = "performance"
    CUSTOM = "custom"


@dataclass
class TemplateVariable:
    """A variable placeholder in a template.

    Attributes:
        name: The variable name (used as ``{{name}}`` in templates).
        description: A human-readable description of the variable.
        default: Default value if not provided during rendering.
        required: Whether this variable must be provided.
    """

    name: str
    description: str = ""
    default: str = ""
    required: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "default": self.default,
            "required": self.required,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TemplateVariable":
        """Create from a dictionary."""
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            default=data.get("default", ""),
            required=data.get("required", False),
        )


@dataclass
class TaskTemplate:
    """A reusable task template with variable substitution.

    Attributes:
        id: Unique template identifier.
        name: The template display name.
        category: The template category.
        description: A description of what this template creates.
        title_template: Title with ``{{variable}}`` placeholders.
        body_template: Body/description with ``{{variable}}`` placeholders.
        variables: List of template variables.
        tags: Tags for organization and search.
        priority: Default task priority (1-10).
        estimated_complexity: Estimated complexity ('low', 'medium', 'high').
        checklist: List of checklist items for the generated task.
        author: Template author.
        created_at: When the template was created.
        is_builtin: Whether this is a builtin (non-deletable) template.
    """

    id: str
    name: str
    category: TemplateCategory
    description: str = ""
    title_template: str = ""
    body_template: str = ""
    variables: list[TemplateVariable] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    priority: int = 5
    estimated_complexity: str = "medium"
    checklist: list[str] = field(default_factory=list)
    author: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_builtin: bool = False

    def render(self, **kwargs: str) -> dict[str, Any]:
        """Render the template with variable substitution.

        Args:
            **kwargs: Variable values keyed by variable name.

        Returns:
            A dict with ``'title'``, ``'body'``, ``'tags'``, ``'priority'``,
            ``'checklist'``, ``'category'``, ``'metadata'``.

        Raises:
            ValueError: If a required variable is missing.
        """
        # Build the substitution map
        sub_map: dict[str, str] = {}
        for var in self.variables:
            value = kwargs.get(var.name, var.default)
            if var.required and not value:
                raise ValueError(
                    f"Required variable '{var.name}' not provided for template '{self.name}'."
                )
            sub_map[var.name] = value

        title = self._substitute(self.title_template, sub_map)
        body = self._substitute(self.body_template, sub_map)
        checklist = [self._substitute(item, sub_map) for item in self.checklist]

        return {
            "title": title,
            "body": body,
            "tags": list(self.tags),
            "priority": self.priority,
            "checklist": checklist,
            "category": self.category.value,
            "template_id": self.id,
            "metadata": {
                "template_name": self.name,
                "estimated_complexity": self.estimated_complexity,
                "variables_used": sub_map,
            },
        }

    @staticmethod
    def _substitute(text: str, sub_map: dict[str, str]) -> str:
        """Replace ``{{variable}}`` placeholders in text.

        Args:
            text: The template text.
            sub_map: Variable name → value mapping.

        Returns:
            The substituted text.
        """
        for key, value in sub_map.items():
            text = text.replace(f"{{{{{key}}}}}", value)
        return text

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary (YAML-friendly)."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "title_template": self.title_template,
            "body_template": self.body_template,
            "variables": [v.to_dict() for v in self.variables],
            "tags": self.tags,
            "priority": self.priority,
            "estimated_complexity": self.estimated_complexity,
            "checklist": self.checklist,
            "author": self.author,
            "created_at": self.created_at.isoformat(),
            "is_builtin": self.is_builtin,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskTemplate":
        """Create from a dictionary (e.g., parsed from YAML).

        Args:
            data: Template data dictionary.

        Returns:
            A TaskTemplate instance.
        """
        category_str = data.get("category", "custom")
        try:
            category = TemplateCategory(category_str)
        except ValueError:
            category = TemplateCategory.CUSTOM

        variables = [TemplateVariable.from_dict(v) for v in data.get("variables", [])]

        created_at_str = data.get("created_at")
        created_at = datetime.now(timezone.utc)
        if created_at_str:
            try:
                created_at = datetime.fromisoformat(str(created_at_str))
            except (ValueError, TypeError):
                pass

        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            category=category,
            description=data.get("description", ""),
            title_template=data.get("title_template", ""),
            body_template=data.get("body_template", ""),
            variables=variables,
            tags=data.get("tags", []),
            priority=data.get("priority", 5),
            estimated_complexity=data.get("estimated_complexity", "medium"),
            checklist=data.get("checklist", []),
            author=data.get("author", ""),
            created_at=created_at,
            is_builtin=data.get("is_builtin", False),
        )


# -----------------------------------------------------------------------
# Builtin templates
# -----------------------------------------------------------------------

BUILTIN_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "feature",
        "name": "New Feature",
        "category": "feature",
        "description": "Template for implementing a new feature with component, endpoint, and tests.",
        "title_template": "Implement {{component}} — {{feature_name}}",
        "body_template": (
            "## Feature: {{feature_name}}\n\n"
            "### Description\n{{description}}\n\n"
            "### Component\n`{{component}}`\n\n"
            "### Endpoint\n`{{endpoint}}`\n\n"
            "### Acceptance Criteria\n"
            "- [ ] {{component}} component is created and functional\n"
            "- [ ] Endpoint {{endpoint}} returns expected data\n"
            "- [ ] Unit tests cover happy path and edge cases\n"
            "- [ ] Code review approved\n"
        ),
        "variables": [
            {"name": "component", "description": "Component name", "required": True},
            {"name": "feature_name", "description": "Feature name", "required": True},
            {"name": "endpoint", "description": "API endpoint", "default": "/api/v1/"},
            {
                "name": "description",
                "description": "Feature description",
                "default": "",
            },
        ],
        "tags": ["feature", "implementation"],
        "priority": 5,
        "estimated_complexity": "medium",
        "checklist": [
            "Create {{component}} component",
            "Implement {{endpoint}} endpoint",
            "Write unit tests",
            "Write integration tests",
            "Update documentation",
        ],
        "is_builtin": True,
    },
    {
        "id": "bugfix",
        "name": "Bug Fix",
        "category": "bugfix",
        "description": "Template for fixing a bug with reproduction steps and regression tests.",
        "title_template": "Fix: {{bug_title}}",
        "body_template": (
            "## Bug Fix: {{bug_title}}\n\n"
            "### Reproduction Steps\n{{reproduction_steps}}\n\n"
            "### Expected Behavior\n{{expected_behavior}}\n\n"
            "### Actual Behavior\n{{actual_behavior}}\n\n"
            "### Affected Component\n`{{component}}`\n\n"
            "### Fix Strategy\n"
            "1. Identify root cause in `{{component}}`\n"
            "2. Implement minimal fix\n"
            "3. Add regression test\n"
        ),
        "variables": [
            {
                "name": "bug_title",
                "description": "Short bug description",
                "required": True,
            },
            {
                "name": "component",
                "description": "Affected component",
                "required": True,
            },
            {
                "name": "reproduction_steps",
                "description": "Steps to reproduce",
                "default": "TBD",
            },
            {
                "name": "expected_behavior",
                "description": "Expected behavior",
                "default": "TBD",
            },
            {
                "name": "actual_behavior",
                "description": "Actual behavior",
                "default": "TBD",
            },
        ],
        "tags": ["bugfix", "fix"],
        "priority": 3,
        "estimated_complexity": "medium",
        "checklist": [
            "Reproduce the bug",
            "Identify root cause",
            "Implement fix in {{component}}",
            "Add regression test",
            "Verify fix does not introduce new issues",
        ],
        "is_builtin": True,
    },
    {
        "id": "refactoring",
        "name": "Code Refactoring",
        "category": "refactoring",
        "description": "Template for refactoring code with before/after patterns.",
        "title_template": "Refactor: {{target}} — {{refactoring_type}}",
        "body_template": (
            "## Refactoring: {{target}}\n\n"
            "### Type\n{{refactoring_type}}\n\n"
            "### Motivation\n{{motivation}}\n\n"
            "### Scope\n`{{target}}`\n\n"
            "### Constraints\n"
            "- No behavior changes\n"
            "- All existing tests must pass\n"
            "- Maintain backward compatibility\n"
        ),
        "variables": [
            {
                "name": "target",
                "description": "Target module/class/function",
                "required": True,
            },
            {
                "name": "refactoring_type",
                "description": "Type (Extract Method, Split Class, etc.)",
                "default": "General cleanup",
            },
            {
                "name": "motivation",
                "description": "Why this refactoring",
                "default": "Improve code quality and maintainability",
            },
        ],
        "tags": ["refactoring", "cleanup"],
        "priority": 6,
        "estimated_complexity": "medium",
        "checklist": [
            "Run existing tests (baseline)",
            "Refactor {{target}}",
            "Verify all tests still pass",
            "Check for performance regression",
            "Update documentation if needed",
        ],
        "is_builtin": True,
    },
    {
        "id": "migration",
        "name": "Migration",
        "category": "migration",
        "description": "Template for framework/library migration tasks.",
        "title_template": "Migrate: {{source}} → {{target}}",
        "body_template": (
            "## Migration: {{source}} → {{target}}\n\n"
            "### Context\n{{context}}\n\n"
            "### Migration Steps\n"
            "1. Update dependencies ({{source}} → {{target}})\n"
            "2. Migrate API calls and imports\n"
            "3. Update configuration files\n"
            "4. Fix breaking changes\n"
            "5. Update tests\n\n"
            "### Rollback Plan\n"
            "Revert the dependency change and restore original files.\n"
        ),
        "variables": [
            {
                "name": "source",
                "description": "Source framework/version",
                "required": True,
            },
            {
                "name": "target",
                "description": "Target framework/version",
                "required": True,
            },
            {"name": "context", "description": "Migration context", "default": ""},
        ],
        "tags": ["migration", "upgrade"],
        "priority": 4,
        "estimated_complexity": "high",
        "checklist": [
            "Backup current state",
            "Update dependencies",
            "Migrate code from {{source}} to {{target}}",
            "Fix breaking changes",
            "Run full test suite",
            "Performance benchmark",
        ],
        "is_builtin": True,
    },
    {
        "id": "testing",
        "name": "Add Tests",
        "category": "testing",
        "description": "Template for adding test coverage to a module.",
        "title_template": "Add tests for {{module}}",
        "body_template": (
            "## Test Coverage: {{module}}\n\n"
            "### Target\n`{{module}}`\n\n"
            "### Test Types\n"
            "- Unit tests for all public functions\n"
            "- Edge case coverage\n"
            "- Error handling tests\n"
            "{{additional_notes}}\n"
        ),
        "variables": [
            {"name": "module", "description": "Module/file to test", "required": True},
            {
                "name": "additional_notes",
                "description": "Additional test notes",
                "default": "",
            },
        ],
        "tags": ["testing", "coverage"],
        "priority": 5,
        "estimated_complexity": "medium",
        "checklist": [
            "Analyze {{module}} for testable functions",
            "Write happy path tests",
            "Write edge case tests",
            "Write error handling tests",
            "Verify coverage > 80%",
        ],
        "is_builtin": True,
    },
    {
        "id": "security",
        "name": "Security Fix",
        "category": "security",
        "description": "Template for addressing security vulnerabilities.",
        "title_template": "Security: Fix {{vulnerability}} in {{component}}",
        "body_template": (
            "## Security Fix: {{vulnerability}}\n\n"
            "### Severity\n{{severity}}\n\n"
            "### Affected Component\n`{{component}}`\n\n"
            "### Description\n{{description}}\n\n"
            "### Remediation\n{{remediation}}\n\n"
            "### Verification\n"
            "- [ ] Vulnerability is no longer exploitable\n"
            "- [ ] No new vulnerabilities introduced\n"
            "- [ ] Security scan passes\n"
        ),
        "variables": [
            {
                "name": "vulnerability",
                "description": "Vulnerability name/CVE",
                "required": True,
            },
            {
                "name": "component",
                "description": "Affected component",
                "required": True,
            },
            {"name": "severity", "description": "Severity level", "default": "high"},
            {
                "name": "description",
                "description": "Vulnerability description",
                "default": "",
            },
            {"name": "remediation", "description": "Suggested fix", "default": ""},
        ],
        "tags": ["security", "vulnerability"],
        "priority": 1,
        "estimated_complexity": "high",
        "checklist": [
            "Reproduce/confirm vulnerability",
            "Implement fix in {{component}}",
            "Run security scan",
            "Add regression test",
            "Update security documentation",
        ],
        "is_builtin": True,
    },
]


class TaskTemplateManager:
    """Manager for task templates — CRUD, import/export, variable substitution.

    Attributes:
        _templates: Dictionary of templates keyed by ID.
        _project_dir: Optional project directory for custom templates.
    """

    TEMPLATES_DIR = ".auto-claude/templates"

    def __init__(self, project_dir: str | None = None) -> None:
        """Initialize the template manager.

        Args:
            project_dir: Optional project root for loading/saving custom templates.
        """
        self._templates: dict[str, TaskTemplate] = {}
        self._project_dir = project_dir

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_builtin_templates(self) -> int:
        """Load all builtin templates into the manager.

        Returns:
            The number of templates loaded.
        """
        count = 0
        for tpl_data in BUILTIN_TEMPLATES:
            tpl = TaskTemplate.from_dict(tpl_data)
            self._templates[tpl.id] = tpl
            count += 1
        return count

    def load_from_directory(self, directory: str | None = None) -> int:
        """Load custom templates from a directory of YAML files.

        Args:
            directory: Path to the templates directory. Defaults to
                ``{project_dir}/.auto-claude/templates/``.

        Returns:
            The number of templates loaded.

        Raises:
            RuntimeError: If YAML library is not available.
        """
        if not HAS_YAML:
            raise RuntimeError(
                "PyYAML is required for YAML template loading. "
                "Install with: pip install pyyaml"
            )

        if directory is None:
            if self._project_dir:
                directory = os.path.join(self._project_dir, self.TEMPLATES_DIR)
            else:
                return 0

        if not os.path.isdir(directory):
            return 0

        count = 0
        for filename in os.listdir(directory):
            if filename.endswith((".yaml", ".yml")):
                filepath = os.path.join(directory, filename)
                try:
                    with open(filepath, encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                    if data and isinstance(data, dict):
                        tpl = TaskTemplate.from_dict(data)
                        if not tpl.id:
                            tpl.id = os.path.splitext(filename)[0]
                        self._templates[tpl.id] = tpl
                        count += 1
                except Exception as exc:
                    logger.warning(f"Failed to load template from {filepath}: {exc}")

        return count

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add_template(self, template: TaskTemplate) -> None:
        """Add or update a template.

        Args:
            template: The template to add.
        """
        self._templates[template.id] = template

    def get_template(self, template_id: str) -> TaskTemplate | None:
        """Get a template by ID.

        Args:
            template_id: The template ID.

        Returns:
            The TaskTemplate or None.
        """
        return self._templates.get(template_id)

    def remove_template(self, template_id: str) -> bool:
        """Remove a template by ID.

        Args:
            template_id: The template ID.

        Returns:
            True if removed, False if not found or is builtin.
        """
        tpl = self._templates.get(template_id)
        if not tpl:
            return False
        if tpl.is_builtin:
            return False
        del self._templates[template_id]
        return True

    def list_templates(
        self, category: TemplateCategory | None = None
    ) -> list[TaskTemplate]:
        """List all templates, optionally filtered by category.

        Args:
            category: Filter by category, or None for all.

        Returns:
            A list of TaskTemplate objects.
        """
        templates = list(self._templates.values())
        if category:
            templates = [t for t in templates if t.category == category]
        return sorted(templates, key=lambda t: t.name)

    def search_templates(self, query: str) -> list[TaskTemplate]:
        """Search templates by name, description, or tags.

        Args:
            query: The search query (case-insensitive).

        Returns:
            A list of matching templates.
        """
        query_lower = query.lower()
        results = []
        for tpl in self._templates.values():
            if (
                query_lower in tpl.name.lower()
                or query_lower in tpl.description.lower()
                or any(query_lower in tag.lower() for tag in tpl.tags)
            ):
                results.append(tpl)
        return sorted(results, key=lambda t: t.name)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render_template(self, template_id: str, **kwargs: str) -> dict[str, Any]:
        """Render a template by ID with variable substitution.

        Args:
            template_id: The template ID.
            **kwargs: Variable values.

        Returns:
            The rendered task dict.

        Raises:
            ValueError: If the template is not found or a required variable is missing.
        """
        tpl = self.get_template(template_id)
        if not tpl:
            raise ValueError(f"Template '{template_id}' not found.")
        return tpl.render(**kwargs)

    # ------------------------------------------------------------------
    # Import / Export (YAML)
    # ------------------------------------------------------------------

    def export_template(self, template_id: str) -> str:
        """Export a template as a YAML string.

        Args:
            template_id: The template ID.

        Returns:
            A YAML-formatted string.

        Raises:
            ValueError: If the template is not found.
            RuntimeError: If YAML library is not available.
        """
        if not HAS_YAML:
            raise RuntimeError("PyYAML is required for YAML export.")

        tpl = self.get_template(template_id)
        if not tpl:
            raise ValueError(f"Template '{template_id}' not found.")
        return yaml.dump(tpl.to_dict(), default_flow_style=False, allow_unicode=True)

    def import_template(self, yaml_string: str) -> TaskTemplate:
        """Import a template from a YAML string.

        Args:
            yaml_string: The YAML content.

        Returns:
            The imported TaskTemplate.

        Raises:
            RuntimeError: If YAML library is not available.
            ValueError: If the YAML is invalid.
        """
        if not HAS_YAML:
            raise RuntimeError("PyYAML is required for YAML import.")

        data = yaml.safe_load(yaml_string)
        if not isinstance(data, dict):
            raise ValueError("Invalid YAML: expected a mapping.")

        tpl = TaskTemplate.from_dict(data)
        self._templates[tpl.id] = tpl
        return tpl

    def save_template_to_file(
        self, template_id: str, directory: str | None = None
    ) -> str:
        """Save a template to a YAML file.

        Args:
            template_id: The template ID.
            directory: Target directory. Defaults to project templates dir.

        Returns:
            The path to the saved file.

        Raises:
            ValueError: If template not found.
            RuntimeError: If YAML library is not available.
        """
        if not HAS_YAML:
            raise RuntimeError("PyYAML is required for file export.")

        tpl = self.get_template(template_id)
        if not tpl:
            raise ValueError(f"Template '{template_id}' not found.")

        if directory is None:
            if self._project_dir:
                directory = os.path.join(self._project_dir, self.TEMPLATES_DIR)
            else:
                raise ValueError("No directory specified and no project_dir set.")

        os.makedirs(directory, exist_ok=True)
        filepath = os.path.join(directory, f"{template_id}.yaml")
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(tpl.to_dict(), f, default_flow_style=False, allow_unicode=True)

        return filepath

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Get template manager statistics.

        Returns:
            Dict with ``'total_templates'``, ``'builtin'``, ``'custom'``,
            ``'by_category'``.
        """
        by_category: dict[str, int] = {}
        builtin_count = 0
        custom_count = 0

        for tpl in self._templates.values():
            cat = tpl.category.value
            by_category[cat] = by_category.get(cat, 0) + 1
            if tpl.is_builtin:
                builtin_count += 1
            else:
                custom_count += 1

        return {
            "total_templates": len(self._templates),
            "builtin": builtin_count,
            "custom": custom_count,
            "by_category": by_category,
        }
