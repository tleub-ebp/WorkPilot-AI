"""
Spec Templates Library
======================

Manages built-in and user-defined spec templates.
Provides listing, lookup, creation, and persistence of custom templates.
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import SpecTemplate, TemplateCategory

# =============================================================================
# BUILT-IN TEMPLATES
# =============================================================================

_BUILTIN_TEMPLATES: list[SpecTemplate] = [
    # ── CRUD API ─────────────────────────────────────────────────────────────
    SpecTemplate(
        id="crud-api",
        name="CRUD REST API",
        category=TemplateCategory.CRUD,
        description="Full CRUD endpoint set for a resource (list, get, create, update, delete)",
        workflow_type="feature",
        task_description_template=(
            "Implement a complete CRUD REST API for the {resource} resource. "
            "Endpoints: GET /api/{resources} (list with pagination), "
            "GET /api/{resources}/{id}, POST /api/{resources}, "
            "PUT /api/{resources}/{id}, DELETE /api/{resources}/{id}. "
            "Include input validation, error handling, and OpenAPI documentation."
        ),
        additional_context=(
            "Follow existing API conventions in the project. "
            "Add appropriate authentication middleware if the project already has auth."
        ),
        suggested_keywords=[
            "router",
            "controller",
            "model",
            "schema",
            "validation",
            "endpoint",
        ],
        suggested_services=["backend", "api"],
        qa_criteria=[
            "All 5 CRUD endpoints return correct HTTP status codes",
            "Input validation rejects malformed payloads with 400 errors",
            "404 returned for non-existent resources",
            "Pagination works correctly on list endpoint",
            "Unit tests cover happy path and error cases for each endpoint",
        ],
    ),
    # ── AUTHENTICATION ────────────────────────────────────────────────────────
    SpecTemplate(
        id="jwt-authentication",
        name="JWT Authentication",
        category=TemplateCategory.AUTH,
        description="JWT-based login/register/refresh flow with secure token handling",
        workflow_type="feature",
        task_description_template=(
            "Implement JWT authentication: user registration with hashed passwords, "
            "login endpoint returning access + refresh tokens, "
            "token refresh endpoint, logout (token invalidation), "
            "and auth middleware to protect routes."
        ),
        additional_context=(
            "Use bcrypt or argon2 for password hashing. "
            "Store refresh tokens securely (DB or Redis). "
            "Access token expiry: 15 min. Refresh token expiry: 7 days."
        ),
        suggested_keywords=[
            "auth",
            "login",
            "token",
            "jwt",
            "password",
            "middleware",
            "session",
        ],
        suggested_services=["backend", "auth"],
        qa_criteria=[
            "Registration rejects duplicate emails with clear error",
            "Login returns valid JWT on correct credentials",
            "Invalid credentials return 401",
            "Protected routes reject requests without valid token",
            "Refresh token flow works and rotates tokens",
            "Passwords are never stored in plaintext",
        ],
    ),
    # ── DASHBOARD ─────────────────────────────────────────────────────────────
    SpecTemplate(
        id="analytics-dashboard",
        name="Analytics Dashboard",
        category=TemplateCategory.DASHBOARD,
        description="Data dashboard with charts, KPI cards, and date-range filters",
        workflow_type="feature",
        task_description_template=(
            "Build an analytics dashboard for {subject} showing: "
            "KPI summary cards (total, daily, weekly trends), "
            "time-series chart with date-range picker, "
            "breakdown table with sorting and export to CSV. "
            "Data should load asynchronously with skeleton loading states."
        ),
        additional_context=(
            "Use the existing charting library in the project. "
            "Implement server-side aggregation for large datasets. "
            "Cache aggregated results for 5 minutes."
        ),
        suggested_keywords=[
            "chart",
            "dashboard",
            "metrics",
            "analytics",
            "graph",
            "stats",
            "kpi",
        ],
        suggested_services=["frontend", "backend", "api"],
        qa_criteria=[
            "KPI cards display correct values matching the database",
            "Date-range filter updates all charts and tables",
            "CSV export downloads correct data",
            "Loading states shown while data fetches",
            "Charts are responsive on mobile viewport",
        ],
    ),
    # ── FORM ──────────────────────────────────────────────────────────────────
    SpecTemplate(
        id="form-with-validation",
        name="Form with Validation",
        category=TemplateCategory.FORM,
        description="Multi-field form with client-side and server-side validation",
        workflow_type="feature",
        task_description_template=(
            "Create a {form_name} form with fields: {fields}. "
            "Implement real-time client-side validation, "
            "server-side validation with field-level error messages, "
            "success/error feedback, and autosave draft functionality."
        ),
        additional_context=(
            "Use the existing form library/validation schema in the project. "
            "Ensure accessibility (ARIA labels, keyboard navigation, error announcements)."
        ),
        suggested_keywords=["form", "validation", "input", "submit", "error", "field"],
        suggested_services=["frontend"],
        qa_criteria=[
            "Required fields show inline error on blur",
            "Form cannot be submitted with invalid data",
            "Server validation errors displayed per field",
            "Successful submission shows confirmation and resets form",
            "Form is keyboard-navigable and screen-reader accessible",
        ],
    ),
    # ── DB MIGRATION ──────────────────────────────────────────────────────────
    SpecTemplate(
        id="db-migration",
        name="Database Migration",
        category=TemplateCategory.MIGRATION,
        description="Safe database schema migration with rollback support",
        workflow_type="feature",
        task_description_template=(
            "Create database migration to {migration_goal}. "
            "Include: forward migration, rollback migration, "
            "data migration if needed, and index updates. "
            "Ensure zero-downtime deployment compatibility."
        ),
        additional_context=(
            "Follow existing migration naming conventions. "
            "Test the migration on a copy of production data if possible. "
            "Document any manual steps required."
        ),
        suggested_keywords=[
            "migration",
            "schema",
            "database",
            "alter",
            "table",
            "index",
            "column",
        ],
        suggested_services=["backend", "database"],
        qa_criteria=[
            "Forward migration applies cleanly on empty and populated DB",
            "Rollback migration restores the original schema",
            "No data loss for existing records",
            "Migration runs within acceptable time on expected data volume",
            "Application functions correctly after migration",
        ],
    ),
    # ── REFACTORING ───────────────────────────────────────────────────────────
    SpecTemplate(
        id="code-refactoring",
        name="Code Refactoring",
        category=TemplateCategory.REFACTOR,
        description="Structured refactoring with test coverage and no regression",
        workflow_type="refactor",
        task_description_template=(
            "Refactor {target}: {refactoring_goal}. "
            "Preserve all existing behavior. "
            "Improve code structure, readability, and maintainability. "
            "Update or add tests to cover the refactored code."
        ),
        additional_context=(
            "Run existing tests before and after to confirm no regressions. "
            "Keep changes focused — avoid unrelated fixes in the same PR."
        ),
        suggested_keywords=[
            "refactor",
            "cleanup",
            "extract",
            "simplify",
            "rename",
            "reorganize",
        ],
        suggested_services=[],
        qa_criteria=[
            "All existing tests pass after refactoring",
            "No behavior change visible to end users",
            "Code coverage maintained or improved",
            "No new linting errors introduced",
        ],
    ),
    # ── THIRD-PARTY INTEGRATION ───────────────────────────────────────────────
    SpecTemplate(
        id="third-party-integration",
        name="Third-Party Integration",
        category=TemplateCategory.INTEGRATION,
        description="Integrate an external service/API with error handling and fallbacks",
        workflow_type="feature",
        task_description_template=(
            "Integrate {service_name} API ({service_purpose}). "
            "Implement: authentication/credential management, "
            "API client with retry logic, "
            "webhook handler if applicable, "
            "error handling and graceful degradation, "
            "and configuration via environment variables."
        ),
        additional_context=(
            "Store API credentials in environment variables, never hardcode. "
            "Implement circuit breaker or fallback for service outages. "
            "Add integration tests using mock/sandbox environment."
        ),
        suggested_keywords=[
            "integration",
            "api",
            "webhook",
            "client",
            "service",
            "external",
        ],
        suggested_services=["backend"],
        qa_criteria=[
            "Authentication with the external service works",
            "API errors are caught and handled gracefully",
            "Credentials are loaded from environment variables",
            "Integration tests pass using mock/sandbox mode",
            "Service unavailability does not crash the application",
        ],
    ),
    # ── REST API ENDPOINT ─────────────────────────────────────────────────────
    SpecTemplate(
        id="rest-endpoint",
        name="Single REST Endpoint",
        category=TemplateCategory.API,
        description="Single API endpoint with validation, auth, and tests",
        workflow_type="feature",
        task_description_template=(
            "Add {method} {path} endpoint that {description}. "
            "Include request validation, authentication check, "
            "proper error responses, and unit/integration tests."
        ),
        suggested_keywords=["endpoint", "route", "handler", "controller", "api"],
        suggested_services=["backend", "api"],
        qa_criteria=[
            "Endpoint returns correct response for valid input",
            "Unauthenticated requests return 401",
            "Invalid input returns 422/400 with field errors",
            "Unit test covers happy path and error cases",
        ],
    ),
    # ── TEST SUITE ────────────────────────────────────────────────────────────
    SpecTemplate(
        id="test-suite",
        name="Test Suite",
        category=TemplateCategory.TESTING,
        description="Comprehensive test coverage for an existing module",
        workflow_type="test",
        task_description_template=(
            "Add comprehensive test suite for {module}. "
            "Cover: unit tests for core logic, "
            "integration tests for external interactions, "
            "edge cases and error scenarios, "
            "and mocks for dependencies."
        ),
        suggested_keywords=[
            "test",
            "spec",
            "mock",
            "assert",
            "coverage",
            "unit",
            "integration",
        ],
        suggested_services=[],
        qa_criteria=[
            "Test coverage reaches at least 80% for the target module",
            "All happy paths are tested",
            "Error cases and edge cases are tested",
            "Tests are independent and can run in any order",
            "No flaky tests (run suite 3 times, all pass)",
        ],
    ),
]

# Index by ID for O(1) lookup
_BUILTIN_BY_ID: dict[str, SpecTemplate] = {t.id: t for t in _BUILTIN_TEMPLATES}


# =============================================================================
# TEMPLATE LIBRARY
# =============================================================================


class TemplateLibrary:
    """
    Manages built-in and user-defined spec templates.

    Custom templates are persisted in .auto-claude/spec_templates.json
    inside the project directory so teams can share templates via git.
    """

    CUSTOM_TEMPLATES_FILE = "spec_templates.json"

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)
        self._custom_templates: dict[str, SpecTemplate] = {}
        self._load_custom_templates()

    # ── Public API ─────────────────────────────────────────────────────────

    def list_templates(
        self,
        category: TemplateCategory | None = None,
        include_custom: bool = True,
    ) -> list[SpecTemplate]:
        """List all available templates, optionally filtered by category."""
        templates: list[SpecTemplate] = list(_BUILTIN_TEMPLATES)
        if include_custom:
            templates.extend(self._custom_templates.values())
        if category:
            templates = [t for t in templates if t.category == category]
        return templates

    def get_template(self, template_id: str) -> SpecTemplate | None:
        """Get a template by ID (builtin or custom)."""
        return _BUILTIN_BY_ID.get(template_id) or self._custom_templates.get(
            template_id
        )

    def save_custom_template(self, template: SpecTemplate) -> None:
        """Persist a custom template to the project's template store."""
        template.is_builtin = False
        self._custom_templates[template.id] = template
        self._save_custom_templates()

    def delete_custom_template(self, template_id: str) -> bool:
        """Delete a custom template. Returns True if deleted, False if not found."""
        if template_id in self._custom_templates:
            del self._custom_templates[template_id]
            self._save_custom_templates()
            return True
        return False

    def suggest_templates(self, task_description: str) -> list[SpecTemplate]:
        """
        Suggest relevant templates based on keyword matching in the task description.
        Returns up to 3 best matches.
        """
        task_lower = task_description.lower()
        scored: list[tuple[int, SpecTemplate]] = []

        for template in self.list_templates():
            score = 0
            # Match keywords
            for kw in template.suggested_keywords:
                if kw.lower() in task_lower:
                    score += 2
            # Match name/description words
            for word in (template.name + " " + template.description).lower().split():
                if len(word) > 3 and word in task_lower:
                    score += 1
            if score > 0:
                scored.append((score, template))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [t for _, t in scored[:3]]

    def apply_template(
        self,
        template_id: str,
        substitutions: dict[str, str] | None = None,
    ) -> dict | None:
        """
        Apply a template and return a requirements patch dict.

        Args:
            template_id: Template to apply
            substitutions: {placeholder: value} dict for template variables

        Returns:
            requirements patch dict, or None if template not found
        """
        template = self.get_template(template_id)
        if not template:
            return None
        applied = template.apply(substitutions or {})
        return applied.to_requirements_patch()

    # ── Persistence ────────────────────────────────────────────────────────

    def _custom_templates_path(self) -> Path:
        return self.project_dir / ".auto-claude" / self.CUSTOM_TEMPLATES_FILE

    def _load_custom_templates(self) -> None:
        path = self._custom_templates_path()
        if not path.exists():
            return
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            for entry in data:
                try:
                    t = SpecTemplate.from_dict(entry)
                    t.is_builtin = False
                    self._custom_templates[t.id] = t
                except (KeyError, ValueError):
                    pass
        except (OSError, json.JSONDecodeError):
            pass

    def _save_custom_templates(self) -> None:
        path = self._custom_templates_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [t.to_dict() for t in self._custom_templates.values()]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
