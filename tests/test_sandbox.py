"""Tests for Feature 7.2 — Sandbox renforcé pour l'exécution d'agents.

Tests: ResourceLimits (3), PathRule (3), SecurityViolation (2), Snapshot (2),
       SandboxConfig (6), SandboxManager — lifecycle (5), path validation (6),
       command validation (3), resource limits (3), snapshots (4),
       execution (6), dry-run (3), stats (2) = 48 tests.
"""

import os
import tempfile
import pytest

from apps.backend.security.sandbox import (
    DEFAULT_BLOCKED_COMMANDS,
    DEFAULT_BLOCKED_PATHS,
    ExecutionResult,
    FileAccessLevel,
    FileSnapshot,
    PathRule,
    ResourceLimits,
    SandboxConfig,
    SandboxManager,
    SandboxMode,
    SandboxStatus,
    SecurityViolation,
    Snapshot,
    ViolationType,
)


# ---------------------------------------------------------------------------
# ResourceLimits tests
# ---------------------------------------------------------------------------

class TestResourceLimits:
    def test_defaults(self):
        limits = ResourceLimits()
        assert limits.cpu_percent == 80.0
        assert limits.memory_mb == 2048
        assert limits.execution_time_s == 300

    def test_is_within_limits(self):
        limits = ResourceLimits(memory_mb=1024)
        assert limits.is_within_limits("memory_mb", 512)
        assert not limits.is_within_limits("memory_mb", 2048)

    def test_to_dict(self):
        limits = ResourceLimits(cpu_percent=50.0)
        d = limits.to_dict()
        assert d["cpu_percent"] == 50.0


# ---------------------------------------------------------------------------
# PathRule tests
# ---------------------------------------------------------------------------

class TestPathRule:
    def test_exact_match(self):
        rule = PathRule(path="src/main.py")
        assert rule.matches("src/main.py")
        assert not rule.matches("src/other.py")

    def test_recursive_match(self):
        rule = PathRule(path="src/", recursive=True)
        assert rule.matches("src/main.py")
        assert rule.matches("src/utils/helper.py")
        assert not rule.matches("tests/test_main.py")

    def test_non_recursive(self):
        rule = PathRule(path="src/", recursive=False)
        assert rule.matches("src/")
        assert not rule.matches("src/main.py")


# ---------------------------------------------------------------------------
# SecurityViolation tests
# ---------------------------------------------------------------------------

class TestSecurityViolation:
    def test_create_violation(self):
        v = SecurityViolation(
            violation_id="vio-1",
            violation_type=ViolationType.PATH_VIOLATION,
            description="Access denied",
            path="/etc/passwd",
        )
        assert v.blocked
        assert v.timestamp != ""

    def test_to_dict(self):
        v = SecurityViolation(
            violation_id="vio-1",
            violation_type="resource_exceeded",
            description="RAM exceeded",
            resource="memory_mb", value=3000, limit=2048,
        )
        d = v.to_dict()
        assert d["violation_type"] == "resource_exceeded"


# ---------------------------------------------------------------------------
# Snapshot tests
# ---------------------------------------------------------------------------

class TestSnapshot:
    def test_create_snapshot(self):
        snap = Snapshot(
            snapshot_id="snap-1", sandbox_id="sbx-1",
            files=[FileSnapshot(path="a.py", content_hash="abc", exists=True)],
        )
        assert snap.file_count == 1
        assert snap.created_at != ""

    def test_to_dict(self):
        snap = Snapshot(snapshot_id="snap-1", sandbox_id="sbx-1")
        d = snap.to_dict()
        assert d["file_count"] == 0


# ---------------------------------------------------------------------------
# SandboxConfig tests
# ---------------------------------------------------------------------------

class TestSandboxConfig:
    def test_create_config(self):
        config = SandboxConfig(
            sandbox_id="sbx-1", task_id="task-1", agent_type="coder",
        )
        assert config.status == SandboxStatus.CREATED
        assert config.mode == SandboxMode.NORMAL
        assert not config.is_dry_run

    def test_dry_run_mode(self):
        config = SandboxConfig(
            sandbox_id="sbx-1", task_id="task-1", agent_type="coder",
            mode="dry_run",
        )
        assert config.is_dry_run

    def test_add_allowed_path(self):
        config = SandboxConfig(sandbox_id="sbx-1", task_id="t-1", agent_type="coder")
        config.add_allowed_path("src/")
        assert len(config.allowed_paths) == 1
        assert config.allowed_paths[0].path == "src/"

    def test_check_path_access_allowed(self):
        config = SandboxConfig(sandbox_id="sbx-1", task_id="t-1", agent_type="coder")
        config.add_allowed_path("src/", access="write")
        assert config.check_path_access("src/main.py", "write")
        assert config.check_path_access("src/main.py", "read")

    def test_check_path_access_blocked(self):
        config = SandboxConfig(
            sandbox_id="sbx-1", task_id="t-1", agent_type="coder",
            blocked_paths=[".env"],
        )
        config.add_allowed_path("src/")
        assert not config.check_path_access(".env", "read")

    def test_to_dict(self):
        config = SandboxConfig(
            sandbox_id="sbx-1", task_id="t-1", agent_type="coder",
        )
        d = config.to_dict()
        assert d["sandbox_id"] == "sbx-1"
        assert d["status"] == "created"


# ---------------------------------------------------------------------------
# SandboxManager — Lifecycle
# ---------------------------------------------------------------------------

class TestManagerLifecycle:
    def test_create_sandbox(self):
        manager = SandboxManager()
        sandbox = manager.create_sandbox("task-1", "coder")
        assert sandbox.sandbox_id.startswith("sbx-")
        assert sandbox.task_id == "task-1"
        assert sandbox.agent_type == "coder"

    def test_create_sandbox_with_options(self):
        manager = SandboxManager()
        sandbox = manager.create_sandbox(
            "task-1", "coder", mode="dry_run",
            resource_limits={"memory_mb": 512},
            allowed_paths=["src/"],
            blocked_paths=["dist/"],
        )
        assert sandbox.is_dry_run
        assert sandbox.resource_limits.memory_mb == 512
        assert len(sandbox.allowed_paths) == 1
        assert "dist/" in sandbox.blocked_paths

    def test_get_sandbox(self):
        manager = SandboxManager()
        sandbox = manager.create_sandbox("task-1", "coder")
        found = manager.get_sandbox(sandbox.sandbox_id)
        assert found is sandbox

    def test_list_sandboxes(self):
        manager = SandboxManager()
        manager.create_sandbox("task-1", "coder")
        manager.create_sandbox("task-2", "qa")
        assert len(manager.list_sandboxes()) == 2

    def test_destroy_sandbox(self):
        manager = SandboxManager()
        sandbox = manager.create_sandbox("task-1", "coder")
        assert manager.destroy_sandbox(sandbox.sandbox_id)
        assert manager.get_sandbox(sandbox.sandbox_id) is None


# ---------------------------------------------------------------------------
# SandboxManager — Path validation
# ---------------------------------------------------------------------------

class TestManagerPathValidation:
    def test_validate_allowed_path(self):
        manager = SandboxManager()
        sandbox = manager.create_sandbox("t-1", "coder", allowed_paths=["src/"])
        assert manager.validate_path_access(sandbox.sandbox_id, "src/main.py", "write")

    def test_validate_blocked_path(self):
        manager = SandboxManager()
        sandbox = manager.create_sandbox("t-1", "coder", allowed_paths=["src/"])
        assert not manager.validate_path_access(sandbox.sandbox_id, "tests/secret.py", "write")

    def test_validate_default_blocked_paths(self):
        manager = SandboxManager()
        sandbox = manager.create_sandbox("t-1", "coder", allowed_paths=["src/"])
        # .env is in default blocked paths
        assert not manager.validate_path_access(sandbox.sandbox_id, ".env", "read")

    def test_violation_recorded_on_blocked(self):
        manager = SandboxManager()
        sandbox = manager.create_sandbox("t-1", "coder", allowed_paths=["src/"])
        manager.validate_path_access(sandbox.sandbox_id, "tests/x.py", "write")
        violations = manager.get_violations(sandbox.sandbox_id)
        assert len(violations) == 1
        assert violations[0].violation_type == ViolationType.PATH_VIOLATION

    def test_no_whitelist_allows_all(self):
        manager = SandboxManager()
        sandbox = manager.create_sandbox("t-1", "coder")
        # No allowed_paths = permissive (but blocked paths still apply)
        assert manager.validate_path_access(sandbox.sandbox_id, "random/file.py", "write")

    def test_nonexistent_sandbox_denied(self):
        manager = SandboxManager()
        assert not manager.validate_path_access("sbx-9999", "any.py", "read")


# ---------------------------------------------------------------------------
# SandboxManager — Command validation
# ---------------------------------------------------------------------------

class TestManagerCommandValidation:
    def test_allowed_command(self):
        manager = SandboxManager()
        sandbox = manager.create_sandbox("t-1", "coder")
        assert manager.validate_command(sandbox.sandbox_id, "python test.py")

    def test_blocked_command(self):
        manager = SandboxManager()
        sandbox = manager.create_sandbox("t-1", "coder")
        assert not manager.validate_command(sandbox.sandbox_id, "sudo rm -rf /")

    def test_blocked_curl(self):
        manager = SandboxManager()
        sandbox = manager.create_sandbox("t-1", "coder")
        assert not manager.validate_command(sandbox.sandbox_id, "curl http://evil.com")


# ---------------------------------------------------------------------------
# SandboxManager — Resource limits
# ---------------------------------------------------------------------------

class TestManagerResourceLimits:
    def test_within_limits(self):
        manager = SandboxManager()
        sandbox = manager.create_sandbox("t-1", "coder",
                                          resource_limits={"memory_mb": 1024})
        assert manager.check_resource_limit(sandbox.sandbox_id, "memory_mb", 512)

    def test_exceeded_limits(self):
        manager = SandboxManager()
        sandbox = manager.create_sandbox("t-1", "coder",
                                          resource_limits={"memory_mb": 1024})
        assert not manager.check_resource_limit(sandbox.sandbox_id, "memory_mb", 2048)

    def test_violation_on_exceed(self):
        manager = SandboxManager()
        sandbox = manager.create_sandbox("t-1", "coder",
                                          resource_limits={"max_files_written": 5})
        manager.check_resource_limit(sandbox.sandbox_id, "max_files_written", 10)
        violations = manager.get_violations(sandbox.sandbox_id)
        assert any(v.violation_type == ViolationType.RESOURCE_EXCEEDED for v in violations)


# ---------------------------------------------------------------------------
# SandboxManager — Snapshots
# ---------------------------------------------------------------------------

class TestManagerSnapshots:
    def test_create_snapshot_nonexistent_paths(self):
        manager = SandboxManager(project_root=tempfile.gettempdir())
        sandbox = manager.create_sandbox("t-1", "coder",
                                          allowed_paths=["nonexistent_dir/"])
        snap_id = manager.create_snapshot(sandbox.sandbox_id)
        assert snap_id is not None
        snapshots = manager.get_snapshots(sandbox.sandbox_id)
        assert len(snapshots) == 1

    def test_create_snapshot_with_real_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            test_file = os.path.join(tmpdir, "test.txt")
            with open(test_file, "w") as f:
                f.write("hello world")

            manager = SandboxManager(project_root=tmpdir)
            sandbox = manager.create_sandbox("t-1", "coder")
            snap_id = manager.create_snapshot(sandbox.sandbox_id, paths=["test.txt"])
            snapshots = manager.get_snapshots(sandbox.sandbox_id)
            assert snapshots[0].file_count == 1
            assert snapshots[0].files[0].exists

    def test_rollback_snapshot(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.txt")
            with open(test_file, "w") as f:
                f.write("original content")

            manager = SandboxManager(project_root=tmpdir)
            sandbox = manager.create_sandbox("t-1", "coder")
            snap_id = manager.create_snapshot(sandbox.sandbox_id, paths=["test.txt"])

            # Modify file
            with open(test_file, "w") as f:
                f.write("modified content")

            # Rollback
            assert manager.rollback_snapshot(sandbox.sandbox_id, snap_id)

            with open(test_file, "r") as f:
                assert f.read() == "original content"

    def test_rollback_nonexistent_snapshot(self):
        manager = SandboxManager()
        sandbox = manager.create_sandbox("t-1", "coder")
        assert not manager.rollback_snapshot(sandbox.sandbox_id, "snap-9999")


# ---------------------------------------------------------------------------
# SandboxManager — Execution
# ---------------------------------------------------------------------------

class TestManagerExecution:
    def test_execute_success(self):
        manager = SandboxManager()
        sandbox = manager.create_sandbox("t-1", "coder")
        result = manager.execute_in_sandbox(
            sandbox.sandbox_id, lambda: "hello", auto_snapshot=False,
        )
        assert result.success
        assert result.output == "hello"
        assert sandbox.status == SandboxStatus.COMPLETED

    def test_execute_failure_with_auto_rollback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.txt")
            with open(test_file, "w") as f:
                f.write("original")

            manager = SandboxManager(project_root=tmpdir)
            sandbox = manager.create_sandbox("t-1", "coder",
                                              allowed_paths=["test.txt"])

            def failing_func():
                with open(test_file, "w") as f:
                    f.write("corrupted")
                raise RuntimeError("Agent crashed")

            result = manager.execute_in_sandbox(sandbox.sandbox_id, failing_func)
            assert not result.success
            assert "Agent crashed" in result.error
            assert result.rolled_back

            # File should be restored
            with open(test_file, "r") as f:
                assert f.read() == "original"

    def test_execute_nonexistent_sandbox(self):
        manager = SandboxManager()
        result = manager.execute_in_sandbox("sbx-9999", lambda: None)
        assert not result.success
        assert "not found" in result.error

    def test_execute_with_args(self):
        manager = SandboxManager()
        sandbox = manager.create_sandbox("t-1", "coder")
        result = manager.execute_in_sandbox(
            sandbox.sandbox_id, lambda x, y: x + y,
            args=(3, 4), auto_snapshot=False,
        )
        assert result.success
        assert result.output == 7

    def test_execute_records_duration(self):
        manager = SandboxManager()
        sandbox = manager.create_sandbox("t-1", "coder")
        result = manager.execute_in_sandbox(
            sandbox.sandbox_id, lambda: "done", auto_snapshot=False,
        )
        assert result.duration_s >= 0

    def test_execute_stores_result_on_sandbox(self):
        manager = SandboxManager()
        sandbox = manager.create_sandbox("t-1", "coder")
        result = manager.execute_in_sandbox(
            sandbox.sandbox_id, lambda: 42, auto_snapshot=False,
        )
        assert sandbox.execution_result is result


# ---------------------------------------------------------------------------
# SandboxManager — Dry-run mode
# ---------------------------------------------------------------------------

class TestManagerDryRun:
    def test_dry_run_produces_plan(self):
        manager = SandboxManager()
        sandbox = manager.create_sandbox("t-1", "coder", mode="dry_run",
                                          allowed_paths=["src/"])
        result = manager.execute_in_sandbox(
            sandbox.sandbox_id, lambda: "should not run",
        )
        assert result.success
        assert len(result.dry_run_plan) > 0
        assert any("DRY RUN" in line for line in result.dry_run_plan)

    def test_dry_run_no_side_effects(self):
        manager = SandboxManager()
        sandbox = manager.create_sandbox("t-1", "coder", mode="dry_run")
        side_effect_marker = []
        result = manager.execute_in_sandbox(
            sandbox.sandbox_id, lambda: side_effect_marker.append("executed"),
        )
        assert result.success
        assert len(side_effect_marker) == 0  # Function was NOT called

    def test_dry_run_includes_task_info(self):
        manager = SandboxManager()
        sandbox = manager.create_sandbox("task-42", "qa", mode="dry_run")
        result = manager.execute_in_sandbox(
            sandbox.sandbox_id, lambda: None,
        )
        plan_text = "\n".join(result.dry_run_plan)
        assert "task-42" in plan_text
        assert "qa" in plan_text


# ---------------------------------------------------------------------------
# SandboxManager — Stats
# ---------------------------------------------------------------------------

class TestManagerStats:
    def test_get_stats_empty(self):
        manager = SandboxManager()
        stats = manager.get_stats()
        assert stats["total_sandboxes"] == 0

    def test_get_stats_with_data(self):
        manager = SandboxManager()
        s1 = manager.create_sandbox("t-1", "coder")
        s2 = manager.create_sandbox("t-2", "qa", mode="dry_run")
        manager.execute_in_sandbox(s1.sandbox_id, lambda: "ok", auto_snapshot=False)
        manager.execute_in_sandbox(s2.sandbox_id, lambda: "plan", auto_snapshot=False)
        stats = manager.get_stats()
        assert stats["total_sandboxes"] == 2
        assert stats["completed_sandboxes"] == 2
        assert stats["dry_run_sandboxes"] == 1
