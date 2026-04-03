"""Tests for Feature 1.1 — Dashboard de métriques projet.

Tests for DashboardMetrics, TaskRecord, QARecord, TokenRecord,
MergeRecord, DashboardSnapshot, and export functionality.

40 tests total:
- TaskRecord: 3
- QARecord: 2
- TokenRecord: 2
- MergeRecord: 2
- DashboardSnapshot: 2
- DashboardMetrics recording: 8
- DashboardMetrics queries: 5
- DashboardMetrics snapshot KPIs: 8
- DashboardMetrics export: 5
- DashboardMetrics stats: 3
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.scheduling.dashboard_metrics import (
    DashboardMetrics,
    DashboardSnapshot,
    ExportFormat,
    MergeRecord,
    MergeResolution,
    QARecord,
    TaskComplexity,
    TaskRecord,
    TaskStatus,
    TokenRecord,
)

# -----------------------------------------------------------------------
# TaskRecord
# -----------------------------------------------------------------------

class TestTaskRecord:
    def test_create_task_record(self):
        record = TaskRecord(
            project_id="proj-1",
            task_id="task-1",
            title="Implement login",
            status=TaskStatus.COMPLETED,
            complexity=TaskComplexity.HIGH,
            completion_seconds=3600.0,
        )
        assert record.project_id == "proj-1"
        assert record.task_id == "task-1"
        assert record.status == TaskStatus.COMPLETED
        assert record.complexity == TaskComplexity.HIGH
        assert record.completion_seconds == 3600.0

    def test_task_record_to_dict(self):
        record = TaskRecord(project_id="p", task_id="t", title="T")
        d = record.to_dict()
        assert d["project_id"] == "p"
        assert d["status"] == "pending"
        assert d["complexity"] == "medium"
        assert "created_at" in d

    def test_task_record_default_created_at(self):
        record = TaskRecord(project_id="p", task_id="t", title="T")
        assert record.created_at != ""


# -----------------------------------------------------------------------
# QARecord
# -----------------------------------------------------------------------

class TestQARecord:
    def test_create_qa_record(self):
        record = QARecord(project_id="p", task_id="t", passed=True, score=92.5, attempt=1)
        assert record.passed is True
        assert record.score == 92.5
        assert record.attempt == 1

    def test_qa_record_to_dict(self):
        record = QARecord(project_id="p", task_id="t", passed=False, score=45.0)
        d = record.to_dict()
        assert d["passed"] is False
        assert d["score"] == 45.0
        assert "timestamp" in d


# -----------------------------------------------------------------------
# TokenRecord
# -----------------------------------------------------------------------

class TestTokenRecord:
    def test_create_token_record(self):
        record = TokenRecord(
            project_id="p", provider="anthropic", model="claude-sonnet-4-20250514",
            input_tokens=1000, output_tokens=500, cost=0.01,
        )
        assert record.provider == "anthropic"
        assert record.input_tokens == 1000
        assert record.cost == 0.01

    def test_token_record_to_dict(self):
        record = TokenRecord(project_id="p", provider="openai", model="gpt-4o")
        d = record.to_dict()
        assert d["provider"] == "openai"
        assert d["model"] == "gpt-4o"


# -----------------------------------------------------------------------
# MergeRecord
# -----------------------------------------------------------------------

class TestMergeRecord:
    def test_create_merge_record(self):
        record = MergeRecord(
            project_id="p", task_id="t",
            resolution=MergeResolution.MANUAL, files_affected=3,
        )
        assert record.resolution == MergeResolution.MANUAL
        assert record.files_affected == 3

    def test_merge_record_to_dict(self):
        record = MergeRecord(project_id="p", task_id="t")
        d = record.to_dict()
        assert d["resolution"] == "automatic"


# -----------------------------------------------------------------------
# DashboardSnapshot
# -----------------------------------------------------------------------

class TestDashboardSnapshot:
    def test_create_snapshot(self):
        snap = DashboardSnapshot(
            project_id="p",
            tasks_by_status={"completed": 5, "pending": 2},
            qa_first_pass_rate=80.0,
            total_tokens=10000,
        )
        assert snap.project_id == "p"
        assert snap.tasks_by_status["completed"] == 5
        assert snap.total_tokens == 10000

    def test_snapshot_to_dict(self):
        snap = DashboardSnapshot(project_id="p")
        d = snap.to_dict()
        assert "project_id" in d
        assert "generated_at" in d
        assert "tasks_by_status" in d


# -----------------------------------------------------------------------
# DashboardMetrics — recording
# -----------------------------------------------------------------------

class TestDashboardMetricsRecording:
    def setup_method(self):
        self.dashboard = DashboardMetrics()

    def test_record_task(self):
        task = self.dashboard.record_task("p", "t1", "Task 1", status="completed")
        assert task.status == TaskStatus.COMPLETED

    def test_record_task_updates_existing(self):
        self.dashboard.record_task("p", "t1", "Task 1", status="pending")
        task = self.dashboard.record_task("p", "t1", "Task 1 updated", status="completed")
        assert task.status == TaskStatus.COMPLETED
        assert task.title == "Task 1 updated"
        assert len(self.dashboard.get_tasks("p")) == 1

    def test_record_task_sets_completed_at(self):
        task = self.dashboard.record_task("p", "t1", "T", status="completed")
        assert task.completed_at is not None

    def test_record_task_invalid_status_defaults(self):
        task = self.dashboard.record_task("p", "t1", "T", status="unknown_status")
        assert task.status == TaskStatus.PENDING

    def test_record_qa_result(self):
        qa = self.dashboard.record_qa_result("p", "t1", passed=True, score=95.0)
        assert qa.passed is True
        assert qa.score == 95.0

    def test_record_token_usage(self):
        token = self.dashboard.record_token_usage(
            "p", "anthropic", "claude-sonnet-4-20250514", input_tokens=1000, output_tokens=500, cost=0.01,
        )
        assert token.input_tokens == 1000

    def test_record_merge_automatic(self):
        merge = self.dashboard.record_merge("p", "t1", resolution="automatic")
        assert merge.resolution == MergeResolution.AUTOMATIC

    def test_record_merge_manual(self):
        merge = self.dashboard.record_merge("p", "t1", resolution="manual", files_affected=5)
        assert merge.resolution == MergeResolution.MANUAL
        assert merge.files_affected == 5


# -----------------------------------------------------------------------
# DashboardMetrics — queries
# -----------------------------------------------------------------------

class TestDashboardMetricsQueries:
    def setup_method(self):
        self.dashboard = DashboardMetrics()
        self.dashboard.record_task("p", "t1", "T1", status="completed")
        self.dashboard.record_task("p", "t2", "T2", status="pending")
        self.dashboard.record_task("p2", "t3", "T3", status="completed")

    def test_get_tasks_all(self):
        tasks = self.dashboard.get_tasks("p")
        assert len(tasks) == 2

    def test_get_tasks_by_status(self):
        tasks = self.dashboard.get_tasks("p", status="completed")
        assert len(tasks) == 1
        assert tasks[0].task_id == "t1"

    def test_get_tasks_other_project(self):
        tasks = self.dashboard.get_tasks("p2")
        assert len(tasks) == 1

    def test_get_qa_results(self):
        self.dashboard.record_qa_result("p", "t1", True, 90.0)
        results = self.dashboard.get_qa_results("p")
        assert len(results) == 1

    def test_get_merge_records(self):
        self.dashboard.record_merge("p", "t1", "automatic")
        self.dashboard.record_merge("p", "t2", "manual")
        records = self.dashboard.get_merge_records("p")
        assert len(records) == 2


# -----------------------------------------------------------------------
# DashboardMetrics — snapshot KPIs
# -----------------------------------------------------------------------

class TestDashboardMetricsSnapshot:
    def setup_method(self):
        self.dashboard = DashboardMetrics()

    def test_snapshot_tasks_by_status(self):
        self.dashboard.record_task("p", "t1", "T1", status="completed", completion_seconds=100)
        self.dashboard.record_task("p", "t2", "T2", status="pending")
        self.dashboard.record_task("p", "t3", "T3", status="failed")
        snap = self.dashboard.get_snapshot("p")
        assert snap.tasks_by_status["completed"] == 1
        assert snap.tasks_by_status["pending"] == 1
        assert snap.tasks_by_status["failed"] == 1

    def test_snapshot_avg_completion_by_complexity(self):
        self.dashboard.record_task("p", "t1", "T1", status="completed", complexity="low", completion_seconds=100)
        self.dashboard.record_task("p", "t2", "T2", status="completed", complexity="low", completion_seconds=200)
        self.dashboard.record_task("p", "t3", "T3", status="completed", complexity="high", completion_seconds=600)
        snap = self.dashboard.get_snapshot("p")
        assert snap.avg_completion_by_complexity["low"] == 150.0
        assert snap.avg_completion_by_complexity["high"] == 600.0

    def test_snapshot_qa_first_pass_rate(self):
        self.dashboard.record_qa_result("p", "t1", True, 90.0, attempt=1)
        self.dashboard.record_qa_result("p", "t2", False, 40.0, attempt=1)
        self.dashboard.record_qa_result("p", "t2", True, 80.0, attempt=2)
        snap = self.dashboard.get_snapshot("p")
        assert snap.qa_first_pass_rate == 50.0  # 1 out of 2 first-pass

    def test_snapshot_qa_avg_score(self):
        self.dashboard.record_qa_result("p", "t1", True, 90.0)
        self.dashboard.record_qa_result("p", "t2", True, 80.0)
        snap = self.dashboard.get_snapshot("p")
        assert snap.qa_avg_score == 85.0

    def test_snapshot_tokens(self):
        self.dashboard.record_token_usage("p", "anthropic", "claude", input_tokens=1000, output_tokens=500)
        self.dashboard.record_token_usage("p", "openai", "gpt-4o", input_tokens=2000, output_tokens=1000)
        snap = self.dashboard.get_snapshot("p")
        assert snap.total_tokens == 4500
        assert snap.tokens_by_provider["anthropic"] == 1500
        assert snap.tokens_by_provider["openai"] == 3000

    def test_snapshot_cost(self):
        self.dashboard.record_token_usage("p", "anthropic", "claude", cost=0.01)
        self.dashboard.record_token_usage("p", "openai", "gpt", cost=0.05)
        snap = self.dashboard.get_snapshot("p")
        assert snap.total_cost == 0.06

    def test_snapshot_merge_counts(self):
        self.dashboard.record_merge("p", "t1", "automatic")
        self.dashboard.record_merge("p", "t2", "automatic")
        self.dashboard.record_merge("p", "t3", "manual")
        snap = self.dashboard.get_snapshot("p")
        assert snap.merge_auto_count == 2
        assert snap.merge_manual_count == 1

    def test_snapshot_empty_project(self):
        snap = self.dashboard.get_snapshot("empty_project")
        assert snap.tasks_by_status == {}
        assert snap.qa_first_pass_rate == 0.0
        assert snap.total_tokens == 0


# -----------------------------------------------------------------------
# DashboardMetrics — export
# -----------------------------------------------------------------------

class TestDashboardMetricsExport:
    def setup_method(self):
        self.dashboard = DashboardMetrics()
        self.dashboard.record_task("p", "t1", "T1", status="completed", completion_seconds=100)
        self.dashboard.record_qa_result("p", "t1", True, 90.0)
        self.dashboard.record_token_usage("p", "anthropic", "claude", input_tokens=1000, output_tokens=500, cost=0.01)
        self.dashboard.record_merge("p", "t1", "automatic")

    def test_export_json(self):
        output = self.dashboard.export_report("p", fmt="json")
        data = json.loads(output)
        assert data["project_id"] == "p"
        assert "tasks_by_status" in data

    def test_export_csv(self):
        output = self.dashboard.export_report("p", fmt="csv")
        assert "project_id" in output
        assert "tasks_by_status" in output
        assert "total_tokens" in output

    def test_export_json_parseable(self):
        output = self.dashboard.export_report("p", fmt="json")
        data = json.loads(output)
        assert data["total_cost"] == 0.01

    def test_export_csv_has_rows(self):
        output = self.dashboard.export_report("p", fmt="csv")
        lines = [l for l in output.strip().split("\n") if l]
        assert len(lines) > 5  # header + multiple data rows

    def test_export_empty_project(self):
        output = self.dashboard.export_report("empty", fmt="json")
        data = json.loads(output)
        assert data["total_tokens"] == 0


# -----------------------------------------------------------------------
# DashboardMetrics — stats
# -----------------------------------------------------------------------

class TestDashboardMetricsStats:
    def test_stats_empty(self):
        dashboard = DashboardMetrics()
        stats = dashboard.get_stats()
        assert stats["total_projects"] == 0
        assert stats["total_tasks"] == 0

    def test_stats_with_data(self):
        dashboard = DashboardMetrics()
        dashboard.record_task("p1", "t1", "T1")
        dashboard.record_task("p2", "t2", "T2")
        dashboard.record_qa_result("p1", "t1", True)
        stats = dashboard.get_stats()
        assert stats["total_projects"] == 2
        assert stats["total_tasks"] == 2
        assert stats["total_qa_results"] == 1

    def test_stats_counts_all_record_types(self):
        dashboard = DashboardMetrics()
        dashboard.record_task("p", "t1", "T1")
        dashboard.record_qa_result("p", "t1", True)
        dashboard.record_token_usage("p", "anthropic", "claude")
        dashboard.record_merge("p", "t1", "automatic")
        stats = dashboard.get_stats()
        assert stats["total_token_records"] == 1
        assert stats["total_merge_records"] == 1
