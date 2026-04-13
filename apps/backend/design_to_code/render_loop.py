"""
Render Loop — Orchestrates the render → diff → correct cycle.

Manages multiple iterations of rendering, diffing, and correcting
until the visual fidelity score meets the threshold or the maximum
iteration count is reached.

The actual rendering and correction are handled by pluggable
callbacks, making this engine provider-agnostic.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from .semantic_diff import ComponentSpec, SemanticDiffAnalyzer, SemanticDiffResult
from .visual_diff import PixelGrid, VisualDiffConfig, VisualDiffEngine, VisualDiffResult

logger = logging.getLogger(__name__)


@dataclass
class RenderLoopConfig:
    """Configuration for the render loop."""

    max_iterations: int = 5
    target_similarity: float = 0.95
    visual_diff_config: VisualDiffConfig | None = None
    enable_semantic_diff: bool = True
    visual_budget_seconds: float = 120.0  # Max time for all iterations


@dataclass
class RenderResult:
    """Result of a single render operation."""

    pixels: PixelGrid = field(default_factory=list)
    components: list[ComponentSpec] = field(default_factory=list)
    width: int = 0
    height: int = 0
    code: str = ""
    render_time_ms: float = 0.0


@dataclass
class RenderIteration:
    """Data for a single iteration of the render loop."""

    iteration: int
    visual_diff: VisualDiffResult | None = None
    semantic_diff: SemanticDiffResult | None = None
    corrections_applied: list[str] = field(default_factory=list)
    code_before: str = ""
    code_after: str = ""
    duration_seconds: float = 0.0
    passed: bool = False


class RenderLoop:
    """Orchestrate the iterative render → diff → correct cycle.

    Usage::

        loop = RenderLoop(config=RenderLoopConfig(max_iterations=3))
        iterations = loop.run(
            design_pixels=design_img,
            design_components=design_comps,
            design_width=1280, design_height=720,
            render_fn=my_render_function,
            correct_fn=my_correction_function,
        )
        final = iterations[-1]
        print(f"Final similarity: {final.visual_diff.overall_similarity:.1%}")
    """

    def __init__(self, config: RenderLoopConfig | None = None) -> None:
        self._config = config or RenderLoopConfig()
        diff_config = self._config.visual_diff_config or VisualDiffConfig(
            similarity_threshold=self._config.target_similarity
        )
        self._visual_engine = VisualDiffEngine(diff_config)
        self._semantic_engine = SemanticDiffAnalyzer()

    @property
    def config(self) -> RenderLoopConfig:
        return self._config

    def run(
        self,
        design_pixels: PixelGrid,
        design_components: list[ComponentSpec],
        design_width: int,
        design_height: int,
        render_fn: Callable[[str], RenderResult],
        correct_fn: Callable[[str, list[str]], str],
        initial_code: str = "",
    ) -> list[RenderIteration]:
        """Run the iterative render → diff → correct cycle.

        Args:
            design_pixels: Original design mockup pixel grid.
            design_components: Component specs from the design.
            design_width: Design width in pixels.
            design_height: Design height in pixels.
            render_fn: Callable that takes code and returns RenderResult.
            correct_fn: Callable that takes (code, suggestions) and returns corrected code.
            initial_code: Starting code to render.

        Returns:
            List of RenderIteration records, one per iteration.
        """
        iterations: list[RenderIteration] = []
        current_code = initial_code
        budget_start = time.time()

        for i in range(self._config.max_iterations):
            iter_start = time.time()

            # Check time budget
            elapsed = time.time() - budget_start
            if elapsed > self._config.visual_budget_seconds:
                logger.warning(
                    "Visual budget exhausted after %d iterations (%.1fs)",
                    i,
                    elapsed,
                )
                break

            # 1. Render
            render_result = render_fn(current_code)

            # 2. Visual diff
            visual_diff = self._visual_engine.compare(
                design_pixels,
                render_result.pixels,
                design_width,
                design_height,
            )
            visual_diff.iteration = i + 1

            # 3. Semantic diff (optional)
            semantic_diff = None
            if self._config.enable_semantic_diff and design_components:
                semantic_diff = self._semantic_engine.compare(
                    design_components, render_result.components
                )

            # 4. Collect suggestions
            suggestions = list(visual_diff.suggestions)
            if semantic_diff:
                suggestions.extend(semantic_diff.correction_hints)

            passed = visual_diff.passed
            if (
                semantic_diff
                and semantic_diff.fidelity_score < self._config.target_similarity
            ):
                passed = False

            iteration = RenderIteration(
                iteration=i + 1,
                visual_diff=visual_diff,
                semantic_diff=semantic_diff,
                corrections_applied=suggestions,
                code_before=current_code,
                passed=passed,
                duration_seconds=time.time() - iter_start,
            )

            if passed:
                iteration.code_after = current_code
                iterations.append(iteration)
                logger.info("Render loop passed at iteration %d", i + 1)
                break

            # 5. Correct
            corrected_code = correct_fn(current_code, suggestions)
            iteration.code_after = corrected_code
            iterations.append(iteration)

            current_code = corrected_code

        return iterations

    def run_single(
        self,
        design_pixels: PixelGrid,
        rendered: RenderResult,
        design_width: int,
        design_height: int,
        design_components: list[ComponentSpec] | None = None,
    ) -> RenderIteration:
        """Run a single diff pass (no correction loop)."""
        visual_diff = self._visual_engine.compare(
            design_pixels, rendered.pixels, design_width, design_height
        )

        semantic_diff = None
        if design_components and self._config.enable_semantic_diff:
            semantic_diff = self._semantic_engine.compare(
                design_components, rendered.components
            )

        passed = visual_diff.passed
        if (
            semantic_diff
            and semantic_diff.fidelity_score < self._config.target_similarity
        ):
            passed = False

        return RenderIteration(
            iteration=1,
            visual_diff=visual_diff,
            semantic_diff=semantic_diff,
            code_before=rendered.code,
            code_after=rendered.code,
            passed=passed,
        )
