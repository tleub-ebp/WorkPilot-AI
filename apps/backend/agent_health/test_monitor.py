"""Tests for the Agent Health Monitor."""

from __future__ import annotations

import pytest
from agent_health import (
    AgentRun,
    HealthAction,
    HealthMonitor,
    HealthStatus,
)


def _runs(
    agent: str,
    n: int,
    success: bool = True,
    duration: float = 1.0,
    retries: int = 0,
    error: str = "",
) -> list[AgentRun]:
    return [
        AgentRun(
            agent_name=agent,
            success=success,
            duration_s=duration,
            retries=retries,
            error=error,
        )
        for _ in range(n)
    ]


class TestHealthStatus:
    def test_grade_thresholds(self) -> None:
        assert HealthStatus.from_score(95) == HealthStatus.HEALTHY
        assert HealthStatus.from_score(70) == HealthStatus.DEGRADED
        assert HealthStatus.from_score(45) == HealthStatus.FAILING
        assert HealthStatus.from_score(20) == HealthStatus.BURNED_OUT

    def test_grade_at_boundaries(self) -> None:
        assert HealthStatus.from_score(80) == HealthStatus.HEALTHY
        assert HealthStatus.from_score(79.99) == HealthStatus.DEGRADED
        assert HealthStatus.from_score(60) == HealthStatus.DEGRADED
        assert HealthStatus.from_score(30) == HealthStatus.FAILING
        assert HealthStatus.from_score(29.99) == HealthStatus.BURNED_OUT


class TestRecording:
    def test_empty_monitor_returns_no_score(self) -> None:
        monitor = HealthMonitor()
        assert monitor.score("planner") is None

    def test_below_minimum_runs_returns_none(self) -> None:
        monitor = HealthMonitor()
        monitor.record_many(_runs("coder", n=2))
        assert monitor.score("coder") is None

    def test_record_requires_agent_name(self) -> None:
        with pytest.raises(ValueError):
            HealthMonitor().record(AgentRun(agent_name=""))

    def test_window_evicts_old_runs(self) -> None:
        monitor = HealthMonitor(window_size=10)
        monitor.record_many(_runs("planner", n=15))
        score = monitor.score("planner")
        assert score is not None
        assert score.runs_in_window == 10  # ring buffer caps at window_size

    def test_invalid_window_size_raises(self) -> None:
        with pytest.raises(ValueError):
            HealthMonitor(window_size=0)

    def test_known_agents_lists_only_recorded(self) -> None:
        monitor = HealthMonitor()
        monitor.record_many(_runs("planner", n=3))
        monitor.record_many(_runs("coder", n=4))
        assert monitor.known_agents() == ["coder", "planner"]

    def test_reset_clears_history(self) -> None:
        monitor = HealthMonitor()
        monitor.record_many(_runs("planner", n=5))
        monitor.reset("planner")
        assert monitor.score("planner") is None

    def test_reset_all_clears_everything(self) -> None:
        monitor = HealthMonitor()
        monitor.record_many(_runs("a", n=5))
        monitor.record_many(_runs("b", n=5))
        monitor.reset()
        assert monitor.known_agents() == []


class TestScoring:
    def test_perfect_history_scores_high(self) -> None:
        monitor = HealthMonitor()
        monitor.record_many(_runs("planner", n=20))
        score = monitor.score("planner")
        assert score is not None
        assert score.score >= 80
        assert score.status == HealthStatus.HEALTHY

    def test_all_failures_with_errors_score_burned_out(self) -> None:
        monitor = HealthMonitor()
        monitor.record_many(
            _runs("planner", n=20, success=False, error="boom", retries=2)
        )
        score = monitor.score("planner")
        assert score is not None
        assert score.score <= 30
        assert score.status == HealthStatus.BURNED_OUT

    def test_mixed_history_yields_mid_score(self) -> None:
        monitor = HealthMonitor()
        monitor.record_many(_runs("planner", n=10, success=True))
        monitor.record_many(_runs("planner", n=10, success=False, error="x"))
        score = monitor.score("planner")
        assert score is not None
        assert 30 <= score.score < 80

    def test_degrading_trend_detected(self) -> None:
        # First half passing, second half failing → degrading.
        monitor = HealthMonitor()
        monitor.record_many(_runs("planner", n=10, success=True))
        monitor.record_many(_runs("planner", n=10, success=False))
        score = monitor.score("planner")
        assert score is not None
        assert score.trend == "degrading"

    def test_improving_trend_detected(self) -> None:
        monitor = HealthMonitor()
        monitor.record_many(_runs("planner", n=10, success=False))
        monitor.record_many(_runs("planner", n=10, success=True))
        score = monitor.score("planner")
        assert score is not None
        assert score.trend == "improving"

    def test_slowness_detected(self) -> None:
        # 20 fast runs to set baseline ~1.0s, then keep adding slow runs.
        monitor = HealthMonitor(window_size=40)
        monitor.record_many(_runs("planner", n=20, duration=1.0))
        monitor.record_many(_runs("planner", n=10, duration=5.0))
        score = monitor.score("planner")
        assert score is not None
        assert score.slowness_ratio > 1.5

    def test_score_clamped_to_0_100(self) -> None:
        monitor = HealthMonitor()
        # Pathological case: catastrophic everything.
        monitor.record_many(_runs("x", n=20, success=False, retries=10, duration=999.0))
        score = monitor.score("x")
        assert score is not None
        assert 0.0 <= score.score <= 100.0


class TestActions:
    def test_healthy_agent_has_no_action(self) -> None:
        monitor = HealthMonitor()
        monitor.record_many(_runs("planner", n=20))
        score = monitor.score("planner")
        assert score is not None
        assert score.actions == [HealthAction.NONE]

    def test_burned_out_alerts_operator(self) -> None:
        # Catastrophic agent: all failures, all crash with errors, all retry.
        monitor = HealthMonitor()
        monitor.record_many(
            _runs("planner", n=20, success=False, error="boom", retries=2)
        )
        score = monitor.score("planner")
        assert score is not None
        assert score.status == HealthStatus.BURNED_OUT
        assert HealthAction.ALERT_OPERATOR in score.actions
        assert HealthAction.REDUCE_PARALLELISM in score.actions

    def test_failing_status_reduces_parallelism(self) -> None:
        # 100% failures but no explicit errors → FAILING (still bad).
        monitor = HealthMonitor()
        monitor.record_many(_runs("planner", n=20, success=False, retries=2))
        score = monitor.score("planner")
        assert score is not None
        assert score.status == HealthStatus.FAILING
        assert HealthAction.REDUCE_PARALLELISM in score.actions
        assert HealthAction.THROTTLE in score.actions

    def test_recent_failures_trigger_throttle(self) -> None:
        # Long history of success, then last 5 all failed.
        monitor = HealthMonitor()
        monitor.record_many(_runs("planner", n=15, success=True))
        monitor.record_many(_runs("planner", n=5, success=False))
        score = monitor.score("planner")
        assert score is not None
        assert HealthAction.THROTTLE in score.actions

    def test_high_retry_rate_suggests_rotate(self) -> None:
        monitor = HealthMonitor()
        monitor.record_many(_runs("planner", n=20, retries=2))
        score = monitor.score("planner")
        assert score is not None
        assert HealthAction.ROTATE_MODEL in score.actions

    def test_severe_slowdown_suggests_retrain(self) -> None:
        monitor = HealthMonitor(window_size=40)
        monitor.record_many(_runs("planner", n=20, duration=1.0))
        monitor.record_many(_runs("planner", n=10, duration=10.0))
        score = monitor.score("planner")
        assert score is not None
        assert HealthAction.RETRAIN_PROMPT in score.actions


class TestScoreAll:
    def test_score_all_returns_per_agent(self) -> None:
        monitor = HealthMonitor()
        monitor.record_many(_runs("planner", n=10))
        monitor.record_many(_runs("coder", n=10))
        scores = monitor.score_all()
        assert {s.agent_name for s in scores} == {"planner", "coder"}

    def test_score_all_skips_agents_below_min_runs(self) -> None:
        monitor = HealthMonitor()
        monitor.record_many(_runs("a", n=5))
        monitor.record_many(_runs("b", n=2))  # below MIN_RUNS_FOR_SCORING
        scores = monitor.score_all()
        assert {s.agent_name for s in scores} == {"a"}

    def test_to_dict_serialisable(self) -> None:
        import json

        monitor = HealthMonitor()
        monitor.record_many(_runs("planner", n=10))
        score = monitor.score("planner")
        assert score is not None
        decoded = json.loads(json.dumps(score.to_dict()))
        assert decoded["status"] in {s.value for s in HealthStatus}
        assert isinstance(decoded["actions"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
