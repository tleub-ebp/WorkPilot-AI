"""Tests for Feature 6.1 — Routing intelligent multi-provider.

Tests: ProviderConfig (3), PerformanceRecord (2), RoutingDecision (2), PipelineConfig (2),
       ABTest (3), IntelligentRouter — providers (7), routing strategies (8),
       performance (4), fallback (4), pipelines (3), A/B testing (5),
       routing log & stats (2) = 45 tests.
"""

import pytest

from apps.backend.scheduling.intelligent_router import (
    ABTest,
    ABTestStatus,
    IntelligentRouter,
    PerformanceRecord,
    PipelineConfig,
    ProviderConfig,
    ProviderStatus,
    RoutingDecision,
    RoutingStrategy,
    TaskType,
)


# ---------------------------------------------------------------------------
# Data model tests
# ---------------------------------------------------------------------------

class TestProviderConfig:
    def test_create_provider(self):
        config = ProviderConfig(provider="anthropic", model="claude-sonnet-4-20250514",
                                capabilities=["coding", "planning"])
        assert config.provider_model_key == "anthropic/claude-sonnet-4-20250514"
        assert config.is_available
        assert not config.is_local

    def test_unavailable_when_down(self):
        config = ProviderConfig(provider="openai", model="gpt-4o",
                                status=ProviderStatus.DOWN)
        assert not config.is_available

    def test_to_dict(self):
        config = ProviderConfig(provider="anthropic", model="claude-sonnet-4-20250514")
        d = config.to_dict()
        assert d["status"] == "available"
        assert d["provider_model_key"] == "anthropic/claude-sonnet-4-20250514"


class TestPerformanceRecord:
    def test_create_record(self):
        record = PerformanceRecord(
            provider="anthropic", model="claude-sonnet-4-20250514",
            task_type="coding", latency_ms=1200, quality_score=85.0, success=True,
        )
        assert record.timestamp != ""
        assert record.success

    def test_to_dict(self):
        record = PerformanceRecord(
            provider="openai", model="gpt-4o",
            task_type="review", latency_ms=800, quality_score=90.0, success=True,
        )
        d = record.to_dict()
        assert d["quality_score"] == 90.0


class TestRoutingDecision:
    def test_create_decision(self):
        decision = RoutingDecision(
            provider="anthropic", model="claude-sonnet-4-20250514",
            reason="Best performance", strategy="best_performance", score=85.0,
        )
        assert decision.strategy == RoutingStrategy.BEST_PERFORMANCE
        assert decision.timestamp != ""

    def test_to_dict(self):
        decision = RoutingDecision(
            provider="openai", model="gpt-4o",
            reason="Cheapest", strategy=RoutingStrategy.CHEAPEST, score=90.0,
        )
        d = decision.to_dict()
        assert d["strategy"] == "cheapest"


class TestPipelineConfig:
    def test_create_pipeline(self):
        pipeline = PipelineConfig(
            pipeline_id="pipe-1", name="Default",
            phase_routing={
                "planning": {"provider": "anthropic", "model": "claude-sonnet-4-20250514"},
                "coding": {"provider": "openai", "model": "gpt-4o"},
            },
        )
        result = pipeline.get_provider_for_phase("planning")
        assert result == ("anthropic", "claude-sonnet-4-20250514")

    def test_get_nonexistent_phase(self):
        pipeline = PipelineConfig(pipeline_id="pipe-1", name="Test")
        assert pipeline.get_provider_for_phase("unknown") is None


class TestABTest:
    def test_create_test(self):
        test = ABTest(
            test_id="ab-1", name="Claude vs GPT", task_type="coding",
            provider_a="anthropic", model_a="claude-sonnet-4-20250514",
            provider_b="openai", model_b="gpt-4o",
        )
        assert test.status == ABTestStatus.RUNNING
        assert test.total_runs == 0

    def test_summary(self):
        test = ABTest(
            test_id="ab-1", name="Test", task_type="coding",
            provider_a="anthropic", model_a="claude-sonnet-4-20250514",
            provider_b="openai", model_b="gpt-4o",
            results_a=[{"quality_score": 80, "latency_ms": 1000, "cost": 0.01}],
            results_b=[{"quality_score": 90, "latency_ms": 800, "cost": 0.02}],
        )
        summary = test.get_summary()
        assert summary["a"]["avg_quality"] == 80.0
        assert summary["b"]["avg_quality"] == 90.0
        assert summary["total_runs"] == 2

    def test_to_dict(self):
        test = ABTest(
            test_id="ab-1", name="Test", task_type="coding",
            provider_a="a", model_a="m-a", provider_b="b", model_b="m-b",
        )
        d = test.to_dict()
        assert d["status"] == "running"
        assert "summary" in d


# ---------------------------------------------------------------------------
# IntelligentRouter — Provider management
# ---------------------------------------------------------------------------

class TestRouterProviderManagement:
    def test_register_provider(self):
        router = IntelligentRouter()
        config = router.register_provider("anthropic", "claude-sonnet-4-20250514",
                                          capabilities=["coding"])
        assert config.provider == "anthropic"
        assert len(router.get_available_providers()) == 1

    def test_unregister_provider(self):
        router = IntelligentRouter()
        router.register_provider("anthropic", "claude-sonnet-4-20250514")
        assert router.unregister_provider("anthropic", "claude-sonnet-4-20250514")
        assert len(router.get_available_providers()) == 0

    def test_unregister_nonexistent(self):
        router = IntelligentRouter()
        assert not router.unregister_provider("x", "y")

    def test_get_provider(self):
        router = IntelligentRouter()
        router.register_provider("openai", "gpt-4o")
        config = router.get_provider("openai", "gpt-4o")
        assert config is not None
        assert config.model == "gpt-4o"

    def test_get_available_filtered_by_capability(self):
        router = IntelligentRouter()
        router.register_provider("anthropic", "claude-sonnet-4-20250514", capabilities=["coding"])
        router.register_provider("openai", "gpt-4o", capabilities=["review"])
        coding = router.get_available_providers("coding")
        assert len(coding) == 1
        assert coding[0].provider == "anthropic"

    def test_update_provider_status(self):
        router = IntelligentRouter()
        router.register_provider("anthropic", "claude-sonnet-4-20250514")
        assert router.update_provider_status("anthropic", "claude-sonnet-4-20250514", "down")
        config = router.get_provider("anthropic", "claude-sonnet-4-20250514")
        assert config.status == ProviderStatus.DOWN

    def test_mark_rate_limited(self):
        router = IntelligentRouter()
        router.register_provider("openai", "gpt-4o")
        assert router.mark_rate_limited("openai", "gpt-4o", "2026-01-01T12:00:00Z")
        config = router.get_provider("openai", "gpt-4o")
        assert config.status == ProviderStatus.RATE_LIMITED


# ---------------------------------------------------------------------------
# IntelligentRouter — Routing strategies
# ---------------------------------------------------------------------------

class TestRouterStrategies:
    def _setup_router(self) -> IntelligentRouter:
        router = IntelligentRouter()
        router.register_provider("anthropic", "claude-sonnet-4-20250514",
                                 capabilities=["coding", "planning"],
                                 priority=1, cost_per_1m_input=3.0, cost_per_1m_output=15.0)
        router.register_provider("openai", "gpt-4o",
                                 capabilities=["coding", "review"],
                                 priority=2, cost_per_1m_input=2.5, cost_per_1m_output=10.0)
        router.register_provider("openai", "gpt-4o-mini",
                                 capabilities=["coding", "quick_feedback"],
                                 priority=3, cost_per_1m_input=0.15, cost_per_1m_output=0.60)
        return router

    def test_route_best_performance_default(self):
        router = self._setup_router()
        decision = router.route("coding")
        assert decision is not None
        assert decision.strategy == RoutingStrategy.BEST_PERFORMANCE

    def test_route_cheapest(self):
        router = self._setup_router()
        decision = router.route("coding", strategy="cheapest")
        assert decision is not None
        assert decision.provider == "openai"
        assert decision.model == "gpt-4o-mini"

    def test_route_cheapest_prefers_local(self):
        router = self._setup_router()
        router.register_provider("ollama", "llama3:8b", capabilities=["coding"],
                                 is_local=True, priority=5)
        decision = router.route("coding", strategy="cheapest")
        assert decision.provider == "ollama"

    def test_route_lowest_latency(self):
        router = self._setup_router()
        router._providers["openai/gpt-4o-mini"].avg_latency_ms = 200
        router._providers["anthropic/claude-sonnet-4-20250514"].avg_latency_ms = 500
        router._providers["openai/gpt-4o"].avg_latency_ms = 400
        decision = router.route("coding", strategy="lowest_latency")
        assert decision.model == "gpt-4o-mini"

    def test_route_round_robin(self):
        router = self._setup_router()
        d1 = router.route("coding", strategy="round_robin")
        d2 = router.route("coding", strategy="round_robin")
        d3 = router.route("coding", strategy="round_robin")
        # Should cycle through providers
        providers = [f"{d.provider}/{d.model}" for d in [d1, d2, d3]]
        assert len(set(providers)) >= 2  # At least 2 different providers

    def test_route_no_available_providers(self):
        router = IntelligentRouter()
        decision = router.route("coding")
        assert decision is None

    def test_route_with_max_cost(self):
        router = self._setup_router()
        decision = router.route("coding", max_cost=1.0)
        assert decision is not None
        config = router.get_provider(decision.provider, decision.model)
        assert config.cost_per_1m_input + config.cost_per_1m_output <= 1.0

    def test_route_skips_unavailable_providers(self):
        router = self._setup_router()
        router.update_provider_status("anthropic", "claude-sonnet-4-20250514", "down")
        decision = router.route("coding")
        assert decision.provider != "anthropic"


# ---------------------------------------------------------------------------
# IntelligentRouter — Performance tracking
# ---------------------------------------------------------------------------

class TestRouterPerformance:
    def test_record_performance(self):
        router = IntelligentRouter()
        router.register_provider("anthropic", "claude-sonnet-4-20250514")
        record = router.record_performance(
            "anthropic", "claude-sonnet-4-20250514", "coding",
            latency_ms=1200, quality_score=85.0, success=True,
        )
        assert record.quality_score == 85.0

    def test_get_performance_scores(self):
        router = IntelligentRouter()
        router.register_provider("anthropic", "claude-sonnet-4-20250514")
        for _ in range(5):
            router.record_performance(
                "anthropic", "claude-sonnet-4-20250514", "coding",
                latency_ms=1000, quality_score=90.0, success=True,
            )
        scores = router.get_performance_scores("coding")
        assert "anthropic/claude-sonnet-4-20250514" in scores
        assert scores["anthropic/claude-sonnet-4-20250514"]["avg_quality"] == 90.0

    def test_performance_affects_routing(self):
        router = IntelligentRouter()
        router.register_provider("anthropic", "claude-sonnet-4-20250514",
                                 capabilities=["coding"], priority=2)
        router.register_provider("openai", "gpt-4o",
                                 capabilities=["coding"], priority=2)
        # Record great performance for OpenAI
        for _ in range(10):
            router.record_performance("openai", "gpt-4o", "coding",
                                      latency_ms=500, quality_score=95.0, success=True)
        # Record poor performance for Anthropic
        for _ in range(10):
            router.record_performance("anthropic", "claude-sonnet-4-20250514", "coding",
                                      latency_ms=2000, quality_score=60.0, success=True)
        decision = router.route("coding", strategy="best_performance")
        assert decision.provider == "openai"

    def test_updates_avg_latency(self):
        router = IntelligentRouter()
        router.register_provider("anthropic", "claude-sonnet-4-20250514")
        router.record_performance("anthropic", "claude-sonnet-4-20250514", "coding",
                                  latency_ms=1000, quality_score=80, success=True)
        router.record_performance("anthropic", "claude-sonnet-4-20250514", "coding",
                                  latency_ms=2000, quality_score=80, success=True)
        config = router.get_provider("anthropic", "claude-sonnet-4-20250514")
        assert config.avg_latency_ms == 1500.0


# ---------------------------------------------------------------------------
# IntelligentRouter — Fallback
# ---------------------------------------------------------------------------

class TestRouterFallback:
    def test_get_fallback_when_primary_fails(self):
        router = IntelligentRouter()
        router.register_provider("anthropic", "claude-sonnet-4-20250514",
                                 capabilities=["coding"], priority=1)
        router.register_provider("openai", "gpt-4o",
                                 capabilities=["coding"], priority=2)
        fallback = router.get_fallback("anthropic", "claude-sonnet-4-20250514", "coding")
        assert fallback is not None
        assert fallback.provider == "openai"

    def test_get_fallback_no_alternative(self):
        router = IntelligentRouter()
        router.register_provider("anthropic", "claude-sonnet-4-20250514",
                                 capabilities=["coding"])
        fallback = router.get_fallback("anthropic", "claude-sonnet-4-20250514", "coding")
        assert fallback is None

    def test_set_and_use_fallback_chain(self):
        router = IntelligentRouter()
        router.register_provider("anthropic", "claude-sonnet-4-20250514",
                                 capabilities=["coding"])
        router.register_provider("openai", "gpt-4o", capabilities=["coding"])
        router.set_fallback_chain("coding", [
            "anthropic/claude-sonnet-4-20250514",
            "openai/gpt-4o",
        ])
        decision = router.route("coding", strategy="fallback_chain")
        assert decision.provider == "anthropic"
        assert len(decision.fallback_chain) >= 1

    def test_fallback_chain_skips_unavailable(self):
        router = IntelligentRouter()
        router.register_provider("anthropic", "claude-sonnet-4-20250514",
                                 capabilities=["coding"])
        router.register_provider("openai", "gpt-4o", capabilities=["coding"])
        router.update_provider_status("anthropic", "claude-sonnet-4-20250514", "down")
        router.set_fallback_chain("coding", [
            "anthropic/claude-sonnet-4-20250514",
            "openai/gpt-4o",
        ])
        decision = router.route("coding", strategy="fallback_chain")
        assert decision.provider == "openai"


# ---------------------------------------------------------------------------
# IntelligentRouter — Pipelines
# ---------------------------------------------------------------------------

class TestRouterPipelines:
    def test_create_pipeline(self):
        router = IntelligentRouter()
        router.register_provider("anthropic", "claude-sonnet-4-20250514")
        router.register_provider("openai", "gpt-4o")
        pipeline = router.create_pipeline("Production", {
            "planning": {"provider": "anthropic", "model": "claude-sonnet-4-20250514"},
            "coding": {"provider": "openai", "model": "gpt-4o"},
        })
        assert pipeline.pipeline_id.startswith("pipe-")
        assert len(router.list_pipelines()) == 1

    def test_route_with_pipeline(self):
        router = IntelligentRouter()
        router.register_provider("anthropic", "claude-sonnet-4-20250514",
                                 capabilities=["planning", "coding"])
        router.register_provider("openai", "gpt-4o",
                                 capabilities=["planning", "coding"])
        pipeline = router.create_pipeline("Test", {
            "coding": {"provider": "openai", "model": "gpt-4o"},
        })
        decision = router.route("coding", pipeline_id=pipeline.pipeline_id)
        assert decision.provider == "openai"
        assert decision.model == "gpt-4o"

    def test_pipeline_fallback_if_provider_unavailable(self):
        router = IntelligentRouter()
        router.register_provider("anthropic", "claude-sonnet-4-20250514",
                                 capabilities=["coding"], priority=2)
        router.register_provider("openai", "gpt-4o",
                                 capabilities=["coding"], priority=1)
        router.update_provider_status("openai", "gpt-4o", "down")
        pipeline = router.create_pipeline("Test", {
            "coding": {"provider": "openai", "model": "gpt-4o"},
        })
        # Should fall through to normal routing since pipeline provider is down
        decision = router.route("coding", pipeline_id=pipeline.pipeline_id)
        assert decision.provider == "anthropic"


# ---------------------------------------------------------------------------
# IntelligentRouter — A/B Testing
# ---------------------------------------------------------------------------

class TestRouterABTesting:
    def test_create_ab_test(self):
        router = IntelligentRouter()
        test = router.create_ab_test(
            "Claude vs GPT", "coding",
            "anthropic", "claude-sonnet-4-20250514",
            "openai", "gpt-4o",
        )
        assert test.test_id.startswith("ab-")
        assert test.status == ABTestStatus.RUNNING

    def test_route_ab_test_alternates(self):
        router = IntelligentRouter()
        test = router.create_ab_test(
            "Test", "coding",
            "anthropic", "claude-sonnet-4-20250514",
            "openai", "gpt-4o",
        )
        d1 = router.route_ab_test(test.test_id)
        router.record_ab_result(test.test_id, "a", 85, 1000)
        d2 = router.route_ab_test(test.test_id)
        # First should be A (fewer runs), second should be B
        assert d1.provider == "anthropic"
        assert d2.provider == "openai"

    def test_record_ab_result(self):
        router = IntelligentRouter()
        test = router.create_ab_test("Test", "coding", "a", "m-a", "b", "m-b")
        assert router.record_ab_result(test.test_id, "a", 85.0, 1000, 0.01)
        assert router.record_ab_result(test.test_id, "b", 90.0, 800, 0.02)
        assert test.total_runs == 2

    def test_complete_ab_test(self):
        router = IntelligentRouter()
        test = router.create_ab_test("Test", "coding", "a", "m-a", "b", "m-b")
        router.record_ab_result(test.test_id, "a", 85.0, 1000, 0.01)
        router.record_ab_result(test.test_id, "b", 90.0, 800, 0.02)
        summary = router.complete_ab_test(test.test_id)
        assert summary is not None
        assert summary["a"]["avg_quality"] == 85.0
        assert summary["b"]["avg_quality"] == 90.0
        assert test.status == ABTestStatus.COMPLETED

    def test_route_ab_completed_returns_none(self):
        router = IntelligentRouter()
        test = router.create_ab_test("Test", "coding", "a", "m-a", "b", "m-b")
        router.complete_ab_test(test.test_id)
        assert router.route_ab_test(test.test_id) is None


# ---------------------------------------------------------------------------
# IntelligentRouter — Routing log & Stats
# ---------------------------------------------------------------------------

class TestRouterLogAndStats:
    def test_routing_log(self):
        router = IntelligentRouter()
        router.register_provider("anthropic", "claude-sonnet-4-20250514",
                                 capabilities=["coding"])
        router.route("coding")
        router.route("coding")
        log = router.get_routing_log()
        assert len(log) == 2

    def test_get_stats(self):
        router = IntelligentRouter()
        router.register_provider("anthropic", "claude-sonnet-4-20250514")
        router.register_provider("ollama", "llama3:8b", is_local=True)
        router.update_provider_status("anthropic", "claude-sonnet-4-20250514", "rate_limited")
        router.create_ab_test("Test", "coding", "a", "m-a", "b", "m-b")
        stats = router.get_stats()
        assert stats["total_providers"] == 2
        assert stats["local_providers"] == 1
        assert stats["rate_limited"] == 1
        assert stats["ab_tests_running"] == 1
