"""
Carbon / Energy Profiler — Track energy consumption and CO2 footprint.

Estimates energy usage (kWh) and carbon emissions (gCO2eq) for LLM
inference, CI/CD pipelines, and local compute.  Supports per-provider
and per-model tracking with regional grid intensity factors.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ComputeSource(str, Enum):
    LLM_CLOUD = "llm_cloud"
    LLM_LOCAL = "llm_local"
    CI_CD = "ci_cd"
    LOCAL_DEV = "local_dev"


@dataclass
class EnergyRecord:
    """A single energy consumption record."""

    source: ComputeSource
    provider: str = ""
    model: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    duration_s: float = 0.0
    kwh: float = 0.0
    co2_g: float = 0.0
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class CarbonReport:
    """Aggregated carbon footprint report."""

    records: list[EnergyRecord] = field(default_factory=list)
    total_kwh: float = 0.0
    total_co2_g: float = 0.0
    period_start: float = 0.0
    period_end: float = 0.0
    by_provider: dict[str, float] = field(default_factory=dict)
    by_model: dict[str, float] = field(default_factory=dict)

    @property
    def summary(self) -> str:
        return f"{self.total_kwh:.4f} kWh, {self.total_co2_g:.1f} gCO2eq over {len(self.records)} operations"


# Energy per million tokens (kWh) — approximate estimates
_MODEL_ENERGY_KWH_PER_M_TOKENS: dict[str, float] = {
    # Cloud API models (data centre PUE ~1.2 included)
    "claude-opus-4": 0.012,
    "claude-sonnet-4": 0.006,
    "claude-haiku-3.5": 0.002,
    "gpt-4.1": 0.010,
    "gpt-4o": 0.008,
    "gpt-4o-mini": 0.003,
    "gemini-2.5-pro": 0.009,
    "gemini-2.5-flash": 0.003,
    # Local models (Ollama, consumer GPU)
    "llama-3.3-70b": 0.080,
    "llama-3.3-8b": 0.015,
    "mistral-large": 0.060,
    "mistral-small": 0.012,
    "deepseek-v3": 0.070,
    "qwen-2.5-72b": 0.075,
    "qwen-2.5-7b": 0.014,
    "phi-3-mini": 0.008,
}

# Regional grid carbon intensity (gCO2/kWh) — 2024 averages
_GRID_INTENSITY: dict[str, float] = {
    "us-east": 380,
    "us-west": 230,
    "eu-west": 270,
    "eu-north": 50,  # Nordics — very clean
    "eu-central": 340,
    "ap-southeast": 500,
    "ap-northeast": 450,
    "ca-central": 30,  # Quebec hydro
    "global_avg": 440,
}


class EnergyTracker:
    """Track energy consumption and carbon emissions.

    Usage::

        tracker = EnergyTracker(region="eu-west")
        tracker.record_llm_call("anthropic", "claude-sonnet-4", tokens_in=1000, tokens_out=500)
        report = tracker.generate_report()
    """

    def __init__(self, region: str = "global_avg") -> None:
        self._region = region
        self._grid_intensity = _GRID_INTENSITY.get(
            region, _GRID_INTENSITY["global_avg"]
        )
        self._records: list[EnergyRecord] = []

    def record_llm_call(
        self,
        provider: str,
        model: str,
        tokens_in: int = 0,
        tokens_out: int = 0,
        duration_s: float = 0.0,
        source: ComputeSource = ComputeSource.LLM_CLOUD,
    ) -> EnergyRecord:
        """Record a single LLM API call."""
        total_tokens = tokens_in + tokens_out
        energy_per_m = _MODEL_ENERGY_KWH_PER_M_TOKENS.get(model, 0.005)
        kwh = (total_tokens / 1_000_000) * energy_per_m

        if source == ComputeSource.LLM_LOCAL:
            co2 = kwh * self._grid_intensity
        else:
            # Cloud providers often use cleaner grids
            co2 = kwh * self._grid_intensity * 0.7

        record = EnergyRecord(
            source=source,
            provider=provider,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            duration_s=duration_s,
            kwh=kwh,
            co2_g=co2,
        )
        self._records.append(record)
        return record

    def record_ci_run(
        self, duration_s: float, runner_type: str = "standard"
    ) -> EnergyRecord:
        """Record a CI/CD pipeline run."""
        # Approximate: standard runner ~0.05 kW, GPU runner ~0.3 kW
        power_kw = 0.3 if "gpu" in runner_type.lower() else 0.05
        kwh = power_kw * (duration_s / 3600)
        co2 = kwh * self._grid_intensity

        record = EnergyRecord(
            source=ComputeSource.CI_CD,
            duration_s=duration_s,
            kwh=kwh,
            co2_g=co2,
            metadata={"runner_type": runner_type},
        )
        self._records.append(record)
        return record

    def generate_report(
        self,
        since: float | None = None,
        until: float | None = None,
    ) -> CarbonReport:
        """Generate an aggregated carbon report."""
        filtered = self._records
        if since:
            filtered = [r for r in filtered if r.timestamp >= since]
        if until:
            filtered = [r for r in filtered if r.timestamp <= until]

        report = CarbonReport(
            records=filtered,
            total_kwh=sum(r.kwh for r in filtered),
            total_co2_g=sum(r.co2_g for r in filtered),
            period_start=min((r.timestamp for r in filtered), default=0),
            period_end=max((r.timestamp for r in filtered), default=0),
        )

        for r in filtered:
            report.by_provider[r.provider] = (
                report.by_provider.get(r.provider, 0) + r.co2_g
            )
            if r.model:
                report.by_model[r.model] = report.by_model.get(r.model, 0) + r.co2_g

        return report

    @property
    def total_co2_g(self) -> float:
        return sum(r.co2_g for r in self._records)

    @property
    def total_kwh(self) -> float:
        return sum(r.kwh for r in self._records)
