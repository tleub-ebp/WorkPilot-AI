"""Adaptive Model Router.

Picks a (provider, model) for a given task based on task class, prompt
size, and a quality/cost tradeoff. Backed by `cost_intelligence.PricingCatalog`
for live pricing data.

The router is intentionally simple: a heuristic decision table that can be
overridden via a `RoutingPolicy`. A real production version would learn the
mapping from execution history (`analytics/collector.py`), but the heuristic
version already captures 80% of the savings — refactor 50 lines should not
spend Opus tokens.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum

from cost_intelligence.catalog import PricingCatalog

logger = logging.getLogger(__name__)


class TaskClass(str, Enum):
    """Coarse task buckets — what kind of work the agent is doing."""

    TRIVIAL = "trivial"  # rename, fix typo, format
    SIMPLE_EDIT = "simple_edit"  # single-file change, < 100 LoC
    MULTI_FILE = "multi_file"  # 2-10 file refactor
    ARCHITECTURE = "architecture"  # design decision, system-wide change
    REVIEW = "review"  # code review, QA
    PLANNING = "planning"  # task decomposition
    IDEATION = "ideation"  # brainstorm, exploration
    DOCUMENTATION = "documentation"


class QualityTier(str, Enum):
    """How much we care about output quality vs cost."""

    BUDGET = "budget"  # cheapest model that probably works
    BALANCED = "balanced"  # default — reasonable quality at reasonable cost
    PREMIUM = "premium"  # best available, cost no object


@dataclass(frozen=True)
class ModelChoice:
    """The router's decision for a single dispatch."""

    provider: str
    model: str
    task_class: TaskClass
    tier: QualityTier
    estimated_cost_usd: float
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "model": self.model,
            "task_class": self.task_class.value,
            "tier": self.tier.value,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
            "reason": self.reason,
        }


@dataclass
class RoutingPolicy:
    """Per-task-class preferred model lists, in fallback order.

    Each entry is `(provider, model)`. The router walks the list and picks
    the first one available in the catalog (i.e. for which we know pricing
    AND that the user has configured locally).
    """

    budget: dict[TaskClass, list[tuple[str, str]]] = field(default_factory=dict)
    balanced: dict[TaskClass, list[tuple[str, str]]] = field(default_factory=dict)
    premium: dict[TaskClass, list[tuple[str, str]]] = field(default_factory=dict)

    @classmethod
    def default(cls) -> RoutingPolicy:
        # Budget tier — cheap models, good for trivial / simple work.
        budget_default: list[tuple[str, str]] = [
            ("anthropic", "claude-haiku-4-5"),
            ("openai", "gpt-4o-mini"),
            ("google", "gemini-2.5-flash"),
            ("ollama", "qwen2.5-coder"),
        ]
        # Balanced tier — Sonnet-class models.
        balanced_default: list[tuple[str, str]] = [
            ("anthropic", "claude-sonnet-4-6"),
            ("openai", "gpt-4.1"),
            ("google", "gemini-2.5-pro"),
        ]
        # Premium tier — Opus-class.
        premium_default: list[tuple[str, str]] = [
            ("anthropic", "claude-opus-4-6"),
            ("openai", "gpt-4.1"),
            ("google", "gemini-2.5-pro"),
        ]
        # All task classes share the same fallback chain by tier; callers
        # can specialise per-class if they want.
        budget = dict.fromkeys(TaskClass, budget_default)
        balanced = dict.fromkeys(TaskClass, balanced_default)
        premium = dict.fromkeys(TaskClass, premium_default)
        return cls(budget=budget, balanced=balanced, premium=premium)

    def chain_for(self, tier: QualityTier, task: TaskClass) -> list[tuple[str, str]]:
        table = {
            QualityTier.BUDGET: self.budget,
            QualityTier.BALANCED: self.balanced,
            QualityTier.PREMIUM: self.premium,
        }[tier]
        return table.get(task, [])


# Heuristic mapping: (task_class, prompt_size_chars) -> default tier.
# Smaller inputs + simpler classes downgrade towards BUDGET.
def _default_tier(task: TaskClass, prompt_chars: int) -> QualityTier:
    if task in (TaskClass.TRIVIAL, TaskClass.SIMPLE_EDIT):
        return QualityTier.BUDGET
    if task in (TaskClass.ARCHITECTURE, TaskClass.PLANNING):
        return QualityTier.PREMIUM
    if task == TaskClass.MULTI_FILE and prompt_chars > 50_000:
        return QualityTier.PREMIUM
    return QualityTier.BALANCED


def classify_task(prompt: str, hint: str | None = None) -> TaskClass:
    """Best-effort classification from a free-form prompt.

    `hint` lets the caller force a class explicitly (e.g. an agent that
    knows it is doing a "review" passes hint="review").
    """
    if hint:
        try:
            return TaskClass(hint.lower())
        except ValueError:
            pass

    p = (prompt or "").lower()
    # Order matters: more specific first.
    if any(kw in p for kw in ("typo", "rename", "format", "lint")):
        return TaskClass.TRIVIAL
    if any(kw in p for kw in ("review", "audit", "qa", "lgtm")):
        return TaskClass.REVIEW
    if any(kw in p for kw in ("plan", "decompose", "breakdown", "subtask")):
        return TaskClass.PLANNING
    if any(kw in p for kw in ("architect", "design", "trade-off", "tradeoff")):
        return TaskClass.ARCHITECTURE
    if any(kw in p for kw in ("brainstorm", "ideate", "explore")):
        return TaskClass.IDEATION
    if any(kw in p for kw in ("docstring", "readme", "documentation")):
        return TaskClass.DOCUMENTATION
    if len(prompt) > 8_000:
        return TaskClass.MULTI_FILE
    return TaskClass.SIMPLE_EDIT


class ModelRouter:
    """Routes a task to the cheapest acceptable model.

    Usage:

        router = ModelRouter(available={"anthropic", "openai"})
        choice = router.route(prompt="rename foo to bar", hint="trivial")
        # choice.model == "claude-haiku-4-5"
    """

    def __init__(
        self,
        available: Iterable[str] | None = None,
        catalog: PricingCatalog | None = None,
        policy: RoutingPolicy | None = None,
    ) -> None:
        self.available = {p.lower() for p in (available or [])} or None
        self.catalog = catalog or PricingCatalog()
        self.policy = policy or RoutingPolicy.default()

    def route(
        self,
        prompt: str = "",
        hint: str | None = None,
        tier: QualityTier | None = None,
        expected_output_tokens: int = 1_000,
    ) -> ModelChoice:
        """Pick the cheapest available model for this task."""
        task = classify_task(prompt, hint=hint)
        chosen_tier = tier or _default_tier(task, len(prompt or ""))

        chain = self.policy.chain_for(chosen_tier, task)
        for provider, model in chain:
            if self.available is not None and provider not in self.available:
                continue
            pricing = self.catalog.get_pricing(provider, model)
            if pricing is None:
                # No pricing data — only allow if user explicitly made it
                # available (probably a local provider like Ollama).
                if self.available and provider in self.available:
                    return ModelChoice(
                        provider=provider,
                        model=model,
                        task_class=task,
                        tier=chosen_tier,
                        estimated_cost_usd=0.0,
                        reason=f"local provider {provider} (no pricing data)",
                    )
                continue
            input_tokens = max(1, len(prompt) // 4)  # ~4 chars/token rule of thumb
            cost = pricing.cost_for_tokens(
                input_tokens=input_tokens,
                output_tokens=expected_output_tokens,
            )
            return ModelChoice(
                provider=provider,
                model=model,
                task_class=task,
                tier=chosen_tier,
                estimated_cost_usd=cost,
                reason=f"{chosen_tier.value} tier for {task.value}",
            )

        # Nothing in the chain is available — fall back to the first entry
        # of the BALANCED tier so callers always get a non-None choice.
        fallback_chain = self.policy.chain_for(QualityTier.BALANCED, task)
        if not fallback_chain:
            raise RuntimeError("RoutingPolicy has no balanced fallback configured")
        provider, model = fallback_chain[0]
        return ModelChoice(
            provider=provider,
            model=model,
            task_class=task,
            tier=QualityTier.BALANCED,
            estimated_cost_usd=0.0,
            reason="no available provider matched preferred chain — using fallback",
        )

    def compare(
        self,
        prompt: str = "",
        hint: str | None = None,
        expected_output_tokens: int = 1_000,
    ) -> dict[str, ModelChoice]:
        """Return one ModelChoice per tier — useful for showing 'this would cost X with Haiku, Y with Opus'."""
        return {
            tier.value: self.route(
                prompt=prompt,
                hint=hint,
                tier=tier,
                expected_output_tokens=expected_output_tokens,
            )
            for tier in QualityTier
        }
