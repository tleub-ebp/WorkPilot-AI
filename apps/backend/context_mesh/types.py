"""
Data models for the Context Mesh cross-project intelligence system.
"""

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class PatternCategory(str, Enum):
    """Category of cross-project pattern."""

    ARCHITECTURE = "architecture"
    AUTH = "auth"
    API_DESIGN = "api_design"
    STATE_MANAGEMENT = "state_management"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    ERROR_HANDLING = "error_handling"
    SECURITY = "security"
    PERFORMANCE = "performance"
    NAMING_CONVENTION = "naming_convention"
    PROJECT_STRUCTURE = "project_structure"
    DATABASE = "database"
    LOGGING = "logging"
    CI_CD = "ci_cd"
    OTHER = "other"


class HandbookDomain(str, Enum):
    """Domain for engineering handbook entries."""

    AUTH = "auth"
    API_DESIGN = "api_design"
    STATE_MANAGEMENT = "state_management"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    SECURITY = "security"
    PERFORMANCE = "performance"
    DATABASE = "database"
    FRONTEND = "frontend"
    BACKEND = "backend"
    DEVOPS = "devops"
    GENERAL = "general"


class RecommendationType(str, Enum):
    """Type of contextual recommendation."""

    PATTERN_REUSE = "pattern_reuse"
    CONVENTION_ADOPTION = "convention_adoption"
    BUG_PREVENTION = "bug_prevention"
    DIVERGENCE_ALERT = "divergence_alert"
    COMPLEXITY_ESTIMATE = "complexity_estimate"
    SKILL_TRANSFER = "skill_transfer"


@dataclass
class ProjectSummary:
    """Summary of a registered project in the mesh."""

    project_path: str
    project_name: str
    registered_at: str = ""
    last_analyzed_at: str = ""
    pattern_count: int = 0
    tech_stack: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.registered_at:
            self.registered_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectSummary":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @staticmethod
    def generate_id(project_path: str) -> str:
        return f"proj-{uuid.uuid5(uuid.NAMESPACE_URL, project_path).hex[:12]}"


@dataclass
class CrossProjectPattern:
    """A pattern detected across multiple projects."""

    pattern_id: str
    category: PatternCategory
    title: str
    description: str
    source_projects: list[str]
    target_projects: list[str] = field(default_factory=list)
    confidence: float = 0.0
    occurrence_count: int = 1
    code_example: str = ""
    migration_hint: str = ""
    first_seen: str = ""
    last_seen: str = ""
    applied_count: int = 0
    dismissed_count: int = 0

    def __post_init__(self):
        now = datetime.now(timezone.utc).isoformat()
        if not self.first_seen:
            self.first_seen = now
        if not self.last_seen:
            self.last_seen = now
        if isinstance(self.category, str):
            self.category = PatternCategory(self.category)

    @property
    def adoption_rate(self) -> float:
        total = self.applied_count + self.dismissed_count
        if total == 0:
            return 0.0
        return self.applied_count / total

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["category"] = self.category.value
        d["adoption_rate"] = self.adoption_rate
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CrossProjectPattern":
        data = dict(data)
        data.pop("adoption_rate", None)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @staticmethod
    def generate_id() -> str:
        return f"cxp-{uuid.uuid4().hex[:12]}"


@dataclass
class HandbookEntry:
    """An entry in the auto-generated engineering handbook."""

    entry_id: str
    domain: HandbookDomain
    title: str
    description: str
    decision_rationale: str
    source_projects: list[str]
    related_commits: list[str] = field(default_factory=list)
    related_prs: list[str] = field(default_factory=list)
    code_examples: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    version: int = 1

    def __post_init__(self):
        now = datetime.now(timezone.utc).isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now
        if isinstance(self.domain, str):
            self.domain = HandbookDomain(self.domain)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["domain"] = self.domain.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HandbookEntry":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @staticmethod
    def generate_id() -> str:
        return f"hbe-{uuid.uuid4().hex[:12]}"


@dataclass
class SkillTransfer:
    """A skill or convention learned in one project, transferable to others."""

    transfer_id: str
    skill_name: str
    description: str
    source_project: str
    target_projects: list[str]
    category: PatternCategory
    framework_or_api: str = ""
    convention_details: str = ""
    confidence: float = 0.0
    status: str = "pending"  # pending | accepted | dismissed
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if isinstance(self.category, str):
            self.category = PatternCategory(self.category)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["category"] = self.category.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillTransfer":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @staticmethod
    def generate_id() -> str:
        return f"skt-{uuid.uuid4().hex[:12]}"


@dataclass
class ContextualRecommendation:
    """A contextual recommendation based on cross-project knowledge."""

    recommendation_id: str
    recommendation_type: RecommendationType
    title: str
    description: str
    source_project: str
    target_project: str
    relevance_score: float = 0.0
    phase: str = ""  # spec | planning | coding | qa
    related_pattern_id: str = ""
    action_suggestion: str = ""
    created_at: str = ""
    status: str = "active"  # active | applied | dismissed | expired

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if isinstance(self.recommendation_type, str):
            self.recommendation_type = RecommendationType(self.recommendation_type)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["recommendation_type"] = self.recommendation_type.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContextualRecommendation":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @staticmethod
    def generate_id() -> str:
        return f"rec-{uuid.uuid4().hex[:12]}"


@dataclass
class ContextMeshConfig:
    """Configuration for the Context Mesh feature."""

    enabled: bool = False
    auto_analyze: bool = True
    analyze_on_build_complete: bool = True
    cross_project_suggestions: bool = True
    handbook_generation: bool = True
    skill_transfer: bool = True
    max_projects: int = 20
    min_confidence_threshold: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContextMeshConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class MeshAnalysisReport:
    """Report produced after a cross-project mesh analysis."""

    analyzed_projects: list[str]
    patterns_found: list[CrossProjectPattern]
    handbook_entries: list[HandbookEntry]
    skill_transfers: list[SkillTransfer]
    recommendations: list[ContextualRecommendation]
    generated_at: str = ""
    analysis_model: str = ""

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "analyzed_projects": self.analyzed_projects,
            "patterns_found": [p.to_dict() for p in self.patterns_found],
            "handbook_entries": [e.to_dict() for e in self.handbook_entries],
            "skill_transfers": [s.to_dict() for s in self.skill_transfers],
            "recommendations": [r.to_dict() for r in self.recommendations],
            "generated_at": self.generated_at,
            "analysis_model": self.analysis_model,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MeshAnalysisReport":
        data = dict(data)
        data["patterns_found"] = [
            CrossProjectPattern.from_dict(p) for p in data.get("patterns_found", [])
        ]
        data["handbook_entries"] = [
            HandbookEntry.from_dict(e) for e in data.get("handbook_entries", [])
        ]
        data["skill_transfers"] = [
            SkillTransfer.from_dict(s) for s in data.get("skill_transfers", [])
        ]
        data["recommendations"] = [
            ContextualRecommendation.from_dict(r)
            for r in data.get("recommendations", [])
        ]
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
