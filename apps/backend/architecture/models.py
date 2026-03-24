"""
Architecture Enforcement Models
================================

Dataclasses for architecture rules, violations, and reports.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LayerConfig:
    """A single architectural layer definition."""

    name: str
    patterns: list[str]  # glob patterns matching files in this layer
    allowed_imports: list[str] = field(default_factory=list)
    forbidden_imports: list[str] = field(default_factory=list)


@dataclass
class BoundedContextConfig:
    """A bounded context (DDD) boundary definition."""

    name: str
    patterns: list[str]  # glob patterns matching files in this context
    allowed_cross_context_imports: list[str] = field(default_factory=list)


@dataclass
class ForbiddenPattern:
    """A specific forbidden import pattern rule."""

    from_pattern: str  # glob pattern for source files
    import_pattern: str  # regex pattern for forbidden imports
    description: str = ""


@dataclass
class RulesConfig:
    """Global architecture rules."""

    no_circular_dependencies: bool = True
    max_dependency_depth: int = 10
    forbidden_patterns: list[ForbiddenPattern] = field(default_factory=list)


@dataclass
class ArchitectureConfig:
    """Complete architecture configuration for a project."""

    version: str = "1.0"
    architecture_style: str = "layered"
    layers: list[LayerConfig] = field(default_factory=list)
    bounded_contexts: list[BoundedContextConfig] = field(default_factory=list)
    rules: RulesConfig = field(default_factory=RulesConfig)
    ai_review: bool = True
    inferred: bool = False  # True if auto-generated, not from explicit config


@dataclass
class ImportEdge:
    """A single import relationship."""

    source_file: str
    target_module: str  # the imported module/path
    line: int | None = None
    import_statement: str = ""  # the raw import string


@dataclass
class ImportGraph:
    """Graph of all import relationships in analyzed files."""

    edges: list[ImportEdge] = field(default_factory=list)
    files_analyzed: int = 0

    def get_edges_from(self, source_file: str) -> list[ImportEdge]:
        """Get all imports originating from a specific file."""
        return [e for e in self.edges if e.source_file == source_file]

    def get_edges_to(self, target_module: str) -> list[ImportEdge]:
        """Get all files importing a specific module."""
        return [e for e in self.edges if e.target_module == target_module]

    def get_all_sources(self) -> set[str]:
        """Get all unique source files."""
        return {e.source_file for e in self.edges}

    def get_adjacency(self) -> dict[str, set[str]]:
        """Build adjacency list: file -> set of imported modules."""
        adj: dict[str, set[str]] = {}
        for edge in self.edges:
            adj.setdefault(edge.source_file, set()).add(edge.target_module)
        return adj


@dataclass
class ArchitectureViolation:
    """A single architecture violation."""

    type: str  # layer_violation | circular_dependency | forbidden_import | bounded_context
    severity: str  # error | warning
    file: str
    line: int | None = None
    import_target: str = ""
    rule: str = ""
    description: str = ""
    suggestion: str = ""

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "severity": self.severity,
            "file": self.file,
            "line": self.line,
            "import_target": self.import_target,
            "rule": self.rule,
            "description": self.description,
            "suggestion": self.suggestion,
        }


@dataclass
class ArchitectureReport:
    """Results of architecture validation."""

    violations: list[ArchitectureViolation] = field(default_factory=list)
    warnings: list[ArchitectureViolation] = field(default_factory=list)
    passed: bool = True
    summary: str = ""
    files_analyzed: int = 0
    duration_seconds: float = 0.0
    config_source: str = "none"  # explicit | inferred | none

    def to_dict(self) -> dict:
        return {
            "status": "approved" if self.passed else "rejected",
            "violations": [v.to_dict() for v in self.violations],
            "warnings": [w.to_dict() for w in self.warnings],
            "summary": self.summary,
            "files_analyzed": self.files_analyzed,
            "duration_seconds": self.duration_seconds,
            "config_source": self.config_source,
            "violation_count": len(self.violations),
            "warning_count": len(self.warnings),
        }
