"""
Tests for Auto-Fix Loop
========================

Tests the intelligent auto-fix loop functionality.
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.backend.qa.auto_fix_loop import (
    DEFAULT_MAX_AUTO_FIX_ATTEMPTS,
    AutoFixAttempt,
    AutoFixLoop,
    TestResult,
    run_auto_fix_loop,
)
from apps.backend.qa.auto_fix_metrics import (
    AutoFixMetricsTracker,
    AutoFixStats,
    get_auto_fix_dashboard_data,
    get_auto_fix_stats,
    print_auto_fix_summary,
    record_auto_fix_run,
)


@pytest.fixture
def mock_project_dir(tmp_path):
    """Create a mock project directory."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    return project_dir


@pytest.fixture
def mock_spec_dir(tmp_path):
    """Create a mock spec directory."""
    spec_dir = tmp_path / ".auto-claude" / "specs" / "001-test-spec"
    spec_dir.mkdir(parents=True)
    
    # Create implementation_plan.json
    plan = {
        "spec_name": "test-spec",
        "subtasks": []
    }
    (spec_dir / "implementation_plan.json").write_text(json.dumps(plan))
    
    return spec_dir


@pytest.fixture
def mock_test_discovery():
    """Mock test discovery."""
    with patch("apps.backend.qa.auto_fix_loop.TestDiscovery") as mock:
        discovery_instance = MagicMock()
        discovery_instance.discover.return_value = MagicMock(
            has_tests=True,
            test_command="pytest",
            frameworks=[MagicMock(name="pytest")],
        )
        mock.return_value = discovery_instance
        yield mock


@pytest.fixture
def mock_client():
    """Mock Claude client."""
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


class TestAutoFixLoop:
    """Tests for AutoFixLoop class."""

    def test_initialization(self, mock_project_dir, mock_spec_dir):
        """Test AutoFixLoop initialization."""
        loop = AutoFixLoop(
            project_dir=mock_project_dir,
            spec_dir=mock_spec_dir,
            model="claude-opus-4-5-20251101",
            verbose=True,
        )

        assert loop.project_dir == mock_project_dir
        assert loop.spec_dir == mock_spec_dir
        assert loop.model == "claude-opus-4-5-20251101"
        assert loop.verbose is True
        assert loop.attempts == []

    @pytest.mark.asyncio
    async def test_run_tests_success(
        self, mock_project_dir, mock_spec_dir, mock_test_discovery
    ):
        """Test successful test execution."""
        loop = AutoFixLoop(mock_project_dir, mock_spec_dir, "test-model")

        # Mock subprocess
        with patch(
            "apps.backend.qa.auto_fix_loop.asyncio.create_subprocess_shell"
        ) as mock_subprocess:
            mock_proc = AsyncMock()
            mock_proc.communicate.return_value = (
                b"5 passed in 1.2s",
                b"",
            )
            mock_proc.returncode = 0
            mock_subprocess.return_value = mock_proc

            result = await loop._run_tests()

            assert result.executed is True
            assert result.passed is True
            assert result.test_count > 0
            assert result.failed_count == 0

    @pytest.mark.asyncio
    async def test_run_tests_failure(
        self, mock_project_dir, mock_spec_dir, mock_test_discovery
    ):
        """Test failed test execution."""
        loop = AutoFixLoop(mock_project_dir, mock_spec_dir, "test-model")

        # Mock subprocess
        with patch(
            "apps.backend.qa.auto_fix_loop.asyncio.create_subprocess_shell"
        ) as mock_subprocess:
            mock_proc = AsyncMock()
            mock_proc.communicate.return_value = (
                b"3 passed, 2 failed in 1.2s",
                b"AssertionError: expected 5 but got 3",
            )
            mock_proc.returncode = 1
            mock_subprocess.return_value = mock_proc

            result = await loop._run_tests()

            assert result.executed is True
            assert result.passed is False
            assert result.test_count > 0
            assert result.failed_count == 2

    @pytest.mark.asyncio
    async def test_run_tests_timeout(
        self, mock_project_dir, mock_spec_dir, mock_test_discovery
    ):
        """Test test execution timeout."""
        loop = AutoFixLoop(mock_project_dir, mock_spec_dir, "test-model")

        # Mock subprocess with timeout
        with patch(
            "apps.backend.qa.auto_fix_loop.asyncio.create_subprocess_shell"
        ) as mock_subprocess:
            mock_proc = AsyncMock()
            mock_proc.communicate.side_effect = asyncio.TimeoutError()
            mock_proc.kill = MagicMock()
            mock_subprocess.return_value = mock_proc

            result = await loop._run_tests()

            assert result.executed is True
            assert result.passed is False
            assert "Timeout" in result.error

    def test_parse_test_counts_pytest(self, mock_project_dir, mock_spec_dir):
        """Test parsing pytest output."""
        loop = AutoFixLoop(mock_project_dir, mock_spec_dir, "test-model")

        output = "5 passed, 2 failed in 1.2s"
        total, failed = loop._parse_test_counts(output)

        assert total == 7
        assert failed == 2

    def test_parse_test_counts_jest(self, mock_project_dir, mock_spec_dir):
        """Test parsing jest output."""
        loop = AutoFixLoop(mock_project_dir, mock_spec_dir, "test-model")

        output = "Tests: 2 failed, 5 passed, 7 total"
        total, failed = loop._parse_test_counts(output)

        assert total == 7
        assert failed == 2

    def test_analyze_failure_patterns(self, mock_project_dir, mock_spec_dir):
        """Test error pattern analysis."""
        loop = AutoFixLoop(mock_project_dir, mock_spec_dir, "test-model")

        # Test assertion failure
        result = TestResult(
            executed=True,
            passed=False,
            output="AssertionError: expected 5 but got 3",
            error="assertion failed",
            duration=1.0,
        )
        pattern = loop._analyze_failure(result)
        assert pattern == "assertion_failure"

        # Test timeout
        result = TestResult(
            executed=True,
            passed=False,
            output="Test timeout after 30 seconds",
            error="timeout",
            duration=30.0,
        )
        pattern = loop._analyze_failure(result)
        assert pattern == "timeout"

        # Test import error
        result = TestResult(
            executed=True,
            passed=False,
            output="ImportError: No module named 'foo'",
            error="import error",
            duration=0.5,
        )
        pattern = loop._analyze_failure(result)
        assert pattern == "import_error"

    @pytest.mark.asyncio
    async def test_create_fix_request(
        self, mock_project_dir, mock_spec_dir, mock_test_discovery
    ):
        """Test fix request creation."""
        loop = AutoFixLoop(mock_project_dir, mock_spec_dir, "test-model")

        test_result = TestResult(
            executed=True,
            passed=False,
            output="test failed",
            error="assertion error",
            duration=1.0,
            test_count=5,
            failed_count=2,
        )

        await loop._create_fix_request(test_result, "assertion_failure", "memory context")

        fix_request_file = mock_spec_dir / "QA_FIX_REQUEST.md"
        assert fix_request_file.exists()

        content = fix_request_file.read_text()
        assert "Test Execution Failed" in content
        assert "assertion_failure" in content
        assert "memory context" in content

    @pytest.mark.asyncio
    async def test_run_until_green_success_first_try(
        self, mock_project_dir, mock_spec_dir, mock_test_discovery, mock_client
    ):
        """Test successful fix on first attempt."""
        loop = AutoFixLoop(mock_project_dir, mock_spec_dir, "test-model")

        # Mock tests passing on first run
        with patch.object(loop, "_run_tests") as mock_run_tests:
            mock_run_tests.return_value = TestResult(
                executed=True,
                passed=True,
                output="5 passed",
                error=None,
                duration=1.0,
                test_count=5,
                failed_count=0,
            )

            with patch.object(loop, "_load_memory_context") as mock_memory:
                mock_memory.return_value = "memory context"

                with patch.object(loop, "_save_success_to_memory"):
                    with patch.object(loop, "_update_metrics"):
                        success = await loop.run_until_green(max_attempts=5)

        assert success is True
        assert len(loop.attempts) == 1
        assert loop.attempts[0].test_result.passed is True

    @pytest.mark.asyncio
    async def test_run_until_green_success_after_fixes(
        self, mock_project_dir, mock_spec_dir, mock_test_discovery, mock_client
    ):
        """Test successful fix after multiple attempts."""
        loop = AutoFixLoop(mock_project_dir, mock_spec_dir, "test-model")

        # Mock tests failing first, then passing
        call_count = [0]

        async def mock_run_tests():
            call_count[0] += 1
            if call_count[0] == 1:
                return TestResult(
                    executed=True,
                    passed=False,
                    output="2 failed",
                    error="assertion failed",
                    duration=1.0,
                    test_count=5,
                    failed_count=2,
                )
            else:
                return TestResult(
                    executed=True,
                    passed=True,
                    output="5 passed",
                    error=None,
                    duration=1.0,
                    test_count=5,
                    failed_count=0,
                )

        with patch.object(loop, "_run_tests", side_effect=mock_run_tests):
            with patch.object(loop, "_load_memory_context") as mock_memory:
                mock_memory.return_value = "memory context"

                with patch.object(loop, "_create_fix_request"):
                    with patch.object(loop, "_apply_fix") as mock_apply:
                        mock_apply.return_value = ("fixed", "fix applied")

                        with patch.object(loop, "_save_success_to_memory"):
                            with patch.object(loop, "_update_metrics"):
                                success = await loop.run_until_green(max_attempts=5)

        assert success is True
        assert len(loop.attempts) == 2

    @pytest.mark.asyncio
    async def test_run_until_green_max_attempts(
        self, mock_project_dir, mock_spec_dir, mock_test_discovery
    ):
        """Test max attempts reached."""
        loop = AutoFixLoop(mock_project_dir, mock_spec_dir, "test-model")

        # Mock tests always failing
        with patch.object(loop, "_run_tests") as mock_run_tests:
            mock_run_tests.return_value = TestResult(
                executed=True,
                passed=False,
                output="2 failed",
                error="assertion failed",
                duration=1.0,
                test_count=5,
                failed_count=2,
            )

            with patch.object(loop, "_load_memory_context") as mock_memory:
                mock_memory.return_value = "memory context"

                with patch.object(loop, "_create_fix_request"):
                    with patch.object(loop, "_apply_fix") as mock_apply:
                        mock_apply.return_value = ("fixed", "fix applied")

                        with patch.object(loop, "_save_failure_to_memory"):
                            with patch.object(loop, "_update_metrics"):
                                with patch.object(loop, "_escalate_to_human"):
                                    success = await loop.run_until_green(max_attempts=3)

        assert success is False
        assert len(loop.attempts) == 3


class TestAutoFixMetrics:
    """Tests for AutoFixMetricsTracker."""

    def test_load_stats_no_file(self, mock_spec_dir):
        """Test loading stats when file doesn't exist."""
        # Remove implementation_plan.json
        (mock_spec_dir / "implementation_plan.json").unlink()

        tracker = AutoFixMetricsTracker(mock_spec_dir)
        stats = tracker.load_stats()

        assert stats.total_runs == 0
        assert stats.success_rate == 0.0

    def test_load_stats_no_stats(self, mock_spec_dir):
        """Test loading stats when stats don't exist."""
        tracker = AutoFixMetricsTracker(mock_spec_dir)
        stats = tracker.load_stats()

        assert stats.total_runs == 0
        assert stats.success_rate == 0.0

    def test_record_run_success(self, mock_spec_dir):
        """Test recording a successful run."""
        tracker = AutoFixMetricsTracker(mock_spec_dir)

        tracker.record_run(
            success=True,
            attempts=2,
            duration=45.3,
            error_patterns=["assertion_failure"],
            test_framework="pytest",
        )

        stats = tracker.load_stats()
        assert stats.total_runs == 1
        assert stats.successful_runs == 1
        assert stats.success_rate == 1.0
        assert stats.average_attempts == 2.0

    def test_record_run_failure(self, mock_spec_dir):
        """Test recording a failed run."""
        tracker = AutoFixMetricsTracker(mock_spec_dir)

        tracker.record_run(
            success=False,
            attempts=5,
            duration=120.5,
            error_patterns=["import_error", "type_error"],
            test_framework="pytest",
        )

        stats = tracker.load_stats()
        assert stats.total_runs == 1
        assert stats.successful_runs == 0
        assert stats.success_rate == 0.0
        assert stats.average_attempts == 5.0

    def test_record_multiple_runs(self, mock_spec_dir):
        """Test recording multiple runs."""
        tracker = AutoFixMetricsTracker(mock_spec_dir)

        # Record successful run
        tracker.record_run(success=True, attempts=2, duration=30.0)

        # Record failed run
        tracker.record_run(success=False, attempts=5, duration=60.0)

        # Record another successful run
        tracker.record_run(success=True, attempts=3, duration=45.0)

        stats = tracker.load_stats()
        assert stats.total_runs == 3
        assert stats.successful_runs == 2
        assert stats.success_rate == pytest.approx(0.666, rel=0.01)
        assert stats.average_attempts == pytest.approx(3.333, rel=0.01)

    def test_common_patterns_tracking(self, mock_spec_dir):
        """Test tracking common error patterns."""
        tracker = AutoFixMetricsTracker(mock_spec_dir)

        tracker.record_run(
            success=True,
            attempts=2,
            duration=30.0,
            error_patterns=["assertion_failure"],
        )
        tracker.record_run(
            success=True,
            attempts=3,
            duration=40.0,
            error_patterns=["assertion_failure", "import_error"],
        )
        tracker.record_run(
            success=False,
            attempts=5,
            duration=60.0,
            error_patterns=["type_error"],
        )

        stats = tracker.load_stats()
        assert stats.common_patterns["assertion_failure"] == 2
        assert stats.common_patterns["import_error"] == 1
        assert stats.common_patterns["type_error"] == 1

    def test_get_dashboard_data(self, mock_spec_dir):
        """Test getting dashboard-ready data."""
        tracker = AutoFixMetricsTracker(mock_spec_dir)

        tracker.record_run(success=True, attempts=2, duration=30.0)
        tracker.record_run(success=True, attempts=3, duration=40.0)

        dashboard = tracker.get_dashboard_data()

        assert dashboard["totalRuns"] == 2
        assert dashboard["successfulRuns"] == 2
        assert dashboard["successRate"] == 100.0
        assert dashboard["averageAttempts"] == 2.5
        assert "commonPatterns" in dashboard
        assert "recentRuns" in dashboard

    def test_get_summary(self, mock_spec_dir):
        """Test getting human-readable summary."""
        tracker = AutoFixMetricsTracker(mock_spec_dir)

        tracker.record_run(
            success=True,
            attempts=2,
            duration=30.0,
            error_patterns=["assertion_failure"],
        )

        summary = tracker.get_summary()

        assert "Total Runs: 1" in summary
        assert "Successful: 1" in summary
        assert "80.0%" in summary or "100.0%" in summary

    def test_reset_stats(self, mock_spec_dir):
        """Test resetting statistics."""
        tracker = AutoFixMetricsTracker(mock_spec_dir)

        # Add some data
        tracker.record_run(success=True, attempts=2, duration=30.0)
        tracker.record_run(success=False, attempts=5, duration=60.0)

        # Reset
        tracker.reset_stats()

        # Verify reset
        stats = tracker.load_stats()
        assert stats.total_runs == 0
        assert stats.successful_runs == 0
        assert stats.success_rate == 0.0


class TestAutoFixPublicAPI:
    """Tests for public API functions."""

    @pytest.mark.asyncio
    async def test_run_auto_fix_loop(
        self, mock_project_dir, mock_spec_dir, mock_test_discovery
    ):
        """Test run_auto_fix_loop public function."""
        with patch(
            "apps.backend.qa.auto_fix_loop.AutoFixLoop"
        ) as MockAutoFixLoop:
            mock_instance = MagicMock()
            mock_instance.run_until_green = AsyncMock(return_value=True)
            MockAutoFixLoop.return_value = mock_instance

            success = await run_auto_fix_loop(
                mock_project_dir,
                mock_spec_dir,
                "test-model",
                max_attempts=5,
                verbose=True,
            )

            assert success is True
            MockAutoFixLoop.assert_called_once_with(
                mock_project_dir, mock_spec_dir, "test-model", True
            )
            mock_instance.run_until_green.assert_called_once_with(5)

    def test_get_auto_fix_stats(self, mock_spec_dir):
        """Test get_auto_fix_stats public function."""
        # Record some runs first
        tracker = AutoFixMetricsTracker(mock_spec_dir)
        tracker.record_run(success=True, attempts=2, duration=30.0)

        stats = get_auto_fix_stats(mock_spec_dir)

        assert stats.total_runs == 1
        assert stats.successful_runs == 1

    def test_record_auto_fix_run(self, mock_spec_dir):
        """Test record_auto_fix_run public function."""
        record_auto_fix_run(
            mock_spec_dir,
            success=True,
            attempts=2,
            duration=30.0,
            error_patterns=["assertion_failure"],
            test_framework="pytest",
        )

        stats = get_auto_fix_stats(mock_spec_dir)
        assert stats.total_runs == 1
        assert stats.successful_runs == 1

    def test_get_auto_fix_dashboard_data(self, mock_spec_dir):
        """Test get_auto_fix_dashboard_data public function."""
        # Record some runs
        record_auto_fix_run(mock_spec_dir, success=True, attempts=2, duration=30.0)

        dashboard = get_auto_fix_dashboard_data(mock_spec_dir)

        assert dashboard["totalRuns"] == 1
        assert dashboard["successfulRuns"] == 1
        assert "successRate" in dashboard

    def test_print_auto_fix_summary(self, mock_spec_dir, capsys):
        """Test print_auto_fix_summary public function."""
        # Record some runs
        record_auto_fix_run(mock_spec_dir, success=True, attempts=2, duration=30.0)

        print_auto_fix_summary(mock_spec_dir)

        captured = capsys.readouterr()
        assert "Total Runs: 1" in captured.out
        assert "Successful: 1" in captured.out
