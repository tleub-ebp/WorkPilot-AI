"""Agent Health Monitor.

Maintains a sliding-window history of agent runs and emits:

* a 0–100 **health score** per agent
* a `HealthStatus` (healthy / degraded / failing / burned_out)
* a list of recommended `HealthAction`s (throttle, retry, rotate, retrain, alert)

Scoring inputs (per agent over the last N runs)
-----------------------------------------------

* **success_rate**   — passing / total                          weight 40%
* **error_rate**     — runs with errors / total                 weight 20%
* **retry_rate**     — runs that retried at least once          weight 15%
* **slowness**       — current avg_duration vs. baseline        weight 15%
* **trend**          — slope of success rate over the window    weight 10%

The scoring is intentionally heuristic; the value is the framing
(numerical, comparable, actionable) and the alert plumbing, not the
exact weights.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    HEALTHY = "healthy"  # score ≥ 80
    DEGRADED = "degraded"  # 60–79
    FAILING = "failing"  # 30–59
    BURNED_OUT = "burned_out"  # < 30

    @classmethod
    def from_score(cls, score: float) -> HealthStatus:
        if score >= 80:
            return cls.HEALTHY
        if score >= 60:
            return cls.DEGRADED
        if score >= 30:
            return cls.FAILING
        return cls.BURNED_OUT


class HealthAction(str, Enum):
    NONE = "none"
    THROTTLE = "throttle"  # slow down dispatch (too many recent failures)
    REDUCE_PARALLELISM = "reduce_parallelism"
    RETRAIN_PROMPT = "retrain_prompt"  # repeated semantic failures — refresh few-shots
    ROTATE_MODEL = "rotate_model"  # try another provider/model
    ALERT_OPERATOR = "alert_operator"  # human attention required


@dataclass(frozen=True)
class AgentRun:
    """One execution of an agent. Compatible with `agent_coach.AgentRunRecord`."""

    agent_name: str
    success: bool = True
    duration_s: float = 0.0
    retries: int = 0
    error: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class AgentHealthScore:
    agent_name: str
    score: float
    status: HealthStatus
    success_rate: float
    error_rate: float
    retry_rate: float
    slowness_ratio: float  # current_avg / baseline_avg ; 1.0 = no change
    trend: str  # "improving" | "stable" | "degrading"
    runs_in_window: int
    actions: list[HealthAction] = field(default_factory=list)
    diagnostics: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "agent_name": self.agent_name,
            "score": round(self.score, 2),
            "status": self.status.value,
            "success_rate": round(self.success_rate, 3),
            "error_rate": round(self.error_rate, 3),
            "retry_rate": round(self.retry_rate, 3),
            "slowness_ratio": round(self.slowness_ratio, 3),
            "trend": self.trend,
            "runs_in_window": self.runs_in_window,
            "actions": [a.value for a in self.actions],
            "diagnostics": {k: round(v, 3) for k, v in self.diagnostics.items()},
        }


class HealthMonitor:
    """Tracks per-agent run history and produces health scores."""

    # Scoring weights — tuned so that 100% success + zero retries + steady
    # speed gives a perfect 100. Sum must = 1.0 for the math to map cleanly.
    W_SUCCESS = 0.40
    W_ERROR = 0.20
    W_RETRY = 0.15
    W_SLOWNESS = 0.15
    W_TREND = 0.10

    # Sliding-window default
    DEFAULT_WINDOW = 50
    MIN_RUNS_FOR_SCORING = 3

    # Thresholds for emitting actions
    THROTTLE_FAILURE_RATIO_LAST5 = 0.6  # ≥ 60% of last 5 failed → throttle
    SLOWNESS_RETRAIN_THRESHOLD = 2.0  # ≥ 2× baseline → suggest prompt retrain
    BURNOUT_RETRY_RATE = 0.4  # ≥ 40% retries → consider rotate
    ALERT_BURNED_OUT = True  # always alert on burned_out

    def __init__(self, window_size: int = DEFAULT_WINDOW) -> None:
        if window_size < 1:
            raise ValueError("window_size must be ≥ 1")
        self._window_size = window_size
        # Per-agent ring buffer of recent runs.
        self._runs: dict[str, deque[AgentRun]] = {}
        # Per-agent baseline avg duration (computed lazily from the first
        # half of the window; updated as we go).
        self._baselines: dict[str, float] = {}

    # ------------------------------------------------------------------
    # Recording

    def record(self, run: AgentRun) -> None:
        if not run.agent_name:
            raise ValueError("AgentRun.agent_name is required")
        buf = self._runs.setdefault(run.agent_name, deque(maxlen=self._window_size))
        buf.append(run)

        # Update baseline once we have a stable initial estimate.
        agent = run.agent_name
        if agent not in self._baselines and len(buf) >= max(5, self._window_size // 2):
            durations = [r.duration_s for r in list(buf)[: len(buf) // 2] if r.success]
            if durations:
                self._baselines[agent] = sum(durations) / len(durations)

    def record_many(self, runs: Iterable[AgentRun]) -> None:
        for r in runs:
            self.record(r)

    def reset(self, agent_name: str | None = None) -> None:
        if agent_name is None:
            self._runs.clear()
            self._baselines.clear()
        else:
            self._runs.pop(agent_name, None)
            self._baselines.pop(agent_name, None)

    # ------------------------------------------------------------------
    # Scoring

    def known_agents(self) -> list[str]:
        return sorted(self._runs.keys())

    def score(self, agent_name: str) -> AgentHealthScore | None:
        runs = list(self._runs.get(agent_name, ()))
        if len(runs) < self.MIN_RUNS_FOR_SCORING:
            return None

        total = len(runs)
        successes = sum(1 for r in runs if r.success)
        with_errors = sum(1 for r in runs if r.error)
        with_retries = sum(1 for r in runs if r.retries > 0)

        success_rate = successes / total
        error_rate = with_errors / total
        retry_rate = with_retries / total

        # Slowness vs baseline (if we have one).
        avg_dur_recent = sum(r.duration_s for r in runs[-min(10, total) :]) / min(
            10, total
        )
        baseline = self._baselines.get(agent_name, avg_dur_recent or 1.0)
        slowness_ratio = (avg_dur_recent / baseline) if baseline > 0 else 1.0

        # Trend: success-rate slope between the first and second halves.
        half = total // 2
        if half >= 2:
            sr_first = sum(1 for r in runs[:half] if r.success) / half
            sr_second = sum(1 for r in runs[half:] if r.success) / (total - half)
            slope = sr_second - sr_first
        else:
            slope = 0.0

        if slope > 0.05:
            trend = "improving"
        elif slope < -0.05:
            trend = "degrading"
        else:
            trend = "stable"

        # Per-component scores 0..1 (higher = better) — normalise then weight.
        score_success = success_rate
        score_error = max(0.0, 1.0 - error_rate)
        score_retry = max(0.0, 1.0 - retry_rate)
        # slowness 1.0 = perfect. Cap penalty at 3× slowdown.
        score_speed = max(0.0, 1.0 - min(1.0, max(0.0, slowness_ratio - 1.0) / 2.0))
        # Trend: improving = 1, stable = 0.5, degrading = 0.
        score_trend = (
            1.0 if trend == "improving" else 0.0 if trend == "degrading" else 0.5
        )

        composite = (
            self.W_SUCCESS * score_success
            + self.W_ERROR * score_error
            + self.W_RETRY * score_retry
            + self.W_SLOWNESS * score_speed
            + self.W_TREND * score_trend
        ) * 100.0

        composite = max(0.0, min(100.0, composite))
        status = HealthStatus.from_score(composite)
        actions = self._suggest_actions(
            runs=runs,
            status=status,
            slowness_ratio=slowness_ratio,
            retry_rate=retry_rate,
        )

        return AgentHealthScore(
            agent_name=agent_name,
            score=composite,
            status=status,
            success_rate=success_rate,
            error_rate=error_rate,
            retry_rate=retry_rate,
            slowness_ratio=slowness_ratio,
            trend=trend,
            runs_in_window=total,
            actions=actions,
            diagnostics={
                "score_success": score_success,
                "score_error": score_error,
                "score_retry": score_retry,
                "score_speed": score_speed,
                "score_trend": score_trend,
            },
        )

    def score_all(self) -> list[AgentHealthScore]:
        return [s for s in (self.score(a) for a in self.known_agents()) if s]

    # ------------------------------------------------------------------
    # Recommendations

    def _suggest_actions(
        self,
        runs: list[AgentRun],
        status: HealthStatus,
        slowness_ratio: float,
        retry_rate: float,
    ) -> list[HealthAction]:
        actions: list[HealthAction] = []

        # Throttle if the most recent runs are catastrophically bad.
        last5 = runs[-5:]
        if (
            last5
            and sum(1 for r in last5 if not r.success) / len(last5)
            >= self.THROTTLE_FAILURE_RATIO_LAST5
        ):
            actions.append(HealthAction.THROTTLE)

        # Slow agent → retrain prompt (cache might be stale, examples outdated).
        if slowness_ratio >= self.SLOWNESS_RETRAIN_THRESHOLD:
            actions.append(HealthAction.RETRAIN_PROMPT)

        # High retry rate → suggest a different model.
        if retry_rate >= self.BURNOUT_RETRY_RATE:
            actions.append(HealthAction.ROTATE_MODEL)

        if status in (HealthStatus.FAILING, HealthStatus.BURNED_OUT):
            actions.append(HealthAction.REDUCE_PARALLELISM)

        if status == HealthStatus.BURNED_OUT and self.ALERT_BURNED_OUT:
            actions.append(HealthAction.ALERT_OPERATOR)

        if not actions:
            actions.append(HealthAction.NONE)
        return actions
