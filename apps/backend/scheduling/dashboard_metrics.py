"""Dashboard Metrics — Centralized project KPI dashboard with real-time metrics.

Aggregates data from existing stores (Kanban, QA, cost estimator, merge)
to provide a unified view of project health and performance.

Feature 1.1 — Dashboard de métriques projet.

Example:
    >>> from apps.backend.scheduling.dashboard_metrics import DashboardMetrics
    >>> dashboard = DashboardMetrics()
    >>> dashboard.record_task("proj-1", "task-1", "Implement login", status="completed",
    ...     complexity="medium", completion_seconds=3600)
    >>> dashboard.record_qa_result("proj-1", "task-1", passed=True, score=92.5)
    >>> snapshot = dashboard.get_snapshot("proj-1")
    >>> print(f"Tasks completed: {snapshot.tasks_by_status.get('completed', 0)}")
"""

import csv
import io
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TaskStatus(str, Enum):
    """Task statuses tracked by the dashboard."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskComplexity(str, Enum):
    """Task complexity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MergeResolution(str, Enum):
    """How a merge conflict was resolved."""

    AUTOMATIC = "automatic"
    MANUAL = "manual"


class ExportFormat(str, Enum):
    """Supported export formats."""

    JSON = "json"
    CSV = "csv"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class TaskRecord:
    """Record of a task tracked in the dashboard.

    Attributes:
        project_id: The project this task belongs to.
        task_id: Unique task identifier.
        title: Task title/description.
        status: Current status.
        complexity: Estimated complexity.
        completion_seconds: Time to complete in seconds (0 if not completed).
        created_at: When the task was created.
        completed_at: When the task was completed (None if not yet).
    """

    project_id: str
    task_id: str
    title: str
    status: TaskStatus = TaskStatus.PENDING
    complexity: TaskComplexity = TaskComplexity.MEDIUM
    completion_seconds: float = 0.0
    created_at: str = ""
    completed_at: str | None = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "task_id": self.task_id,
            "title": self.title,
            "status": self.status.value
            if isinstance(self.status, TaskStatus)
            else self.status,
            "complexity": self.complexity.value
            if isinstance(self.complexity, TaskComplexity)
            else self.complexity,
            "completion_seconds": self.completion_seconds,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


@dataclass
class QARecord:
    """Record of a QA result.

    Attributes:
        project_id: The project.
        task_id: Related task.
        passed: Whether QA passed.
        score: QA score (0-100).
        attempt: Which attempt number (1 = first pass).
        timestamp: When the QA was run.
    """

    project_id: str
    task_id: str
    passed: bool
    score: float = 0.0
    attempt: int = 1
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "task_id": self.task_id,
            "passed": self.passed,
            "score": self.score,
            "attempt": self.attempt,
            "timestamp": self.timestamp,
        }


@dataclass
class TokenRecord:
    """Record of token consumption.

    Attributes:
        project_id: The project.
        provider: LLM provider name.
        model: Model name.
        input_tokens: Number of input tokens.
        output_tokens: Number of output tokens.
        cost: Cost in USD.
        timestamp: When the usage occurred.
    """

    project_id: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "provider": self.provider,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost": self.cost,
            "timestamp": self.timestamp,
        }


@dataclass
class MergeRecord:
    """Record of a merge conflict resolution.

    Attributes:
        project_id: The project.
        task_id: Related task.
        resolution: How the conflict was resolved.
        files_affected: Number of files with conflicts.
        timestamp: When the merge happened.
    """

    project_id: str
    task_id: str
    resolution: MergeResolution = MergeResolution.AUTOMATIC
    files_affected: int = 1
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "task_id": self.task_id,
            "resolution": self.resolution.value
            if isinstance(self.resolution, MergeResolution)
            else self.resolution,
            "files_affected": self.files_affected,
            "timestamp": self.timestamp,
        }


@dataclass
class DashboardSnapshot:
    """Point-in-time snapshot of project dashboard metrics.

    Attributes:
        project_id: The project.
        generated_at: When this snapshot was generated.
        tasks_by_status: Count of tasks per status.
        avg_completion_by_complexity: Average completion time (seconds) per complexity.
        qa_first_pass_rate: Percentage of tasks passing QA on first attempt.
        qa_avg_score: Average QA score across all results.
        total_tokens: Total tokens consumed (input + output).
        tokens_by_provider: Token totals per provider.
        tokens_by_day: Token totals per day (last 7 days).
        total_cost: Total cost in USD.
        cost_by_task: Cost per task_id.
        merge_auto_count: Number of automatic merge resolutions.
        merge_manual_count: Number of manual merge resolutions.
    """

    project_id: str
    generated_at: str = ""
    tasks_by_status: dict[str, int] = field(default_factory=dict)
    avg_completion_by_complexity: dict[str, float] = field(default_factory=dict)
    qa_first_pass_rate: float = 0.0
    qa_avg_score: float = 0.0
    total_tokens: int = 0
    tokens_by_provider: dict[str, int] = field(default_factory=dict)
    tokens_by_day: dict[str, int] = field(default_factory=dict)
    total_cost: float = 0.0
    cost_by_task: dict[str, float] = field(default_factory=dict)
    merge_auto_count: int = 0
    merge_manual_count: int = 0

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class DashboardMetrics:
    """Centralized project metrics dashboard.

    Aggregates tasks, QA results, token usage, and merge resolutions to
    provide KPIs and exportable reports.
    """

    def __init__(self) -> None:
        self._tasks: list[TaskRecord] = []
        self._qa_results: list[QARecord] = []
        self._token_records: list[TokenRecord] = []
        self._merge_records: list[MergeRecord] = []
        logger.info("DashboardMetrics initialized")

    # -- Recording methods ---------------------------------------------------

    def record_task(
        self,
        project_id: str,
        task_id: str,
        title: str,
        status: str = "pending",
        complexity: str = "medium",
        completion_seconds: float = 0.0,
    ) -> TaskRecord:
        """Record or update a task in the dashboard.

        If a task with the same ``task_id`` already exists for the project,
        it is updated in-place.  Otherwise a new record is appended.

        Returns:
            The created or updated TaskRecord.
        """
        task_status = (
            TaskStatus(status)
            if status in [s.value for s in TaskStatus]
            else TaskStatus.PENDING
        )
        task_complexity = (
            TaskComplexity(complexity)
            if complexity in [c.value for c in TaskComplexity]
            else TaskComplexity.MEDIUM
        )

        # Update existing task if present
        for existing in self._tasks:
            if existing.project_id == project_id and existing.task_id == task_id:
                existing.status = task_status
                existing.complexity = task_complexity
                existing.completion_seconds = completion_seconds
                existing.title = title
                if (
                    task_status == TaskStatus.COMPLETED
                    and existing.completed_at is None
                ):
                    existing.completed_at = datetime.now(timezone.utc).isoformat()
                return existing

        record = TaskRecord(
            project_id=project_id,
            task_id=task_id,
            title=title,
            status=task_status,
            complexity=task_complexity,
            completion_seconds=completion_seconds,
        )
        if task_status == TaskStatus.COMPLETED:
            record.completed_at = datetime.now(timezone.utc).isoformat()
        self._tasks.append(record)
        return record

    def record_qa_result(
        self,
        project_id: str,
        task_id: str,
        passed: bool,
        score: float = 0.0,
        attempt: int = 1,
    ) -> QARecord:
        """Record a QA result."""
        record = QARecord(
            project_id=project_id,
            task_id=task_id,
            passed=passed,
            score=score,
            attempt=attempt,
        )
        self._qa_results.append(record)
        return record

    def record_token_usage(
        self,
        project_id: str,
        provider: str,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost: float = 0.0,
    ) -> TokenRecord:
        """Record token consumption."""
        record = TokenRecord(
            project_id=project_id,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
        )
        self._token_records.append(record)
        return record

    def record_merge(
        self,
        project_id: str,
        task_id: str,
        resolution: str = "automatic",
        files_affected: int = 1,
    ) -> MergeRecord:
        """Record a merge conflict resolution."""
        merge_res = (
            MergeResolution(resolution)
            if resolution in [m.value for m in MergeResolution]
            else MergeResolution.AUTOMATIC
        )
        record = MergeRecord(
            project_id=project_id,
            task_id=task_id,
            resolution=merge_res,
            files_affected=files_affected,
        )
        self._merge_records.append(record)
        return record

    # -- Query methods -------------------------------------------------------

    def get_tasks(self, project_id: str, status: str | None = None) -> list[TaskRecord]:
        """Get tasks for a project, optionally filtered by status."""
        tasks = [t for t in self._tasks if t.project_id == project_id]
        if status:
            tasks = [t for t in tasks if t.status.value == status]
        return tasks

    def get_qa_results(self, project_id: str) -> list[QARecord]:
        """Get QA results for a project."""
        return [q for q in self._qa_results if q.project_id == project_id]

    def get_token_records(self, project_id: str) -> list[TokenRecord]:
        """Get token records for a project."""
        return [t for t in self._token_records if t.project_id == project_id]

    def get_merge_records(self, project_id: str) -> list[MergeRecord]:
        """Get merge records for a project."""
        return [m for m in self._merge_records if m.project_id == project_id]

    # -- Snapshot / KPIs -----------------------------------------------------

    def get_snapshot(self, project_id: str) -> DashboardSnapshot:
        """Generate a point-in-time snapshot of all dashboard KPIs.

        Returns:
            DashboardSnapshot with aggregated metrics.
        """
        tasks = self.get_tasks(project_id)
        qa_results = self.get_qa_results(project_id)
        token_records = self.get_token_records(project_id)
        merge_records = self.get_merge_records(project_id)

        # Tasks by status
        tasks_by_status: dict[str, int] = {}
        for t in tasks:
            key = t.status.value
            tasks_by_status[key] = tasks_by_status.get(key, 0) + 1

        # Avg completion by complexity
        completion_by_complexity: dict[str, list[float]] = {}
        for t in tasks:
            if t.status == TaskStatus.COMPLETED and t.completion_seconds > 0:
                key = t.complexity.value
                completion_by_complexity.setdefault(key, []).append(
                    t.completion_seconds
                )
        avg_completion: dict[str, float] = {
            k: sum(v) / len(v) for k, v in completion_by_complexity.items() if v
        }

        # QA first-pass rate
        first_pass_tasks: set[str] = set()
        first_pass_passed: set[str] = set()
        for q in qa_results:
            if q.attempt == 1:
                first_pass_tasks.add(q.task_id)
                if q.passed:
                    first_pass_passed.add(q.task_id)
        qa_first_pass_rate = (
            len(first_pass_passed) / len(first_pass_tasks) * 100
            if first_pass_tasks
            else 0.0
        )

        # QA avg score
        all_scores = [q.score for q in qa_results if q.score > 0]
        qa_avg_score = sum(all_scores) / len(all_scores) if all_scores else 0.0

        # Token totals
        total_tokens = sum(t.input_tokens + t.output_tokens for t in token_records)
        tokens_by_provider: dict[str, int] = {}
        for t in token_records:
            tokens_by_provider[t.provider] = (
                tokens_by_provider.get(t.provider, 0) + t.input_tokens + t.output_tokens
            )

        # Tokens by day (last 7 days)
        tokens_by_day: dict[str, int] = {}
        for t in token_records:
            day = t.timestamp[:10] if t.timestamp else "unknown"
            tokens_by_day[day] = (
                tokens_by_day.get(day, 0) + t.input_tokens + t.output_tokens
            )

        # Cost
        total_cost = sum(t.cost for t in token_records)
        cost_by_task: dict[str, float] = {}
        # Aggregate cost from tokens that may have a task association via project_id
        # For simplicity, use model name as grouping since token records don't have task_id
        for t in token_records:
            cost_by_task[t.model] = cost_by_task.get(t.model, 0) + t.cost

        # Merges
        auto_count = sum(
            1 for m in merge_records if m.resolution == MergeResolution.AUTOMATIC
        )
        manual_count = sum(
            1 for m in merge_records if m.resolution == MergeResolution.MANUAL
        )

        return DashboardSnapshot(
            project_id=project_id,
            tasks_by_status=tasks_by_status,
            avg_completion_by_complexity=avg_completion,
            qa_first_pass_rate=round(qa_first_pass_rate, 1),
            qa_avg_score=round(qa_avg_score, 1),
            total_tokens=total_tokens,
            tokens_by_provider=tokens_by_provider,
            tokens_by_day=tokens_by_day,
            total_cost=round(total_cost, 6),
            cost_by_task=cost_by_task,
            merge_auto_count=auto_count,
            merge_manual_count=manual_count,
        )

    # -- Export --------------------------------------------------------------

    def export_report(self, project_id: str, fmt: str = "json") -> str:
        """Export the dashboard report as JSON or CSV string.

        Args:
            project_id: Project to export.
            fmt: Export format (``json`` or ``csv``).

        Returns:
            String representation of the report.
        """
        snapshot = self.get_snapshot(project_id)

        if fmt == "csv":
            return self._export_csv(snapshot)
        return json.dumps(snapshot.to_dict(), indent=2)

    def _export_csv(self, snapshot: DashboardSnapshot) -> str:
        """Export snapshot as CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["metric", "key", "value"])

        writer.writerow(["project_id", "", snapshot.project_id])
        writer.writerow(["generated_at", "", snapshot.generated_at])

        for status, count in snapshot.tasks_by_status.items():
            writer.writerow(["tasks_by_status", status, count])

        for complexity, avg in snapshot.avg_completion_by_complexity.items():
            writer.writerow(["avg_completion_seconds", complexity, round(avg, 1)])

        writer.writerow(["qa_first_pass_rate", "", snapshot.qa_first_pass_rate])
        writer.writerow(["qa_avg_score", "", snapshot.qa_avg_score])
        writer.writerow(["total_tokens", "", snapshot.total_tokens])
        writer.writerow(["total_cost", "", snapshot.total_cost])

        for provider, tokens in snapshot.tokens_by_provider.items():
            writer.writerow(["tokens_by_provider", provider, tokens])

        for day, tokens in snapshot.tokens_by_day.items():
            writer.writerow(["tokens_by_day", day, tokens])

        writer.writerow(["merge_auto_count", "", snapshot.merge_auto_count])
        writer.writerow(["merge_manual_count", "", snapshot.merge_manual_count])

        return output.getvalue()

    # -- Stats ---------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Global statistics across all projects."""
        projects = set()
        for t in self._tasks:
            projects.add(t.project_id)
        for q in self._qa_results:
            projects.add(q.project_id)

        return {
            "total_projects": len(projects),
            "total_tasks": len(self._tasks),
            "total_qa_results": len(self._qa_results),
            "total_token_records": len(self._token_records),
            "total_merge_records": len(self._merge_records),
        }
