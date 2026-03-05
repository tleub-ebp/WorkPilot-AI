"""
Phase Configuration Module
===========================

Handles model and thinking level configuration for different execution phases.
Reads configuration from task_metadata.json and provides resolved model IDs.
"""

import json
import os
from pathlib import Path
from typing import Literal, TypedDict

# Model shorthand to full model ID mapping
MODEL_ID_MAP: dict[str, str] = {
    "opus": "claude-opus-4-5-20251101",
    "sonnet": "claude-sonnet-4-5-20250929",
    "haiku": "claude-haiku-4-5-20251001",
}

# Thinking level to budget tokens mapping (None = no extended thinking)
# Values must match workpilot-ai/src/shared/constants/models.ts THINKING_BUDGET_MAP
THINKING_BUDGET_MAP: dict[str, int | None] = {
    "none": None,
    "low": 1024,
    "medium": 4096,  # Moderate analysis
    "high": 16384,  # Deep thinking for QA review
    "ultrathink": 63999,  # Maximum reasoning depth (API requires max_tokens >= budget + 1, so 63999 + 1 = 64000 limit)
}

# Spec runner phase-specific thinking levels
# Heavy phases use ultrathink for deep analysis
# Light phases use medium after compaction
SPEC_PHASE_THINKING_LEVELS: dict[str, str] = {
    # Heavy phases - ultrathink (discovery, spec creation, self-critique)
    "discovery": "ultrathink",
    "spec_writing": "ultrathink",
    "self_critique": "ultrathink",
    # Light phases - medium (after first invocation with compaction)
    "requirements": "medium",
    "research": "medium",
    "context": "medium",
    "planning": "medium",
    "validation": "medium",
    "quick_spec": "medium",
    "historical_context": "medium",
    "complexity_assessment": "medium",
}

# Default phase configuration (fallback, matches 'Balanced' profile)
DEFAULT_PHASE_MODELS: dict[str, str] = {
    "spec": "sonnet",
    "planning": "sonnet",  # Changed from "opus" (fix #433)
    "coding": "sonnet",
    "qa": "sonnet",
}

# Provider-specific default models (full model IDs, not Claude shorthands).
# Used when a task has a provider set but no explicit model configuration.
# Keys must match provider names from provider_api.py / ProviderContext.
# Values are the "standard" tier model for each provider — a sensible default
# that balances quality and cost across all phases.
PROVIDER_DEFAULT_MODELS: dict[str, dict[str, str]] = {
    # Anthropic / Claude — use Claude shorthands (resolved by resolve_model_id)
    "anthropic": {"spec": "sonnet", "planning": "sonnet", "coding": "sonnet", "qa": "sonnet"},
    "claude":    {"spec": "sonnet", "planning": "sonnet", "coding": "sonnet", "qa": "sonnet"},
    # OpenAI
    "openai":    {"spec": "gpt-4o", "planning": "gpt-4o", "coding": "gpt-4o", "qa": "gpt-4o"},
    # GitHub Copilot
    "copilot":   {"spec": "claude-sonnet-4-5", "planning": "claude-sonnet-4-5", "coding": "claude-sonnet-4-5", "qa": "claude-sonnet-4-5"},
    # Google Gemini
    "google":    {"spec": "gemini-2.5-pro", "planning": "gemini-2.5-pro", "coding": "gemini-2.5-pro", "qa": "gemini-2.5-pro"},
    # Mistral AI
    "mistral":   {"spec": "mistral-large-2", "planning": "mistral-large-2", "coding": "mistral-large-2", "qa": "mistral-large-2"},
    # DeepSeek
    "deepseek":  {"spec": "deepseek-v3", "planning": "deepseek-v3", "coding": "deepseek-v3", "qa": "deepseek-v3"},
    # Grok (xAI)
    "grok":      {"spec": "grok-2", "planning": "grok-2", "coding": "grok-2", "qa": "grok-2"},
    # Meta (LLaMA)
    "meta":      {"spec": "meta-llama/llama-4-scout", "planning": "meta-llama/llama-4-scout", "coding": "meta-llama/llama-4-scout", "qa": "meta-llama/llama-4-scout"},
    # AWS Bedrock
    "aws":       {"spec": "anthropic.claude-sonnet-4-5-v1", "planning": "anthropic.claude-sonnet-4-5-v1", "coding": "anthropic.claude-sonnet-4-5-v1", "qa": "anthropic.claude-sonnet-4-5-v1"},
    # Ollama (local)
    "ollama":    {"spec": "llama3.3", "planning": "llama3.3", "coding": "llama3.3", "qa": "llama3.3"},
}

DEFAULT_PHASE_THINKING: dict[str, str] = {
    "spec": "medium",
    "planning": "high",
    "coding": "medium",
    "qa": "high",
}


class PhaseModelConfig(TypedDict, total=False):
    spec: str
    planning: str
    coding: str
    qa: str


class PhaseThinkingConfig(TypedDict, total=False):
    spec: str
    planning: str
    coding: str
    qa: str


class TaskMetadataConfig(TypedDict, total=False):
    """Structure of model-related fields in task_metadata.json"""

    provider: str
    isAutoProfile: bool
    phaseModels: PhaseModelConfig
    phaseThinking: PhaseThinkingConfig
    model: str
    thinkingLevel: str


Phase = Literal["spec", "planning", "coding", "qa"]


def resolve_model_id(model: str) -> str:
    """
    Resolve a model shorthand (haiku, sonnet, opus) to a full model ID.
    If the model is already a full ID, return it unchanged.

    Priority:
    1. Environment variable override (from API Profile)
    2. Hardcoded MODEL_ID_MAP
    3. Pass through unchanged (assume full model ID)

    Args:
        model: Model shorthand or full ID

    Returns:
        Full Claude model ID
    """
    # Check for environment variable override (from API Profile custom model mappings)
    if model in MODEL_ID_MAP:
        env_var_map = {
            "haiku": "ANTHROPIC_DEFAULT_HAIKU_MODEL",
            "sonnet": "ANTHROPIC_DEFAULT_SONNET_MODEL",
            "opus": "ANTHROPIC_DEFAULT_OPUS_MODEL",
        }
        env_var = env_var_map.get(model)
        if env_var:
            env_value = os.environ.get(env_var)
            if env_value:
                return env_value

        # Fall back to hardcoded mapping
        return MODEL_ID_MAP[model]

    # Already a full model ID or unknown shorthand
    return model


def get_thinking_budget(thinking_level: str) -> int | None:
    """
    Get the thinking budget for a thinking level.

    Args:
        thinking_level: Thinking level (none, low, medium, high, ultrathink)

    Returns:
        Token budget or None for no extended thinking
    """
    import logging

    if thinking_level not in THINKING_BUDGET_MAP:
        valid_levels = ", ".join(THINKING_BUDGET_MAP.keys())
        logging.warning(
            f"Invalid thinking_level '{thinking_level}'. Valid values: {valid_levels}. "
            f"Defaulting to 'medium'."
        )
        return THINKING_BUDGET_MAP["medium"]

    return THINKING_BUDGET_MAP[thinking_level]


def load_task_metadata(spec_dir: Path) -> TaskMetadataConfig | None:
    """
    Load task_metadata.json from the spec directory.

    Args:
        spec_dir: Path to the spec directory

    Returns:
        Parsed task metadata or None if not found
    """
    metadata_path = spec_dir / "task_metadata.json"
    if not metadata_path.exists():
        return None

    try:
        with open(metadata_path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def get_phase_provider(
    spec_dir: Path,
    cli_provider: str | None = None,
) -> str | None:
    """
    Get the LLM provider configured for this task.

    Priority:
    1. CLI argument (if provided)
    2. Provider from task_metadata.json
    3. Provider selected via IPC (from frontend UI)
    4. None (let downstream code use its default)

    Args:
        spec_dir: Path to the spec directory
        cli_provider: Provider from CLI argument (optional)

    Returns:
        Provider string (e.g. 'anthropic', 'openai', 'ollama') or None
    """
    if cli_provider:
        return cli_provider

    metadata = load_task_metadata(spec_dir)
    if metadata and metadata.get("provider"):
        return metadata["provider"]

    # Check provider selected via IPC (from frontend UI)
    try:
        import provider_api
        selected_provider = provider_api.get_selected_provider()
        if selected_provider:
            return selected_provider
    except Exception:
        pass

    return None


def _resolve_provider_model(model: str, provider: str | None) -> str:
    """
    Resolve a model identifier to a full model ID, provider-aware.

    For Anthropic/Claude providers (or no provider), uses resolve_model_id()
    which maps shorthands like "sonnet" to full Claude model IDs.
    For other providers, model IDs are already full IDs and are passed through.

    Args:
        model: Model shorthand or full ID
        provider: LLM provider name (e.g. 'openai', 'anthropic') or None

    Returns:
        Full model ID ready for the API
    """
    # Anthropic/Claude shorthands need resolution
    if not provider or provider in ("anthropic", "claude"):
        return resolve_model_id(model)

    # For non-Anthropic providers, check if it's a Claude shorthand
    # (could happen if user switched providers but metadata still has "sonnet")
    if model in MODEL_ID_MAP:
        # This is a Claude shorthand but provider is not Anthropic — use provider defaults
        # Caller should handle this; just pass through resolve_model_id as fallback
        return resolve_model_id(model)

    # Already a full model ID for non-Anthropic provider
    return model


def get_phase_model(
    spec_dir: Path,
    phase: Phase,
    cli_model: str | None = None,
    cli_provider: str | None = None,
) -> str:
    """
    Get the resolved model ID for a specific execution phase.

    Priority:
    1. CLI argument (if provided)
    2. Phase-specific config from task_metadata.json (if auto profile)
    3. Single model from task_metadata.json (if not auto profile)
    4. Provider-specific default (if provider is known)
    5. Default phase configuration (Anthropic/Claude fallback)

    Args:
        spec_dir: Path to the spec directory
        phase: Execution phase (spec, planning, coding, qa)
        cli_model: Model from CLI argument (optional)
        cli_provider: Provider from CLI argument (optional)

    Returns:
        Resolved full model ID
    """
    # CLI argument takes precedence
    if cli_model:
        return resolve_model_id(cli_model)

    # Load task metadata
    metadata = load_task_metadata(spec_dir)

    if metadata:
        # Check for auto profile with phase-specific config
        if metadata.get("isAutoProfile") and metadata.get("phaseModels"):
            phase_models = metadata["phaseModels"]
            provider = cli_provider or metadata.get("provider")
            model = phase_models.get(phase, DEFAULT_PHASE_MODELS[phase])
            return _resolve_provider_model(model, provider)

        # Non-auto profile: use single model
        if metadata.get("model"):
            provider = cli_provider or metadata.get("provider")
            return _resolve_provider_model(metadata["model"], provider)

    # Fall back to provider-specific defaults if provider is known
    provider = cli_provider
    if not provider and metadata:
        provider = metadata.get("provider")
    if not provider:
        provider = get_phase_provider(spec_dir)

    if provider and provider in PROVIDER_DEFAULT_MODELS:
        provider_models = PROVIDER_DEFAULT_MODELS[provider]
        model = provider_models.get(phase, DEFAULT_PHASE_MODELS[phase])
        return _resolve_provider_model(model, provider)

    # Ultimate fallback: Anthropic/Claude default
    return resolve_model_id(DEFAULT_PHASE_MODELS[phase])


def get_phase_thinking(
    spec_dir: Path,
    phase: Phase,
    cli_thinking: str | None = None,
) -> str:
    """
    Get the thinking level for a specific execution phase.

    Priority:
    1. CLI argument (if provided)
    2. Phase-specific config from task_metadata.json (if auto profile)
    3. Single thinking level from task_metadata.json (if not auto profile)
    4. Default phase configuration

    Args:
        spec_dir: Path to the spec directory
        phase: Execution phase (spec, planning, coding, qa)
        cli_thinking: Thinking level from CLI argument (optional)

    Returns:
        Thinking level string
    """
    # CLI argument takes precedence
    if cli_thinking:
        return cli_thinking

    # Load task metadata
    metadata = load_task_metadata(spec_dir)

    if metadata:
        # Check for auto profile with phase-specific config
        if metadata.get("isAutoProfile") and metadata.get("phaseThinking"):
            phase_thinking = metadata["phaseThinking"]
            return phase_thinking.get(phase, DEFAULT_PHASE_THINKING[phase])

        # Non-auto profile: use single thinking level
        if metadata.get("thinkingLevel"):
            return metadata["thinkingLevel"]

    # Fall back to default phase configuration
    return DEFAULT_PHASE_THINKING[phase]


def get_phase_thinking_budget(
    spec_dir: Path,
    phase: Phase,
    cli_thinking: str | None = None,
) -> int | None:
    """
    Get the thinking budget tokens for a specific execution phase.

    Args:
        spec_dir: Path to the spec directory
        phase: Execution phase (spec, planning, coding, qa)
        cli_thinking: Thinking level from CLI argument (optional)

    Returns:
        Token budget or None for no extended thinking
    """
    thinking_level = get_phase_thinking(spec_dir, phase, cli_thinking)
    return get_thinking_budget(thinking_level)


def get_phase_config(
    spec_dir: Path,
    phase: Phase,
    cli_model: str | None = None,
    cli_thinking: str | None = None,
    cli_provider: str | None = None,
) -> tuple[str, str, int | None]:
    """
    Get the full configuration for a specific execution phase.

    Args:
        spec_dir: Path to the spec directory
        phase: Execution phase (spec, planning, coding, qa)
        cli_model: Model from CLI argument (optional)
        cli_thinking: Thinking level from CLI argument (optional)
        cli_provider: Provider from CLI argument (optional)

    Returns:
        Tuple of (model_id, thinking_level, thinking_budget)
    """
    model_id = get_phase_model(spec_dir, phase, cli_model, cli_provider)
    thinking_level = get_phase_thinking(spec_dir, phase, cli_thinking)
    thinking_budget = get_thinking_budget(thinking_level)

    return model_id, thinking_level, thinking_budget


def get_spec_phase_thinking_budget(phase_name: str) -> int | None:
    """
    Get the thinking budget for a specific spec runner phase.

    This maps granular spec phases (discovery, spec_writing, etc.) to their
    appropriate thinking budgets based on SPEC_PHASE_THINKING_LEVELS.

    Args:
        phase_name: Name of the spec phase (e.g., 'discovery', 'spec_writing')

    Returns:
        Token budget for extended thinking, or None for no extended thinking
    """
    thinking_level = SPEC_PHASE_THINKING_LEVELS.get(phase_name, "medium")
    return get_thinking_budget(thinking_level)
