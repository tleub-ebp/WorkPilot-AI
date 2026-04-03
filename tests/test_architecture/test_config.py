"""
Tests for architecture/config.py — config loading and inference.
"""

import json
import os

# Add backend to sys.path for imports
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "apps" / "backend"))

from architecture.config import (
    infer_architecture_config,
    load_architecture_config,
)
from architecture.models import ArchitectureConfig


@pytest.fixture
def tmp_project(tmp_path):
    """Create a temporary project directory."""
    auto_claude = tmp_path / ".workpilot"
    auto_claude.mkdir()
    return tmp_path


class TestLoadArchitectureConfig:
    """Tests for load_architecture_config()."""

    def test_returns_none_when_no_config(self, tmp_project):
        """Should return None if no architecture_rules.json exists."""
        result = load_architecture_config(tmp_project)
        assert result is None

    def test_loads_valid_config(self, tmp_project):
        """Should load a valid architecture_rules.json."""
        config_data = {
            "version": "1.0",
            "architecture_style": "layered",
            "layers": [
                {
                    "name": "presentation",
                    "patterns": ["src/components/**"],
                    "allowed_imports": ["application"],
                    "forbidden_imports": ["infrastructure"],
                }
            ],
            "bounded_contexts": [
                {
                    "name": "auth",
                    "patterns": ["**/auth/**"],
                    "allowed_cross_context_imports": ["shared"],
                }
            ],
            "rules": {
                "no_circular_dependencies": True,
                "max_dependency_depth": 5,
                "forbidden_patterns": [
                    {
                        "from": "src/components/**",
                        "import_pattern": "database|prisma",
                        "description": "No DB from UI",
                    }
                ],
            },
            "ai_review": False,
        }

        config_path = tmp_project / ".workpilot" / "architecture_rules.json"
        config_path.write_text(json.dumps(config_data), encoding="utf-8")

        result = load_architecture_config(tmp_project)

        assert result is not None
        assert isinstance(result, ArchitectureConfig)
        assert result.version == "1.0"
        assert result.architecture_style == "layered"
        assert len(result.layers) == 1
        assert result.layers[0].name == "presentation"
        assert result.layers[0].forbidden_imports == ["infrastructure"]
        assert len(result.bounded_contexts) == 1
        assert result.bounded_contexts[0].name == "auth"
        assert result.rules.no_circular_dependencies is True
        assert result.rules.max_dependency_depth == 5
        assert len(result.rules.forbidden_patterns) == 1
        assert result.ai_review is False
        assert result.inferred is False

    def test_handles_malformed_json(self, tmp_project):
        """Should return None for malformed JSON."""
        config_path = tmp_project / ".workpilot" / "architecture_rules.json"
        config_path.write_text("{ not valid json }", encoding="utf-8")

        result = load_architecture_config(tmp_project)
        assert result is None

    def test_handles_empty_config(self, tmp_project):
        """Should handle an empty config with defaults."""
        config_path = tmp_project / ".workpilot" / "architecture_rules.json"
        config_path.write_text("{}", encoding="utf-8")

        result = load_architecture_config(tmp_project)

        assert result is not None
        assert result.layers == []
        assert result.bounded_contexts == []
        assert result.rules.no_circular_dependencies is True
        assert result.ai_review is True

    def test_loads_minimal_layer_config(self, tmp_project):
        """Should handle layers with minimal fields."""
        config_data = {
            "layers": [
                {
                    "name": "core",
                    "patterns": ["src/core/**"],
                }
            ]
        }
        config_path = tmp_project / ".workpilot" / "architecture_rules.json"
        config_path.write_text(json.dumps(config_data), encoding="utf-8")

        result = load_architecture_config(tmp_project)

        assert result is not None
        assert len(result.layers) == 1
        assert result.layers[0].name == "core"
        assert result.layers[0].allowed_imports == []
        assert result.layers[0].forbidden_imports == []


class TestInferArchitectureConfig:
    """Tests for infer_architecture_config()."""

    def test_infer_react_project(self, tmp_project):
        """Should infer frontend layers for React projects."""
        project_index = {
            "project_type": "single",
            "detected_stack": {
                "languages": ["typescript", "javascript"],
                "frameworks": ["React"],
            },
            "services": {},
        }

        result = infer_architecture_config(tmp_project, project_index)

        assert result is not None
        assert result.inferred is True
        assert len(result.layers) > 0
        layer_names = [l.name for l in result.layers]
        assert "presentation" in layer_names

    def test_infer_django_project(self, tmp_project):
        """Should infer MVC layers for Django projects."""
        project_index = {
            "project_type": "single",
            "detected_stack": {
                "languages": ["python"],
                "frameworks": ["Django"],
            },
            "services": {},
        }

        result = infer_architecture_config(tmp_project, project_index)

        assert result is not None
        assert result.inferred is True
        layer_names = [l.name for l in result.layers]
        assert "views" in layer_names
        assert "models" in layer_names

    def test_infer_fastapi_project(self, tmp_project):
        """Should infer API layers for FastAPI projects."""
        project_index = {
            "project_type": "single",
            "detected_stack": {
                "languages": ["python"],
                "frameworks": ["FastAPI"],
            },
            "services": {},
        }

        result = infer_architecture_config(tmp_project, project_index)

        assert result is not None
        layer_names = [l.name for l in result.layers]
        assert "routes" in layer_names
        assert "services" in layer_names

    def test_infer_monorepo_bounded_contexts(self, tmp_project):
        """Should infer bounded contexts for monorepos with multiple services."""
        project_index = {
            "project_type": "monorepo",
            "detected_stack": {
                "languages": ["typescript"],
                "frameworks": [],
            },
            "services": {
                "api": {"path": "apps/api", "type": "backend"},
                "web": {"path": "apps/web", "type": "frontend"},
                "shared": {"path": "packages/shared", "type": "library"},
            },
        }

        result = infer_architecture_config(tmp_project, project_index)

        assert result is not None
        assert len(result.bounded_contexts) == 3
        ctx_names = [c.name for c in result.bounded_contexts]
        assert "api" in ctx_names
        assert "web" in ctx_names

    def test_infer_empty_project_index(self, tmp_project):
        """Should return minimal config for empty project index."""
        result = infer_architecture_config(tmp_project, {})

        assert result is not None
        assert result.inferred is True
        assert result.rules.no_circular_dependencies is True

    def test_infer_generic_layers_from_directory_structure(self, tmp_project):
        """Should detect layers from common directory names."""
        # Create common architecture directories
        (tmp_project / "src" / "presentation").mkdir(parents=True)
        (tmp_project / "src" / "domain").mkdir(parents=True)
        (tmp_project / "src" / "infrastructure").mkdir(parents=True)

        result = infer_architecture_config(tmp_project, {})

        assert result is not None
        layer_names = [l.name for l in result.layers]
        assert "presentation" in layer_names
        assert "domain" in layer_names
        assert "infrastructure" in layer_names

    def test_infer_always_enables_circular_dependency_check(self, tmp_project):
        """Circular dependency detection should always be enabled."""
        result = infer_architecture_config(tmp_project, {})
        assert result.rules.no_circular_dependencies is True

    def test_infer_adds_forbidden_db_import_for_frontend(self, tmp_project):
        """React projects should have forbidden DB imports from components."""
        project_index = {
            "project_type": "single",
            "detected_stack": {
                "languages": ["typescript"],
                "frameworks": ["React"],
            },
            "services": {},
        }

        result = infer_architecture_config(tmp_project, project_index)

        assert len(result.rules.forbidden_patterns) > 0
        db_pattern = result.rules.forbidden_patterns[0]
        assert "database" in db_pattern.import_pattern or "prisma" in db_pattern.import_pattern
