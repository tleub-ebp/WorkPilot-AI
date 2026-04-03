"""Tests for Feature 6.3 — Estimation et contrôle des coûts.

Tests for CostEstimator, TokenUsage, ProjectBudget, BudgetAlert,
CostEstimate, and pricing calculations.

40 tests total:
- TokenUsage: 3
- BudgetAlert: 2
- CostEstimate: 2
- ProjectBudget: 1
- CostEstimator pricing: 6
- CostEstimator usage tracking: 6
- CostEstimator budget management: 7
- CostEstimator cost estimation: 5
- CostEstimator reporting: 5
- CostEstimator suggestions: 3
"""

import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.scheduling.cost_estimator import (
    PROVIDER_PRICING,
    TASK_TOKEN_ESTIMATES,
    AlertLevel,
    BudgetAlert,
    CostEstimate,
    CostEstimator,
    ProjectBudget,
    TokenUsage,
)

# -----------------------------------------------------------------------
# TokenUsage
# -----------------------------------------------------------------------

class TestTokenUsage:
    def test_create_token_usage(self):
        usage = TokenUsage(
            project_id="proj-1",
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            input_tokens=1000,
            output_tokens=500,
            cost=0.0105,
        )
        assert usage.project_id == "proj-1"
        assert usage.provider == "anthropic"
        assert usage.input_tokens == 1000
        assert usage.output_tokens == 500
        assert usage.cost == 0.0105

    def test_token_usage_to_dict(self):
        usage = TokenUsage(
            project_id="p1", provider="openai", model="gpt-4o",
            input_tokens=100, output_tokens=50, cost=0.001, task_id="t1",
        )
        d = usage.to_dict()
        assert d["project_id"] == "p1"
        assert d["provider"] == "openai"
        assert d["task_id"] == "t1"
        assert "timestamp" in d

    def test_token_usage_default_timestamp(self):
        usage = TokenUsage(
            project_id="p1", provider="a", model="m",
            input_tokens=0, output_tokens=0, cost=0,
        )
        assert isinstance(usage.timestamp, datetime)
        assert usage.timestamp.tzinfo is not None


# -----------------------------------------------------------------------
# BudgetAlert
# -----------------------------------------------------------------------

class TestBudgetAlert:
    def test_create_budget_alert(self):
        alert = BudgetAlert(
            project_id="p1",
            level=AlertLevel.WARNING,
            message="Budget warning",
            current_spend=37.5,
            budget_limit=50.0,
            percentage=0.75,
        )
        assert alert.level == AlertLevel.WARNING
        assert alert.current_spend == 37.5

    def test_budget_alert_to_dict(self):
        alert = BudgetAlert(
            project_id="p1", level=AlertLevel.EXCEEDED,
            message="Over budget", current_spend=55.0,
            budget_limit=50.0, percentage=1.1,
        )
        d = alert.to_dict()
        assert d["level"] == "exceeded"
        assert d["percentage"] == 1.1


# -----------------------------------------------------------------------
# CostEstimate
# -----------------------------------------------------------------------

class TestCostEstimate:
    def test_create_cost_estimate(self):
        est = CostEstimate(
            provider="anthropic", model="claude-sonnet-4-20250514",
            estimated_input_tokens=2000, estimated_output_tokens=1000,
            estimated_cost=0.021, confidence="high",
        )
        assert est.estimated_cost == 0.021
        assert est.confidence == "high"

    def test_cost_estimate_to_dict(self):
        est = CostEstimate(
            provider="openai", model="gpt-4o",
            estimated_input_tokens=1000, estimated_output_tokens=500,
            estimated_cost=0.01,
        )
        d = est.to_dict()
        assert d["provider"] == "openai"
        assert d["estimated_input_tokens"] == 1000


# -----------------------------------------------------------------------
# ProjectBudget
# -----------------------------------------------------------------------

class TestProjectBudget:
    def test_create_project_budget(self):
        budget = ProjectBudget(project_id="p1", limit=100.0, currency="EUR")
        assert budget.limit == 100.0
        assert budget.currency == "EUR"
        assert budget.warning_threshold == 0.75
        assert budget.critical_threshold == 0.90


# -----------------------------------------------------------------------
# CostEstimator — Pricing
# -----------------------------------------------------------------------

class TestCostEstimatorPricing:
    def test_get_known_token_price(self):
        estimator = CostEstimator()
        price = estimator.get_token_price("anthropic", "claude-sonnet-4-20250514")
        assert price["input"] == 3.0
        assert price["output"] == 15.0

    def test_get_unknown_model_returns_zero(self):
        estimator = CostEstimator()
        price = estimator.get_token_price("unknown_provider", "unknown_model")
        assert price["input"] == 0.0
        assert price["output"] == 0.0

    def test_get_local_model_returns_zero(self):
        estimator = CostEstimator()
        price = estimator.get_token_price("ollama", "llama3:8b")
        assert price["input"] == 0.0
        assert price["output"] == 0.0

    def test_set_custom_pricing(self):
        estimator = CostEstimator()
        estimator.set_custom_pricing("custom", "my-model", 1.0, 2.0)
        price = estimator.get_token_price("custom", "my-model")
        assert price["input"] == 1.0
        assert price["output"] == 2.0

    def test_calculate_cost_anthropic(self):
        estimator = CostEstimator()
        cost = estimator.calculate_cost(
            "anthropic", "claude-sonnet-4-20250514",
            input_tokens=1_000_000, output_tokens=1_000_000,
        )
        assert cost == 18.0  # 3.0 + 15.0

    def test_calculate_cost_zero_for_local(self):
        estimator = CostEstimator()
        cost = estimator.calculate_cost("ollama", "llama3:8b", 5000, 3000)
        assert cost == 0.0


# -----------------------------------------------------------------------
# CostEstimator — Usage tracking
# -----------------------------------------------------------------------

class TestCostEstimatorUsage:
    def test_record_usage(self):
        estimator = CostEstimator()
        usage = estimator.record_usage(
            "proj-1", "anthropic", "claude-sonnet-4-20250514",
            input_tokens=1000, output_tokens=500, task_id="t1",
        )
        assert usage.cost > 0
        assert usage.project_id == "proj-1"

    def test_get_usages_filter_by_project(self):
        estimator = CostEstimator()
        estimator.record_usage("p1", "anthropic", "claude-sonnet-4-20250514", 100, 50)
        estimator.record_usage("p2", "openai", "gpt-4o", 200, 100)
        usages = estimator.get_usages(project_id="p1")
        assert len(usages) == 1
        assert usages[0].project_id == "p1"

    def test_get_usages_filter_by_provider(self):
        estimator = CostEstimator()
        estimator.record_usage("p1", "anthropic", "claude-sonnet-4-20250514", 100, 50)
        estimator.record_usage("p1", "openai", "gpt-4o", 200, 100)
        usages = estimator.get_usages(provider="openai")
        assert len(usages) == 1

    def test_get_usages_filter_by_task(self):
        estimator = CostEstimator()
        estimator.record_usage("p1", "anthropic", "claude-sonnet-4-20250514", 100, 50, task_id="t1")
        estimator.record_usage("p1", "anthropic", "claude-sonnet-4-20250514", 200, 100, task_id="t2")
        usages = estimator.get_usages(task_id="t1")
        assert len(usages) == 1

    def test_get_total_cost(self):
        estimator = CostEstimator()
        estimator.record_usage("p1", "anthropic", "claude-sonnet-4-20250514", 1000, 500)
        estimator.record_usage("p1", "openai", "gpt-4o", 1000, 500)
        total = estimator.get_total_cost(project_id="p1")
        assert total > 0

    def test_get_total_cost_by_provider(self):
        estimator = CostEstimator()
        estimator.record_usage("p1", "anthropic", "claude-sonnet-4-20250514", 1000, 500)
        estimator.record_usage("p1", "openai", "gpt-4o", 1000, 500)
        anthropic_cost = estimator.get_total_cost(provider="anthropic")
        openai_cost = estimator.get_total_cost(provider="openai")
        assert anthropic_cost != openai_cost


# -----------------------------------------------------------------------
# CostEstimator — Budget management
# -----------------------------------------------------------------------

class TestCostEstimatorBudget:
    def test_set_budget(self):
        estimator = CostEstimator()
        budget = estimator.set_budget("p1", 50.0)
        assert budget.limit == 50.0
        assert budget.project_id == "p1"

    def test_get_budget(self):
        estimator = CostEstimator()
        estimator.set_budget("p1", 100.0)
        b = estimator.get_budget("p1")
        assert b is not None
        assert b.limit == 100.0

    def test_get_budget_nonexistent(self):
        estimator = CostEstimator()
        assert estimator.get_budget("nonexistent") is None

    def test_budget_warning_alert(self):
        estimator = CostEstimator()
        estimator.set_budget("p1", 0.001, warning_threshold=0.5)
        # Record enough usage to trigger warning (>50% of 0.001)
        estimator.record_usage("p1", "anthropic", "claude-sonnet-4-20250514", 1000, 500)
        alerts = estimator.get_alerts(project_id="p1")
        assert len(alerts) > 0

    def test_budget_exceeded_alert(self):
        estimator = CostEstimator()
        estimator.set_budget("p1", 0.0001)  # Very low budget
        estimator.record_usage("p1", "anthropic", "claude-sonnet-4-20250514", 10000, 5000)
        alerts = estimator.get_alerts(project_id="p1", level=AlertLevel.EXCEEDED)
        assert len(alerts) >= 1

    def test_no_alert_when_under_budget(self):
        estimator = CostEstimator()
        estimator.set_budget("p1", 1000.0)  # Very high budget
        estimator.record_usage("p1", "anthropic", "claude-sonnet-4-20250514", 100, 50)
        alerts = estimator.get_alerts(project_id="p1")
        assert len(alerts) == 0

    def test_budget_custom_thresholds(self):
        estimator = CostEstimator()
        budget = estimator.set_budget(
            "p1", 100.0, warning_threshold=0.5, critical_threshold=0.8
        )
        assert budget.warning_threshold == 0.5
        assert budget.critical_threshold == 0.8


# -----------------------------------------------------------------------
# CostEstimator — Cost estimation (pre-execution)
# -----------------------------------------------------------------------

class TestCostEstimatorEstimation:
    def test_estimate_task_cost(self):
        estimator = CostEstimator()
        est = estimator.estimate_task_cost("anthropic", "claude-sonnet-4-20250514", "coding")
        assert est.estimated_cost > 0
        assert est.estimated_input_tokens > 0
        assert est.estimated_output_tokens > 0

    def test_estimate_with_complexity_multiplier(self):
        estimator = CostEstimator()
        est1 = estimator.estimate_task_cost("anthropic", "claude-sonnet-4-20250514", "coding", 1.0)
        est2 = estimator.estimate_task_cost("anthropic", "claude-sonnet-4-20250514", "coding", 2.0)
        assert est2.estimated_cost > est1.estimated_cost

    def test_estimate_unknown_task_type_uses_general(self):
        estimator = CostEstimator()
        est = estimator.estimate_task_cost("anthropic", "claude-sonnet-4-20250514", "unknown_type")
        general_est = estimator.estimate_task_cost("anthropic", "claude-sonnet-4-20250514", "general")
        assert est.estimated_cost == general_est.estimated_cost

    def test_estimate_local_model_is_free(self):
        estimator = CostEstimator()
        est = estimator.estimate_task_cost("ollama", "llama3:8b", "coding")
        assert est.estimated_cost == 0.0

    def test_estimate_confidence_varies(self):
        estimator = CostEstimator()
        est_low = estimator.estimate_task_cost("anthropic", "claude-sonnet-4-20250514", "coding", 3.0)
        est_high = estimator.estimate_task_cost("anthropic", "claude-sonnet-4-20250514", "coding", 1.5)
        assert est_low.confidence == "low"
        assert est_high.confidence == "high"


# -----------------------------------------------------------------------
# CostEstimator — Reporting
# -----------------------------------------------------------------------

class TestCostEstimatorReporting:
    def test_get_project_report(self):
        estimator = CostEstimator()
        estimator.record_usage("p1", "anthropic", "claude-sonnet-4-20250514", 1000, 500, task_id="t1")
        estimator.record_usage("p1", "openai", "gpt-4o", 500, 200, task_id="t2")
        report = estimator.get_project_report("p1")
        assert report["project_id"] == "p1"
        assert report["total_cost"] > 0
        assert "anthropic" in report["by_provider"]
        assert report["usage_count"] == 2

    def test_report_with_budget(self):
        estimator = CostEstimator()
        estimator.set_budget("p1", 100.0)
        estimator.record_usage("p1", "anthropic", "claude-sonnet-4-20250514", 1000, 500)
        report = estimator.get_project_report("p1")
        assert report["budget"] is not None
        assert report["budget"]["limit"] == 100.0
        assert report["budget"]["remaining"] > 0

    def test_report_without_budget(self):
        estimator = CostEstimator()
        estimator.record_usage("p1", "anthropic", "claude-sonnet-4-20250514", 100, 50)
        report = estimator.get_project_report("p1")
        assert report["budget"] is None

    def test_weekly_report(self):
        estimator = CostEstimator()
        estimator.record_usage("p1", "anthropic", "claude-sonnet-4-20250514", 100, 50)
        report = estimator.get_weekly_report("p1")
        assert report["usage_count"] == 1

    def test_get_global_stats(self):
        estimator = CostEstimator()
        estimator.record_usage("p1", "anthropic", "claude-sonnet-4-20250514", 100, 50)
        estimator.record_usage("p2", "openai", "gpt-4o", 200, 100)
        stats = estimator.get_stats()
        assert stats["total_usages"] == 2
        assert len(stats["projects"]) == 2
        assert len(stats["providers_used"]) == 2


# -----------------------------------------------------------------------
# CostEstimator — Suggestions
# -----------------------------------------------------------------------

class TestCostEstimatorSuggestions:
    def test_suggest_cheapest_model(self):
        estimator = CostEstimator()
        suggestions = estimator.suggest_cheapest_model("coding")
        assert len(suggestions) > 0
        # Should be sorted by cost
        costs = [s["estimated_cost"] for s in suggestions]
        assert costs == sorted(costs)

    def test_suggest_with_max_budget(self):
        estimator = CostEstimator()
        suggestions = estimator.suggest_cheapest_model("coding", max_budget=0.001)
        # Only very cheap or free models should appear
        for s in suggestions:
            assert s["estimated_cost"] <= 0.001

    def test_suggest_includes_local_models(self):
        estimator = CostEstimator()
        suggestions = estimator.suggest_cheapest_model("coding")
        local_models = [s for s in suggestions if s["estimated_cost"] == 0.0]
        assert len(local_models) > 0


# -----------------------------------------------------------------------
# Provider pricing data validation
# -----------------------------------------------------------------------

class TestProviderPricing:
    def test_pricing_structure(self):
        for provider, models in PROVIDER_PRICING.items():
            for model, pricing in models.items():
                assert "input" in pricing, f"Missing 'input' for {provider}/{model}"
                assert "output" in pricing, f"Missing 'output' for {provider}/{model}"
                assert pricing["input"] >= 0
                assert pricing["output"] >= 0

    def test_task_token_estimates_structure(self):
        for task_type, estimates in TASK_TOKEN_ESTIMATES.items():
            assert "input" in estimates
            assert "output" in estimates
            assert estimates["input"] > 0
            assert estimates["output"] > 0
