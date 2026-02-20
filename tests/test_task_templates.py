"""Tests for Feature 3.2 — Système de templates de tâches.

Tests for TaskTemplateManager, TaskTemplate, TemplateVariable,
TemplateCategory, builtin templates, rendering, and YAML import/export.

40 tests total:
- TemplateVariable: 3
- TaskTemplate: 8
- TemplateCategory: 1
- TaskTemplateManager loading: 3
- TaskTemplateManager CRUD: 6
- TaskTemplateManager search: 3
- TaskTemplateManager rendering: 5
- TaskTemplateManager import/export: 5
- TaskTemplateManager stats: 2
- Builtin templates validation: 4
"""

import sys
import os
import tempfile
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.scheduling.task_templates import (
    BUILTIN_TEMPLATES,
    TaskTemplate,
    TaskTemplateManager,
    TemplateCategory,
    TemplateVariable,
)


# -----------------------------------------------------------------------
# TemplateVariable
# -----------------------------------------------------------------------

class TestTemplateVariable:
    def test_create_variable(self):
        var = TemplateVariable(name="component", description="Component name", required=True)
        assert var.name == "component"
        assert var.required is True

    def test_variable_to_dict(self):
        var = TemplateVariable(name="x", description="desc", default="val")
        d = var.to_dict()
        assert d["name"] == "x"
        assert d["default"] == "val"

    def test_variable_from_dict(self):
        data = {"name": "endpoint", "description": "API endpoint", "required": False, "default": "/api/"}
        var = TemplateVariable.from_dict(data)
        assert var.name == "endpoint"
        assert var.default == "/api/"


# -----------------------------------------------------------------------
# TaskTemplate
# -----------------------------------------------------------------------

class TestTaskTemplate:
    def test_create_template(self):
        tpl = TaskTemplate(
            id="test-tpl", name="Test Template",
            category=TemplateCategory.FEATURE,
            title_template="Implement {{component}}",
        )
        assert tpl.id == "test-tpl"
        assert tpl.category == TemplateCategory.FEATURE

    def test_render_template(self):
        tpl = TaskTemplate(
            id="t1", name="T1", category=TemplateCategory.FEATURE,
            title_template="Build {{component}} for {{project}}",
            body_template="Create the {{component}} component.",
            variables=[
                TemplateVariable(name="component", required=True),
                TemplateVariable(name="project", default="MyApp"),
            ],
        )
        result = tpl.render(component="LoginPage")
        assert result["title"] == "Build LoginPage for MyApp"
        assert "LoginPage" in result["body"]

    def test_render_with_checklist(self):
        tpl = TaskTemplate(
            id="t1", name="T1", category=TemplateCategory.FEATURE,
            title_template="Build {{component}}",
            checklist=["Create {{component}}", "Test {{component}}"],
            variables=[TemplateVariable(name="component", required=True)],
        )
        result = tpl.render(component="UserProfile")
        assert "Create UserProfile" in result["checklist"]
        assert "Test UserProfile" in result["checklist"]

    def test_render_missing_required_variable_raises(self):
        tpl = TaskTemplate(
            id="t1", name="T1", category=TemplateCategory.FEATURE,
            title_template="Build {{component}}",
            variables=[TemplateVariable(name="component", required=True)],
        )
        with pytest.raises(ValueError, match="Required variable"):
            tpl.render()

    def test_render_returns_metadata(self):
        tpl = TaskTemplate(
            id="t1", name="T1", category=TemplateCategory.FEATURE,
            title_template="{{x}}", estimated_complexity="high",
            variables=[TemplateVariable(name="x", default="val")],
        )
        result = tpl.render()
        assert result["metadata"]["template_name"] == "T1"
        assert result["metadata"]["estimated_complexity"] == "high"
        assert result["template_id"] == "t1"

    def test_template_to_dict(self):
        tpl = TaskTemplate(
            id="t1", name="T1", category=TemplateCategory.BUGFIX,
            tags=["bug"], priority=2,
        )
        d = tpl.to_dict()
        assert d["id"] == "t1"
        assert d["category"] == "bugfix"
        assert d["priority"] == 2

    def test_template_from_dict(self):
        data = {
            "id": "t2", "name": "T2", "category": "refactoring",
            "title_template": "Refactor {{target}}",
            "variables": [{"name": "target", "required": True}],
            "tags": ["refactor"],
        }
        tpl = TaskTemplate.from_dict(data)
        assert tpl.id == "t2"
        assert tpl.category == TemplateCategory.REFACTORING
        assert len(tpl.variables) == 1

    def test_template_from_dict_unknown_category(self):
        data = {"id": "t3", "name": "T3", "category": "not_a_real_category"}
        tpl = TaskTemplate.from_dict(data)
        assert tpl.category == TemplateCategory.CUSTOM


# -----------------------------------------------------------------------
# TemplateCategory
# -----------------------------------------------------------------------

class TestTemplateCategory:
    def test_all_categories_exist(self):
        expected = ["feature", "bugfix", "refactoring", "migration",
                     "documentation", "testing", "security", "performance", "custom"]
        for cat in expected:
            assert TemplateCategory(cat) is not None


# -----------------------------------------------------------------------
# TaskTemplateManager — Loading
# -----------------------------------------------------------------------

class TestManagerLoading:
    def test_load_builtin_templates(self):
        manager = TaskTemplateManager()
        count = manager.load_builtin_templates()
        assert count == len(BUILTIN_TEMPLATES)
        assert count > 0

    def test_load_from_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskTemplateManager(project_dir=tmpdir)
            count = manager.load_from_directory(tmpdir)
            assert count == 0

    def test_load_from_nonexistent_directory(self):
        manager = TaskTemplateManager()
        count = manager.load_from_directory("/nonexistent/path")
        assert count == 0


# -----------------------------------------------------------------------
# TaskTemplateManager — CRUD
# -----------------------------------------------------------------------

class TestManagerCRUD:
    def test_add_template(self):
        manager = TaskTemplateManager()
        tpl = TaskTemplate(id="custom-1", name="Custom", category=TemplateCategory.CUSTOM)
        manager.add_template(tpl)
        assert manager.get_template("custom-1") is not None

    def test_get_template_not_found(self):
        manager = TaskTemplateManager()
        assert manager.get_template("nonexistent") is None

    def test_remove_template(self):
        manager = TaskTemplateManager()
        tpl = TaskTemplate(id="rm-1", name="Remove Me", category=TemplateCategory.CUSTOM)
        manager.add_template(tpl)
        assert manager.remove_template("rm-1") is True
        assert manager.get_template("rm-1") is None

    def test_remove_builtin_fails(self):
        manager = TaskTemplateManager()
        manager.load_builtin_templates()
        assert manager.remove_template("feature") is False

    def test_remove_nonexistent_fails(self):
        manager = TaskTemplateManager()
        assert manager.remove_template("nope") is False

    def test_list_templates(self):
        manager = TaskTemplateManager()
        manager.load_builtin_templates()
        templates = manager.list_templates()
        assert len(templates) == len(BUILTIN_TEMPLATES)


# -----------------------------------------------------------------------
# TaskTemplateManager — Search
# -----------------------------------------------------------------------

class TestManagerSearch:
    def test_search_by_name(self):
        manager = TaskTemplateManager()
        manager.load_builtin_templates()
        results = manager.search_templates("bug")
        assert any("Bug" in t.name for t in results)

    def test_search_by_tag(self):
        manager = TaskTemplateManager()
        manager.load_builtin_templates()
        results = manager.search_templates("security")
        assert len(results) > 0

    def test_search_no_results(self):
        manager = TaskTemplateManager()
        manager.load_builtin_templates()
        results = manager.search_templates("xyznonexistent")
        assert len(results) == 0


# -----------------------------------------------------------------------
# TaskTemplateManager — Rendering
# -----------------------------------------------------------------------

class TestManagerRendering:
    def test_render_feature_template(self):
        manager = TaskTemplateManager()
        manager.load_builtin_templates()
        result = manager.render_template(
            "feature", component="UserProfile", feature_name="User settings page"
        )
        assert "UserProfile" in result["title"]
        assert "User settings page" in result["title"]

    def test_render_bugfix_template(self):
        manager = TaskTemplateManager()
        manager.load_builtin_templates()
        result = manager.render_template(
            "bugfix", bug_title="Login fails on Safari", component="AuthService"
        )
        assert "Login fails on Safari" in result["title"]

    def test_render_nonexistent_raises(self):
        manager = TaskTemplateManager()
        with pytest.raises(ValueError, match="not found"):
            manager.render_template("nonexistent")

    def test_list_by_category(self):
        manager = TaskTemplateManager()
        manager.load_builtin_templates()
        features = manager.list_templates(category=TemplateCategory.FEATURE)
        assert all(t.category == TemplateCategory.FEATURE for t in features)

    def test_render_migration_template(self):
        manager = TaskTemplateManager()
        manager.load_builtin_templates()
        result = manager.render_template("migration", source="React 18", target="React 19")
        assert "React 18" in result["title"]
        assert "React 19" in result["title"]


# -----------------------------------------------------------------------
# TaskTemplateManager — Import/Export
# -----------------------------------------------------------------------

class TestManagerImportExport:
    def _require_yaml(self):
        try:
            import yaml
        except ImportError:
            pytest.skip("PyYAML not installed")

    def test_export_template_yaml(self):
        self._require_yaml()
        manager = TaskTemplateManager()
        manager.load_builtin_templates()
        yaml_str = manager.export_template("feature")
        assert "feature" in yaml_str
        assert "title_template" in yaml_str

    def test_import_template_yaml(self):
        self._require_yaml()
        import yaml
        manager = TaskTemplateManager()
        data = {
            "id": "imported-1",
            "name": "Imported Template",
            "category": "custom",
            "title_template": "Imported: {{x}}",
            "variables": [{"name": "x", "default": "val"}],
        }
        yaml_str = yaml.dump(data)
        tpl = manager.import_template(yaml_str)
        assert tpl.id == "imported-1"
        assert manager.get_template("imported-1") is not None

    def test_save_template_to_file(self):
        self._require_yaml()
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TaskTemplateManager()
            tpl = TaskTemplate(
                id="save-test", name="Save Test",
                category=TemplateCategory.CUSTOM,
                title_template="Test {{x}}",
            )
            manager.add_template(tpl)
            path = manager.save_template_to_file("save-test", directory=tmpdir)
            assert os.path.exists(path)
            assert path.endswith(".yaml")

    def test_load_from_yaml_directory(self):
        self._require_yaml()
        import yaml
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write a YAML template file
            data = {
                "id": "from-file",
                "name": "From File",
                "category": "testing",
                "title_template": "Test {{module}}",
                "variables": [{"name": "module", "required": True}],
            }
            filepath = os.path.join(tmpdir, "from-file.yaml")
            with open(filepath, "w") as f:
                yaml.dump(data, f)

            manager = TaskTemplateManager()
            count = manager.load_from_directory(tmpdir)
            assert count == 1
            tpl = manager.get_template("from-file")
            assert tpl is not None
            assert tpl.name == "From File"

    def test_export_nonexistent_raises(self):
        self._require_yaml()
        manager = TaskTemplateManager()
        with pytest.raises(ValueError, match="not found"):
            manager.export_template("nope")


# -----------------------------------------------------------------------
# TaskTemplateManager — Stats
# -----------------------------------------------------------------------

class TestManagerStats:
    def test_stats_empty(self):
        manager = TaskTemplateManager()
        stats = manager.get_stats()
        assert stats["total_templates"] == 0

    def test_stats_with_builtins(self):
        manager = TaskTemplateManager()
        manager.load_builtin_templates()
        stats = manager.get_stats()
        assert stats["total_templates"] == len(BUILTIN_TEMPLATES)
        assert stats["builtin"] == len(BUILTIN_TEMPLATES)
        assert stats["custom"] == 0


# -----------------------------------------------------------------------
# Builtin templates validation
# -----------------------------------------------------------------------

class TestBuiltinTemplates:
    def test_all_builtins_have_id(self):
        for tpl_data in BUILTIN_TEMPLATES:
            assert tpl_data.get("id"), f"Missing id in builtin template: {tpl_data.get('name')}"

    def test_all_builtins_have_title_template(self):
        for tpl_data in BUILTIN_TEMPLATES:
            assert tpl_data.get("title_template"), f"Missing title_template: {tpl_data['id']}"

    def test_all_builtins_are_loadable(self):
        for tpl_data in BUILTIN_TEMPLATES:
            tpl = TaskTemplate.from_dict(tpl_data)
            assert tpl.id
            assert tpl.name
            assert tpl.is_builtin is True

    def test_all_builtins_are_renderable_with_defaults(self):
        """All builtins should render if all required vars are provided."""
        for tpl_data in BUILTIN_TEMPLATES:
            tpl = TaskTemplate.from_dict(tpl_data)
            kwargs = {}
            for var in tpl.variables:
                if var.required:
                    kwargs[var.name] = "test_value"
            result = tpl.render(**kwargs)
            assert result["title"]
