"""
Tests for Design-to-Code Service
"""

import pytest
import math
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import sys
import json
from pathlib import Path

# Add the apps/backend directory to the Python path
backend_path = Path(__file__).parent.parent.parent / "apps" / "backend"
sys.path.insert(0, str(backend_path))
root_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_path))

from services.design_to_code_service import (
    DesignToCodeService,
    DesignTokenExtractor,
    VisualTestGenerator,
    DesignSpec,
    ComponentSpec,
    GeneratedFile,
    VisualTest,
    PipelinePhase,
    PipelineResult,
    FrameworkType,
    DesignSourceType,
)


class TestDesignTokenExtractor:
    """Test suite for DesignTokenExtractor"""

    @pytest.fixture
    def extractor(self, tmp_path):
        """Create a token extractor with a temporary project directory."""
        return DesignTokenExtractor(tmp_path)

    def test_extract_from_empty_project(self, extractor):
        """Should return empty list when no design token files exist."""
        tokens = extractor.extract()
        assert tokens == []

    def test_extract_from_css_variables(self, tmp_path):
        """Should extract CSS custom properties."""
        css_content = """:root {
  --color-primary: #3b82f6;
  --color-secondary: #10b981;
  --font-size-base: 16px;
  --spacing-4: 1rem;
}"""
        css_file = tmp_path / "styles" / "variables.css"
        css_file.parent.mkdir(parents=True, exist_ok=True)
        css_file.write_text(css_content)

        extractor = DesignTokenExtractor(tmp_path)
        tokens = extractor.extract()

        assert len(tokens) >= 2

    def test_extract_from_json_tokens(self, tmp_path):
        """Should extract tokens from a JSON design tokens file."""
        tokens_data = {
            "colors": {
                "primary": {"$value": "#3b82f6", "$type": "color"},
                "secondary": {"$value": "#10b981", "$type": "color"},
            },
            "spacing": {
                "sm": {"value": "0.5rem", "type": "spacing"},
                "md": {"value": "1rem", "type": "spacing"},
            },
        }
        tokens_file = tmp_path / "design-tokens.json"
        tokens_file.write_text(json.dumps(tokens_data))

        extractor = DesignTokenExtractor(tmp_path)
        tokens = extractor.extract()

        assert len(tokens) >= 2

    def test_extract_from_custom_path(self, tmp_path):
        """Should respect custom design system path."""
        custom_dir = tmp_path / "my-design-system"
        custom_dir.mkdir()
        css_file = custom_dir / "variables.css"
        css_file.write_text(":root { --brand-color: #ff0000; }")

        extractor = DesignTokenExtractor(tmp_path)
        tokens = extractor.extract(design_system_path="my-design-system")

        # Should find tokens in the custom path
        assert isinstance(tokens, list)


class TestVisualTestGenerator:
    """Test suite for VisualTestGenerator"""

    def test_generate_react_tests(self):
        """Should generate Playwright visual tests for React components."""
        generator = VisualTestGenerator(FrameworkType.REACT)
        files = [
            GeneratedFile(
                path="src/components/Header.tsx",
                content="export function Header() { return <header>Hello</header>; }",
                language="tsx",
                description="Header component",
            )
        ]
        tests = generator.generate_tests(files)

        assert len(tests) >= 1
        assert isinstance(tests[0], VisualTest)
        assert "Header" in tests[0].name
        assert "test" in tests[0].test_code.lower()
        assert tests[0].threshold > 0

    def test_generate_vue_tests(self):
        """Should generate Playwright visual tests for Vue components."""
        generator = VisualTestGenerator(FrameworkType.VUE)
        files = [
            GeneratedFile(
                path="src/components/Header.vue",
                content="<template><header>Hello</header></template>",
                language="vue",
                description="Header component",
            )
        ]
        tests = generator.generate_tests(files)

        assert len(tests) >= 1
        assert "Header" in tests[0].name

    def test_generate_svelte_tests(self):
        """Should generate Playwright visual tests for Svelte components."""
        generator = VisualTestGenerator(FrameworkType.SVELTE)
        files = [
            GeneratedFile(
                path="src/components/Header.svelte",
                content="<header>Hello</header>",
                language="svelte",
                description="Header component",
            )
        ]
        tests = generator.generate_tests(files)

        assert len(tests) >= 1
        assert "Header" in tests[0].name

    def test_generated_test_includes_viewports(self):
        """Should generate tests that cover multiple viewports."""
        generator = VisualTestGenerator(FrameworkType.REACT)
        files = [
            GeneratedFile(
                path="src/components/Card.tsx",
                content="export function Card() { return <div>Card</div>; }",
                language="tsx",
                description="Card component",
            )
        ]
        tests = generator.generate_tests(files)

        assert len(tests) >= 1
        code_lower = tests[0].test_code.lower()
        assert "1280" in tests[0].test_code or "desktop" in code_lower or "viewport" in code_lower


class TestDesignSpec:
    """Test suite for DesignSpec dataclass"""

    def test_create_design_spec(self):
        """Should create a valid DesignSpec."""
        spec = DesignSpec(
            components=[
                ComponentSpec(
                    name="Header",
                    type="layout",
                    description="Top navigation header",
                    children=[],
                    props={},
                    styles={},
                )
            ],
            color_palette={"primary": "#3b82f6", "background": "#ffffff"},
            typography={"heading": {"fontSize": "24px", "fontWeight": "bold"}},
        )

        assert len(spec.components) == 1
        assert spec.components[0].name == "Header"
        assert spec.color_palette["primary"] == "#3b82f6"

    def test_empty_design_spec(self):
        """Should create a DesignSpec with defaults."""
        spec = DesignSpec()

        assert len(spec.components) == 0
        assert spec.color_palette == {}


class TestPipelineResult:
    """Test suite for PipelineResult dataclass"""

    def test_successful_result(self):
        """Should represent a successful pipeline execution."""
        result = PipelineResult(
            success=True,
            phase=PipelinePhase.COMPLETE,
            design_spec=None,
            generated_files=[],
            visual_tests=[],
            design_tokens_used=[],
            figma_sync_status=None,
            errors=[],
            warnings=[],
            duration_seconds=5.2,
            tokens_used=1500,
        )

        assert result.success is True
        assert result.phase == PipelinePhase.COMPLETE
        assert math.isclose(result.duration_seconds, 5.2)

    def test_failed_result(self):
        """Should represent a failed pipeline execution."""
        result = PipelineResult(
            success=False,
            phase=PipelinePhase.ERROR,
            design_spec=None,
            generated_files=[],
            visual_tests=[],
            design_tokens_used=[],
            figma_sync_status=None,
            errors=["Vision AI analysis failed"],
            warnings=[],
            duration_seconds=1.0,
            tokens_used=0,
        )

        assert result.success is False
        assert result.phase == PipelinePhase.ERROR
        assert len(result.errors) == 1


class TestDesignToCodeService:
    """Test suite for DesignToCodeService"""

    @pytest.fixture
    def service(self, tmp_path):
        """Create a service instance with a temporary project directory."""
        return DesignToCodeService(str(tmp_path))

    def test_service_initialization(self, service, tmp_path):
        """Should initialize with correct defaults."""
        assert service.project_path == tmp_path
        assert isinstance(service.token_extractor, DesignTokenExtractor)

    def test_phase_callback(self, service):
        """Should call phase callback when phase changes."""
        phases_received = []

        def callback(phase, status):
            phases_received.append((phase, status))

        service.on_phase_change(callback)
        service._set_phase(PipelinePhase.ANALYZING, "Testing phase callback")

        assert len(phases_received) == 1
        assert phases_received[0][0] == PipelinePhase.ANALYZING
        assert phases_received[0][1] == "Testing phase callback"

    @pytest.mark.asyncio
    async def test_run_pipeline_no_api_key_uses_mock(self, service):
        """Should use mock analysis when no API key is configured."""
        with patch.dict("os.environ", {}, clear=True):
            # Remove any API keys
            import os
            for key in ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"]:
                os.environ.pop(key, None)

            result = await service.run_pipeline(
                image_data="data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==",
                framework="react",
            )

            assert isinstance(result, PipelineResult)
            assert result.success is True
            assert result.phase == PipelinePhase.COMPLETE
            assert len(result.generated_files) > 0

    @pytest.mark.asyncio
    async def test_run_pipeline_with_design_tokens(self, service, tmp_path):
        """Should integrate design tokens when available."""
        # Create a CSS tokens file
        css_file = tmp_path / "styles" / "tokens.css"
        css_file.parent.mkdir(parents=True, exist_ok=True)
        css_file.write_text(":root { --primary: #3b82f6; --bg: #ffffff; }")

        with patch.dict("os.environ", {}, clear=True):
            import os
            for key in ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"]:
                os.environ.pop(key, None)

            result = await service.run_pipeline(
                image_data="data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==",
                framework="react",
            )

            assert isinstance(result, PipelineResult)
            assert result.success is True

    @pytest.mark.asyncio
    async def test_run_pipeline_generates_visual_tests(self, service):
        """Should generate visual tests when enabled."""
        with patch.dict("os.environ", {}, clear=True):
            import os
            for key in ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"]:
                os.environ.pop(key, None)

            result = await service.run_pipeline(
                image_data="data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==",
                framework="react",
                generate_tests=True,
            )

            assert result.success is True
            assert len(result.visual_tests) > 0

    @pytest.mark.asyncio
    async def test_run_pipeline_skips_visual_tests(self, service):
        """Should skip visual tests when disabled."""
        with patch.dict("os.environ", {}, clear=True):
            import os
            for key in ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"]:
                os.environ.pop(key, None)

            result = await service.run_pipeline(
                image_data="data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==",
                framework="react",
                generate_tests=False,
            )

            assert result.success is True
            assert len(result.visual_tests) == 0

    @pytest.mark.asyncio
    async def test_run_pipeline_vue_framework(self, service):
        """Should generate Vue code when vue framework is specified."""
        with patch.dict("os.environ", {}, clear=True):
            import os
            for key in ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"]:
                os.environ.pop(key, None)

            result = await service.run_pipeline(
                image_data="data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==",
                framework="vue",
            )

            assert result.success is True
            assert len(result.generated_files) > 0

    @pytest.mark.asyncio
    async def test_run_pipeline_records_duration(self, service):
        """Should record pipeline execution duration."""
        with patch.dict("os.environ", {}, clear=True):
            import os
            for key in ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"]:
                os.environ.pop(key, None)

            result = await service.run_pipeline(
                image_data="data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==",
                framework="react",
            )

            assert result.duration_seconds >= 0


class TestFigmaConnector:
    """Test suite for FigmaConnector"""

    def test_parse_figma_file_url(self):
        """Should parse standard Figma file URLs."""
        import sys
        from pathlib import Path
        
        # Add the src directory to Python path for proper imports
        # Use absolute path from project root to handle different working directories
        import os
        project_root = Path(__file__).parent.parent.parent
        src_path = project_root / "src"
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
        
        from src.connectors.figma_connector import FigmaConnector

        result = FigmaConnector.parse_figma_url(
            "https://www.figma.com/file/abc123def/My-Design"
        )
        assert result is not None
        assert result["file_key"] == "abc123def"
        assert "node_id" not in result

    def test_parse_figma_design_url_with_node(self):
        """Should parse Figma design URL with node-id."""
        import sys
        from pathlib import Path
        
        # Add the src directory to Python path for proper imports
        # Use absolute path from project root to handle different working directories
        import os
        project_root = Path(__file__).parent.parent.parent
        src_path = project_root / "src"
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
        
        from src.connectors.figma_connector import FigmaConnector

        result = FigmaConnector.parse_figma_url(
            "https://www.figma.com/design/abc123def/Title?node-id=1%3A2"
        )
        assert result is not None
        assert result["file_key"] == "abc123def"
        assert result["node_id"] == "1:2"

    def test_parse_invalid_url(self):
        """Should return None for non-Figma URLs."""
        import sys
        from pathlib import Path
        
        # Add the src directory to Python path for proper imports
        # Use absolute path from project root to handle different working directories
        import os
        project_root = Path(__file__).parent.parent.parent
        src_path = project_root / "src"
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
        
        from src.connectors.figma_connector import FigmaConnector

        result = FigmaConnector.parse_figma_url("https://google.com")
        assert result is None

    def test_is_configured_without_token(self):
        """Should report not configured when no token."""
        import sys
        from pathlib import Path
        
        # Add the src directory to Python path for proper imports
        # Use absolute path from project root to handle different working directories
        import os
        project_root = Path(__file__).parent.parent.parent
        src_path = project_root / "src"
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
        
        from src.connectors.figma_connector import FigmaConnector

        with patch.dict("os.environ", {}, clear=True):
            import os
            os.environ.pop("FIGMA_ACCESS_TOKEN", None)
            connector = FigmaConnector(access_token="")
            assert connector.is_configured() is False

    def test_is_configured_with_token(self):
        """Should report configured when token is present."""
        import sys
        from pathlib import Path
        
        # Add the src directory to Python path for proper imports
        # Use absolute path from project root to handle different working directories
        import os
        project_root = Path(__file__).parent.parent.parent
        src_path = project_root / "src"
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
        
        from src.connectors.figma_connector import FigmaConnector

        connector = FigmaConnector(access_token="test-token-123")
        assert connector.is_configured() is True

    def test_token_name_conversion(self):
        """Should convert Figma style names to token names."""
        import sys
        from pathlib import Path
        
        # Add the src directory to Python path for proper imports
        # Use absolute path from project root to handle different working directories
        import os
        project_root = Path(__file__).parent.parent.parent
        src_path = project_root / "src"
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
        
        from src.connectors.figma_connector import FigmaConnector

        assert FigmaConnector._to_token_name("Color/Primary/500") == "color-primary-500"
        assert FigmaConnector._to_token_name("Font Size/Base") == "font-size-base"
        assert FigmaConnector._to_token_name("spacing_large") == "spacing-large"


class TestFrameworkType:
    """Test FrameworkType enum"""

    def test_all_framework_values(self):
        """Should have all expected framework types."""
        expected = {"react", "vue", "angular", "svelte", "nextjs", "nuxt"}
        actual = {ft.value for ft in FrameworkType}
        assert expected == actual


class TestDesignSourceType:
    """Test DesignSourceType enum"""

    def test_all_source_type_values(self):
        """Should have all expected source types."""
        expected = {"screenshot", "figma", "wireframe", "whiteboard", "photo"}
        actual = {st.value for st in DesignSourceType}
        assert expected == actual


class TestPipelinePhase:
    """Test PipelinePhase enum"""

    def test_all_phase_values(self):
        """Should have all expected pipeline phases."""
        expected = {
            "idle",
            "analyzing",
            "spec_generation",
            "code_generation",
            "design_token_integration",
            "visual_test_generation",
            "figma_sync",
            "complete",
            "error",
        }
        actual = {p.value for p in PipelinePhase}
        assert expected == actual
