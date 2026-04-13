"""
Tests for Cost Intelligence — Live budgets, degradation & circuit breaker.

Covers: PricingCatalog, LiveCostTracker, BudgetEnforcer, ReservationManager.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "apps" / "backend"))

from cost_intelligence.catalog import ModelPricing, PricingCatalog
from cost_intelligence.live_tracker import CostEvent, LiveCostTracker, TrackerSnapshot
from cost_intelligence.budget_enforcer import (
    AlertLevel,
    BudgetConfig,
    BudgetEnforcer,
    BudgetStatus,
    CircuitBreakerState,
    DegradationTier,
)
from cost_intelligence.reservation import (
    BudgetReservation,
    ReservationManager,
    ReservationStatus,
)


# =========================================================================
# PricingCatalog tests
# =========================================================================


class TestPricingCatalog:
    def test_default_catalog_has_providers(self):
        catalog = PricingCatalog()
        providers = catalog.list_providers()
        assert "anthropic" in providers
        assert "openai" in providers
        assert "google" in providers
        assert "ollama" in providers

    def test_get_pricing_exact_match(self):
        catalog = PricingCatalog()
        pricing = catalog.get_pricing("anthropic", "claude-sonnet-4-6")
        assert pricing is not None
        assert pricing.input == 3.0
        assert pricing.output == 15.0

    def test_get_pricing_prefix_match(self):
        catalog = PricingCatalog()
        pricing = catalog.get_pricing("anthropic", "claude-sonnet-4-6-latest")
        assert pricing is not None

    def test_get_pricing_not_found(self):
        catalog = PricingCatalog()
        assert catalog.get_pricing("unknown", "unknown-model") is None

    def test_calculate_cost(self):
        catalog = PricingCatalog()
        cost = catalog.calculate_cost(
            "anthropic", "claude-sonnet-4-6",
            input_tokens=1_000_000, output_tokens=500_000,
        )
        # 1M * 3.0/1M + 500K * 15.0/1M = 3.0 + 7.5 = 10.5
        assert abs(cost - 10.5) < 0.01

    def test_calculate_cost_unknown_model(self):
        catalog = PricingCatalog()
        cost = catalog.calculate_cost("unknown", "model", input_tokens=1000)
        assert cost == 0.0

    def test_ollama_is_free(self):
        catalog = PricingCatalog()
        cost = catalog.calculate_cost(
            "ollama", "llama-3.3-70b",
            input_tokens=1_000_000, output_tokens=1_000_000,
        )
        assert cost == 0.0

    def test_add_custom_pricing(self):
        catalog = PricingCatalog()
        custom = ModelPricing(provider="custom", model="my-model", input=1.0, output=2.0)
        catalog.add_pricing(custom)
        assert catalog.get_pricing("custom", "my-model") is not None

    def test_load_from_file(self, tmp_path):
        pricing_file = tmp_path / "pricing.json"
        pricing_file.write_text(json.dumps({
            "test_provider": {
                "test-model": {"input": 5.0, "output": 10.0}
            }
        }), encoding="utf-8")
        catalog = PricingCatalog(catalog_path=pricing_file)
        pricing = catalog.get_pricing("test_provider", "test-model")
        assert pricing is not None
        assert pricing.input == 5.0

    def test_model_pricing_cost_for_tokens(self):
        pricing = ModelPricing(
            provider="test", model="test",
            input=3.0, output=15.0,
            cache_write=3.75, cache_read=0.30,
            thinking=75.0,
        )
        cost = pricing.cost_for_tokens(
            input_tokens=1_000_000,
            output_tokens=100_000,
            cache_write_tokens=50_000,
            cache_read_tokens=200_000,
            thinking_tokens=10_000,
        )
        expected = 3.0 + 1.5 + 0.1875 + 0.06 + 0.75
        assert abs(cost - expected) < 0.001

    def test_list_models(self):
        catalog = PricingCatalog()
        models = catalog.list_models("anthropic")
        assert len(models) > 0
        assert "claude-sonnet-4-6" in models


# =========================================================================
# LiveCostTracker tests
# =========================================================================


class TestLiveCostTracker:
    def test_record_and_get_snapshot(self):
        catalog = PricingCatalog()
        tracker = LiveCostTracker(catalog=catalog)
        tracker.record(CostEvent(
            provider="anthropic", model="claude-sonnet-4-6",
            input_tokens=1000, output_tokens=500,
            scope="spec", scope_id="s1",
        ))
        snap = tracker.get_snapshot("spec", "s1")
        assert snap.total_input_tokens == 1000
        assert snap.total_output_tokens == 500
        assert snap.total_cost_usd > 0
        assert snap.event_count == 1

    def test_multiple_events_accumulate(self):
        tracker = LiveCostTracker()
        for _ in range(3):
            tracker.record(CostEvent(
                provider="openai", model="gpt-4o",
                input_tokens=1000, output_tokens=500,
                scope="project", scope_id="p1",
            ))
        snap = tracker.get_snapshot("project", "p1")
        assert snap.total_input_tokens == 3000
        assert snap.event_count == 3

    def test_retry_events_skipped(self):
        tracker = LiveCostTracker()
        tracker.record(CostEvent(
            provider="anthropic", model="claude-sonnet-4-6",
            input_tokens=1000, output_tokens=500,
            scope="spec", scope_id="s1",
            is_retry=True,
        ))
        snap = tracker.get_snapshot("spec", "s1")
        assert snap.event_count == 0

    def test_get_total_cost(self):
        tracker = LiveCostTracker()
        tracker.record(CostEvent(
            provider="openai", model="gpt-4o",
            input_tokens=1_000_000, output_tokens=0,
            scope="spec", scope_id="s1",
        ))
        cost = tracker.get_total_cost("spec", "s1")
        assert cost > 0

    def test_get_snapshot_nonexistent(self):
        tracker = LiveCostTracker()
        snap = tracker.get_snapshot("spec", "nonexistent")
        assert snap.total_cost_usd == 0.0

    def test_get_events_filtered(self):
        tracker = LiveCostTracker()
        tracker.record(CostEvent(
            provider="anthropic", model="m1",
            input_tokens=100, scope="spec", scope_id="s1",
        ))
        tracker.record(CostEvent(
            provider="openai", model="m2",
            input_tokens=200, scope="project", scope_id="p1",
        ))
        spec_events = tracker.get_events(scope="spec")
        assert len(spec_events) == 1
        all_events = tracker.get_events()
        assert len(all_events) == 2

    def test_reset_specific_scope(self):
        tracker = LiveCostTracker()
        tracker.record(CostEvent(
            provider="a", model="m", input_tokens=100,
            scope="spec", scope_id="s1",
        ))
        tracker.record(CostEvent(
            provider="a", model="m", input_tokens=200,
            scope="spec", scope_id="s2",
        ))
        tracker.reset(scope="spec", scope_id="s1")
        assert tracker.get_snapshot("spec", "s1").event_count == 0
        assert tracker.get_snapshot("spec", "s2").event_count == 1

    def test_reset_all(self):
        tracker = LiveCostTracker()
        tracker.record(CostEvent(
            provider="a", model="m", input_tokens=100,
            scope="spec", scope_id="s1",
        ))
        tracker.reset()
        assert len(tracker.get_all_snapshots()) == 0

    def test_sqlite_persistence(self, tmp_path):
        db_path = tmp_path / "costs.db"
        tracker = LiveCostTracker(db_path=db_path)
        tracker.record(CostEvent(
            provider="anthropic", model="claude-sonnet-4-6",
            input_tokens=1000, output_tokens=500,
            scope="spec", scope_id="s1",
        ))
        assert db_path.exists()

    def test_explicit_cost_used(self):
        tracker = LiveCostTracker()
        tracker.record(CostEvent(
            provider="custom", model="custom-model",
            cost_usd=5.0,
            scope="spec", scope_id="s1",
        ))
        assert tracker.get_total_cost("spec", "s1") == 5.0


# =========================================================================
# BudgetEnforcer tests
# =========================================================================


class TestBudgetEnforcer:
    def _make_enforcer(self) -> tuple[LiveCostTracker, BudgetEnforcer]:
        tracker = LiveCostTracker()
        enforcer = BudgetEnforcer(tracker)
        return tracker, enforcer

    def test_no_budget_set(self):
        tracker, enforcer = self._make_enforcer()
        status = enforcer.check("spec", "s1")
        assert status.alert_level == AlertLevel.NONE
        assert not status.is_stopped

    def test_under_budget(self):
        tracker, enforcer = self._make_enforcer()
        enforcer.set_budget("spec", "s1", hard_stop=10.0)
        tracker.record(CostEvent(
            provider="x", model="m", cost_usd=1.0,
            scope="spec", scope_id="s1",
        ))
        status = enforcer.check("spec", "s1")
        assert status.alert_level == AlertLevel.NONE

    def test_50_percent_alert(self):
        tracker, enforcer = self._make_enforcer()
        enforcer.set_budget("spec", "s1", hard_stop=10.0)
        tracker.record(CostEvent(
            provider="x", model="m", cost_usd=5.5,
            scope="spec", scope_id="s1",
        ))
        status = enforcer.check("spec", "s1")
        assert status.alert_level == AlertLevel.INFO_50

    def test_75_percent_alert(self):
        tracker, enforcer = self._make_enforcer()
        enforcer.set_budget("spec", "s1", hard_stop=10.0)
        tracker.record(CostEvent(
            provider="x", model="m", cost_usd=7.8,
            scope="spec", scope_id="s1",
        ))
        status = enforcer.check("spec", "s1")
        assert status.alert_level == AlertLevel.WARNING_75

    def test_90_percent_alert(self):
        tracker, enforcer = self._make_enforcer()
        enforcer.set_budget("spec", "s1", hard_stop=10.0)
        tracker.record(CostEvent(
            provider="x", model="m", cost_usd=9.2,
            scope="spec", scope_id="s1",
        ))
        status = enforcer.check("spec", "s1")
        assert status.alert_level == AlertLevel.CRITICAL_90

    def test_hard_stop(self):
        tracker, enforcer = self._make_enforcer()
        enforcer.set_budget("spec", "s1", hard_stop=10.0)
        tracker.record(CostEvent(
            provider="x", model="m", cost_usd=10.5,
            scope="spec", scope_id="s1",
        ))
        status = enforcer.check("spec", "s1")
        assert status.alert_level == AlertLevel.HARD_STOP
        assert status.is_stopped

    def test_auto_degradation(self):
        tracker, enforcer = self._make_enforcer()
        enforcer.set_budget("spec", "s1", hard_stop=10.0)
        tracker.record(CostEvent(
            provider="x", model="m", cost_usd=7.8,
            scope="spec", scope_id="s1",
        ))
        status = enforcer.check("spec", "s1")
        # At 78%, should degrade to FAST tier
        assert status.current_tier.rank < DegradationTier.FLAGSHIP.rank

    def test_degradation_only_degrades(self):
        tracker, enforcer = self._make_enforcer()
        enforcer.set_budget("spec", "s1", hard_stop=10.0)
        tracker.record(CostEvent(
            provider="x", model="m", cost_usd=9.5,
            scope="spec", scope_id="s1",
        ))
        status = enforcer.check("spec", "s1")
        tier_after_90 = status.current_tier
        # Cost stays at 95% — should not upgrade back
        status2 = enforcer.check("spec", "s1")
        assert status2.current_tier.rank <= tier_after_90.rank

    def test_circuit_breaker_open(self):
        tracker, enforcer = self._make_enforcer()
        enforcer.set_budget("spec", "s1", hard_stop=10.0, circuit_breaker_multiplier=2.0)
        tracker.record(CostEvent(
            provider="x", model="m", cost_usd=25.0,
            scope="spec", scope_id="s1",
        ))
        status = enforcer.check("spec", "s1")
        assert status.circuit_breaker == CircuitBreakerState.OPEN
        assert status.is_stopped

    def test_circuit_breaker_half_open_with_progress(self):
        tracker, enforcer = self._make_enforcer()
        enforcer.set_budget(
            "spec", "s1", hard_stop=10.0, circuit_breaker_multiplier=2.0
        )
        enforcer.mark_progress("spec", "s1")  # Mark progress right now
        tracker.record(CostEvent(
            provider="x", model="m", cost_usd=25.0,
            scope="spec", scope_id="s1",
        ))
        status = enforcer.check("spec", "s1")
        assert status.circuit_breaker == CircuitBreakerState.HALF_OPEN

    def test_percentage_used(self):
        tracker, enforcer = self._make_enforcer()
        enforcer.set_budget("spec", "s1", hard_stop=10.0)
        tracker.record(CostEvent(
            provider="x", model="m", cost_usd=3.0,
            scope="spec", scope_id="s1",
        ))
        status = enforcer.check("spec", "s1")
        assert abs(status.percentage_used - 30.0) < 0.1
        assert abs(status.remaining_usd - 7.0) < 0.01

    def test_alert_callback(self):
        tracker, enforcer = self._make_enforcer()
        alerts: list[BudgetStatus] = []
        enforcer.on_alert(lambda s: alerts.append(s))
        enforcer.set_budget("spec", "s1", hard_stop=10.0)
        tracker.record(CostEvent(
            provider="x", model="m", cost_usd=5.5,
            scope="spec", scope_id="s1",
        ))
        enforcer.check("spec", "s1")
        assert len(alerts) == 1
        assert alerts[0].alert_level == AlertLevel.INFO_50

    def test_get_recommended_model(self):
        tracker, enforcer = self._make_enforcer()
        enforcer.set_budget("spec", "s1", hard_stop=10.0)
        model = enforcer.get_recommended_model("spec", "s1", preferred_provider="anthropic")
        assert model is not None
        assert model["provider"] == "anthropic"

    def test_degradation_tier_ordering(self):
        assert DegradationTier.FLAGSHIP.rank > DegradationTier.STANDARD.rank
        assert DegradationTier.STANDARD.rank > DegradationTier.FAST.rank
        assert DegradationTier.FAST.rank > DegradationTier.LOCAL.rank

    def test_degrade_method(self):
        assert DegradationTier.FLAGSHIP.degrade() == DegradationTier.STANDARD
        assert DegradationTier.STANDARD.degrade() == DegradationTier.FAST
        assert DegradationTier.FAST.degrade() == DegradationTier.LOCAL
        assert DegradationTier.LOCAL.degrade() == DegradationTier.LOCAL


# =========================================================================
# ReservationManager tests
# =========================================================================


class TestReservationManager:
    def test_reserve_and_release(self):
        mgr = ReservationManager(total_budget=100.0)
        res = mgr.reserve("p1", "spec-001", estimated_usd=10.0)
        assert res.status == ReservationStatus.ACTIVE
        mgr.release(res.id, actual_cost=8.0)
        assert res.status == ReservationStatus.RELEASED
        assert res.actual_usd == 8.0

    def test_available_budget(self):
        mgr = ReservationManager(total_budget=100.0)
        mgr.reserve("p1", "spec-001", estimated_usd=30.0)
        available = mgr.available_budget("p1")
        assert abs(available - 70.0) < 0.01

    def test_insufficient_budget(self):
        mgr = ReservationManager(total_budget=10.0)
        with pytest.raises(ValueError, match="Insufficient budget"):
            mgr.reserve("p1", "spec-001", estimated_usd=15.0)

    def test_unlimited_budget(self):
        mgr = ReservationManager(total_budget=0.0)
        res = mgr.reserve("p1", "spec-001", estimated_usd=999.0)
        assert res.status == ReservationStatus.ACTIVE

    def test_concurrent_reservations(self):
        mgr = ReservationManager(total_budget=50.0)
        mgr.reserve("p1", "s1", estimated_usd=20.0)
        mgr.reserve("p1", "s2", estimated_usd=20.0)
        available = mgr.available_budget("p1")
        assert abs(available - 10.0) < 0.01

    def test_release_frees_difference(self):
        mgr = ReservationManager(total_budget=50.0)
        res = mgr.reserve("p1", "s1", estimated_usd=20.0)
        mgr.release(res.id, actual_cost=10.0)
        # Reservation released: 50 - 10 (actual spent) = 40
        available = mgr.available_budget("p1")
        assert abs(available - 40.0) < 0.01

    def test_total_reserved(self):
        mgr = ReservationManager(total_budget=100.0)
        mgr.reserve("p1", "s1", estimated_usd=10.0)
        mgr.reserve("p1", "s2", estimated_usd=15.0)
        assert mgr.total_reserved("p1") == 25.0

    def test_total_spent(self):
        mgr = ReservationManager(total_budget=100.0)
        r1 = mgr.reserve("p1", "s1", estimated_usd=10.0)
        mgr.release(r1.id, actual_cost=8.0)
        assert mgr.total_spent("p1") == 8.0

    def test_list_active(self):
        mgr = ReservationManager(total_budget=100.0)
        mgr.reserve("p1", "s1", estimated_usd=10.0)
        r2 = mgr.reserve("p1", "s2", estimated_usd=15.0)
        mgr.release(r2.id, actual_cost=12.0)
        active = mgr.list_active("p1")
        assert len(active) == 1

    def test_get_reservation(self):
        mgr = ReservationManager(total_budget=100.0)
        res = mgr.reserve("p1", "s1", estimated_usd=10.0)
        fetched = mgr.get_reservation(res.id)
        assert fetched is not None
        assert fetched.spec_id == "s1"

    def test_release_nonexistent(self):
        mgr = ReservationManager()
        with pytest.raises(KeyError):
            mgr.release("nonexistent")

    def test_double_release(self):
        mgr = ReservationManager(total_budget=100.0)
        res = mgr.reserve("p1", "s1", estimated_usd=10.0)
        mgr.release(res.id)
        with pytest.raises(ValueError, match="already released"):
            mgr.release(res.id)

    def test_list_all(self):
        mgr = ReservationManager(total_budget=100.0)
        mgr.reserve("p1", "s1", estimated_usd=5.0)
        mgr.reserve("p1", "s2", estimated_usd=10.0)
        mgr.reserve("p2", "s3", estimated_usd=15.0)
        assert len(mgr.list_all()) == 3
        assert len(mgr.list_all(scope_id="p1")) == 2


# =========================================================================
# Integration tests
# =========================================================================


class TestCostIntelligenceIntegration:
    def test_full_workflow_with_degradation(self):
        catalog = PricingCatalog()
        tracker = LiveCostTracker(catalog=catalog)
        enforcer = BudgetEnforcer(tracker)
        enforcer.set_budget("spec", "s1", hard_stop=10.0)

        # Record cost events
        for _ in range(5):
            tracker.record(CostEvent(
                provider="anthropic", model="claude-sonnet-4-6",
                input_tokens=500_000, output_tokens=100_000,
                scope="spec", scope_id="s1",
            ))

        status = enforcer.check("spec", "s1")
        # Should be near or above budget with degradation
        assert status.current_cost > 0
        assert status.percentage_used > 0

    def test_reservation_with_tracking(self):
        catalog = PricingCatalog()
        tracker = LiveCostTracker(catalog=catalog)
        mgr = ReservationManager(total_budget=50.0)

        res = mgr.reserve("p1", "s1", estimated_usd=10.0)
        # Simulate spec running
        tracker.record(CostEvent(
            provider="anthropic", model="claude-sonnet-4-6",
            input_tokens=1_000_000, output_tokens=200_000,
            scope="spec", scope_id="s1",
        ))
        actual = tracker.get_total_cost("spec", "s1")
        mgr.release(res.id, actual_cost=actual)
        assert mgr.available_budget("p1") > 0
