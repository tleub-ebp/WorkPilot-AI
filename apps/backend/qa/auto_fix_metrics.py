"""
Auto-Fix Metrics Module
========================

Tracks and reports auto-fix loop success rates, failure patterns,
and statistics for dashboard visualization.

Features:
- Success rate tracking
- Average attempts calculation
- Common failure pattern identification
- Historical run data
- Dashboard-ready JSON export
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from debug import debug_error, debug_success


@dataclass
class AutoFixRun:
    """Record of a single auto-fix run."""

    timestamp: float
    success: bool
    attempts: int
    duration: float
    error_patterns: list[str] | None = None
    test_framework: str | None = None


@dataclass
class AutoFixStats:
    """Auto-fix statistics."""

    total_runs: int = 0
    successful_runs: int = 0
    total_attempts: int = 0
    success_rate: float = 0.0
    average_attempts: float = 0.0
    common_patterns: dict[str, int] | None = None
    runs: list[dict[str, Any]] | None = None


class AutoFixMetricsTracker:
    """
    Tracks auto-fix metrics in implementation_plan.json.

    Stores:
    - Total runs and successes
    - Success rate
    - Average attempts per run
    - Recent run history (last 50)
    - Common error patterns
    """

    def __init__(self, spec_dir: Path):
        """
        Initialize metrics tracker.

        Args:
            spec_dir: Spec directory containing implementation_plan.json
        """
        self.spec_dir = spec_dir
        self.plan_file = spec_dir / "implementation_plan.json"

    def load_stats(self) -> AutoFixStats:
        """
        Load current auto-fix statistics.

        Returns:
            AutoFixStats object with current metrics
        """
        try:
            if not self.plan_file.exists():
                debug_error(
                    "auto_fix_metrics",
                    "implementation_plan.json not found",
                    path=str(self.plan_file),
                )
                return AutoFixStats()

            plan = json.loads(self.plan_file.read_text(encoding="utf-8"))

            if "auto_fix_stats" not in plan:
                return AutoFixStats()

            stats_data = plan["auto_fix_stats"]
            return AutoFixStats(
                total_runs=stats_data.get("total_runs", 0),
                successful_runs=stats_data.get("successful_runs", 0),
                total_attempts=stats_data.get("total_attempts", 0),
                success_rate=stats_data.get("success_rate", 0.0),
                average_attempts=stats_data.get("average_attempts", 0.0),
                common_patterns=stats_data.get("common_patterns", {}),
                runs=stats_data.get("runs", []),
            )

        except Exception as e:
            debug_error("auto_fix_metrics", f"Failed to load stats: {e}")
            return AutoFixStats()

    def record_run(
        self,
        success: bool,
        attempts: int,
        duration: float,
        error_patterns: list[str] | None = None,
        test_framework: str | None = None,
    ) -> None:
        """
        Record a new auto-fix run.

        Args:
            success: Whether the run succeeded
            attempts: Number of attempts made
            duration: Total duration in seconds
            error_patterns: List of error patterns encountered
            test_framework: Test framework used
        """
        try:
            if not self.plan_file.exists():
                debug_error(
                    "auto_fix_metrics",
                    "implementation_plan.json not found, cannot record run",
                )
                return

            plan = json.loads(self.plan_file.read_text(encoding="utf-8"))

            if "auto_fix_stats" not in plan:
                plan["auto_fix_stats"] = {
                    "total_runs": 0,
                    "successful_runs": 0,
                    "total_attempts": 0,
                    "success_rate": 0.0,
                    "average_attempts": 0.0,
                    "common_patterns": {},
                    "runs": [],
                }

            stats = plan["auto_fix_stats"]
            stats["total_runs"] += 1
            stats["total_attempts"] += attempts

            if success:
                stats["successful_runs"] += 1

            # Update calculated fields
            stats["success_rate"] = (
                stats["successful_runs"] / stats["total_runs"]
                if stats["total_runs"] > 0
                else 0.0
            )
            stats["average_attempts"] = (
                stats["total_attempts"] / stats["total_runs"]
                if stats["total_runs"] > 0
                else 0.0
            )

            # Update common patterns
            if error_patterns:
                if "common_patterns" not in stats:
                    stats["common_patterns"] = {}
                for pattern in error_patterns:
                    stats["common_patterns"][pattern] = (
                        stats["common_patterns"].get(pattern, 0) + 1
                    )

            # Record this run
            import time

            run_data = {
                "timestamp": time.time(),
                "success": success,
                "attempts": attempts,
                "duration": duration,
                "error_patterns": error_patterns or [],
                "test_framework": test_framework,
            }
            stats["runs"].append(run_data)

            # Keep only last 50 runs
            if len(stats["runs"]) > 50:
                stats["runs"] = stats["runs"][-50:]

            # Save updated plan
            self.plan_file.write_text(json.dumps(plan, indent=2), encoding="utf-8")
            debug_success("auto_fix_metrics", "Recorded auto-fix run", success=success)

        except Exception as e:
            debug_error("auto_fix_metrics", f"Failed to record run: {e}")

    def get_dashboard_data(self) -> dict[str, Any]:
        """
        Get dashboard-ready metrics data.

        Returns:
            Dictionary with formatted metrics for frontend display
        """
        stats = self.load_stats()

        # Get top 5 common patterns
        common_patterns = []
        if stats.common_patterns:
            sorted_patterns = sorted(
                stats.common_patterns.items(), key=lambda x: x[1], reverse=True
            )
            common_patterns = [
                {"pattern": pattern, "count": count}
                for pattern, count in sorted_patterns[:5]
            ]

        # Get recent runs (last 10)
        recent_runs = []
        if stats.runs:
            recent_runs = stats.runs[-10:]

        return {
            "totalRuns": stats.total_runs,
            "successfulRuns": stats.successful_runs,
            "successRate": round(stats.success_rate * 100, 1),  # Convert to percentage
            "averageAttempts": round(stats.average_attempts, 1),
            "commonPatterns": common_patterns,
            "recentRuns": recent_runs,
        }

    def get_summary(self) -> str:
        """
        Get a human-readable summary of auto-fix metrics.

        Returns:
            Formatted summary string
        """
        stats = self.load_stats()

        if stats.total_runs == 0:
            return "No auto-fix runs recorded yet."

        summary = f"""Auto-Fix Metrics Summary:
- Total Runs: {stats.total_runs}
- Successful: {stats.successful_runs} ({stats.success_rate*100:.1f}%)
- Average Attempts: {stats.average_attempts:.1f}
"""

        if stats.common_patterns:
            summary += "\nMost Common Error Patterns:\n"
            sorted_patterns = sorted(
                stats.common_patterns.items(), key=lambda x: x[1], reverse=True
            )
            for pattern, count in sorted_patterns[:5]:
                summary += f"  - {pattern}: {count} occurrences\n"

        return summary

    def reset_stats(self) -> None:
        """Reset all auto-fix statistics (for testing)."""
        try:
            if not self.plan_file.exists():
                return

            plan = json.loads(self.plan_file.read_text(encoding="utf-8"))

            plan["auto_fix_stats"] = {
                "total_runs": 0,
                "successful_runs": 0,
                "total_attempts": 0,
                "success_rate": 0.0,
                "average_attempts": 0.0,
                "common_patterns": {},
                "runs": [],
            }

            self.plan_file.write_text(json.dumps(plan, indent=2), encoding="utf-8")
            debug_success("auto_fix_metrics", "Reset auto-fix stats")

        except Exception as e:
            debug_error("auto_fix_metrics", f"Failed to reset stats: {e}")


# =============================================================================
# PUBLIC API
# =============================================================================


def get_auto_fix_stats(spec_dir: Path) -> AutoFixStats:
    """
    Get auto-fix statistics for a spec.

    Args:
        spec_dir: Spec directory

    Returns:
        AutoFixStats object
    """
    tracker = AutoFixMetricsTracker(spec_dir)
    return tracker.load_stats()


def record_auto_fix_run(
    spec_dir: Path,
    success: bool,
    attempts: int,
    duration: float,
    error_patterns: list[str] | None = None,
    test_framework: str | None = None,
) -> None:
    """
    Record an auto-fix run.

    Args:
        spec_dir: Spec directory
        success: Whether the run succeeded
        attempts: Number of attempts made
        duration: Total duration in seconds
        error_patterns: List of error patterns encountered
        test_framework: Test framework used
    """
    tracker = AutoFixMetricsTracker(spec_dir)
    tracker.record_run(success, attempts, duration, error_patterns, test_framework)


def get_auto_fix_dashboard_data(spec_dir: Path) -> dict[str, Any]:
    """
    Get dashboard-ready auto-fix metrics.

    Args:
        spec_dir: Spec directory

    Returns:
        Dictionary with formatted metrics
    """
    tracker = AutoFixMetricsTracker(spec_dir)
    return tracker.get_dashboard_data()


def print_auto_fix_summary(spec_dir: Path) -> None:
    """
    Print auto-fix metrics summary.

    Args:
        spec_dir: Spec directory
    """
    tracker = AutoFixMetricsTracker(spec_dir)
    print(tracker.get_summary())
