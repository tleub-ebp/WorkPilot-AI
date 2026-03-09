"""
Tests for architecture/rules_engine.py — full validation pipeline.
"""

import json
from pathlib import Path

import pytest

import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "apps" / "backend"))

from architecture.models import (
    ArchitectureConfig,
    BoundedContextConfig,
    ForbiddenPattern,
    LayerConfig,
    RulesConfig,
)
from architecture.rules_engine import ArchitectureRulesEngine


@pytest.fixture
def tmp_project(tmp_path):
    """Create a temporary project directory."""
    return tmp_path


def _make_layered_project(tmp_project: Path) -> ArchitectureConfig:
    """Create a project with layered architecture and return config."""
    # Presentation layer
    comp_dir = tmp_project / "src" / "components"
    comp_dir.mkdir(parents=True)

    # Application layer
    hooks_dir = tmp_project / "src" / "hooks"
    hooks_dir.mkdir(parents=True)

    # Infrastructure layer
    infra_dir = tmp_project / "src" / "infrastructure"
    infra_dir.mkdir(parents=True)

    return ArchitectureConfig(
        layers=[
            LayerConfig(
                name="presentation",
                patterns=["src/components/**"],
                allowed_imports=["application"],
                forbidden_imports=["infrastructure"],
            ),
            LayerConfig(
                name="application",
                patterns=["src/hooks/**"],
                allowed_imports=["domain"],
                forbidden_imports=[],
            ),
            LayerConfig(
                name="infrastructure",
                patterns=["src/infrastructure/**"],
                allowed_imports=["domain"],
                forbidden_imports=["presentation"],
            ),
        ],
        rules=RulesConfig(
            no_circular_dependencies=True,
            forbidden_patterns=[
                ForbiddenPattern(
                    from_pattern="src/components/**",
                    import_pattern=r"database|prisma",
                    description="No DB from UI",
                )
            ],
        ),
    )


class TestRulesEngineValidation:
    """Tests for ArchitectureRulesEngine.validate()."""

    def test_clean_project_passes(self, tmp_project):
        """Should pass when no violations exist."""
        config = _make_layered_project(tmp_project)

        # Clean component that imports correctly
        (tmp_project / "src" / "components" / "App.tsx").write_text(
            "import React from 'react';\n"
            "import { useAuth } from '../hooks/useAuth';\n",
            encoding="utf-8",
        )
        (tmp_project / "src" / "hooks" / "useAuth.ts").write_text(
            "export function useAuth() { return {}; }\n",
            encoding="utf-8",
        )

        engine = ArchitectureRulesEngine(tmp_project, config)
        report = engine.validate(
            changed_files=["src/components/App.tsx"]
        )

        assert report.passed is True
        assert len(report.violations) == 0
        assert report.files_analyzed == 1

    def test_detects_layer_violation(self, tmp_project):
        """Should detect layer boundary violations."""
        config = _make_layered_project(tmp_project)

        # Component importing from infrastructure (VIOLATION)
        (tmp_project / "src" / "components" / "App.tsx").write_text(
            "import { db } from '../infrastructure/database';\n",
            encoding="utf-8",
        )
        (tmp_project / "src" / "infrastructure" / "database.ts").write_text(
            "export const db = {};\n",
            encoding="utf-8",
        )

        engine = ArchitectureRulesEngine(tmp_project, config)
        report = engine.validate(
            changed_files=["src/components/App.tsx"]
        )

        # Should have violations (layer + possibly forbidden pattern)
        total_issues = len(report.violations) + len(report.warnings)
        assert total_issues > 0

    def test_detects_forbidden_import(self, tmp_project):
        """Should detect forbidden import patterns."""
        config = _make_layered_project(tmp_project)

        # Component importing prisma directly (FORBIDDEN)
        (tmp_project / "src" / "components" / "List.tsx").write_text(
            "import { PrismaClient } from '@prisma/client';\n",
            encoding="utf-8",
        )

        engine = ArchitectureRulesEngine(tmp_project, config)
        report = engine.validate(
            changed_files=["src/components/List.tsx"]
        )

        # Should have at least one forbidden import violation
        forbidden = [
            v for v in report.violations + report.warnings if v.type == "forbidden_import"
        ]
        assert len(forbidden) > 0

    def test_detects_circular_dependency(self, tmp_project):
        """Should detect circular dependencies."""
        (tmp_project / "a.py").write_text(
            "from b import something\n",
            encoding="utf-8",
        )
        (tmp_project / "b.py").write_text(
            "from a import other\n",
            encoding="utf-8",
        )

        config = ArchitectureConfig(
            rules=RulesConfig(no_circular_dependencies=True),
        )

        engine = ArchitectureRulesEngine(tmp_project, config)
        report = engine.validate(changed_files=["a.py", "b.py"])

        cycle_violations = [
            v
            for v in report.violations + report.warnings
            if v.type == "circular_dependency"
        ]
        assert len(cycle_violations) >= 1

    def test_report_format(self, tmp_project):
        """Should produce a well-structured report."""
        config = ArchitectureConfig()
        (tmp_project / "app.py").write_text("import os\n", encoding="utf-8")

        engine = ArchitectureRulesEngine(tmp_project, config)
        report = engine.validate(changed_files=["app.py"])

        assert report.files_analyzed >= 0
        assert report.duration_seconds >= 0
        assert isinstance(report.summary, str)
        assert isinstance(report.violations, list)
        assert isinstance(report.warnings, list)

    def test_report_to_dict(self, tmp_project):
        """Should serialize report to dict correctly."""
        config = ArchitectureConfig()
        (tmp_project / "app.py").write_text("import os\n", encoding="utf-8")

        engine = ArchitectureRulesEngine(tmp_project, config)
        report = engine.validate(changed_files=["app.py"])
        d = report.to_dict()

        assert "status" in d
        assert d["status"] in ("approved", "rejected")
        assert "violations" in d
        assert "warnings" in d
        assert "summary" in d
        assert "files_analyzed" in d
        assert "duration_seconds" in d

    def test_explicit_config_produces_errors(self, tmp_project):
        """Explicit configs should produce errors for violations."""
        config = _make_layered_project(tmp_project)
        assert config.inferred is False

        (tmp_project / "src" / "components" / "Bad.tsx").write_text(
            "import { PrismaClient } from 'prisma';\n",
            encoding="utf-8",
        )

        engine = ArchitectureRulesEngine(tmp_project, config)
        report = engine.validate(changed_files=["src/components/Bad.tsx"])

        # Explicit config violations should be errors
        if report.violations:
            assert all(v.severity == "error" for v in report.violations)

    def test_empty_project(self, tmp_project):
        """Should handle project with no files."""
        config = ArchitectureConfig()

        engine = ArchitectureRulesEngine(tmp_project, config)
        report = engine.validate(changed_files=[])

        assert report.passed is True
        assert report.files_analyzed == 0

    def test_config_source_in_report(self, tmp_project):
        """Should correctly report config source."""
        (tmp_project / "app.py").write_text("import os\n", encoding="utf-8")

        # Explicit config
        config = ArchitectureConfig(inferred=False)
        engine = ArchitectureRulesEngine(tmp_project, config)
        report = engine.validate(changed_files=["app.py"])
        assert report.config_source == "explicit"

        # Inferred config
        config_inferred = ArchitectureConfig(inferred=True)
        engine2 = ArchitectureRulesEngine(tmp_project, config_inferred)
        report2 = engine2.validate(changed_files=["app.py"])
        assert report2.config_source == "inferred"


class TestBoundedContextIntegration:
    """Tests for bounded context validation in the full engine."""

    def test_detects_cross_context_violation(self, tmp_project):
        """Should detect bounded context violations through the engine."""
        # Create context directories
        auth_dir = tmp_project / "auth"
        auth_dir.mkdir()
        billing_dir = tmp_project / "billing"
        billing_dir.mkdir()

        (auth_dir / "login.py").write_text(
            "from billing.invoice import create_invoice\n",
            encoding="utf-8",
        )
        (billing_dir / "invoice.py").write_text(
            "def create_invoice(): pass\n",
            encoding="utf-8",
        )

        config = ArchitectureConfig(
            bounded_contexts=[
                BoundedContextConfig(
                    name="auth",
                    patterns=["auth/**"],
                    allowed_cross_context_imports=["shared"],
                ),
                BoundedContextConfig(
                    name="billing",
                    patterns=["billing/**"],
                    allowed_cross_context_imports=["shared"],
                ),
            ],
            rules=RulesConfig(no_circular_dependencies=True),
        )

        engine = ArchitectureRulesEngine(tmp_project, config)
        report = engine.validate(changed_files=["auth/login.py"])

        context_violations = [
            v
            for v in report.violations + report.warnings
            if v.type == "bounded_context"
        ]
        assert len(context_violations) >= 1
