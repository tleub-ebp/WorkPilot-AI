"""Complexity-Based Model Router — Cost Intelligence Engine.

Maps task complexity tiers (simple/standard/complex) from complexity_assessment.json
to appropriate model selections per phase, enabling cost-intelligent routing.

When enabled (via auto-profile), this module automatically selects cheaper models
for simple tasks (Haiku) and more capable models for complex tasks (Opus),
achieving 50-70% cost savings compared to using Sonnet for everything.

Example:
    >>> from scheduling.complexity_router import get_complexity_routing
    >>> routing = get_complexity_routing(spec_dir)
    >>> print(routing.complexity, routing.phase_models)
    'simple' {'spec': 'haiku', 'planning': 'haiku', 'coding': 'sonnet', 'qa': 'haiku'}
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Complexity → model shorthand mapping per phase
# ---------------------------------------------------------------------------

COMPLEXITY_MODEL_MAP: dict[str, dict[str, str]] = {
    "simple": {
        "spec": "haiku",
        "planning": "haiku",
        "coding": "sonnet",      # Even simple tasks need competent coding
        "qa": "haiku",
    },
    "standard": {
        "spec": "sonnet",
        "planning": "sonnet",
        "coding": "sonnet",
        "qa": "sonnet",
    },
    "complex": {
        "spec": "opus",
        "planning": "opus",
        "coding": "sonnet",      # Sonnet for coding to manage cost
        "qa": "opus",
    },
}

# Complexity → thinking level mapping per phase
COMPLEXITY_THINKING_MAP: dict[str, dict[str, str]] = {
    "simple": {
        "spec": "low",
        "planning": "low",
        "coding": "low",
        "qa": "low",
    },
    "standard": {
        "spec": "medium",
        "planning": "medium",
        "coding": "medium",
        "qa": "medium",
    },
    "complex": {
        "spec": "ultrathink",
        "planning": "high",
        "coding": "medium",
        "qa": "high",
    },
}

# Estimated cost multiplier relative to "standard" baseline
COMPLEXITY_COST_MULTIPLIERS: dict[str, float] = {
    "simple": 0.3,
    "standard": 1.0,
    "complex": 2.5,
}


@dataclass
class ComplexityRouting:
    """Result of complexity-based routing decision.

    Attributes:
        complexity: The complexity tier (simple, standard, complex).
        phase_models: Recommended model shorthand per phase.
        phase_thinking: Recommended thinking level per phase.
        estimated_cost_multiplier: Cost multiplier relative to standard baseline.
        source: Where the complexity was determined from.
    """
    complexity: str
    phase_models: dict[str, str]
    phase_thinking: dict[str, str]
    estimated_cost_multiplier: float
    source: str


def get_complexity_from_spec(spec_dir: Path) -> str | None:
    """Read complexity tier from complexity_assessment.json.

    Args:
        spec_dir: Path to the spec directory.

    Returns:
        Complexity tier string or None if not found.
    """
    assessment_file = spec_dir / "complexity_assessment.json"
    if not assessment_file.exists():
        return None
    try:
        with open(assessment_file, encoding="utf-8") as f:
            data = json.load(f)
        complexity = data.get("complexity", "").lower()
        if complexity in COMPLEXITY_MODEL_MAP:
            return complexity
        logger.warning("Unknown complexity '%s' in %s", complexity, assessment_file)
        return None
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read complexity assessment: %s", exc)
        return None


def get_complexity_routing(
    spec_dir: Path,
    complexity_override: str | None = None,
) -> ComplexityRouting:
    """Get model/thinking routing based on task complexity.

    Priority:
    1. Explicit override (if provided)
    2. complexity_assessment.json in spec_dir
    3. Default to 'standard'

    Args:
        spec_dir: Path to the spec directory.
        complexity_override: Override complexity tier.

    Returns:
        ComplexityRouting with recommended models and thinking levels.
    """
    if complexity_override:
        complexity = complexity_override.lower()
        source = "override"
    else:
        assessed = get_complexity_from_spec(spec_dir)
        if assessed:
            complexity = assessed
            source = "complexity_assessment"
        else:
            complexity = "standard"
            source = "default"

    if complexity not in COMPLEXITY_MODEL_MAP:
        logger.warning("Invalid complexity '%s', falling back to 'standard'", complexity)
        complexity = "standard"

    return ComplexityRouting(
        complexity=complexity,
        phase_models=COMPLEXITY_MODEL_MAP[complexity].copy(),
        phase_thinking=COMPLEXITY_THINKING_MAP[complexity].copy(),
        estimated_cost_multiplier=COMPLEXITY_COST_MULTIPLIERS.get(complexity, 1.0),
        source=source,
    )
