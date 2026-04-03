"""Tests for Feature 6.2 — Advanced Local Model Support.

Tests for LocalModelManager, RuntimeStatus, LocalModel, BenchmarkResult,
SystemResources, ResourceAlert, and hybrid mode configuration.
"""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from apps.backend.scheduling.local_model_manager import (
    BENCHMARK_PROMPTS,
    KNOWN_MODELS,
    RECOMMENDED_MODELS_BY_TASK,
    BenchmarkResult,
    LocalModel,
    LocalModelManager,
    ResourceAlert,
    RuntimeStatus,
    RuntimeType,
    SystemResources,
    _fetch_json,
    _post_json,
)

# ── RuntimeStatus tests ───────────────────────────────────────────


class TestRuntimeStatus:
    """Tests for RuntimeStatus dataclass."""

    def test_defaults(self):
        """Default values should be sensible."""
        status = RuntimeStatus()
        assert status.runtime_type == RuntimeType.UNKNOWN
        assert not status.running

    def test_to_dict(self):
        """to_dict should serialize correctly."""
        status = RuntimeStatus(
            runtime_type=RuntimeType.OLLAMA,
            running=True,
            url="http://localhost:11434",
            version="0.10.0",
            models_loaded=5,
        )
        d = status.to_dict()
        assert d["runtime_type"] == "ollama"
        assert d["running"] is True
        assert d["version"] == "0.10.0"
        assert d["models_loaded"] == 5


# ── LocalModel tests ──────────────────────────────────────────────


class TestLocalModel:
    """Tests for LocalModel dataclass."""

    def test_defaults(self):
        model = LocalModel(name="llama3:8b")
        assert model.name == "llama3:8b"
        assert model.runtime == RuntimeType.OLLAMA

    def test_to_dict(self):
        model = LocalModel(
            name="mistral:7b",
            size_gb=4.5,
            family="mistral",
            capabilities=["planning"],
        )
        d = model.to_dict()
        assert d["name"] == "mistral:7b"
        assert d["size_gb"] == 4.5
        assert d["family"] == "mistral"
        assert "planning" in d["capabilities"]


# ── BenchmarkResult tests ─────────────────────────────────────────


class TestBenchmarkResult:
    """Tests for BenchmarkResult dataclass."""

    def test_defaults(self):
        result = BenchmarkResult(model_name="test")
        assert result.model_name == "test"
        assert result.tokens_per_second == 0.0

    def test_to_dict(self):
        result = BenchmarkResult(
            model_name="llama3:8b",
            tokens_per_second=45.2,
            quality_score=80.0,
            task_type="coding",
        )
        d = result.to_dict()
        assert d["model_name"] == "llama3:8b"
        assert d["tokens_per_second"] == 45.2
        assert d["quality_score"] == 80.0
        assert "timestamp" in d


# ── SystemResources tests ─────────────────────────────────────────


class TestSystemResources:
    """Tests for SystemResources dataclass."""

    def test_to_dict(self):
        res = SystemResources(
            total_ram_gb=32.0,
            available_ram_gb=16.0,
            gpu_detected=True,
            gpu_name="RTX 4090",
            total_vram_gb=24.0,
        )
        d = res.to_dict()
        assert d["total_ram_gb"] == 32.0
        assert d["gpu_name"] == "RTX 4090"


# ── ResourceAlert tests ──────────────────────────────────────────


class TestResourceAlert:
    """Tests for ResourceAlert dataclass."""

    def test_to_dict(self):
        alert = ResourceAlert(
            alert_type="ram",
            message="High RAM usage",
            current_value=0.95,
            threshold=0.9,
            severity="critical",
        )
        d = alert.to_dict()
        assert d["alert_type"] == "ram"
        assert d["severity"] == "critical"


# ── LocalModelManager tests ───────────────────────────────────────


class TestLocalModelManager:
    """Tests for the LocalModelManager class."""

    def setup_method(self):
        self.manager = LocalModelManager()

    # ── Runtime detection ───────────────────────────────────

    @patch("apps.backend.scheduling.local_model_manager._fetch_json")
    def test_detect_ollama_running(self, mock_fetch):
        """Should detect Ollama when it responds."""
        mock_fetch.side_effect = lambda url, **kw: (
            {"version": "0.10.0"}
            if "version" in url
            else {"models": [{"name": "llama3:8b"}]}
        )
        status = self.manager.detect_runtime()
        assert status.running
        assert status.runtime_type == RuntimeType.OLLAMA
        assert status.version == "0.10.0"

    @patch("apps.backend.scheduling.local_model_manager._fetch_json")
    def test_detect_lmstudio_fallback(self, mock_fetch):
        """Should fall back to LM Studio if Ollama is down."""
        call_count = [0]

        def side_effect(url, **kw):
            call_count[0] += 1
            # Ollama calls fail (first 2 calls)
            if "11434" in url:
                return None
            # LM Studio responds
            return {"data": [{"id": "model-1"}]}

        mock_fetch.side_effect = side_effect
        status = self.manager.detect_runtime()
        assert status.running
        assert status.runtime_type == RuntimeType.LMSTUDIO

    @patch("apps.backend.scheduling.local_model_manager._fetch_json")
    def test_detect_nothing_running(self, mock_fetch):
        """Should return UNKNOWN if nothing is running."""
        mock_fetch.return_value = None
        status = self.manager.detect_runtime()
        assert not status.running
        assert status.runtime_type == RuntimeType.UNKNOWN

    # ── Model listing ───────────────────────────────────────

    @patch("apps.backend.scheduling.local_model_manager._fetch_json")
    def test_list_ollama_models(self, mock_fetch):
        """Should parse Ollama model list."""
        mock_fetch.return_value = {
            "models": [
                {"name": "llama3:8b", "size": 5_000_000_000, "modified_at": "2026-01-01"},
                {"name": "mistral:7b", "size": 4_000_000_000, "modified_at": "2026-01-01"},
            ]
        }
        models = self.manager._list_ollama_models()
        assert len(models) == 2
        assert models[0].name == "llama3:8b"
        assert models[0].family == "llama"
        assert models[1].family == "mistral"

    @patch("apps.backend.scheduling.local_model_manager._fetch_json")
    def test_list_lmstudio_models(self, mock_fetch):
        """Should parse LM Studio model list."""
        mock_fetch.return_value = {"data": [{"id": "deepseek-coder"}]}
        models = self.manager._list_lmstudio_models()
        assert len(models) == 1
        assert models[0].name == "deepseek-coder"
        assert models[0].runtime == RuntimeType.LMSTUDIO

    @patch("apps.backend.scheduling.local_model_manager._fetch_json")
    def test_list_models_empty(self, mock_fetch):
        """Should return empty list when server is down."""
        mock_fetch.return_value = None
        models = self.manager.list_models()
        assert models == []

    # ── Model family detection ──────────────────────────────

    def test_detect_family_llama(self):
        assert self.manager._detect_model_family("llama3:8b") == "llama"

    def test_detect_family_mistral(self):
        assert self.manager._detect_model_family("mistral:7b-instruct") == "mistral"

    def test_detect_family_deepseek(self):
        assert self.manager._detect_model_family("deepseek-coder-v2:16b") == "deepseek"

    def test_detect_family_unknown(self):
        assert self.manager._detect_model_family("custom-model") == "unknown"

    # ── Quantization detection ──────────────────────────────

    def test_detect_quantization_q4(self):
        assert self.manager._detect_quantization("model-Q4_K_M") == "Q4_K_M"

    def test_detect_quantization_f16(self):
        assert self.manager._detect_quantization("model-F16") == "F16"

    def test_detect_quantization_none(self):
        assert self.manager._detect_quantization("llama3:8b") == ""

    # ── Benchmarking ────────────────────────────────────────

    @patch("apps.backend.scheduling.local_model_manager._post_json")
    def test_benchmark_model(self, mock_post):
        """Should parse Ollama generate response."""
        mock_post.return_value = {
            "response": "def merge_sorted_lists(a: list, b: list) -> list:\n    return sorted(a + b)",
            "prompt_eval_count": 50,
            "eval_count": 30,
            "eval_duration": 1_000_000_000,  # 1 second
            "prompt_eval_duration": 200_000_000,  # 200ms
        }
        result = self.manager.benchmark_model("llama3:8b", "coding")
        assert result.model_name == "llama3:8b"
        assert result.tokens_per_second == 30.0
        assert result.time_to_first_token_ms == 200.0
        assert result.quality_score > 0

    @patch("apps.backend.scheduling.local_model_manager._post_json")
    def test_benchmark_no_response(self, mock_post):
        """Should handle benchmark failure gracefully."""
        mock_post.return_value = None
        result = self.manager.benchmark_model("bad-model")
        assert result.tokens_per_second == 0.0

    def test_get_benchmark_results_empty(self):
        """Should return empty results when nothing benchmarked."""
        results = self.manager.get_benchmark_results("nonexistent")
        assert results == {"nonexistent": []}

    @patch("apps.backend.scheduling.local_model_manager._post_json")
    def test_benchmark_cached(self, mock_post):
        """Benchmark results should be cached."""
        mock_post.return_value = {
            "response": "result",
            "eval_count": 10,
            "eval_duration": 500_000_000,
            "prompt_eval_count": 20,
            "prompt_eval_duration": 100_000_000,
        }
        self.manager.benchmark_model("test-model", "general")
        results = self.manager.get_benchmark_results("test-model")
        assert len(results["test-model"]) == 1

    # ── Quality assessment ──────────────────────────────────

    def test_assess_quality_coding(self):
        """Coding output with function def should score well."""
        code = 'def merge_sorted_lists(a: list, b: list) -> list:\n    """Merge two sorted lists."""\n    return sorted(a + b)'
        score = self.manager._assess_quality(code, "coding")
        assert score >= 50

    def test_assess_quality_planning(self):
        """Planning output with numbered list should score well."""
        plan = "1. Create models\n2. Implement endpoints\n3. GET /api/tasks\n4. POST /api/tasks\n5. Add tests"
        score = self.manager._assess_quality(plan, "planning")
        assert score >= 40

    def test_assess_quality_review(self):
        """Review output with suggestions should score well."""
        review = "I suggest using enumerate instead of range(len(data)).\nUse 'is not None' instead of '!= None'.\nBetter to use list comprehension."
        score = self.manager._assess_quality(review, "review")
        assert score >= 40

    def test_assess_quality_empty(self):
        """Empty output should score 0."""
        assert self.manager._assess_quality("", "general") == 0.0
        assert self.manager._assess_quality("   ", "general") == 0.0

    # ── System resources ────────────────────────────────────

    def test_get_system_resources_basic(self):
        """Should return basic resources with os_name populated."""
        import sys

        # Temporarily hide psutil so the fallback path runs
        saved = sys.modules.get("psutil")
        sys.modules["psutil"] = None  # type: ignore[assignment]
        try:
            # Also patch GPU detection to avoid subprocess calls
            with patch.object(self.manager, "_detect_gpu", side_effect=lambda r: r):
                resources = self.manager.get_system_resources()
                assert resources.os_name  # should be 'Windows', 'Linux', etc.
                assert resources.cpu_count >= 0
        finally:
            if saved is not None:
                sys.modules["psutil"] = saved
            else:
                sys.modules.pop("psutil", None)

    # ── Resource alerts ─────────────────────────────────────

    def test_check_alerts_high_ram(self):
        """Should alert when RAM usage exceeds threshold."""
        fake_resources = SystemResources(
            total_ram_gb=16.0,
            available_ram_gb=0.5,  # 96.9% usage → critical
        )

        def mock_get_resources():
            self.manager._system_resources = fake_resources
            return fake_resources

        with patch.object(self.manager, "get_system_resources", side_effect=mock_get_resources):
            alerts = self.manager.check_resource_alerts(ram_threshold=0.9)
            assert len(alerts) >= 1
            assert alerts[0].alert_type == "ram"
            assert alerts[0].severity == "critical"

    def test_check_alerts_high_vram(self):
        """Should alert when VRAM usage exceeds threshold."""
        self.manager._system_resources = SystemResources(
            total_ram_gb=32.0,
            available_ram_gb=20.0,
            total_vram_gb=8.0,
            available_vram_gb=0.5,
            gpu_detected=True,
        )
        with patch.object(self.manager, "get_system_resources", return_value=self.manager._system_resources):
            alerts = self.manager.check_resource_alerts(vram_threshold=0.9)
            vram_alerts = [a for a in alerts if a.alert_type == "vram"]
            assert len(vram_alerts) == 1

    def test_no_alerts_when_ok(self):
        """No alerts when usage is below threshold."""
        self.manager._system_resources = SystemResources(
            total_ram_gb=32.0,
            available_ram_gb=20.0,
        )
        with patch.object(self.manager, "get_system_resources", return_value=self.manager._system_resources):
            alerts = self.manager.check_resource_alerts()
            assert len(alerts) == 0

    # ── Recommendations ─────────────────────────────────────

    @patch("apps.backend.scheduling.local_model_manager._fetch_json")
    def test_recommend_models_coding(self, mock_fetch):
        """Should recommend coding models."""
        mock_fetch.return_value = {"models": []}
        self.manager._system_resources = SystemResources(available_ram_gb=16.0)
        recs = self.manager.recommend_models("coding", max_ram_gb=16.0)
        assert len(recs) > 0
        assert all("model" in r for r in recs)
        assert all("fits_resources" in r for r in recs)

    @patch("apps.backend.scheduling.local_model_manager._fetch_json")
    def test_recommend_models_ram_filter(self, mock_fetch):
        """Models exceeding RAM should be flagged."""
        mock_fetch.return_value = {"models": []}
        recs = self.manager.recommend_models("planning", max_ram_gb=5.0)
        large_models = [r for r in recs if not r["fits_resources"]]
        # llama3:70b needs 40GB, should not fit
        assert any(r["model"] == "llama3:70b" for r in large_models)

    # ── Hybrid mode ─────────────────────────────────────────

    def test_configure_hybrid_mode(self):
        """Should produce a valid hybrid config."""
        config = self.manager.configure_hybrid_mode(
            local_model="llama3:8b",
            cloud_provider="anthropic",
            cloud_model="claude-sonnet-4-20250514",
        )
        assert config["hybrid_mode"] is True
        assert config["draft"]["model"] == "llama3:8b"
        assert config["validation"]["provider"] == "anthropic"
        assert len(config["pipeline"]) == 3

    def test_configure_hybrid_mode_custom_cloud(self):
        """Should support custom cloud provider/model."""
        config = self.manager.configure_hybrid_mode(
            local_model="mistral:7b",
            cloud_provider="openai",
            cloud_model="gpt-4o",
        )
        assert config["validation"]["provider"] == "openai"
        assert config["validation"]["model"] == "gpt-4o"

    # ── Model compatibility ─────────────────────────────────

    def test_check_compatibility_fits(self):
        """Model that fits resources should be compatible."""
        self.manager._system_resources = SystemResources(
            available_ram_gb=16.0,
            available_vram_gb=16.0,
            gpu_detected=True,
        )
        report = self.manager.check_model_compatibility("llama3:8b")
        assert report["compatible"]
        assert report["ram_ok"]
        assert len(report["warnings"]) == 0

    def test_check_compatibility_too_large(self):
        """Model exceeding RAM should be incompatible."""
        self.manager._system_resources = SystemResources(
            available_ram_gb=4.0,
            available_vram_gb=4.0,
            gpu_detected=True,
        )
        report = self.manager.check_model_compatibility("llama3:70b")
        assert not report["compatible"]
        assert not report["ram_ok"]
        assert len(report["warnings"]) > 0

    def test_check_compatibility_no_gpu_warning(self):
        """Should warn when GPU is needed but not detected."""
        self.manager._system_resources = SystemResources(
            available_ram_gb=50.0,
            gpu_detected=False,
        )
        report = self.manager.check_model_compatibility("llama3:8b")
        gpu_warnings = [w for w in report["warnings"] if "GPU" in w or "CPU" in w]
        assert len(gpu_warnings) >= 1

    # ── Stats ───────────────────────────────────────────────

    @patch("apps.backend.scheduling.local_model_manager._fetch_json")
    def test_get_stats(self, mock_fetch):
        """get_stats should return summary."""
        mock_fetch.return_value = None
        stats = self.manager.get_stats()
        assert "runtime" in stats
        assert "models_count" in stats
        assert "benchmarks_count" in stats

    # ── Known data ──────────────────────────────────────────

    def test_known_models_data(self):
        """KNOWN_MODELS should have valid entries."""
        for name, info in KNOWN_MODELS.items():
            assert "ram_gb" in info
            assert "tasks" in info
            assert isinstance(info["tasks"], list)

    def test_recommended_models_by_task(self):
        """RECOMMENDED_MODELS_BY_TASK should have entries for all task types."""
        assert "coding" in RECOMMENDED_MODELS_BY_TASK
        assert "planning" in RECOMMENDED_MODELS_BY_TASK
        assert "review" in RECOMMENDED_MODELS_BY_TASK

    def test_benchmark_prompts_exist(self):
        """BENCHMARK_PROMPTS should have entries for key task types."""
        assert "coding" in BENCHMARK_PROMPTS
        assert "planning" in BENCHMARK_PROMPTS
        assert "review" in BENCHMARK_PROMPTS
        assert "general" in BENCHMARK_PROMPTS
