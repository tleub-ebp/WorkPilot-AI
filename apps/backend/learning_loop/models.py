"""
Data models for the Autonomous Agent Learning Loop.

Defines patterns, reports, and enums used throughout the learning loop system.
"""

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class PatternCategory(str, Enum):
    """Category of learning pattern extracted from build analysis."""

    TOOL_SEQUENCE = "tool_sequence"
    PROMPT_STRATEGY = "prompt_strategy"
    ERROR_RESOLUTION = "error_resolution"
    QA_PATTERN = "qa_pattern"
    CODE_STRUCTURE = "code_structure"


class PatternType(str, Enum):
    """Whether the pattern represents a success, failure, or optimization."""

    SUCCESS = "success"
    FAILURE = "failure"
    OPTIMIZATION = "optimization"


class PatternSource(str, Enum):
    """Origin of the pattern extraction."""

    BUILD_ANALYSIS = "build_analysis"
    QA_FEEDBACK = "qa_feedback"
    ERROR_RECOVERY = "error_recovery"


@dataclass
class LearningPattern:
    """A single learning pattern extracted from build analysis."""

    pattern_id: str
    category: PatternCategory
    pattern_type: PatternType
    source: PatternSource
    description: str
    confidence: float  # 0.0 to 1.0
    occurrence_count: int
    agent_phase: str  # planning, coding, qa_review, qa_fixing
    context_tags: list[str]
    actionable_instruction: str
    first_seen: str = ""
    last_seen: str = ""
    applied_count: int = 0
    success_after_apply: int = 0
    source_build_ids: list[str] = field(default_factory=list)
    enabled: bool = True

    def __post_init__(self):
        now = datetime.now(timezone.utc).isoformat()
        if not self.first_seen:
            self.first_seen = now
        if not self.last_seen:
            self.last_seen = now
        if isinstance(self.category, str):
            self.category = PatternCategory(self.category)
        if isinstance(self.pattern_type, str):
            self.pattern_type = PatternType(self.pattern_type)
        if isinstance(self.source, str):
            self.source = PatternSource(self.source)

    @property
    def effectiveness_rate(self) -> float:
        """Rate of success when this pattern was applied."""
        if self.applied_count == 0:
            return 0.0
        return self.success_after_apply / self.applied_count

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["category"] = self.category.value
        d["pattern_type"] = self.pattern_type.value
        d["source"] = self.source.value
        d["effectiveness_rate"] = self.effectiveness_rate
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LearningPattern":
        data = dict(data)
        data.pop("effectiveness_rate", None)
        return cls(**data)

    @staticmethod
    def generate_id() -> str:
        return f"lp-{uuid.uuid4().hex[:12]}"


@dataclass
class ImprovementMetrics:
    """Before/after metrics showing learning loop impact."""

    qa_first_pass_rate: dict[str, float] = field(
        default_factory=lambda: {"before": 0.0, "after": 0.0}
    )
    avg_qa_iterations: dict[str, float] = field(
        default_factory=lambda: {"before": 0.0, "after": 0.0}
    )
    error_rate: dict[str, float] = field(
        default_factory=lambda: {"before": 0.0, "after": 0.0}
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ImprovementMetrics":
        return cls(**data)


@dataclass
class LearningReport:
    """Report produced after a learning loop analysis run."""

    project_path: str
    analyzed_builds: int
    patterns_found: list[LearningPattern]
    improvement_metrics: ImprovementMetrics | None = None
    generated_at: str = ""
    analysis_model: str = ""

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_path": self.project_path,
            "analyzed_builds": self.analyzed_builds,
            "patterns_found": [p.to_dict() for p in self.patterns_found],
            "improvement_metrics": self.improvement_metrics.to_dict()
            if self.improvement_metrics
            else None,
            "generated_at": self.generated_at,
            "analysis_model": self.analysis_model,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LearningReport":
        data = dict(data)
        data["patterns_found"] = [
            LearningPattern.from_dict(p) for p in data.get("patterns_found", [])
        ]
        metrics = data.get("improvement_metrics")
        if metrics:
            data["improvement_metrics"] = ImprovementMetrics.from_dict(metrics)
        return cls(**data)
