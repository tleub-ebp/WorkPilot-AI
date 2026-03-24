"""
Spec Template Data Models
=========================
"""

from dataclasses import dataclass, field
from enum import Enum


class TemplateCategory(str, Enum):
    """Template categories for organization."""

    CRUD = "crud"
    AUTH = "authentication"
    DASHBOARD = "dashboard"
    FORM = "form"
    MIGRATION = "db_migration"
    REFACTOR = "refactoring"
    INTEGRATION = "third_party_integration"
    API = "api"
    TESTING = "testing"
    CUSTOM = "custom"


@dataclass
class SpecTemplate:
    """
    A reusable spec template for common development patterns.

    Templates pre-fill requirements, impacted files hints, and QA criteria
    so recurring specs go from minutes to seconds.
    """

    # Identity
    id: str  # Unique slug (e.g. "crud-api", "jwt-auth")
    name: str  # Human-readable name
    category: TemplateCategory
    description: str  # One-line summary

    # Pre-filled content
    workflow_type: str = "feature"  # feature | bugfix | refactor | docs | test
    task_description_template: str = ""  # Template text with {placeholders}
    additional_context: str = ""

    # Hints for the spec pipeline
    suggested_keywords: list[str] = field(default_factory=list)
    suggested_services: list[str] = field(default_factory=list)

    # Pre-filled QA criteria (added to spec as acceptance criteria hints)
    qa_criteria: list[str] = field(default_factory=list)

    # Metadata
    is_builtin: bool = True
    author: str | None = None
    version: str = "1.0"

    def apply(self, substitutions: dict[str, str]) -> "AppliedTemplate":
        """
        Apply the template with context-specific substitutions.

        Args:
            substitutions: Mapping of {placeholder} → value

        Returns:
            AppliedTemplate with all placeholders resolved
        """
        task = self.task_description_template
        context = self.additional_context

        for key, value in substitutions.items():
            task = task.replace(f"{{{key}}}", value)
            context = context.replace(f"{{{key}}}", value)

        return AppliedTemplate(
            template_id=self.id,
            template_name=self.name,
            task_description=task,
            workflow_type=self.workflow_type,
            additional_context=context if context.strip() else None,
            suggested_keywords=list(self.suggested_keywords),
            suggested_services=list(self.suggested_services),
            qa_criteria=list(self.qa_criteria),
        )

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "workflow_type": self.workflow_type,
            "task_description_template": self.task_description_template,
            "additional_context": self.additional_context,
            "suggested_keywords": self.suggested_keywords,
            "suggested_services": self.suggested_services,
            "qa_criteria": self.qa_criteria,
            "is_builtin": self.is_builtin,
            "author": self.author,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SpecTemplate":
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            category=TemplateCategory(data.get("category", "custom")),
            description=data.get("description", ""),
            workflow_type=data.get("workflow_type", "feature"),
            task_description_template=data.get("task_description_template", ""),
            additional_context=data.get("additional_context", ""),
            suggested_keywords=data.get("suggested_keywords", []),
            suggested_services=data.get("suggested_services", []),
            qa_criteria=data.get("qa_criteria", []),
            is_builtin=data.get("is_builtin", False),
            author=data.get("author"),
            version=data.get("version", "1.0"),
        )


@dataclass
class AppliedTemplate:
    """Result of applying a template — ready to inject into requirements."""

    template_id: str
    template_name: str
    task_description: str
    workflow_type: str
    additional_context: str | None
    suggested_keywords: list[str]
    suggested_services: list[str]
    qa_criteria: list[str]

    def to_requirements_patch(self) -> dict:
        """
        Return a dict that can be merged into a requirements.json payload.
        Fields are only included if non-empty so they don't overwrite user input.
        """
        patch: dict = {
            "template_id": self.template_id,
            "template_name": self.template_name,
            "workflow_type": self.workflow_type,
        }
        if self.task_description:
            patch["task_description"] = self.task_description
        if self.additional_context:
            patch["additional_context"] = self.additional_context
        if self.suggested_keywords:
            patch["template_keywords"] = self.suggested_keywords
        if self.suggested_services:
            patch["services_involved"] = self.suggested_services
        if self.qa_criteria:
            patch["qa_criteria_hints"] = self.qa_criteria
        return patch
