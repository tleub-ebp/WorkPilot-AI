#!/usr/bin/env python3
"""
Design-to-Code Pipeline Service
================================

Complete pipeline to convert visual designs (screenshots, Figma mockups,
hand-drawn wireframes, whiteboard photos) into production-ready code.

Pipeline stages:
    1. Vision Analysis — Analyze the design with Vision AI (GPT-4o, Claude Vision)
    2. Spec Generation — Generate structured spec with components, layout, interactions
    3. Code Generation — Produce pixel-perfect code adapted to the project framework
    4. Design Token Integration — Integrate existing design tokens and design system
    5. Visual Test Generation — Generate screenshot comparison tests

Usage:
    from services.design_to_code_service import DesignToCodeService

    service = DesignToCodeService(project_path="/path/to/project")
    result = await service.run_pipeline(
        image_data=base64_image,
        framework="react",
        design_system_path="src/design-system",
    )
"""

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Constants
CONTENT_TYPE_JSON = "application/json"
DEFAULT_FONT_FAMILY = "Inter, sans-serif"


# =============================================================================
# ENUMS & DATA CLASSES
# =============================================================================


class PipelinePhase(str, Enum):
    """Phases of the design-to-code pipeline."""

    IDLE = "idle"
    ANALYZING = "analyzing"
    SPEC_GENERATION = "spec_generation"
    CODE_GENERATION = "code_generation"
    DESIGN_TOKEN_INTEGRATION = "design_token_integration"
    VISUAL_TEST_GENERATION = "visual_test_generation"
    FIGMA_SYNC = "figma_sync"
    COMPLETE = "complete"
    ERROR = "error"


class FrameworkType(str, Enum):
    """Supported frontend frameworks."""

    REACT = "react"
    VUE = "vue"
    ANGULAR = "angular"
    SVELTE = "svelte"
    NEXTJS = "nextjs"
    NUXT = "nuxt"


class DesignSourceType(str, Enum):
    """Types of design sources."""

    SCREENSHOT = "screenshot"
    FIGMA = "figma"
    WIREFRAME = "wireframe"
    WHITEBOARD = "whiteboard"
    PHOTO = "photo"


@dataclass
class ComponentSpec:
    """Specification for a single UI component."""

    name: str
    type: str  # button, input, card, header, nav, etc.
    props: dict[str, Any] = field(default_factory=dict)
    children: list["ComponentSpec"] = field(default_factory=list)
    styles: dict[str, str] = field(default_factory=dict)
    interactions: list[str] = field(default_factory=list)
    accessibility: dict[str, str] = field(default_factory=dict)
    description: str = ""


@dataclass
class LayoutSpec:
    """Layout specification extracted from design."""

    type: str  # flex, grid, absolute
    direction: str = "column"  # row, column
    gap: str = "0"
    padding: str = "0"
    alignment: str = "start"
    justify: str = "start"
    responsive_breakpoints: dict[str, dict[str, str]] = field(default_factory=dict)


@dataclass
class DesignSpec:
    """Complete structured specification from design analysis."""

    components: list[ComponentSpec] = field(default_factory=list)
    layout: LayoutSpec | None = None
    color_palette: dict[str, str] = field(default_factory=dict)
    typography: dict[str, dict[str, str]] = field(default_factory=dict)
    spacing_scale: list[str] = field(default_factory=list)
    interactions: list[dict[str, Any]] = field(default_factory=list)
    responsive_notes: list[str] = field(default_factory=list)
    raw_analysis: str = ""


@dataclass
class DesignToken:
    """A design token from the project's design system."""

    name: str
    value: str
    category: str  # color, spacing, typography, shadow, border, etc.
    description: str = ""


@dataclass
class GeneratedFile:
    """A generated code file."""

    path: str
    content: str
    language: str
    description: str = ""


@dataclass
class VisualTest:
    """A generated visual test."""

    name: str
    test_code: str
    reference_screenshot: str = ""  # base64
    threshold: float = 0.95
    description: str = ""


@dataclass
class PipelineResult:
    """Complete result of the design-to-code pipeline."""

    success: bool = False
    phase: PipelinePhase = PipelinePhase.IDLE
    design_spec: DesignSpec | None = None
    generated_files: list[GeneratedFile] = field(default_factory=list)
    visual_tests: list[VisualTest] = field(default_factory=list)
    design_tokens_used: list[DesignToken] = field(default_factory=list)
    figma_sync_status: dict[str, Any] | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    tokens_used: int = 0


# =============================================================================
# DESIGN TOKEN EXTRACTOR
# =============================================================================


class DesignTokenExtractor:
    """Extracts design tokens from an existing project design system."""

    SUPPORTED_TOKEN_FILES = [
        "tokens.json",
        "design-tokens.json",
        "theme.json",
        "theme.ts",
        "theme.js",
        "variables.css",
        "variables.scss",
        "_variables.scss",
        "tailwind.config.js",
        "tailwind.config.ts",
        "stitches.config.ts",
        "styled-system.config.ts",
    ]

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.tokens: list[DesignToken] = []

    def extract(self, design_system_path: str | None = None) -> list[DesignToken]:
        """Extract design tokens from the project."""
        search_paths = []
        if design_system_path:
            search_paths.append(self.project_path / design_system_path)
        search_paths.extend(
            [
                self.project_path / "src",
                self.project_path / "styles",
                self.project_path / "theme",
                self.project_path / "design-system",
                self.project_path,
            ]
        )

        for search_path in search_paths:
            if not search_path.exists():
                continue
            self._scan_directory(search_path)

        logger.info(f"Extracted {len(self.tokens)} design tokens from project")
        return self.tokens

    def _scan_directory(self, directory: Path, depth: int = 0) -> None:
        """Recursively scan directory for token files."""
        if depth > 5:
            return
        try:
            for item in directory.iterdir():
                if item.is_file() and item.name in self.SUPPORTED_TOKEN_FILES:
                    self._parse_token_file(item)
                elif item.is_dir() and not item.name.startswith(
                    (".", "node_modules", "__")
                ):
                    self._scan_directory(item, depth + 1)
        except PermissionError:
            pass

    def _parse_token_file(self, filepath: Path) -> None:
        """Parse a design token file and extract tokens."""
        try:
            content = filepath.read_text(encoding="utf-8")
            suffix = filepath.suffix.lower()

            if suffix == ".json":
                self._parse_json_tokens(content)
            elif suffix in (".css", ".scss"):
                self._parse_css_tokens(content)
            elif suffix in (".js", ".ts"):
                self._parse_js_tokens(content)

            logger.debug(f"Parsed tokens from {filepath}")
        except Exception as e:
            logger.warning(f"Could not parse token file {filepath}: {e}")

    def _parse_json_tokens(self, content: str) -> None:
        """Parse JSON token files (Design Tokens Format)."""
        try:
            data = json.loads(content)
            self._extract_json_tokens_recursive(data, "")
        except json.JSONDecodeError:
            pass

    def _extract_json_tokens_recursive(self, data: Any, prefix: str) -> None:
        """Recursively extract tokens from nested JSON."""
        if isinstance(data, dict):
            if "$value" in data:
                category = data.get("$type", self._guess_category(prefix))
                self.tokens.append(
                    DesignToken(
                        name=prefix.strip("."),
                        value=str(data["$value"]),
                        category=category,
                        description=data.get("$description", ""),
                    )
                )
            elif "value" in data and isinstance(data["value"], (str, int, float)):
                category = data.get("type", self._guess_category(prefix))
                self.tokens.append(
                    DesignToken(
                        name=prefix.strip("."),
                        value=str(data["value"]),
                        category=str(category),
                        description=data.get("description", ""),
                    )
                )
            else:
                for key, value in data.items():
                    if not key.startswith("$"):
                        self._extract_json_tokens_recursive(value, f"{prefix}.{key}")

    def _parse_css_tokens(self, content: str) -> None:
        """Parse CSS/SCSS variable files."""
        # CSS custom properties: --color-primary: #3b82f6;
        css_var_pattern = re.compile(r"--([\w-]+)\s*:\s*([^;]+);")
        for match in css_var_pattern.finditer(content):
            name = match.group(1)
            value = match.group(2).strip()
            self.tokens.append(
                DesignToken(
                    name=f"--{name}",
                    value=value,
                    category=self._guess_category(name),
                )
            )

        # SCSS variables: $color-primary: #3b82f6;
        scss_var_pattern = re.compile(r"\$([\w-]+)\s*:\s*([^;]+);")
        for match in scss_var_pattern.finditer(content):
            name = match.group(1)
            value = match.group(2).strip()
            self.tokens.append(
                DesignToken(
                    name=f"${name}",
                    value=value,
                    category=self._guess_category(name),
                )
            )

    def _parse_js_tokens(self, content: str) -> None:
        """Parse JS/TS theme config files (Tailwind, Stitches, etc.)."""
        # Extract color definitions
        color_pattern = re.compile(
            r"['\"]?([\w.-]+)['\"]?\s*:\s*['\"]?(#[0-9a-fA-F]{3,8}|rgb[a]?\([^)]+\)|hsl[a]?\([^)]+\))['\"]?"
        )
        for match in color_pattern.finditer(content):
            name = match.group(1)
            value = match.group(2)
            self.tokens.append(
                DesignToken(
                    name=name,
                    value=value,
                    category="color",
                )
            )

    @staticmethod
    def _guess_category(name: str) -> str:
        """Guess the token category from its name."""
        name_lower = name.lower()
        if any(
            k in name_lower
            for k in (
                "color",
                "bg",
                "background",
                "text",
                "border-color",
                "fill",
                "stroke",
            )
        ):
            return "color"
        if any(
            k in name_lower
            for k in (
                "font",
                "text-size",
                "line-height",
                "letter-spacing",
                "typography",
            )
        ):
            return "typography"
        if any(
            k in name_lower for k in ("spacing", "gap", "margin", "padding", "space")
        ):
            return "spacing"
        if any(k in name_lower for k in ("shadow", "elevation")):
            return "shadow"
        if any(k in name_lower for k in ("radius", "rounded", "border-radius")):
            return "border"
        if any(k in name_lower for k in ("breakpoint", "screen")):
            return "breakpoint"
        return "other"

    def get_tokens_as_context(self) -> str:
        """Return tokens formatted for LLM context injection."""
        if not self.tokens:
            return "No design tokens found in the project."

        grouped: dict[str, list[DesignToken]] = {}
        for token in self.tokens:
            grouped.setdefault(token.category, []).append(token)

        lines = ["## Project Design Tokens\n"]
        for category, tokens in sorted(grouped.items()):
            lines.append(f"### {category.title()}")
            for t in tokens[:30]:  # Limit per category
                lines.append(f"  - `{t.name}`: {t.value}")
            if len(tokens) > 30:
                lines.append(f"  ... and {len(tokens) - 30} more")
            lines.append("")

        return "\n".join(lines)


# =============================================================================
# VISUAL TEST GENERATOR
# =============================================================================


class VisualTestGenerator:
    """Generates visual regression tests for generated components."""

    def __init__(self, framework: FrameworkType):
        self.framework = framework

    def generate_tests(
        self,
        generated_files: list[GeneratedFile],
    ) -> list[VisualTest]:
        """Generate visual tests for the generated components."""
        tests = []
        for gf in generated_files:
            if not self._is_component_file(gf):
                continue
            component_name = self._extract_component_name(gf)
            if not component_name:
                continue
            test = self._generate_visual_test(component_name)
            tests.append(test)

        logger.info(f"Generated {len(tests)} visual tests")
        return tests

    def _is_component_file(self, gf: GeneratedFile) -> bool:
        """Check if a file is a component file."""
        return gf.language in ("tsx", "jsx", "vue", "svelte")

    def _extract_component_name(self, gf: GeneratedFile) -> str | None:
        """Extract the component name from a generated file."""
        path = Path(gf.path)
        name = path.stem
        if name in ("index", "styles", "types"):
            return path.parent.name
        return name

    def _generate_visual_test(self, component_name: str) -> VisualTest:
        """Generate a visual test for a specific component."""
        if self.framework in (FrameworkType.REACT, FrameworkType.NEXTJS):
            return self._generate_react_visual_test(component_name)
        elif self.framework == FrameworkType.VUE:
            return self._generate_vue_visual_test(component_name)
        elif self.framework == FrameworkType.SVELTE:
            return self._generate_svelte_visual_test(component_name)
        else:
            return self._generate_react_visual_test(component_name)

    def _generate_react_visual_test(self, component_name: str) -> VisualTest:
        """Generate a Playwright visual test for a React component."""
        test_code = f'''import {{ test, expect }} from '@playwright/test';

test.describe('{component_name} Visual Regression', () => {{
  test('should match design screenshot', async ({{ page }}) => {{
    // Navigate to the component story or route
    await page.goto('/components/{component_name.lower()}');

    // Wait for the component to be fully rendered
    await page.waitForSelector('[data-testid="{component_name.lower()}"]');

    // Wait for fonts and images to load
    await page.waitForLoadState('networkidle');

    // Take a screenshot and compare with reference
    await expect(page).toHaveScreenshot('{component_name.lower()}.png', {{
      maxDiffPixelRatio: 0.05,
      threshold: 0.2,
    }});
  }});

  test('should match design on mobile viewport', async ({{ page }}) => {{
    await page.setViewportSize({{ width: 375, height: 812 }});
    await page.goto('/components/{component_name.lower()}');
    await page.waitForSelector('[data-testid="{component_name.lower()}"]');
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveScreenshot('{component_name.lower()}-mobile.png', {{
      maxDiffPixelRatio: 0.05,
      threshold: 0.2,
    }});
  }});

  test('should match design on tablet viewport', async ({{ page }}) => {{
    await page.setViewportSize({{ width: 768, height: 1024 }});
    await page.goto('/components/{component_name.lower()}');
    await page.waitForSelector('[data-testid="{component_name.lower()}"]');
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveScreenshot('{component_name.lower()}-tablet.png', {{
      maxDiffPixelRatio: 0.05,
      threshold: 0.2,
    }});
  }});

  test('should be accessible', async ({{ page }}) => {{
    await page.goto('/components/{component_name.lower()}');
    await page.waitForSelector('[data-testid="{component_name.lower()}"]');

    // Check for accessibility violations
    const violations = await page.evaluate(async () => {{
      const {{ default: axe }} = await import('axe-core');
      const results = await axe.run();
      return results.violations;
    }});

    expect(violations).toEqual([]);
  }});
}});
'''
        return VisualTest(
            name=f"{component_name}VisualTest",
            test_code=test_code,
            threshold=0.95,
            description=f"Visual regression tests for {component_name} component",
        )

    def _generate_vue_visual_test(self, component_name: str) -> VisualTest:
        """Generate a Playwright visual test for a Vue component."""
        test_code = f'''import {{ test, expect }} from '@playwright/test';

test.describe('{component_name} Visual Regression', () => {{
  test('should match design screenshot', async ({{ page }}) => {{
    await page.goto('/components/{component_name.lower()}');
    await page.waitForSelector('[data-testid="{component_name.lower()}"]');
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveScreenshot('{component_name.lower()}.png', {{
      maxDiffPixelRatio: 0.05,
      threshold: 0.2,
    }});
  }});

  test('should match design on mobile', async ({{ page }}) => {{
    await page.setViewportSize({{ width: 375, height: 812 }});
    await page.goto('/components/{component_name.lower()}');
    await page.waitForSelector('[data-testid="{component_name.lower()}"]');
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveScreenshot('{component_name.lower()}-mobile.png', {{
      maxDiffPixelRatio: 0.05,
    }});
  }});
}});
'''
        return VisualTest(
            name=f"{component_name}VisualTest",
            test_code=test_code,
            threshold=0.95,
            description=f"Visual regression tests for {component_name} (Vue)",
        )

    def _generate_svelte_visual_test(self, component_name: str) -> VisualTest:
        """Generate a Playwright visual test for a Svelte component."""
        test_code = f'''import {{ test, expect }} from '@playwright/test';

test.describe('{component_name} Visual Regression', () => {{
  test('should match design screenshot', async ({{ page }}) => {{
    await page.goto('/components/{component_name.lower()}');
    await page.waitForSelector('[data-testid="{component_name.lower()}"]');
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveScreenshot('{component_name.lower()}.png', {{
      maxDiffPixelRatio: 0.05,
      threshold: 0.2,
    }});
  }});
}});
'''
        return VisualTest(
            name=f"{component_name}VisualTest",
            test_code=test_code,
            threshold=0.95,
            description=f"Visual regression tests for {component_name} (Svelte)",
        )


# =============================================================================
# FRAMEWORK CODE TEMPLATES
# =============================================================================


FRAMEWORK_SYSTEM_PROMPTS = {
    FrameworkType.REACT: """You are an expert React developer. Generate production-ready React code using:
- Functional components with TypeScript
- React hooks (useState, useEffect, useCallback, useMemo)
- CSS Modules or Tailwind CSS for styling
- Proper TypeScript interfaces for all props
- data-testid attributes for testing
- Semantic HTML and ARIA attributes for accessibility
- Responsive design with mobile-first approach""",
    FrameworkType.VUE: """You are an expert Vue.js developer. Generate production-ready Vue 3 code using:
- Composition API with <script setup lang="ts">
- TypeScript for type safety
- Scoped styles or Tailwind CSS
- Proper prop definitions with TypeScript interfaces
- data-testid attributes for testing
- Semantic HTML and ARIA attributes for accessibility
- Responsive design with mobile-first approach""",
    FrameworkType.ANGULAR: """You are an expert Angular developer. Generate production-ready Angular code using:
- Standalone components with TypeScript
- Angular signals where appropriate
- SCSS for styling
- Proper Input/Output decorators with TypeScript types
- data-testid attributes for testing
- Semantic HTML and ARIA attributes for accessibility
- Responsive design with mobile-first approach""",
    FrameworkType.SVELTE: """You are an expert Svelte developer. Generate production-ready Svelte code using:
- Svelte 5 with TypeScript
- Scoped styles or Tailwind CSS
- Proper prop exports with TypeScript
- data-testid attributes for testing
- Semantic HTML and ARIA attributes for accessibility
- Responsive design with mobile-first approach""",
}


# =============================================================================
# DESIGN-TO-CODE SERVICE
# =============================================================================


class DesignToCodeService:
    """
    Main service for the Design-to-Code pipeline.

    Orchestrates the full pipeline from visual design to production-ready code:
    1. Vision AI analysis of the design image
    2. Structured spec generation (components, layout, interactions)
    3. Code generation adapted to the project's framework
    4. Design token integration from existing design system
    5. Visual regression test generation
    """

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.token_extractor = DesignTokenExtractor(self.project_path)
        self.phase = PipelinePhase.IDLE
        self.phase_callbacks: list[Any] = []

        # Configuration
        self.vision_model = os.getenv(
            "DESIGN_TO_CODE_VISION_MODEL", "claude-3-5-sonnet-20241022"
        )
        self.code_model = os.getenv(
            "DESIGN_TO_CODE_CODE_MODEL", "claude-3-5-sonnet-20241022"
        )

    def on_phase_change(self, callback) -> None:
        """Register a callback for phase changes."""
        self.phase_callbacks.append(callback)

    def _set_phase(self, phase: PipelinePhase, status: str = "") -> None:
        """Update the current pipeline phase."""
        self.phase = phase
        for cb in self.phase_callbacks:
            try:
                cb(phase, status)
            except Exception:
                pass

    async def run_pipeline(
        self,
        image_data: str,
        framework: str = "react",
        design_system_path: str | None = None,
        source_type: str = "screenshot",
        figma_file_key: str | None = None,
        figma_node_id: str | None = None,
        generate_tests: bool = True,
        custom_instructions: str = "",
    ) -> PipelineResult:
        """
        Run the complete design-to-code pipeline.

        Args:
            image_data: Base64-encoded image data (with or without data URI prefix)
            framework: Target framework (react, vue, angular, svelte)
            design_system_path: Path to the project's design system directory
            source_type: Type of design source (screenshot, figma, wireframe, etc.)
            figma_file_key: Figma file key for API sync
            figma_node_id: Figma node ID for specific component
            generate_tests: Whether to generate visual tests
            custom_instructions: Additional instructions for code generation

        Returns:
            PipelineResult with generated code, tests, and metadata
        """
        start_time = time.time()
        result = PipelineResult()
        fw = (
            FrameworkType(framework)
            if framework in FrameworkType._value2member_map_
            else FrameworkType.REACT
        )

        try:
            # Phase 1: Vision Analysis
            self._set_phase(
                PipelinePhase.ANALYZING, "Analyzing design with Vision AI..."
            )
            design_spec = await self._analyze_design(
                image_data, source_type, custom_instructions
            )
            result.design_spec = design_spec

            # Phase 2: Extract design tokens
            self._set_phase(
                PipelinePhase.DESIGN_TOKEN_INTEGRATION, "Extracting design tokens..."
            )
            tokens = self.token_extractor.extract(design_system_path)
            result.design_tokens_used = tokens

            # Phase 3: Generate structured spec
            self._set_phase(
                PipelinePhase.SPEC_GENERATION, "Generating component specification..."
            )
            enriched_spec = self._enrich_spec_with_tokens(design_spec, tokens)
            result.design_spec = enriched_spec

            # Phase 4: Generate code
            self._set_phase(
                PipelinePhase.CODE_GENERATION, "Generating production-ready code..."
            )
            generated_files = await self._generate_code(
                enriched_spec, fw, tokens, custom_instructions
            )
            result.generated_files = generated_files

            # Phase 5: Visual test generation
            if generate_tests:
                self._set_phase(
                    PipelinePhase.VISUAL_TEST_GENERATION,
                    "Generating visual regression tests...",
                )
                test_gen = VisualTestGenerator(fw)
                visual_tests = test_gen.generate_tests(generated_files)
                result.visual_tests = visual_tests

            # Phase 6: Figma sync (if configured)
            if figma_file_key:
                self._set_phase(PipelinePhase.FIGMA_SYNC, "Syncing with Figma...")
                sync_status = await self._sync_figma(
                    figma_file_key, figma_node_id, generated_files
                )
                result.figma_sync_status = sync_status

            # Complete
            self._set_phase(PipelinePhase.COMPLETE, "Pipeline complete!")
            result.success = True
            result.phase = PipelinePhase.COMPLETE

        except Exception as e:
            logger.error(f"Design-to-code pipeline failed: {e}", exc_info=True)
            self._set_phase(PipelinePhase.ERROR, str(e))
            result.phase = PipelinePhase.ERROR
            result.errors.append(str(e))

        result.duration_seconds = time.time() - start_time
        return result

    # =========================================================================
    # PHASE 1: Vision Analysis
    # =========================================================================

    async def _analyze_design(
        self,
        image_data: str,
        source_type: str,
        custom_instructions: str = "",
    ) -> DesignSpec:
        """Analyze a design image using Vision AI."""
        # Ensure proper base64 format
        if image_data.startswith("data:"):
            # Already has data URI prefix
            pass
        else:
            image_data = f"data:image/png;base64,{image_data}"

        source_context = {
            "screenshot": "This is a screenshot of an existing UI/application.",
            "figma": "This is a Figma design mockup.",
            "wireframe": "This is a hand-drawn or digital wireframe.",
            "whiteboard": "This is a photo of a whiteboard sketch.",
            "photo": "This is a photo of a physical design or sketch.",
        }

        analysis_prompt = f"""Analyze this UI design image and extract a detailed structured specification.

{source_context.get(source_type, "This is a UI design.")}

{f"Additional context: {custom_instructions}" if custom_instructions else ""}

Please provide a comprehensive JSON analysis with the following structure:
{{
  "components": [
    {{
      "name": "ComponentName",
      "type": "component_type (button, input, card, header, nav, list, etc.)",
      "props": {{"key": "value"}},
      "styles": {{"property": "value"}},
      "interactions": ["hover effect", "click action", etc.],
      "accessibility": {{"role": "button", "aria-label": "description"}},
      "children": [],
      "description": "What this component does"
    }}
  ],
  "layout": {{
    "type": "flex|grid|absolute",
    "direction": "row|column",
    "gap": "16px",
    "padding": "24px",
    "alignment": "center|start|end",
    "justify": "center|start|end|between"
  }},
  "color_palette": {{
    "primary": "#hex",
    "secondary": "#hex",
    "background": "#hex",
    "text": "#hex",
    "accent": "#hex"
  }},
  "typography": {{
    "heading": {{"fontFamily": "...", "fontSize": "...", "fontWeight": "..."}},
    "body": {{"fontFamily": "...", "fontSize": "...", "fontWeight": "..."}},
    "small": {{"fontFamily": "...", "fontSize": "...", "fontWeight": "..."}}
  }},
  "spacing_scale": ["4px", "8px", "12px", "16px", "24px", "32px", "48px"],
  "interactions": [
    {{"trigger": "click|hover|scroll", "target": "component", "action": "description"}}
  ],
  "responsive_notes": ["Mobile-first layout", "Cards stack on mobile", etc.]
}}

Be thorough and specific. Extract exact colors, sizes, and positioning from the design.
Return ONLY the JSON, no additional text."""

        # Call Vision AI
        raw_analysis = await self._call_vision_ai(image_data, analysis_prompt)

        # Parse the JSON response
        return self._parse_design_analysis(raw_analysis)

    async def _call_vision_ai(self, image_data: str, prompt: str) -> str:
        """Call Vision AI (Claude or OpenAI) for image analysis."""
        try:
            # Try Claude Vision first
            anthropic_key = os.getenv("ANTHROPIC_API_KEY")
            if anthropic_key:
                return await self._call_claude_vision(anthropic_key, image_data, prompt)

            # Fall back to OpenAI GPT-4o
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key:
                return await self._call_openai_vision(openai_key, image_data, prompt)

            # Fall back to mock analysis for development/testing
            logger.warning("No Vision AI API key found. Using mock analysis.")
            return self._mock_vision_analysis()

        except Exception as e:
            logger.error(f"Vision AI call failed: {e}")
            raise RuntimeError(f"Vision AI analysis failed: {e}")

    async def _call_claude_vision(
        self, api_key: str, image_data: str, prompt: str
    ) -> str:
        """Call Claude Vision API for image analysis."""
        import httpx

        # Extract base64 and media type from data URI
        if image_data.startswith("data:"):
            parts = image_data.split(",", 1)
            media_type = parts[0].split(":")[1].split(";")[0]
            b64_data = parts[1]
        else:
            media_type = "image/png"
            b64_data = image_data

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": CONTENT_TYPE_JSON,
                },
                json={
                    "model": self.vision_model,
                    "max_tokens": 4096,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": media_type,
                                        "data": b64_data,
                                    },
                                },
                                {"type": "text", "text": prompt},
                            ],
                        }
                    ],
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"]

    async def _call_openai_vision(
        self, api_key: str, image_data: str, prompt: str
    ) -> str:
        """Call OpenAI GPT-4o Vision API for image analysis."""
        import httpx

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": CONTENT_TYPE_JSON,
                },
                json={
                    "model": "gpt-4o",
                    "max_tokens": 4096,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": image_data, "detail": "high"},
                                },
                            ],
                        }
                    ],
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    def _mock_vision_analysis(self) -> str:
        """Return a mock analysis for development/testing when no API key is available."""
        return json.dumps(
            {
                "components": [
                    {
                        "name": "Header",
                        "type": "header",
                        "props": {},
                        "styles": {
                            "backgroundColor": "#ffffff",
                            "padding": "16px 24px",
                            "borderBottom": "1px solid #e5e7eb",
                        },
                        "interactions": [],
                        "accessibility": {"role": "banner"},
                        "children": [
                            {
                                "name": "Logo",
                                "type": "image",
                                "props": {"alt": "Logo"},
                                "styles": {"height": "32px"},
                                "interactions": [],
                                "accessibility": {},
                                "children": [],
                                "description": "Company logo",
                            },
                            {
                                "name": "Navigation",
                                "type": "nav",
                                "props": {},
                                "styles": {"display": "flex", "gap": "24px"},
                                "interactions": ["hover highlight"],
                                "accessibility": {"role": "navigation"},
                                "children": [],
                                "description": "Main navigation links",
                            },
                        ],
                        "description": "Page header with logo and navigation",
                    },
                    {
                        "name": "HeroSection",
                        "type": "section",
                        "props": {},
                        "styles": {
                            "padding": "64px 24px",
                            "textAlign": "center",
                            "backgroundColor": "#f9fafb",
                        },
                        "interactions": [],
                        "accessibility": {"role": "region", "aria-label": "Hero"},
                        "children": [],
                        "description": "Hero section with title and call to action",
                    },
                ],
                "layout": {
                    "type": "flex",
                    "direction": "column",
                    "gap": "0",
                    "padding": "0",
                    "alignment": "stretch",
                    "justify": "start",
                },
                "color_palette": {
                    "primary": "#3b82f6",
                    "secondary": "#6366f1",
                    "background": "#ffffff",
                    "text": "#111827",
                    "accent": "#10b981",
                },
                "typography": {
                    "heading": {
                        "fontFamily": DEFAULT_FONT_FAMILY,
                        "fontSize": "36px",
                        "fontWeight": "700",
                    },
                    "body": {
                        "fontFamily": DEFAULT_FONT_FAMILY,
                        "fontSize": "16px",
                        "fontWeight": "400",
                    },
                    "small": {
                        "fontFamily": DEFAULT_FONT_FAMILY,
                        "fontSize": "14px",
                        "fontWeight": "400",
                    },
                },
                "spacing_scale": [
                    "4px",
                    "8px",
                    "12px",
                    "16px",
                    "24px",
                    "32px",
                    "48px",
                    "64px",
                ],
                "interactions": [
                    {
                        "trigger": "click",
                        "target": "CTA Button",
                        "action": "Navigate to signup",
                    }
                ],
                "responsive_notes": [
                    "Mobile-first layout",
                    "Navigation collapses to hamburger on mobile",
                ],
            }
        )

    def _parse_design_analysis(self, raw_json: str) -> DesignSpec:
        """Parse the raw JSON analysis into a DesignSpec."""
        # Clean up the response - remove markdown code blocks if present
        cleaned = raw_json.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = lines[1:]  # Remove first ```json line
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse design analysis JSON: {e}")
            return DesignSpec(raw_analysis=raw_json)

        # Parse components
        components = []
        for comp_data in data.get("components", []):
            comp = ComponentSpec(
                name=comp_data.get("name", "Unknown"),
                type=comp_data.get("type", "div"),
                props=comp_data.get("props", {}),
                styles=comp_data.get("styles", {}),
                interactions=comp_data.get("interactions", []),
                accessibility=comp_data.get("accessibility", {}),
                description=comp_data.get("description", ""),
            )
            # Parse nested children
            for child_data in comp_data.get("children", []):
                child = ComponentSpec(
                    name=child_data.get("name", "Unknown"),
                    type=child_data.get("type", "div"),
                    props=child_data.get("props", {}),
                    styles=child_data.get("styles", {}),
                    interactions=child_data.get("interactions", []),
                    accessibility=child_data.get("accessibility", {}),
                    description=child_data.get("description", ""),
                )
                comp.children.append(child)
            components.append(comp)

        # Parse layout
        layout_data = data.get("layout", {})
        layout = LayoutSpec(
            type=layout_data.get("type", "flex"),
            direction=layout_data.get("direction", "column"),
            gap=layout_data.get("gap", "0"),
            padding=layout_data.get("padding", "0"),
            alignment=layout_data.get("alignment", "start"),
            justify=layout_data.get("justify", "start"),
        )

        return DesignSpec(
            components=components,
            layout=layout,
            color_palette=data.get("color_palette", {}),
            typography=data.get("typography", {}),
            spacing_scale=data.get("spacing_scale", []),
            interactions=data.get("interactions", []),
            responsive_notes=data.get("responsive_notes", []),
            raw_analysis=raw_json,
        )

    # =========================================================================
    # PHASE 2: Enrich Spec with Design Tokens
    # =========================================================================

    def _enrich_spec_with_tokens(
        self, spec: DesignSpec, tokens: list[DesignToken]
    ) -> DesignSpec:
        """Map design spec colors/typography to existing design tokens."""
        if not tokens:
            return spec

        color_tokens = {t.name: t.value for t in tokens if t.category == "color"}

        # Map extracted colors to closest design tokens
        for key, color in spec.color_palette.items():
            closest = self._find_closest_token(color, color_tokens)
            if closest:
                spec.color_palette[key] = (
                    f"var({closest})" if closest.startswith("--") else closest
                )

        return spec

    @staticmethod
    def _find_closest_token(value: str, tokens: dict[str, str]) -> str | None:
        """Find the closest matching token for a given value."""
        value_lower = value.lower().strip()
        for token_name, token_value in tokens.items():
            if token_value.lower().strip() == value_lower:
                return token_name
        return None

    # =========================================================================
    # PHASE 3: Code Generation
    # =========================================================================

    async def _generate_code(
        self,
        spec: DesignSpec,
        framework: FrameworkType,
        tokens: list[DesignToken],
        custom_instructions: str = "",
    ) -> list[GeneratedFile]:
        """Generate production-ready code from the design spec."""
        system_prompt = FRAMEWORK_SYSTEM_PROMPTS.get(
            framework, FRAMEWORK_SYSTEM_PROMPTS[FrameworkType.REACT]
        )

        token_context = self.token_extractor.get_tokens_as_context() if tokens else ""

        # Build the spec context for the LLM
        spec_context = self._spec_to_context(spec)

        generation_prompt = f"""{system_prompt}

## Task
Generate production-ready component code from the following design specification.
The code must be pixel-perfect, responsive, and follow best practices.

{spec_context}

{f"## Project Design Tokens (use these instead of raw values){chr(10)}{token_context}" if token_context else ""}

{f"## Additional Instructions{chr(10)}{custom_instructions}" if custom_instructions else ""}

## Output Format
Return a JSON array of files to generate:
```json
[
  {{
    "path": "src/components/ComponentName/ComponentName.tsx",
    "content": "... full component code ...",
    "language": "tsx",
    "description": "Main component"
  }},
  {{
    "path": "src/components/ComponentName/ComponentName.module.css",
    "content": "... styles ...",
    "language": "css",
    "description": "Component styles"
  }},
  {{
    "path": "src/components/ComponentName/index.ts",
    "content": "export {{ default }} from './ComponentName';",
    "language": "ts",
    "description": "Barrel export"
  }}
]
```

Generate ALL necessary files for a production-ready component.
Include proper TypeScript types, CSS/styles, and barrel exports.
Return ONLY the JSON array."""

        # Call the code generation model
        raw_response = await self._call_code_generation_ai(generation_prompt)
        return self._parse_generated_files(raw_response)

    def _spec_to_context(self, spec: DesignSpec) -> str:
        """Convert a DesignSpec to a human-readable context string for the LLM."""
        lines = ["## Design Specification\n"]

        if spec.layout:
            lines.append("### Layout")
            lines.append(f"- Type: {spec.layout.type}")
            lines.append(f"- Direction: {spec.layout.direction}")
            lines.append(f"- Gap: {spec.layout.gap}")
            lines.append(f"- Padding: {spec.layout.padding}")
            lines.append(f"- Alignment: {spec.layout.alignment}")
            lines.append(f"- Justify: {spec.layout.justify}")
            lines.append("")

        if spec.color_palette:
            lines.append("### Color Palette")
            for name, value in spec.color_palette.items():
                lines.append(f"- {name}: {value}")
            lines.append("")

        if spec.typography:
            lines.append("### Typography")
            for name, props in spec.typography.items():
                lines.append(f"- {name}: {json.dumps(props)}")
            lines.append("")

        if spec.components:
            lines.append("### Components")
            for comp in spec.components:
                lines.append(f"\n#### {comp.name} ({comp.type})")
                lines.append(f"Description: {comp.description}")
                if comp.styles:
                    lines.append(f"Styles: {json.dumps(comp.styles)}")
                if comp.interactions:
                    lines.append(f"Interactions: {', '.join(comp.interactions)}")
                if comp.accessibility:
                    lines.append(f"Accessibility: {json.dumps(comp.accessibility)}")
                if comp.children:
                    lines.append(
                        f"Children: {', '.join(c.name for c in comp.children)}"
                    )
            lines.append("")

        if spec.interactions:
            lines.append("### Interactions")
            for interaction in spec.interactions:
                lines.append(f"- {json.dumps(interaction)}")
            lines.append("")

        if spec.responsive_notes:
            lines.append("### Responsive Notes")
            for note in spec.responsive_notes:
                lines.append(f"- {note}")

        return "\n".join(lines)

    async def _call_code_generation_ai(self, prompt: str) -> str:
        """Call the code generation AI model."""
        try:
            import httpx

            anthropic_key = os.getenv("ANTHROPIC_API_KEY")
            if anthropic_key:
                async with httpx.AsyncClient(timeout=120) as client:
                    response = await client.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={
                            "x-api-key": anthropic_key,
                            "anthropic-version": "2023-06-01",
                            "content-type": CONTENT_TYPE_JSON,
                        },
                        json={
                            "model": self.code_model,
                            "max_tokens": 8192,
                            "messages": [{"role": "user", "content": prompt}],
                        },
                    )
                    response.raise_for_status()
                    data = response.json()
                    return data["content"][0]["text"]

            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key:
                async with httpx.AsyncClient(timeout=120) as client:
                    response = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {openai_key}",
                            "Content-Type": CONTENT_TYPE_JSON,
                        },
                        json={
                            "model": "gpt-4o",
                            "max_tokens": 8192,
                            "messages": [{"role": "user", "content": prompt}],
                        },
                    )
                    response.raise_for_status()
                    data = response.json()
                    return data["choices"][0]["message"]["content"]

            # Mock response for development
            logger.warning("No API key found for code generation. Using mock response.")
            return self._mock_code_generation()

        except Exception as e:
            logger.error(f"Code generation AI call failed: {e}")
            raise RuntimeError(f"Code generation failed: {e}")

    def _mock_code_generation(self) -> str:
        """Return mock generated code for development/testing."""
        return json.dumps(
            [
                {
                    "path": "src/components/DesignComponent/DesignComponent.tsx",
                    "content": """import React from 'react';
import styles from './DesignComponent.module.css';

interface DesignComponentProps {
  className?: string;
}

export const DesignComponent: React.FC<DesignComponentProps> = ({ className }) => {
  return (
    <div className={`${styles.container} ${className || ''}`} data-testid="design-component">
      <header className={styles.header} role="banner">
        <img src="/logo.svg" alt="Logo" className={styles.logo} />
        <nav className={styles.nav} role="navigation">
          <a href="#home">Home</a>
          <a href="#about">About</a>
          <a href="#contact">Contact</a>
        </nav>
      </header>
      <section className={styles.hero} role="region" aria-label="Hero">
        <h1>Welcome</h1>
        <p>Your amazing product description here.</p>
        <button className={styles.cta}>Get Started</button>
      </section>
    </div>
  );
};

export default DesignComponent;
""",
                    "language": "tsx",
                    "description": "Main component generated from design",
                },
                {
                    "path": "src/components/DesignComponent/DesignComponent.module.css",
                    "content": """.container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background-color: #ffffff;
  border-bottom: 1px solid #e5e7eb;
}

.logo {
  height: 32px;
}

.nav {
  display: flex;
  gap: 24px;
}

.nav a {
  color: #111827;
  text-decoration: none;
  font-weight: 500;
}

.nav a:hover {
  color: #3b82f6;
}

.hero {
  padding: 64px 24px;
  text-align: center;
  background-color: #f9fafb;
}

.hero h1 {
  font-size: 36px;
  font-weight: 700;
  color: #111827;
  margin-bottom: 16px;
}

.hero p {
  font-size: 18px;
  color: #6b7280;
  margin-bottom: 32px;
}

.cta {
  padding: 12px 32px;
  background-color: #3b82f6;
  color: #ffffff;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s;
}

.cta:hover {
  background-color: #2563eb;
}

@media (max-width: 768px) {
  .header {
    flex-direction: column;
    gap: 16px;
  }

  .nav {
    gap: 16px;
  }

  .hero {
    padding: 32px 16px;
  }

  .hero h1 {
    font-size: 28px;
  }
}
""",
                    "language": "css",
                    "description": "Component styles",
                },
                {
                    "path": "src/components/DesignComponent/index.ts",
                    "content": "export { DesignComponent, default } from './DesignComponent';\n",
                    "language": "ts",
                    "description": "Barrel export",
                },
            ]
        )

    def _parse_generated_files(self, raw_response: str) -> list[GeneratedFile]:
        """Parse the generated files from the AI response."""
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)

        try:
            files_data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse generated files JSON: {e}")
            return [
                GeneratedFile(
                    path="generated_output.txt",
                    content=raw_response,
                    language="text",
                    description="Raw AI output (JSON parsing failed)",
                )
            ]

        files = []
        for fd in files_data:
            files.append(
                GeneratedFile(
                    path=fd.get("path", "unknown"),
                    content=fd.get("content", ""),
                    language=fd.get("language", "text"),
                    description=fd.get("description", ""),
                )
            )
        return files

    # =========================================================================
    # PHASE 5: Figma Sync
    # =========================================================================

    async def _sync_figma(
        self,
        file_key: str,
        node_id: str | None,
        generated_files: list[GeneratedFile],
    ) -> dict[str, Any]:
        """Sync generated code metadata back to Figma (bidirectional)."""
        try:
            from src.connectors.figma_connector import FigmaConnector

            figma_token = os.getenv("FIGMA_ACCESS_TOKEN")
            if not figma_token:
                return {"status": "skipped", "reason": "No FIGMA_ACCESS_TOKEN set"}

            connector = FigmaConnector(access_token=figma_token)

            # Post a comment on the Figma node with the generated code info
            component_names = []
            for gf in generated_files:
                if gf.language in ("tsx", "jsx", "vue", "svelte"):
                    name = Path(gf.path).stem
                    if name not in ("index", "styles", "types"):
                        component_names.append(name)

            comment = (
                f"🤖 Code generated by WorkPilot Design-to-Code Pipeline\n\n"
                f"Components: {', '.join(component_names)}\n"
                f"Files generated: {len(generated_files)}\n"
            )

            await connector.post_comment(file_key, comment, node_id)

            return {
                "status": "synced",
                "file_key": file_key,
                "node_id": node_id,
                "components_synced": component_names,
            }

        except ImportError:
            return {"status": "skipped", "reason": "Figma connector not available"}
        except Exception as e:
            logger.warning(f"Figma sync failed: {e}")
            return {"status": "error", "error": str(e)}


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================


async def run_design_to_code_pipeline(
    project_path: str,
    image_data: str,
    framework: str = "react",
    design_system_path: str | None = None,
    source_type: str = "screenshot",
    figma_file_key: str | None = None,
    generate_tests: bool = True,
    custom_instructions: str = "",
) -> dict[str, Any]:
    """
    Convenience function to run the complete design-to-code pipeline.

    Returns a serializable dictionary of the pipeline result.
    """
    service = DesignToCodeService(project_path)
    result = await service.run_pipeline(
        image_data=image_data,
        framework=framework,
        design_system_path=design_system_path,
        source_type=source_type,
        figma_file_key=figma_file_key,
        generate_tests=generate_tests,
        custom_instructions=custom_instructions,
    )

    design_spec = result.design_spec

    # Extract design spec properties to avoid nested conditionals
    color_palette = design_spec.color_palette if design_spec else {}
    typography = design_spec.typography if design_spec else {}

    return {
        "success": result.success,
        "phase": result.phase.value,
        "design_spec": {
            "components": [
                {
                    "name": c.name,
                    "type": c.type,
                    "description": c.description,
                    "children": [
                        {"name": ch.name, "type": ch.type} for ch in c.children
                    ],
                }
                for c in (design_spec.components if design_spec else [])
            ],
            "color_palette": color_palette,
            "typography": typography,
        }
        if design_spec
        else None,
        "generated_files": [
            {
                "path": f.path,
                "content": f.content,
                "language": f.language,
                "description": f.description,
            }
            for f in result.generated_files
        ],
        "visual_tests": [
            {
                "name": t.name,
                "test_code": t.test_code,
                "threshold": t.threshold,
                "description": t.description,
            }
            for t in result.visual_tests
        ],
        "design_tokens_used": [
            {"name": t.name, "value": t.value, "category": t.category}
            for t in result.design_tokens_used
        ],
        "figma_sync_status": result.figma_sync_status,
        "errors": result.errors,
        "warnings": result.warnings,
        "duration_seconds": result.duration_seconds,
        "tokens_used": result.tokens_used,
    }
