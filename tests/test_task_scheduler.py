"""Tests for Feature 8.1 — Task Scheduling (Cron-like).

Tests for CronExpression, ScheduledTask, TaskChain, TaskQueue, and TaskScheduler.
"""

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from apps.backend.scheduling.scheduler import (
    CronExpression,
    CronField,
    ScheduledTask,
    TaskChain,
    TaskQueue,
    TaskScheduler,
    TaskStatus,
)


# ── CronExpression tests ───────────────────────────────────────────


class TestCronExpression:
    """Tests for the CronExpression parser and matcher."""

    def test_parse_wildcard(self):
        """All-wildcard expression should match every minute."""
        cron = CronExpression("* * * * *")
        assert len(cron.fields[CronField.MINUTE]) == 60
        assert len(cron.fields[CronField.HOUR]) == 24

    def test_parse_specific_values(self):
        """Specific values should be parsed correctly."""
        cron = CronExpression("30 9 15 6 3")
        assert cron.fields[CronField.MINUTE] == {30}
        assert cron.fields[CronField.HOUR] == {9}
        assert cron.fields[CronField.DAY_OF_MONTH] == {15}
        assert cron.fields[CronField.MONTH] == {6}
        assert cron.fields[CronField.DAY_OF_WEEK] == {3}

    def test_parse_range(self):
        """Range (1-5) should produce correct set."""
        cron = CronExpression("0 9-17 * * *")
        assert cron.fields[CronField.HOUR] == set(range(9, 18))

    def test_parse_list(self):
        """Comma-separated list should produce correct set."""
        cron = CronExpression("0,15,30,45 * * * *")
        assert cron.fields[CronField.MINUTE] == {0, 15, 30, 45}

    def test_parse_step(self):
        """Step (*/15) should produce correct values."""
        cron = CronExpression("*/15 * * * *")
        assert cron.fields[CronField.MINUTE] == {0, 15, 30, 45}

    def test_parse_step_with_range(self):
        """Step with range (1-30/5) should work."""
        cron = CronExpression("1-30/10 * * * *")
        assert cron.fields[CronField.MINUTE] == {1, 11, 21}

    def test_parse_invalid_field_count(self):
        """Wrong number of fields should raise ValueError."""
        with pytest.raises(ValueError, match="5 fields"):
            CronExpression("* * *")

    def test_parse_value_out_of_range(self):
        """Value out of range should raise ValueError."""
        with pytest.raises(ValueError, match="out of range"):
            CronExpression("70 * * * *")

    def test_parse_invalid_step(self):
        """Zero step should raise ValueError."""
        with pytest.raises(ValueError):
            CronExpression("*/0 * * * *")

    def test_matches_every_minute(self):
        """Wildcard cron matches any datetime."""
        cron = CronExpression("* * * * *")
        dt = datetime(2026, 2, 20, 14, 30, tzinfo=timezone.utc)
        assert cron.matches(dt)

    def test_matches_specific_time(self):
        """Specific cron matches the correct time."""
        cron = CronExpression("30 14 * * *")
        dt_match = datetime(2026, 2, 20, 14, 30, tzinfo=timezone.utc)
        dt_no_match = datetime(2026, 2, 20, 14, 31, tzinfo=timezone.utc)
        assert cron.matches(dt_match)
        assert not cron.matches(dt_no_match)

    def test_next_occurrence(self):
        """next_occurrence should find the next matching datetime."""
        cron = CronExpression("0 * * * *")
        after = datetime(2026, 2, 20, 14, 30, tzinfo=timezone.utc)
        next_dt = cron.next_occurrence(after)
        assert next_dt.minute == 0
        assert next_dt.hour == 15

    def test_repr(self):
        """__repr__ should include the expression."""
        cron = CronExpression("*/5 * * * *")
        assert "*/5 * * * *" in repr(cron)

    def test_equality(self):
        """Two CronExpressions with same string should be equal."""
        a = CronExpression("0 22 * * *")
        b = CronExpression("0 22 * * *")
        assert a == b

    def test_inequality(self):
        """Different expressions should not be equal."""
        a = CronExpression("0 22 * * *")
        b = CronExpression("0 23 * * *")
        assert a != b


# ── ScheduledTask tests ────────────────────────────────────────────


class TestScheduledTask:
    """Tests for the ScheduledTask dataclass."""

    def test_auto_id_generation(self):
        """Task should get an auto-generated ID if none provided."""
        task = ScheduledTask(name="Test")
        assert task.task_id
        assert len(task.task_id) == 8

    def test_explicit_id(self):
        """Explicit task_id should be preserved."""
        task = ScheduledTask(task_id="my-task", name="Test")
        assert task.task_id == "my-task"

    def test_cron_computes_next_run(self):
        """Task with cron should have next_run set."""
        task = ScheduledTask(name="Cron Task", cron="0 22 * * *")
        assert task.next_run is not None

    def test_run_at_sets_next_run(self):
        """Task with run_at in the future should have next_run set."""
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        task = ScheduledTask(name="Scheduled", run_at=future)
        assert task.next_run == future

    def test_is_recurring(self):
        """Task with cron should be recurring."""
        recurring = ScheduledTask(name="R", cron="* * * * *")
        one_time = ScheduledTask(name="O")
        assert recurring.is_recurring
        assert not one_time.is_recurring

    def test_is_due(self):
        """Task with past next_run should be due."""
        task = ScheduledTask(name="Due")
        task.next_run = datetime.now(timezone.utc) - timedelta(minutes=1)
        assert task.is_due

    def test_is_not_due_when_disabled(self):
        """Disabled task should not be due."""
        task = ScheduledTask(name="Disabled", enabled=False)
        task.next_run = datetime.now(timezone.utc) - timedelta(minutes=1)
        assert not task.is_due

    def test_is_not_due_when_running(self):
        """Running task should not be due."""
        task = ScheduledTask(name="Running", status=TaskStatus.RUNNING)
        task.next_run = datetime.now(timezone.utc) - timedelta(minutes=1)
        assert not task.is_due

    def test_mark_running(self):
        """mark_running should set status and last_run."""
        task = ScheduledTask(name="T")
        task.mark_running()
        assert task.status == TaskStatus.RUNNING
        assert task.last_run is not None

    def test_mark_completed_recurring(self):
        """Completed recurring task should reschedule as PENDING."""
        task = ScheduledTask(name="T", cron="0 * * * *")
        task.mark_running()
        task.mark_completed()
        assert task.status == TaskStatus.PENDING
        assert task.next_run is not None
        assert task.next_run > datetime.now(timezone.utc) - timedelta(minutes=1)

    def test_mark_failed_with_retry(self):
        """Failed task with retries left should stay pending."""
        task = ScheduledTask(name="T", max_retries=3)
        task.mark_failed("error")
        assert task.status == TaskStatus.PENDING
        assert task.retry_count == 1
        assert task.next_run is not None

    def test_mark_failed_exhausted_retries(self):
        """Failed task with no retries left should be FAILED."""
        task = ScheduledTask(name="T", max_retries=0)
        task.mark_failed("error")
        assert task.status == TaskStatus.FAILED
        assert task.retry_count == 1

    def test_to_dict(self):
        """to_dict should include all important fields."""
        task = ScheduledTask(task_id="abc", name="Test", action="do_thing")
        d = task.to_dict()
        assert d["task_id"] == "abc"
        assert d["name"] == "Test"
        assert d["action"] == "do_thing"
        assert "status" in d
        assert "created_at" in d


# ── TaskChain tests ────────────────────────────────────────────────


class TestTaskChain:
    """Tests for the TaskChain dataclass."""

    def test_auto_id(self):
        """Chain should get an auto-generated ID."""
        chain = TaskChain(name="Test Chain")
        assert chain.chain_id.startswith("chain-")

    def test_current_task_id(self):
        """current_task_id should return the task at current_index."""
        chain = TaskChain(task_ids=["a", "b", "c"])
        assert chain.current_task_id == "a"

    def test_advance(self):
        """advance should move to next task."""
        chain = TaskChain(task_ids=["a", "b", "c"])
        next_id = chain.advance()
        assert next_id == "b"
        assert chain.current_index == 1

    def test_advance_to_completion(self):
        """Advancing past last task should complete the chain."""
        chain = TaskChain(task_ids=["a"])
        result = chain.advance()
        assert result is None
        assert chain.is_complete
        assert chain.status == TaskStatus.COMPLETED

    def test_to_dict(self):
        """to_dict should serialize correctly."""
        chain = TaskChain(chain_id="c1", name="C", task_ids=["a", "b"])
        d = chain.to_dict()
        assert d["chain_id"] == "c1"
        assert d["task_ids"] == ["a", "b"]


# ── TaskQueue tests ────────────────────────────────────────────────


class TestTaskQueue:
    """Tests for the TaskQueue priority queue."""

    def test_push_and_size(self):
        """push should add tasks and size should reflect count."""
        q = TaskQueue()
        q.push(ScheduledTask(name="A"))
        q.push(ScheduledTask(name="B"))
        assert q.size == 2

    def test_pop_returns_due_task(self):
        """pop should return a due task."""
        q = TaskQueue()
        task = ScheduledTask(name="Due")
        task.next_run = datetime.now(timezone.utc) - timedelta(minutes=1)
        q.push(task)
        popped = q.pop()
        assert popped is not None
        assert popped.name == "Due"
        assert q.size == 0

    def test_pop_returns_none_when_no_due(self):
        """pop should return None when no tasks are due."""
        q = TaskQueue()
        task = ScheduledTask(name="Future")
        task.next_run = datetime.now(timezone.utc) + timedelta(hours=1)
        q.push(task)
        assert q.pop() is None

    def test_priority_ordering(self):
        """Higher priority tasks (lower number) should come first."""
        q = TaskQueue()
        past = datetime.now(timezone.utc) - timedelta(minutes=1)

        low = ScheduledTask(name="Low", priority=10)
        low.next_run = past
        high = ScheduledTask(name="High", priority=1)
        high.next_run = past

        q.push(low)
        q.push(high)

        first = q.pop()
        assert first.name == "High"

    def test_remove(self):
        """remove should remove a task by ID."""
        q = TaskQueue()
        task = ScheduledTask(task_id="x", name="X")
        q.push(task)
        assert q.remove("x")
        assert q.size == 0

    def test_remove_not_found(self):
        """remove should return False for missing ID."""
        q = TaskQueue()
        assert not q.remove("nonexistent")

    def test_get(self):
        """get should return task without removing it."""
        q = TaskQueue()
        task = ScheduledTask(task_id="y", name="Y")
        q.push(task)
        found = q.get("y")
        assert found is not None
        assert found.name == "Y"
        assert q.size == 1

    def test_list_due(self):
        """list_due should return only due tasks."""
        q = TaskQueue()
        past = datetime.now(timezone.utc) - timedelta(minutes=1)
        future = datetime.now(timezone.utc) + timedelta(hours=1)

        due = ScheduledTask(name="Due")
        due.next_run = past
        not_due = ScheduledTask(name="NotDue")
        not_due.next_run = future

        q.push(due)
        q.push(not_due)
        assert len(q.list_due()) == 1


# ── TaskScheduler tests ───────────────────────────────────────────


class TestTaskScheduler:
    """Tests for the TaskScheduler engine."""

    def test_add_and_list_tasks(self):
        """Adding tasks should make them listable."""
        scheduler = TaskScheduler()
        scheduler.add_task(ScheduledTask(name="A", tags=["test"]))
        scheduler.add_task(ScheduledTask(name="B", tags=["prod"]))
        assert len(scheduler.list_tasks()) == 2
        assert len(scheduler.list_tasks(tag="test")) == 1

    def test_remove_task(self):
        """Removing a task should reduce the count."""
        scheduler = TaskScheduler()
        task = scheduler.add_task(ScheduledTask(task_id="rm", name="Remove"))
        assert scheduler.remove_task("rm")
        assert scheduler.get_task("rm") is None

    def test_pause_and_resume(self):
        """Pausing and resuming should change task state."""
        scheduler = TaskScheduler()
        task = scheduler.add_task(
            ScheduledTask(task_id="pr", name="PauseResume", cron="* * * * *")
        )
        assert scheduler.pause_task("pr")
        assert task.status == TaskStatus.PAUSED
        assert not task.enabled

        assert scheduler.resume_task("pr")
        assert task.status == TaskStatus.PENDING
        assert task.enabled

    def test_register_and_execute_handler(self):
        """Registered handler should be called on execution."""
        scheduler = TaskScheduler()
        mock_handler = MagicMock(return_value={"result": "ok"})
        scheduler.register_handler("test_action", mock_handler)

        task = ScheduledTask(
            task_id="exec",
            name="Execute",
            action="test_action",
            metadata={"key": "value"},
        )
        result = scheduler.execute_task(task)
        assert result["success"]
        mock_handler.assert_called_once_with({"key": "value"})

    def test_execute_no_handler(self):
        """Executing with no handler should fail gracefully."""
        scheduler = TaskScheduler()
        task = ScheduledTask(name="No Handler", action="missing")
        result = scheduler.execute_task(task)
        assert not result["success"]
        assert "error" in result

    def test_execute_handler_exception(self):
        """Handler exception should be caught and task marked failed."""
        scheduler = TaskScheduler()
        scheduler.register_handler("fail", MagicMock(side_effect=RuntimeError("boom")))
        task = ScheduledTask(name="Fail", action="fail", max_retries=1)
        result = scheduler.execute_task(task)
        assert not result["success"]
        assert task.retry_count == 1

    def test_tick_executes_due_tasks(self):
        """tick() should find and execute due tasks."""
        scheduler = TaskScheduler()
        mock_handler = MagicMock(return_value="done")
        scheduler.register_handler("tick_action", mock_handler)

        task = ScheduledTask(
            task_id="tick",
            name="Tick Task",
            action="tick_action",
        )
        task.next_run = datetime.now(timezone.utc) - timedelta(minutes=1)
        scheduler.add_task(task)

        results = scheduler.tick()
        assert len(results) == 1
        assert results[0]["success"]

    def test_chain_progression(self):
        """Chain should advance when a task completes."""
        scheduler = TaskScheduler()
        mock_handler = MagicMock(return_value="ok")
        scheduler.register_handler("chain_action", mock_handler)

        t1 = ScheduledTask(task_id="c1", name="Chain1", action="chain_action")
        t1.next_run = datetime.now(timezone.utc) - timedelta(minutes=1)
        t2 = ScheduledTask(task_id="c2", name="Chain2", action="chain_action", enabled=False)

        scheduler.add_task(t1)
        scheduler.add_task(t2)

        chain = TaskChain(task_ids=["c1", "c2"])
        scheduler.add_chain(chain)

        # Execute first task
        scheduler.tick()

        # Second task should now be enabled
        assert t2.enabled

    def test_get_execution_log(self):
        """Execution log should record results."""
        scheduler = TaskScheduler()
        scheduler.register_handler("log_action", MagicMock(return_value="ok"))
        task = ScheduledTask(name="Log", action="log_action")
        scheduler.execute_task(task)
        log = scheduler.get_execution_log()
        assert len(log) == 1

    def test_get_stats(self):
        """get_stats should return correct counts."""
        scheduler = TaskScheduler()
        scheduler.add_task(ScheduledTask(name="A"))
        stats = scheduler.get_stats()
        assert stats["total_tasks"] == 1
        assert stats["running"] is False

    def test_start_stop(self):
        """start/stop should control the background thread."""
        scheduler = TaskScheduler(check_interval=1)
        scheduler.start()
        assert scheduler.is_running
        scheduler.stop()
        assert not scheduler.is_running
