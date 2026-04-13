"""
Design-to-Code — Iterative render → diff → correct loop.

Improves visual fidelity of generated UI code by comparing the rendered
result with the original design, computing a visual diff, and auto-
correcting divergences through successive iterations.

Modules:
    - render_loop: orchestrates the render → diff → correct cycle
    - visual_diff: pixel-based and structural diff between images
    - semantic_diff: component-level semantic comparison
"""

from .render_loop import (
    RenderIteration,
    RenderLoop,
    RenderLoopConfig,
    RenderResult,
)
from .semantic_diff import (
    ComponentDiff,
    SemanticDiffAnalyzer,
    SemanticDiffResult,
)
from .visual_diff import (
    RegionDiff,
    VisualDiffConfig,
    VisualDiffEngine,
    VisualDiffResult,
)

__all__ = [
    "RenderLoop",
    "RenderLoopConfig",
    "RenderIteration",
    "RenderResult",
    "VisualDiffEngine",
    "VisualDiffConfig",
    "VisualDiffResult",
    "RegionDiff",
    "SemanticDiffAnalyzer",
    "SemanticDiffResult",
    "ComponentDiff",
]
