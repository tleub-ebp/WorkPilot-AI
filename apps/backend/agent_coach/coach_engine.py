"""
Personal Agent Coach — Track agent performance and suggest improvements.

Monitors agent behaviour across runs, identifies patterns (repeated
failures, cost spikes, slow convergence), and surfaces personalised
tips to improve prompt engineering and workflow efficiency.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class TipCategory(str, Enum):
    PROMPT_ENGINEERING = "prompt_engineering"
    COST_OPTIMISATION = "cost_optimisation"
    WORKFLOW = "workflow"
    ERROR_PREVENTION = "error_prevention"
    PERFORMANCE = "performance"
    BEST_PRACTICE = "best_practice"


class TipPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class AgentRunRecord:
    """A record of a single agent execution."""

    agent_name: str
    run_id: str = ""
    success: bool = True
    duration_s: float = 0.0
    tokens_used: int = 0
    cost_usd: float = 0.0
    errors: list[str] = field(default_factory=list)
    retries: int = 0
    model: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CoachTip:
    """A personalised improvement tip."""

    category: TipCategory
    priority: TipPriority
    title: str
    description: str
    evidence: str = ""
    action: str = ""


@dataclass
class CoachReport:
    """Personalised coaching report based on agent run history."""

    tips: list[CoachTip] = field(default_factory=list)
    total_runs: int = 0
    success_rate: float = 0.0
    avg_cost_usd: float = 0.0
    total_cost_usd: float = 0.0
    most_used_model: str = ""
    most_failing_agent: str = ""

    @property
    def summary(self) -> str:
        return (
            f"{len(self.tips)} tips, {self.total_runs} runs analysed, "
            f"success={self.success_rate:.0%}, total_cost=${self.total_cost_usd:.2f}"
        )


class CoachEngine:
    """Analyse agent run history and generate personalised coaching tips.

    Usage::

        coach = CoachEngine()
        coach.record(run1)
        coach.record(run2)
        report = coach.generate_report()
    """

    def __init__(self) -> None:
        self._runs: list[AgentRunRecord] = []

    def record(self, run: AgentRunRecord) -> None:
        """Record an agent execution."""
        self._runs.append(run)

    def record_batch(self, runs: list[AgentRunRecord]) -> None:
        """Record multiple agent executions."""
        self._runs.extend(runs)

    def generate_report(self) -> CoachReport:
        """Analyse all recorded runs and generate coaching tips."""
        if not self._runs:
            return CoachReport()

        report = CoachReport(
            total_runs=len(self._runs),
            success_rate=sum(1 for r in self._runs if r.success) / len(self._runs),
            total_cost_usd=sum(r.cost_usd for r in self._runs),
            avg_cost_usd=sum(r.cost_usd for r in self._runs) / len(self._runs),
        )

        # Most used model
        model_counts: dict[str, int] = {}
        for r in self._runs:
            if r.model:
                model_counts[r.model] = model_counts.get(r.model, 0) + 1
        if model_counts:
            report.most_used_model = max(model_counts, key=lambda k: model_counts[k])

        # Most failing agent
        agent_failures: dict[str, int] = {}
        for r in self._runs:
            if not r.success:
                agent_failures[r.agent_name] = agent_failures.get(r.agent_name, 0) + 1
        if agent_failures:
            report.most_failing_agent = max(agent_failures, key=lambda k: agent_failures[k])

        # Generate tips
        report.tips = self._generate_tips(report)
        return report

    def _generate_tips(self, report: CoachReport) -> list[CoachTip]:
        tips: list[CoachTip] = []

        # High failure rate
        if report.success_rate < 0.8:
            tips.append(CoachTip(
                category=TipCategory.ERROR_PREVENTION,
                priority=TipPriority.HIGH,
                title="High failure rate detected",
                description=f"Success rate is {report.success_rate:.0%} — below the 80% threshold.",
                evidence=f"Most failing agent: {report.most_failing_agent}",
                action="Review error logs for the failing agent. Consider adding retry logic or simplifying the task.",
            ))

        # Cost analysis
        expensive_runs = [r for r in self._runs if r.cost_usd > report.avg_cost_usd * 3]
        if expensive_runs:
            tips.append(CoachTip(
                category=TipCategory.COST_OPTIMISATION,
                priority=TipPriority.MEDIUM,
                title="Cost outliers detected",
                description=f"{len(expensive_runs)} runs cost 3x+ the average (${report.avg_cost_usd:.4f}).",
                evidence=f"Most expensive: {max(expensive_runs, key=lambda r: r.cost_usd).agent_name}",
                action="Consider using a smaller model for simpler tasks. Use Haiku/GPT-4o-mini for routine work.",
            ))

        # Retry storms
        high_retry_runs = [r for r in self._runs if r.retries >= 3]
        if high_retry_runs:
            tips.append(CoachTip(
                category=TipCategory.PROMPT_ENGINEERING,
                priority=TipPriority.HIGH,
                title="Excessive retries detected",
                description=f"{len(high_retry_runs)} runs required 3+ retries.",
                action="Improve prompt clarity. Add examples and constraints. Consider using structured output (JSON mode).",
            ))

        # Model diversity
        unique_models = {r.model for r in self._runs if r.model}
        if len(unique_models) == 1:
            tips.append(CoachTip(
                category=TipCategory.COST_OPTIMISATION,
                priority=TipPriority.LOW,
                title="Single model usage",
                description=f"All runs use '{report.most_used_model}'. Consider model routing.",
                action="Use cheaper models (Haiku, Flash) for simple tasks and reserve powerful models for complex ones.",
            ))

        # Slow runs
        slow_runs = [r for r in self._runs if r.duration_s > 60]
        if len(slow_runs) > len(self._runs) * 0.2:
            tips.append(CoachTip(
                category=TipCategory.PERFORMANCE,
                priority=TipPriority.MEDIUM,
                title="Many slow agent runs",
                description=f"{len(slow_runs)} runs took over 60 seconds.",
                action="Break complex tasks into smaller sub-tasks. Use streaming for long-running operations.",
            ))

        return tips
