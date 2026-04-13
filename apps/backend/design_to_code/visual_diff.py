"""
Visual Diff Engine — Pixel-based and structural diff between images.

Computes similarity scores between a design mockup and a rendered
screenshot.  Works with raw pixel data (list-of-lists) when Pillow
is unavailable, or with real images when it is.

Provides:
  - Overall similarity percentage
  - Per-region breakdown (header, content, footer, sidebar)
  - Highlighted diff regions

100% algorithmic — no LLM dependency. Vision-capable models can be
plugged in externally for deeper analysis.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class VisualDiffConfig:
    """Configuration for the visual diff engine."""

    similarity_threshold: float = 0.95  # 95% considered "pass"
    max_iterations: int = 5
    regions: list[str] = field(
        default_factory=lambda: ["header", "content", "footer", "sidebar"]
    )
    tolerance_per_pixel: int = 10  # RGB channel tolerance


class DiffSeverity(str, Enum):
    NONE = "none"
    MINOR = "minor"      # < 5% different
    MODERATE = "moderate"  # 5-15% different
    MAJOR = "major"       # > 15% different


@dataclass
class RegionDiff:
    """Diff result for a specific region of the UI."""

    region_name: str
    similarity: float = 1.0
    pixel_diff_count: int = 0
    total_pixels: int = 0
    severity: DiffSeverity = DiffSeverity.NONE
    description: str = ""

    @property
    def diff_percentage(self) -> float:
        if self.total_pixels == 0:
            return 0.0
        return (self.pixel_diff_count / self.total_pixels) * 100


@dataclass
class VisualDiffResult:
    """Complete visual diff result."""

    overall_similarity: float = 1.0
    passed: bool = True
    regions: list[RegionDiff] = field(default_factory=list)
    total_pixels: int = 0
    diff_pixel_count: int = 0
    iteration: int = 0
    suggestions: list[str] = field(default_factory=list)


PixelGrid = list[list[tuple[int, int, int]]]


class VisualDiffEngine:
    """Compare design mockup with rendered screenshot.

    Uses pixel-level comparison with configurable tolerance.  Supports
    region-based breakdown for targeted corrections.

    Usage::

        engine = VisualDiffEngine()
        result = engine.compare(design_pixels, render_pixels, width=800, height=600)
        if not result.passed:
            for region in result.regions:
                print(f"{region.region_name}: {region.similarity:.1%}")
    """

    def __init__(self, config: VisualDiffConfig | None = None) -> None:
        self._config = config or VisualDiffConfig()

    @property
    def config(self) -> VisualDiffConfig:
        return self._config

    def compare(
        self,
        design: PixelGrid,
        rendered: PixelGrid,
        width: int,
        height: int,
    ) -> VisualDiffResult:
        """Compare two pixel grids and return diff result.

        Each pixel grid is ``height`` rows of ``width`` (R, G, B) tuples.
        """
        if not design or not rendered:
            return VisualDiffResult(
                overall_similarity=0.0, passed=False,
                suggestions=["One or both images are empty."],
            )

        total_pixels = width * height
        diff_count = 0
        tolerance = self._config.tolerance_per_pixel

        for y in range(min(height, len(design), len(rendered))):
            for x in range(min(width, len(design[y]), len(rendered[y]))):
                if not self._pixels_match(design[y][x], rendered[y][x], tolerance):
                    diff_count += 1

        similarity = 1.0 - (diff_count / max(total_pixels, 1))

        # Compute per-region diffs
        regions = self._compute_regions(design, rendered, width, height, tolerance)

        suggestions = self._generate_suggestions(regions)

        return VisualDiffResult(
            overall_similarity=similarity,
            passed=similarity >= self._config.similarity_threshold,
            regions=regions,
            total_pixels=total_pixels,
            diff_pixel_count=diff_count,
            suggestions=suggestions,
        )

    def compare_dimensions(
        self, design_w: int, design_h: int, render_w: int, render_h: int
    ) -> dict[str, Any]:
        """Quick check if dimensions match."""
        return {
            "match": design_w == render_w and design_h == render_h,
            "design": {"width": design_w, "height": design_h},
            "rendered": {"width": render_w, "height": render_h},
            "width_diff": abs(design_w - render_w),
            "height_diff": abs(design_h - render_h),
        }

    def _compute_regions(
        self,
        design: PixelGrid,
        rendered: PixelGrid,
        width: int,
        height: int,
        tolerance: int,
    ) -> list[RegionDiff]:
        """Split image into regions and compute per-region diffs."""
        regions: list[RegionDiff] = []

        # Simple region split: header (top 15%), content (middle 60%),
        # footer (bottom 15%), sidebar (left 20% of content area)
        region_bounds = {
            "header": (0, 0, width, int(height * 0.15)),
            "content": (int(width * 0.20), int(height * 0.15), width, int(height * 0.85)),
            "footer": (0, int(height * 0.85), width, height),
            "sidebar": (0, int(height * 0.15), int(width * 0.20), int(height * 0.85)),
        }

        for name in self._config.regions:
            bounds = region_bounds.get(name)
            if not bounds:
                continue
            x1, y1, x2, y2 = bounds
            total = 0
            diff = 0
            for y in range(y1, min(y2, len(design), len(rendered))):
                for x in range(x1, min(x2, len(design[y]) if y < len(design) else 0,
                                       len(rendered[y]) if y < len(rendered) else 0)):
                    total += 1
                    if not self._pixels_match(design[y][x], rendered[y][x], tolerance):
                        diff += 1

            sim = 1.0 - (diff / max(total, 1))
            severity = self._classify_severity(sim)

            regions.append(RegionDiff(
                region_name=name,
                similarity=sim,
                pixel_diff_count=diff,
                total_pixels=total,
                severity=severity,
                description=self._severity_description(name, severity),
            ))

        return regions

    @staticmethod
    def _pixels_match(
        p1: tuple[int, int, int], p2: tuple[int, int, int], tolerance: int
    ) -> bool:
        """Check if two RGB pixels are within tolerance."""
        return (
            abs(p1[0] - p2[0]) <= tolerance
            and abs(p1[1] - p2[1]) <= tolerance
            and abs(p1[2] - p2[2]) <= tolerance
        )

    @staticmethod
    def _classify_severity(similarity: float) -> DiffSeverity:
        if similarity >= 0.95:
            return DiffSeverity.NONE
        if similarity >= 0.85:
            return DiffSeverity.MINOR
        if similarity >= 0.70:
            return DiffSeverity.MODERATE
        return DiffSeverity.MAJOR

    @staticmethod
    def _severity_description(region: str, severity: DiffSeverity) -> str:
        if severity == DiffSeverity.NONE:
            return f"{region}: matches design"
        if severity == DiffSeverity.MINOR:
            return f"{region}: minor differences (spacing/colors)"
        if severity == DiffSeverity.MODERATE:
            return f"{region}: moderate divergence, needs correction"
        return f"{region}: major divergence, significant rework needed"

    @staticmethod
    def _generate_suggestions(regions: list[RegionDiff]) -> list[str]:
        suggestions = []
        for r in regions:
            if r.severity == DiffSeverity.MAJOR:
                suggestions.append(f"Rework {r.region_name}: {r.diff_percentage:.1f}% pixel difference")
            elif r.severity == DiffSeverity.MODERATE:
                suggestions.append(f"Adjust {r.region_name}: {r.diff_percentage:.1f}% pixel difference")
        return suggestions
