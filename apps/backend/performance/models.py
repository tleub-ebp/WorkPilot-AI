"""Data models for the Performance Profiler Agent."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class BottleneckType(Enum):
    ALGORITHM_COMPLEXITY = "algorithm_complexity"
    MEMORY_LEAK = "memory_leak"
    UNNECESSARY_RENDERS = "unnecessary_renders"
    N_PLUS_ONE_QUERY = "n_plus_one_query"
    MISSING_INDEX = "missing_index"
    SYNCHRONOUS_IO = "synchronous_io"
    MISSING_CACHE = "missing_cache"
    LARGE_BUNDLE = "large_bundle"
    BLOCKING_OPERATION = "blocking_operation"
    EXPENSIVE_COMPUTATION = "expensive_computation"


class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OptimizationEffort(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Bottleneck:
    bottleneck_id: str
    file_path: str
    line_start: int
    line_end: int
    type: BottleneckType
    severity: Severity
    description: str
    estimated_impact: str = ""
    code_snippet: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "bottleneck_id": self.bottleneck_id,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "type": self.type.value,
            "severity": self.severity.value,
            "description": self.description,
            "estimated_impact": self.estimated_impact,
            "code_snippet": self.code_snippet,
        }


@dataclass
class OptimizationSuggestion:
    suggestion_id: str
    bottleneck_id: str
    title: str
    description: str
    implementation: str = ""
    estimated_improvement: str = ""
    effort: OptimizationEffort = OptimizationEffort.MEDIUM
    auto_implementable: bool = False

    def to_dict(self) -> dict:
        return {
            "suggestion_id": self.suggestion_id,
            "bottleneck_id": self.bottleneck_id,
            "title": self.title,
            "description": self.description,
            "implementation": self.implementation,
            "estimated_improvement": self.estimated_improvement,
            "effort": self.effort.value,
            "auto_implementable": self.auto_implementable,
        }


@dataclass
class BenchmarkResult:
    name: str
    duration_ms: float
    memory_mb: float = 0.0
    cpu_percent: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "duration_ms": self.duration_ms,
            "memory_mb": self.memory_mb,
            "cpu_percent": self.cpu_percent,
            "timestamp": self.timestamp,
        }


@dataclass
class PerformanceReport:
    project_dir: str
    bottlenecks: list[Bottleneck] = field(default_factory=list)
    suggestions: list[OptimizationSuggestion] = field(default_factory=list)
    benchmarks: list[BenchmarkResult] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def compute_summary(self) -> dict:
        critical = sum(1 for b in self.bottlenecks if b.severity == Severity.CRITICAL)
        high = sum(1 for b in self.bottlenecks if b.severity == Severity.HIGH)
        auto_fix = sum(1 for s in self.suggestions if s.auto_implementable)
        self.summary = {
            "total_bottlenecks": len(self.bottlenecks),
            "critical_count": critical,
            "high_count": high,
            "medium_count": sum(
                1 for b in self.bottlenecks if b.severity == Severity.MEDIUM
            ),
            "low_count": sum(1 for b in self.bottlenecks if b.severity == Severity.LOW),
            "total_suggestions": len(self.suggestions),
            "auto_implementable_suggestions": auto_fix,
            "benchmarks_run": len(self.benchmarks),
        }
        return self.summary

    def to_dict(self) -> dict:
        self.compute_summary()
        return {
            "project_dir": self.project_dir,
            "bottlenecks": [b.to_dict() for b in self.bottlenecks],
            "suggestions": [s.to_dict() for s in self.suggestions],
            "benchmarks": [b.to_dict() for b in self.benchmarks],
            "summary": self.summary,
            "generated_at": self.generated_at,
        }
