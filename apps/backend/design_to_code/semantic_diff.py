"""
Semantic Diff — Component-level comparison between design and code.

Compares the structural hierarchy of UI components (buttons, inputs,
cards, etc.) rather than raw pixels.  This enables targeted corrections
like "missing icon in header" instead of "header region is 12% off".

100% algorithmic — no LLM dependency.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ComponentType(str, Enum):
    BUTTON = "button"
    INPUT = "input"
    TEXT = "text"
    IMAGE = "image"
    ICON = "icon"
    CARD = "card"
    LIST = "list"
    NAVIGATION = "navigation"
    HEADER = "header"
    FOOTER = "footer"
    CONTAINER = "container"
    OTHER = "other"


class DiffAction(str, Enum):
    MISSING = "missing"       # In design but not in code
    EXTRA = "extra"           # In code but not in design
    STYLE_MISMATCH = "style_mismatch"  # Present but styled differently
    POSITION_OFF = "position_off"      # Present but wrong position
    CONTENT_MISMATCH = "content_mismatch"  # Wrong text/content
    MATCH = "match"


@dataclass
class ComponentSpec:
    """Describes a UI component from the design or code."""

    id: str
    component_type: ComponentType
    text: str = ""
    region: str = ""  # header, content, footer, sidebar
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0
    styles: dict[str, str] = field(default_factory=dict)
    children: list[ComponentSpec] = field(default_factory=list)

    @property
    def area(self) -> float:
        return self.width * self.height


@dataclass
class ComponentDiff:
    """Diff between a design component and its rendered counterpart."""

    component_id: str
    component_type: ComponentType
    action: DiffAction
    design_spec: ComponentSpec | None = None
    code_spec: ComponentSpec | None = None
    style_diffs: dict[str, tuple[str, str]] = field(default_factory=dict)
    description: str = ""
    correction_hint: str = ""

    @property
    def is_issue(self) -> bool:
        return self.action != DiffAction.MATCH


@dataclass
class SemanticDiffResult:
    """Complete semantic diff result."""

    total_components: int = 0
    matched: int = 0
    missing: int = 0
    extra: int = 0
    mismatched: int = 0
    fidelity_score: float = 1.0
    diffs: list[ComponentDiff] = field(default_factory=list)
    correction_hints: list[str] = field(default_factory=list)

    @property
    def issues(self) -> list[ComponentDiff]:
        return [d for d in self.diffs if d.is_issue]


class SemanticDiffAnalyzer:
    """Compare design components with rendered code components.

    Usage::

        analyzer = SemanticDiffAnalyzer()
        result = analyzer.compare(design_components, code_components)
        for diff in result.issues:
            print(f"{diff.action.value}: {diff.description}")
    """

    def __init__(
        self,
        position_tolerance: float = 10.0,
        size_tolerance: float = 0.15,  # 15% size tolerance
    ) -> None:
        self._position_tolerance = position_tolerance
        self._size_tolerance = size_tolerance

    def compare(
        self,
        design: list[ComponentSpec],
        code: list[ComponentSpec],
    ) -> SemanticDiffResult:
        """Compare design components against code components."""
        diffs: list[ComponentDiff] = []
        matched_code_ids: set[str] = set()

        for d_comp in design:
            best_match = self._find_best_match(d_comp, code, matched_code_ids)
            if best_match is None:
                diffs.append(ComponentDiff(
                    component_id=d_comp.id,
                    component_type=d_comp.component_type,
                    action=DiffAction.MISSING,
                    design_spec=d_comp,
                    description=f"Missing {d_comp.component_type.value}: '{d_comp.text or d_comp.id}'",
                    correction_hint=f"Add {d_comp.component_type.value} '{d_comp.text or d_comp.id}' in {d_comp.region or 'page'}",
                ))
            else:
                matched_code_ids.add(best_match.id)
                diff = self._compare_components(d_comp, best_match)
                diffs.append(diff)

        # Find extra components in code
        for c_comp in code:
            if c_comp.id not in matched_code_ids:
                diffs.append(ComponentDiff(
                    component_id=c_comp.id,
                    component_type=c_comp.component_type,
                    action=DiffAction.EXTRA,
                    code_spec=c_comp,
                    description=f"Extra {c_comp.component_type.value}: '{c_comp.text or c_comp.id}'",
                    correction_hint=f"Consider removing {c_comp.component_type.value} '{c_comp.text or c_comp.id}'",
                ))

        # Compute stats
        total = len(design)
        matched = sum(1 for d in diffs if d.action == DiffAction.MATCH)
        missing = sum(1 for d in diffs if d.action == DiffAction.MISSING)
        extra = sum(1 for d in diffs if d.action == DiffAction.EXTRA)
        mismatched = sum(
            1 for d in diffs
            if d.action in (DiffAction.STYLE_MISMATCH, DiffAction.POSITION_OFF, DiffAction.CONTENT_MISMATCH)
        )

        fidelity = matched / total if total > 0 else 1.0

        return SemanticDiffResult(
            total_components=total,
            matched=matched,
            missing=missing,
            extra=extra,
            mismatched=mismatched,
            fidelity_score=fidelity,
            diffs=diffs,
            correction_hints=[d.correction_hint for d in diffs if d.is_issue and d.correction_hint],
        )

    def _find_best_match(
        self,
        design_comp: ComponentSpec,
        code_components: list[ComponentSpec],
        already_matched: set[str],
    ) -> ComponentSpec | None:
        """Find the best matching code component for a design component."""
        candidates = [
            c for c in code_components
            if c.id not in already_matched
            and c.component_type == design_comp.component_type
        ]

        if not candidates:
            # Try matching by text content and region
            candidates = [
                c for c in code_components
                if c.id not in already_matched
                and c.text == design_comp.text
                and c.region == design_comp.region
            ]

        if not candidates:
            return None

        # Score candidates
        best = None
        best_score = -1.0
        for c in candidates:
            score = self._match_score(design_comp, c)
            if score > best_score:
                best_score = score
                best = c

        return best if best_score > 0.3 else None

    def _match_score(self, design: ComponentSpec, code: ComponentSpec) -> float:
        """Score how well a code component matches a design component (0-1)."""
        score = 0.0
        weights = 0.0

        # Type match (must match)
        if design.component_type == code.component_type:
            score += 0.3
        weights += 0.3

        # Text match
        if design.text and code.text:
            if design.text == code.text:
                score += 0.3
            elif design.text.lower() == code.text.lower():
                score += 0.2
            weights += 0.3

        # Region match
        if design.region and code.region:
            if design.region == code.region:
                score += 0.2
            weights += 0.2

        # Position proximity
        if design.x > 0 or design.y > 0:
            dist = math.sqrt((design.x - code.x) ** 2 + (design.y - code.y) ** 2)
            if dist <= self._position_tolerance:
                score += 0.2
            elif dist <= self._position_tolerance * 3:
                score += 0.1
            weights += 0.2

        return score / max(weights, 0.01)

    def _compare_components(
        self, design: ComponentSpec, code: ComponentSpec
    ) -> ComponentDiff:
        """Compare two matched components for detailed differences."""
        style_diffs: dict[str, tuple[str, str]] = {}
        action = DiffAction.MATCH
        descriptions: list[str] = []

        # Check text content
        if design.text and design.text != code.text:
            action = DiffAction.CONTENT_MISMATCH
            descriptions.append(
                f"Text mismatch: expected '{design.text}', got '{code.text}'"
            )

        # Check position
        if design.x > 0 or design.y > 0:
            dist = math.sqrt((design.x - code.x) ** 2 + (design.y - code.y) ** 2)
            if dist > self._position_tolerance:
                if action == DiffAction.MATCH:
                    action = DiffAction.POSITION_OFF
                descriptions.append(
                    f"Position off by {dist:.0f}px"
                )

        # Check styles
        for key, expected in design.styles.items():
            actual = code.styles.get(key, "")
            if expected != actual:
                style_diffs[key] = (expected, actual)
                if action == DiffAction.MATCH:
                    action = DiffAction.STYLE_MISMATCH

        if style_diffs:
            descriptions.append(
                f"Style diffs: {', '.join(f'{k}: {v[0]}→{v[1]}' for k, v in style_diffs.items())}"
            )

        correction = ""
        if action != DiffAction.MATCH:
            correction = f"Fix {design.component_type.value} '{design.text or design.id}': {'; '.join(descriptions)}"

        return ComponentDiff(
            component_id=design.id,
            component_type=design.component_type,
            action=action,
            design_spec=design,
            code_spec=code,
            style_diffs=style_diffs,
            description="; ".join(descriptions) if descriptions else "Match",
            correction_hint=correction,
        )
