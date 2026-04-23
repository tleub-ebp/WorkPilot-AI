"""
Tests for Design-to-Code — Iterative render → diff → correct loop.

Covers: VisualDiffEngine, SemanticDiffAnalyzer, RenderLoop.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "apps" / "backend"))

from design_to_code.render_loop import (
    RenderIteration,
    RenderLoop,
    RenderLoopConfig,
    RenderResult,
)
from design_to_code.semantic_diff import (
    ComponentDiff,
    ComponentSpec,
    ComponentType,
    DiffAction,
    SemanticDiffAnalyzer,
    SemanticDiffResult,
)
from design_to_code.visual_diff import (
    DiffSeverity,
    PixelGrid,
    RegionDiff,
    VisualDiffConfig,
    VisualDiffEngine,
    VisualDiffResult,
)

# =========================================================================
# Helpers
# =========================================================================


def _make_grid(width: int, height: int, color: tuple[int, int, int] = (255, 255, 255)) -> PixelGrid:
    """Create a solid-color pixel grid."""
    return [[color for _ in range(width)] for _ in range(height)]


def _make_grid_with_region(
    width: int, height: int,
    base: tuple[int, int, int] = (255, 255, 255),
    region_color: tuple[int, int, int] = (0, 0, 0),
    region_x: int = 0, region_y: int = 0,
    region_w: int = 10, region_h: int = 10,
) -> PixelGrid:
    """Create a grid with a colored region."""
    grid = _make_grid(width, height, base)
    for y in range(region_y, min(region_y + region_h, height)):
        for x in range(region_x, min(region_x + region_w, width)):
            grid[y][x] = region_color
    return grid


# =========================================================================
# VisualDiffEngine tests
# =========================================================================


class TestVisualDiffEngine:
    def test_identical_images(self):
        engine = VisualDiffEngine()
        grid = _make_grid(100, 100)
        result = engine.compare(grid, grid, 100, 100)
        assert result.overall_similarity == 1.0
        assert result.passed

    def test_completely_different(self):
        engine = VisualDiffEngine(VisualDiffConfig(tolerance_per_pixel=0))
        white = _make_grid(100, 100, (255, 255, 255))
        black = _make_grid(100, 100, (0, 0, 0))
        result = engine.compare(white, black, 100, 100)
        assert result.overall_similarity == 0.0
        assert not result.passed

    def test_within_tolerance(self):
        engine = VisualDiffEngine(VisualDiffConfig(tolerance_per_pixel=10))
        grid1 = _make_grid(50, 50, (100, 100, 100))
        grid2 = _make_grid(50, 50, (105, 105, 105))
        result = engine.compare(grid1, grid2, 50, 50)
        assert result.overall_similarity == 1.0

    def test_partial_diff(self):
        engine = VisualDiffEngine(VisualDiffConfig(tolerance_per_pixel=0))
        design = _make_grid(100, 100, (255, 255, 255))
        rendered = _make_grid_with_region(100, 100, region_color=(0, 0, 0), region_w=10, region_h=10)
        result = engine.compare(design, rendered, 100, 100)
        assert 0.0 < result.overall_similarity < 1.0
        assert result.diff_pixel_count == 100  # 10x10 region

    def test_empty_images(self):
        engine = VisualDiffEngine()
        result = engine.compare([], [], 0, 0)
        assert result.overall_similarity == 0.0
        assert not result.passed

    def test_region_diffs(self):
        engine = VisualDiffEngine()
        grid = _make_grid(100, 100)
        result = engine.compare(grid, grid, 100, 100)
        assert len(result.regions) > 0
        assert all(r.severity == DiffSeverity.NONE for r in result.regions)

    def test_compare_dimensions_match(self):
        engine = VisualDiffEngine()
        result = engine.compare_dimensions(1280, 720, 1280, 720)
        assert result["match"]

    def test_compare_dimensions_mismatch(self):
        engine = VisualDiffEngine()
        result = engine.compare_dimensions(1280, 720, 1024, 768)
        assert not result["match"]
        assert result["width_diff"] == 256

    def test_suggestions_for_major_diff(self):
        engine = VisualDiffEngine(VisualDiffConfig(tolerance_per_pixel=0))
        white = _make_grid(100, 100, (255, 255, 255))
        black = _make_grid(100, 100, (0, 0, 0))
        result = engine.compare(white, black, 100, 100)
        assert len(result.suggestions) > 0

    def test_custom_config(self):
        config = VisualDiffConfig(
            similarity_threshold=0.99,
            tolerance_per_pixel=5,
            regions=["header", "content"],
        )
        engine = VisualDiffEngine(config)
        assert engine.config.similarity_threshold == 0.99

    def test_region_diff_percentage(self):
        rd = RegionDiff(region_name="test", pixel_diff_count=50, total_pixels=200)
        assert rd.diff_percentage == 25.0

    def test_region_diff_zero_pixels(self):
        rd = RegionDiff(region_name="test", pixel_diff_count=0, total_pixels=0)
        assert rd.diff_percentage == 0.0


# =========================================================================
# SemanticDiffAnalyzer tests
# =========================================================================


class TestSemanticDiffAnalyzer:
    def test_perfect_match(self):
        analyzer = SemanticDiffAnalyzer()
        design = [
            ComponentSpec(id="btn1", component_type=ComponentType.BUTTON, text="Submit", region="content"),
        ]
        code = [
            ComponentSpec(id="btn1", component_type=ComponentType.BUTTON, text="Submit", region="content"),
        ]
        result = analyzer.compare(design, code)
        assert result.matched == 1
        assert result.fidelity_score == 1.0

    def test_missing_component(self):
        analyzer = SemanticDiffAnalyzer()
        design = [
            ComponentSpec(id="btn1", component_type=ComponentType.BUTTON, text="Submit"),
            ComponentSpec(id="icon1", component_type=ComponentType.ICON, text="search"),
        ]
        code = [
            ComponentSpec(id="btn1", component_type=ComponentType.BUTTON, text="Submit"),
        ]
        result = analyzer.compare(design, code)
        assert result.missing == 1
        assert result.fidelity_score < 1.0

    def test_extra_component(self):
        analyzer = SemanticDiffAnalyzer()
        design = [
            ComponentSpec(id="btn1", component_type=ComponentType.BUTTON, text="Submit"),
        ]
        code = [
            ComponentSpec(id="btn1", component_type=ComponentType.BUTTON, text="Submit"),
            ComponentSpec(id="extra1", component_type=ComponentType.TEXT, text="Debug info"),
        ]
        result = analyzer.compare(design, code)
        assert result.extra == 1

    def test_content_mismatch(self):
        analyzer = SemanticDiffAnalyzer()
        design = [
            ComponentSpec(id="btn1", component_type=ComponentType.BUTTON, text="Submit"),
        ]
        code = [
            ComponentSpec(id="btn1", component_type=ComponentType.BUTTON, text="Send"),
        ]
        result = analyzer.compare(design, code)
        assert result.mismatched == 1
        assert any(d.action == DiffAction.CONTENT_MISMATCH for d in result.diffs)

    def test_style_mismatch(self):
        analyzer = SemanticDiffAnalyzer()
        design = [
            ComponentSpec(
                id="btn1", component_type=ComponentType.BUTTON, text="OK",
                styles={"background": "blue", "color": "white"},
            ),
        ]
        code = [
            ComponentSpec(
                id="btn1", component_type=ComponentType.BUTTON, text="OK",
                styles={"background": "red", "color": "white"},
            ),
        ]
        result = analyzer.compare(design, code)
        assert any(d.action == DiffAction.STYLE_MISMATCH for d in result.diffs)

    def test_position_off(self):
        analyzer = SemanticDiffAnalyzer(position_tolerance=5.0)
        design = [
            ComponentSpec(id="btn1", component_type=ComponentType.BUTTON, text="OK", x=100, y=200),
        ]
        code = [
            ComponentSpec(id="btn1", component_type=ComponentType.BUTTON, text="OK", x=150, y=200),
        ]
        result = analyzer.compare(design, code)
        assert any(d.action == DiffAction.POSITION_OFF for d in result.diffs)

    def test_correction_hints(self):
        analyzer = SemanticDiffAnalyzer()
        design = [
            ComponentSpec(id="icon1", component_type=ComponentType.ICON, text="search", region="header"),
        ]
        code: list[ComponentSpec] = []
        result = analyzer.compare(design, code)
        assert len(result.correction_hints) > 0
        assert "search" in result.correction_hints[0]

    def test_empty_design(self):
        analyzer = SemanticDiffAnalyzer()
        result = analyzer.compare([], [
            ComponentSpec(id="btn1", component_type=ComponentType.BUTTON),
        ])
        assert result.extra == 1
        assert result.total_components == 0

    def test_empty_both(self):
        analyzer = SemanticDiffAnalyzer()
        result = analyzer.compare([], [])
        assert result.fidelity_score == 1.0
        assert len(result.diffs) == 0

    def test_issues_property(self):
        analyzer = SemanticDiffAnalyzer()
        design = [ComponentSpec(id="a", component_type=ComponentType.BUTTON, text="A")]
        code: list[ComponentSpec] = []
        result = analyzer.compare(design, code)
        assert len(result.issues) == 1

    def test_multiple_components(self):
        analyzer = SemanticDiffAnalyzer()
        design = [
            ComponentSpec(id="h1", component_type=ComponentType.HEADER, text="Title", region="header"),
            ComponentSpec(id="btn1", component_type=ComponentType.BUTTON, text="Save", region="content"),
            ComponentSpec(id="input1", component_type=ComponentType.INPUT, text="", region="content"),
            ComponentSpec(id="footer1", component_type=ComponentType.FOOTER, text="© 2025", region="footer"),
        ]
        code = [
            ComponentSpec(id="h1", component_type=ComponentType.HEADER, text="Title", region="header"),
            ComponentSpec(id="btn1", component_type=ComponentType.BUTTON, text="Save", region="content"),
            ComponentSpec(id="input1", component_type=ComponentType.INPUT, text="", region="content"),
            ComponentSpec(id="footer1", component_type=ComponentType.FOOTER, text="© 2025", region="footer"),
        ]
        result = analyzer.compare(design, code)
        assert result.fidelity_score == 1.0
        assert result.missing == 0


# =========================================================================
# RenderLoop tests
# =========================================================================


class TestRenderLoop:
    def _mock_render(self, code: str) -> RenderResult:
        """Mock render function that returns a white grid."""
        return RenderResult(
            pixels=_make_grid(100, 100, (255, 255, 255)),
            components=[],
            width=100, height=100,
            code=code,
        )

    def _mock_correct(self, code: str, suggestions: list[str]) -> str:
        """Mock correction function."""
        return code + "\n// corrected"

    def test_passes_immediately(self):
        loop = RenderLoop(RenderLoopConfig(max_iterations=3, target_similarity=0.95))
        design = _make_grid(100, 100, (255, 255, 255))
        iterations = loop.run(
            design_pixels=design,
            design_components=[],
            design_width=100, design_height=100,
            render_fn=self._mock_render,
            correct_fn=self._mock_correct,
            initial_code="<div>Hello</div>",
        )
        assert len(iterations) == 1
        assert iterations[0].passed

    def test_iterates_on_failure(self):
        call_count = [0]

        def render_fn(code: str) -> RenderResult:
            call_count[0] += 1
            # First render: black (bad), subsequent: white (good)
            if call_count[0] == 1:
                return RenderResult(
                    pixels=_make_grid(100, 100, (0, 0, 0)),
                    components=[], width=100, height=100, code=code,
                )
            return RenderResult(
                pixels=_make_grid(100, 100, (255, 255, 255)),
                components=[], width=100, height=100, code=code,
            )

        loop = RenderLoop(RenderLoopConfig(
            max_iterations=5,
            target_similarity=0.95,
            visual_diff_config=VisualDiffConfig(tolerance_per_pixel=0),
        ))
        design = _make_grid(100, 100, (255, 255, 255))
        iterations = loop.run(
            design_pixels=design,
            design_components=[],
            design_width=100, design_height=100,
            render_fn=render_fn,
            correct_fn=self._mock_correct,
            initial_code="<div>Hello</div>",
        )
        assert len(iterations) == 2
        assert not iterations[0].passed
        assert iterations[1].passed

    def test_max_iterations_respected(self):
        def bad_render(code: str) -> RenderResult:
            return RenderResult(
                pixels=_make_grid(100, 100, (0, 0, 0)),
                components=[], width=100, height=100, code=code,
            )

        loop = RenderLoop(RenderLoopConfig(
            max_iterations=3,
            visual_diff_config=VisualDiffConfig(tolerance_per_pixel=0),
        ))
        design = _make_grid(100, 100, (255, 255, 255))
        iterations = loop.run(
            design_pixels=design,
            design_components=[],
            design_width=100, design_height=100,
            render_fn=bad_render,
            correct_fn=self._mock_correct,
        )
        assert len(iterations) == 3
        assert not iterations[-1].passed

    def test_run_single(self):
        loop = RenderLoop()
        design = _make_grid(100, 100, (255, 255, 255))
        rendered = RenderResult(
            pixels=_make_grid(100, 100, (255, 255, 255)),
            components=[], width=100, height=100, code="<div/>",
        )
        iteration = loop.run_single(design, rendered, 100, 100)
        assert iteration.passed

    def test_run_single_with_semantic(self):
        loop = RenderLoop(RenderLoopConfig(enable_semantic_diff=True))
        design_pixels = _make_grid(100, 100)
        design_comps = [
            ComponentSpec(id="btn1", component_type=ComponentType.BUTTON, text="OK"),
        ]
        rendered = RenderResult(
            pixels=_make_grid(100, 100),
            components=[
                ComponentSpec(id="btn1", component_type=ComponentType.BUTTON, text="OK"),
            ],
            width=100, height=100, code="<button>OK</button>",
        )
        iteration = loop.run_single(design_pixels, rendered, 100, 100, design_comps)
        assert iteration.semantic_diff is not None
        assert iteration.semantic_diff.fidelity_score == 1.0

    def test_time_budget(self):
        loop = RenderLoop(RenderLoopConfig(
            max_iterations=100,
            visual_budget_seconds=0.0,  # Immediately exhausted
        ))
        design = _make_grid(100, 100)
        iterations = loop.run(
            design_pixels=design,
            design_components=[],
            design_width=100, design_height=100,
            render_fn=self._mock_render,
            correct_fn=self._mock_correct,
        )
        # Should stop early due to budget
        assert len(iterations) <= 1

    def test_config_accessible(self):
        config = RenderLoopConfig(max_iterations=7)
        loop = RenderLoop(config)
        assert loop.config.max_iterations == 7


# =========================================================================
# Integration tests
# =========================================================================


class TestDesignToCodeIntegration:
    def test_full_visual_and_semantic_loop(self):
        design_pixels = _make_grid(200, 200, (240, 240, 240))
        design_comps = [
            ComponentSpec(id="h1", component_type=ComponentType.HEADER, text="Welcome", region="header"),
            ComponentSpec(id="btn1", component_type=ComponentType.BUTTON, text="Start", region="content"),
        ]

        call_count = [0]

        def render_fn(code: str) -> RenderResult:
            call_count[0] += 1
            if call_count[0] == 1:
                # First render: slightly off
                return RenderResult(
                    pixels=_make_grid(200, 200, (200, 200, 200)),
                    components=[
                        ComponentSpec(id="h1", component_type=ComponentType.HEADER, text="Welcome", region="header"),
                    ],
                    width=200, height=200, code=code,
                )
            # Second render: perfect match
            return RenderResult(
                pixels=_make_grid(200, 200, (240, 240, 240)),
                components=design_comps,
                width=200, height=200, code=code,
            )

        def correct_fn(code: str, suggestions: list[str]) -> str:
            return code + "\n// fixed"

        loop = RenderLoop(RenderLoopConfig(
            max_iterations=5,
            target_similarity=0.95,
            enable_semantic_diff=True,
        ))

        iterations = loop.run(
            design_pixels=design_pixels,
            design_components=design_comps,
            design_width=200, design_height=200,
            render_fn=render_fn,
            correct_fn=correct_fn,
            initial_code="<div>Hello</div>",
        )

        assert len(iterations) >= 1
        # At some point it should pass
        assert any(it.passed for it in iterations)
