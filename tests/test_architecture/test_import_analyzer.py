"""
Tests for architecture/import_analyzer.py — import graph building and violation detection.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "apps" / "backend"))

from architecture.import_analyzer import ImportAnalyzer
from architecture.models import (
    ArchitectureConfig,
    ForbiddenPattern,
    ImportGraph,
    LayerConfig,
    RulesConfig,
)


@pytest.fixture
def tmp_project(tmp_path):
    """Create a temporary project directory."""
    return tmp_path


def _make_config(
    layers=None, forbidden_patterns=None, inferred=False
) -> ArchitectureConfig:
    """Helper to create a config."""
    return ArchitectureConfig(
        layers=layers or [],
        rules=RulesConfig(
            forbidden_patterns=forbidden_patterns or [],
        ),
        inferred=inferred,
    )


class TestPythonImportParsing:
    """Tests for Python import parsing."""

    def test_parse_absolute_import(self, tmp_project):
        """Should parse 'import X' statements."""
        (tmp_project / "app.py").write_text(
            "import os\nimport json\nimport mypackage.utils\n",
            encoding="utf-8",
        )
        analyzer = ImportAnalyzer(tmp_project, _make_config())
        graph = analyzer.analyze_imports(["app.py"])

        assert graph.files_analyzed == 1
        targets = [e.target_module for e in graph.edges]
        assert "os" in targets
        assert "json" in targets
        assert "mypackage.utils" in targets

    def test_parse_from_import(self, tmp_project):
        """Should parse 'from X import Y' statements."""
        (tmp_project / "app.py").write_text(
            "from pathlib import Path\nfrom mypackage.utils import helper\n",
            encoding="utf-8",
        )
        analyzer = ImportAnalyzer(tmp_project, _make_config())
        graph = analyzer.analyze_imports(["app.py"])

        targets = [e.target_module for e in graph.edges]
        assert "pathlib" in targets
        assert "mypackage.utils" in targets

    def test_parse_relative_import(self, tmp_project):
        """Should resolve relative Python imports."""
        pkg_dir = tmp_project / "mypackage"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
        (pkg_dir / "module.py").write_text(
            "from . import utils\nfrom .helpers import foo\n",
            encoding="utf-8",
        )
        analyzer = ImportAnalyzer(tmp_project, _make_config())
        graph = analyzer.analyze_imports(["mypackage/module.py"])

        assert graph.files_analyzed == 1
        targets = [e.target_module for e in graph.edges]
        assert any("mypackage" in t for t in targets)

    def test_handles_syntax_error(self, tmp_project):
        """Should not crash on Python files with syntax errors."""
        (tmp_project / "bad.py").write_text(
            "def foo(\n  # syntax error\n",
            encoding="utf-8",
        )
        analyzer = ImportAnalyzer(tmp_project, _make_config())
        graph = analyzer.analyze_imports(["bad.py"])

        assert graph.files_analyzed == 1
        assert len(graph.edges) == 0

    def test_records_line_numbers(self, tmp_project):
        """Should record line numbers for imports."""
        (tmp_project / "app.py").write_text(
            "# comment\nimport os\n\nimport json\n",
            encoding="utf-8",
        )
        analyzer = ImportAnalyzer(tmp_project, _make_config())
        graph = analyzer.analyze_imports(["app.py"])

        os_edge = next(e for e in graph.edges if e.target_module == "os")
        assert os_edge.line == 2
        json_edge = next(e for e in graph.edges if e.target_module == "json")
        assert json_edge.line == 4


class TestJSTSImportParsing:
    """Tests for JavaScript/TypeScript import parsing."""

    def test_parse_es_import(self, tmp_project):
        """Should parse ES module imports."""
        (tmp_project / "app.ts").write_text(
            "import { useState } from 'react';\n"
            "import axios from 'axios';\n"
            "import { helper } from './utils';\n",
            encoding="utf-8",
        )
        analyzer = ImportAnalyzer(tmp_project, _make_config())
        graph = analyzer.analyze_imports(["app.ts"])

        targets = [e.target_module for e in graph.edges]
        assert "react" in targets
        assert "axios" in targets
        assert "./utils" in targets

    def test_parse_require(self, tmp_project):
        """Should parse require() calls."""
        (tmp_project / "app.js").write_text(
            "const fs = require('fs');\n"
            "const helper = require('./helpers/utils');\n",
            encoding="utf-8",
        )
        analyzer = ImportAnalyzer(tmp_project, _make_config())
        graph = analyzer.analyze_imports(["app.js"])

        targets = [e.target_module for e in graph.edges]
        assert "fs" in targets
        assert "./helpers/utils" in targets

    def test_parse_dynamic_import(self, tmp_project):
        """Should parse dynamic import() calls."""
        (tmp_project / "app.ts").write_text(
            "const mod = await import('./lazy-module');\n",
            encoding="utf-8",
        )
        analyzer = ImportAnalyzer(tmp_project, _make_config())
        graph = analyzer.analyze_imports(["app.ts"])

        targets = [e.target_module for e in graph.edges]
        assert "./lazy-module" in targets

    def test_parse_reexport(self, tmp_project):
        """Should parse re-export statements."""
        (tmp_project / "index.ts").write_text(
            "export { default } from './component';\n"
            "export { utils } from './utils';\n",
            encoding="utf-8",
        )
        analyzer = ImportAnalyzer(tmp_project, _make_config())
        graph = analyzer.analyze_imports(["index.ts"])

        targets = [e.target_module for e in graph.edges]
        assert "./component" in targets
        assert "./utils" in targets

    def test_skips_comments(self, tmp_project):
        """Should skip commented import lines."""
        (tmp_project / "app.ts").write_text(
            "// import { old } from 'deprecated';\n"
            "import { current } from 'active';\n",
            encoding="utf-8",
        )
        analyzer = ImportAnalyzer(tmp_project, _make_config())
        graph = analyzer.analyze_imports(["app.ts"])

        targets = [e.target_module for e in graph.edges]
        assert "deprecated" not in targets
        assert "active" in targets

    def test_handles_tsx_files(self, tmp_project):
        """Should analyze .tsx files."""
        (tmp_project / "Component.tsx").write_text(
            "import React from 'react';\nimport { Button } from './ui';\n",
            encoding="utf-8",
        )
        analyzer = ImportAnalyzer(tmp_project, _make_config())
        graph = analyzer.analyze_imports(["Component.tsx"])

        assert graph.files_analyzed == 1
        targets = [e.target_module for e in graph.edges]
        assert "react" in targets


class TestLayerViolations:
    """Tests for layer violation detection."""

    def test_detects_forbidden_layer_import(self, tmp_project):
        """Should detect when presentation imports from infrastructure."""
        # Create source file in presentation layer
        comp_dir = tmp_project / "src" / "components"
        comp_dir.mkdir(parents=True)
        (comp_dir / "App.tsx").write_text(
            "import { db } from '../../src/infrastructure/database';\n",
            encoding="utf-8",
        )

        # Create target file in infrastructure
        infra_dir = tmp_project / "src" / "infrastructure"
        infra_dir.mkdir(parents=True)
        (infra_dir / "database.ts").write_text(
            "export const db = {};\n",
            encoding="utf-8",
        )

        config = _make_config(
            layers=[
                LayerConfig(
                    name="presentation",
                    patterns=["src/components/**"],
                    allowed_imports=["application"],
                    forbidden_imports=["infrastructure"],
                ),
                LayerConfig(
                    name="infrastructure",
                    patterns=["src/infrastructure/**"],
                    allowed_imports=["domain"],
                    forbidden_imports=["presentation"],
                ),
            ]
        )

        analyzer = ImportAnalyzer(tmp_project, config)
        graph = analyzer.analyze_imports(["src/components/App.tsx"])
        violations = analyzer.check_layer_violations(graph)

        assert len(violations) > 0
        assert violations[0].type == "layer_violation"
        assert "presentation" in violations[0].description
        assert "infrastructure" in violations[0].description

    def test_allows_valid_layer_imports(self, tmp_project):
        """Should not flag valid imports between allowed layers."""
        (tmp_project / "src" / "components").mkdir(parents=True)
        (tmp_project / "src" / "components" / "App.tsx").write_text(
            "import { useAuth } from '../../src/hooks/useAuth';\n",
            encoding="utf-8",
        )

        config = _make_config(
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
            ]
        )

        analyzer = ImportAnalyzer(tmp_project, config)
        graph = analyzer.analyze_imports(["src/components/App.tsx"])
        violations = analyzer.check_layer_violations(graph)

        # Should have no violations (or only warnings for unresolved imports)
        errors = [v for v in violations if v.severity == "error"]
        assert len(errors) == 0

    def test_inferred_config_produces_warnings(self, tmp_project):
        """Inferred configs should produce warnings, not errors."""
        (tmp_project / "src" / "components").mkdir(parents=True)
        (tmp_project / "src" / "components" / "App.tsx").write_text(
            "import { db } from '../../src/infrastructure/database';\n",
            encoding="utf-8",
        )

        config = _make_config(
            layers=[
                LayerConfig(
                    name="presentation",
                    patterns=["src/components/**"],
                    forbidden_imports=["infrastructure"],
                ),
                LayerConfig(
                    name="infrastructure",
                    patterns=["src/infrastructure/**"],
                    forbidden_imports=[],
                ),
            ],
            inferred=True,
        )

        analyzer = ImportAnalyzer(tmp_project, config)
        graph = analyzer.analyze_imports(["src/components/App.tsx"])
        violations = analyzer.check_layer_violations(graph)

        if violations:
            assert all(v.severity == "warning" for v in violations)


class TestForbiddenImports:
    """Tests for forbidden import pattern detection."""

    def test_detects_forbidden_pattern(self, tmp_project):
        """Should detect imports matching forbidden patterns."""
        (tmp_project / "src" / "renderer").mkdir(parents=True)
        (tmp_project / "src" / "renderer" / "App.tsx").write_text(
            "import { PrismaClient } from '@prisma/client';\n",
            encoding="utf-8",
        )

        config = _make_config(
            forbidden_patterns=[
                ForbiddenPattern(
                    from_pattern="src/renderer/**",
                    import_pattern=r"prisma",
                    description="No Prisma from renderer",
                )
            ]
        )

        analyzer = ImportAnalyzer(tmp_project, config)
        graph = analyzer.analyze_imports(["src/renderer/App.tsx"])
        violations = analyzer.check_forbidden_imports(graph)

        assert len(violations) == 1
        assert violations[0].type == "forbidden_import"
        assert "prisma" in violations[0].import_target.lower() or "prisma" in violations[0].description.lower()

    def test_no_false_positive_for_allowed_imports(self, tmp_project):
        """Should not flag imports that don't match the forbidden pattern."""
        (tmp_project / "src" / "renderer").mkdir(parents=True)
        (tmp_project / "src" / "renderer" / "App.tsx").write_text(
            "import React from 'react';\n",
            encoding="utf-8",
        )

        config = _make_config(
            forbidden_patterns=[
                ForbiddenPattern(
                    from_pattern="src/renderer/**",
                    import_pattern=r"prisma|database",
                    description="No DB from renderer",
                )
            ]
        )

        analyzer = ImportAnalyzer(tmp_project, config)
        graph = analyzer.analyze_imports(["src/renderer/App.tsx"])
        violations = analyzer.check_forbidden_imports(graph)

        assert len(violations) == 0


class TestFullProjectAnalysis:
    """Tests for analyzing an entire project (no changed_files filter)."""

    def test_walks_project_skipping_node_modules(self, tmp_project):
        """Should skip node_modules and similar directories."""
        # Create source file
        (tmp_project / "src").mkdir()
        (tmp_project / "src" / "app.py").write_text("import os\n", encoding="utf-8")

        # Create node_modules file (should be skipped)
        nm = tmp_project / "node_modules" / "pkg"
        nm.mkdir(parents=True)
        (nm / "index.js").write_text("import x from 'y';\n", encoding="utf-8")

        analyzer = ImportAnalyzer(tmp_project, _make_config())
        graph = analyzer.analyze_imports()  # No changed_files — full scan

        # Should only find the src/app.py file
        sources = graph.get_all_sources()
        assert any("app.py" in s for s in sources)
        assert not any("node_modules" in s for s in sources)

    def test_handles_empty_project(self, tmp_project):
        """Should handle a project with no source files."""
        analyzer = ImportAnalyzer(tmp_project, _make_config())
        graph = analyzer.analyze_imports()

        assert graph.files_analyzed == 0
        assert len(graph.edges) == 0
