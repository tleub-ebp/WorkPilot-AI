"""
Windsurf Model Mapping
======================

Maps friendly model names to Windsurf internal ChatModelType enum values.
Ported from opencode-windsurf-auth/src/plugin/types.ts + models.ts

These enum values are used in the gRPC protobuf messages sent to the
Windsurf language server's RawGetChatMessage endpoint.
"""

import logging
from enum import IntEnum

logger = logging.getLogger(__name__)


class ChatModelType(IntEnum):
    """Windsurf internal model enum values (from extension analysis)."""

    # SWE models (Windsurf proprietary)
    SWE_1_5 = 359
    SWE_1_5_THINKING = 369
    SWE_1_5_SLOW = 377

    # Claude models
    CLAUDE_3_OPUS_20240229 = 63
    CLAUDE_3_SONNET_20240229 = 64
    CLAUDE_3_HAIKU_20240307 = 172
    CLAUDE_3_5_SONNET_20240620 = 80
    CLAUDE_3_5_SONNET_20241022 = 166
    CLAUDE_3_5_HAIKU_20241022 = 171
    CLAUDE_3_7_SONNET_20250219 = 226
    CLAUDE_3_7_SONNET_20250219_THINKING = 227
    CLAUDE_4_OPUS = 290
    CLAUDE_4_OPUS_THINKING = 291
    CLAUDE_4_SONNET = 281
    CLAUDE_4_SONNET_THINKING = 282
    CLAUDE_4_1_OPUS = 328
    CLAUDE_4_1_OPUS_THINKING = 329
    CLAUDE_4_5_SONNET = 353
    CLAUDE_4_5_SONNET_THINKING = 354
    CLAUDE_4_5_SONNET_1TM = 370
    CLAUDE_4_5_SONNET_THINKING_1TM = 371
    CLAUDE_4_5_OPUS = 391
    CLAUDE_4_5_OPUS_THINKING = 392
    CLAUDE_CODE = 344

    # GPT models
    GPT_4 = 30
    GPT_4_1106_PREVIEW = 37
    GPT_4O_2024_05_13 = 71
    GPT_4O_2024_08_06 = 109
    GPT_4O_MINI_2024_07_18 = 113
    GPT_4_5 = 228
    GPT_4_1_2025_04_14 = 259
    GPT_4_1_MINI_2025_04_14 = 260
    GPT_4_1_NANO_2025_04_14 = 261
    GPT_5_NANO = 337
    GPT_5_MINIMAL = 338
    GPT_5_LOW = 339
    GPT_5 = 340
    GPT_5_HIGH = 341
    GPT_5_CODEX = 346
    GPT_5_1_CODEX_MINI_LOW = 385
    GPT_5_1_CODEX_MINI_MEDIUM = 386
    GPT_5_1_CODEX_MINI_HIGH = 387
    GPT_5_1_CODEX_LOW = 388
    GPT_5_1_CODEX_MEDIUM = 389
    GPT_5_1_CODEX_HIGH = 390
    GPT_5_1_CODEX_MAX_LOW = 395
    GPT_5_1_CODEX_MAX_MEDIUM = 396
    GPT_5_1_CODEX_MAX_HIGH = 397
    GPT_5_2_NONE = 399
    GPT_5_2_LOW = 400
    GPT_5_2_MEDIUM = 401
    GPT_5_2_HIGH = 402
    GPT_5_2_XHIGH = 403

    # O-series (reasoning)
    O1_PREVIEW = 117
    O1_MINI = 118
    O1 = 170
    O3_MINI = 207
    O3_MINI_LOW = 213
    O3_MINI_HIGH = 214
    O3 = 218
    O3_LOW = 262
    O3_HIGH = 263
    O3_PRO = 294
    O3_PRO_LOW = 295
    O3_PRO_HIGH = 296
    O4_MINI = 264
    O4_MINI_LOW = 265
    O4_MINI_HIGH = 266

    # Gemini models
    GEMINI_1_0_PRO = 61
    GEMINI_1_5_PRO = 62
    GEMINI_2_0_FLASH = 184
    GEMINI_2_5_PRO = 246
    GEMINI_2_5_FLASH = 312
    GEMINI_2_5_FLASH_THINKING = 313
    GEMINI_2_5_FLASH_LITE = 343
    GEMINI_3_0_PRO_LOW = 378
    GEMINI_3_0_PRO_HIGH = 379
    GEMINI_3_0_PRO_MINIMAL = 411
    GEMINI_3_0_PRO_MEDIUM = 412
    GEMINI_3_0_FLASH_MINIMAL = 413
    GEMINI_3_0_FLASH_LOW = 414
    GEMINI_3_0_FLASH_MEDIUM = 415
    GEMINI_3_0_FLASH_HIGH = 416

    # DeepSeek
    DEEPSEEK_V3 = 205
    DEEPSEEK_R1 = 206
    DEEPSEEK_R1_SLOW = 215
    DEEPSEEK_R1_FAST = 216
    DEEPSEEK_V3_2 = 409

    # Llama
    LLAMA_3_1_8B_INSTRUCT = 106
    LLAMA_3_1_70B_INSTRUCT = 107
    LLAMA_3_1_405B_INSTRUCT = 105
    LLAMA_3_3_70B_INSTRUCT = 208
    LLAMA_3_3_70B_INSTRUCT_R1 = 209

    # Qwen
    QWEN_2_5_7B_INSTRUCT = 178
    QWEN_2_5_32B_INSTRUCT = 179
    QWEN_2_5_72B_INSTRUCT = 180
    QWEN_2_5_32B_INSTRUCT_R1 = 224
    QWEN_3_235B_INSTRUCT = 324
    QWEN_3_CODER_480B_INSTRUCT = 325
    QWEN_3_CODER_480B_INSTRUCT_FAST = 327

    # Grok
    GROK_2 = 212
    GROK_3 = 217
    GROK_3_MINI_REASONING = 234
    GROK_CODE_FAST = 345

    # Other
    MISTRAL_7B = 77
    KIMI_K2 = 323
    KIMI_K2_THINKING = 394
    GLM_4_5 = 342
    GLM_4_5_FAST = 352
    GLM_4_6 = 356
    GLM_4_6_FAST = 357
    GLM_4_7 = 417
    GLM_4_7_FAST = 418
    MINIMAX_M2 = 368
    MINIMAX_M2_1 = 419


# =============================================================================
# Friendly name → enum mapping
# =============================================================================

MODEL_NAME_TO_ENUM: dict[str, ChatModelType] = {
    # SWE
    "swe-1.5": ChatModelType.SWE_1_5,
    "swe-1.5-thinking": ChatModelType.SWE_1_5_THINKING,
    "swe-1.5-slow": ChatModelType.SWE_1_5_SLOW,
    "swe-1.5-fast": ChatModelType.SWE_1_5,  # alias
    # Claude
    "claude-3-opus": ChatModelType.CLAUDE_3_OPUS_20240229,
    "claude-3-sonnet": ChatModelType.CLAUDE_3_SONNET_20240229,
    "claude-3-haiku": ChatModelType.CLAUDE_3_HAIKU_20240307,
    "claude-3.5-sonnet": ChatModelType.CLAUDE_3_5_SONNET_20241022,
    "claude-3.5-haiku": ChatModelType.CLAUDE_3_5_HAIKU_20241022,
    "claude-3.7-sonnet": ChatModelType.CLAUDE_3_7_SONNET_20250219,
    "claude-3.7-sonnet-thinking": ChatModelType.CLAUDE_3_7_SONNET_20250219_THINKING,
    "claude-4-opus": ChatModelType.CLAUDE_4_OPUS,
    "claude-4-opus-thinking": ChatModelType.CLAUDE_4_OPUS_THINKING,
    "claude-4-sonnet": ChatModelType.CLAUDE_4_SONNET,
    "claude-4-sonnet-thinking": ChatModelType.CLAUDE_4_SONNET_THINKING,
    "claude-4.1-opus": ChatModelType.CLAUDE_4_1_OPUS,
    "claude-4.1-opus-thinking": ChatModelType.CLAUDE_4_1_OPUS_THINKING,
    "claude-4.5-sonnet": ChatModelType.CLAUDE_4_5_SONNET,
    "claude-4.5-sonnet-thinking": ChatModelType.CLAUDE_4_5_SONNET_THINKING,
    "claude-4.5-opus": ChatModelType.CLAUDE_4_5_OPUS,
    "claude-4.5-opus-thinking": ChatModelType.CLAUDE_4_5_OPUS_THINKING,
    "claude-code": ChatModelType.CLAUDE_CODE,
    # Aliases
    "claude-sonnet-4": ChatModelType.CLAUDE_4_SONNET,
    "claude-opus-4": ChatModelType.CLAUDE_4_OPUS,
    "claude-sonnet-4.5": ChatModelType.CLAUDE_4_5_SONNET,
    "claude-opus-4.5": ChatModelType.CLAUDE_4_5_OPUS,
    # GPT
    "gpt-4": ChatModelType.GPT_4,
    "gpt-4o": ChatModelType.GPT_4O_2024_08_06,
    "gpt-4o-mini": ChatModelType.GPT_4O_MINI_2024_07_18,
    "gpt-4.5": ChatModelType.GPT_4_5,
    "gpt-4.1": ChatModelType.GPT_4_1_2025_04_14,
    "gpt-4.1-mini": ChatModelType.GPT_4_1_MINI_2025_04_14,
    "gpt-4.1-nano": ChatModelType.GPT_4_1_NANO_2025_04_14,
    "gpt-5": ChatModelType.GPT_5,
    "gpt-5-low": ChatModelType.GPT_5_LOW,
    "gpt-5-high": ChatModelType.GPT_5_HIGH,
    "gpt-5-codex": ChatModelType.GPT_5_CODEX,
    "gpt-5.2-low": ChatModelType.GPT_5_2_LOW,
    "gpt-5.2": ChatModelType.GPT_5_2_MEDIUM,
    "gpt-5.2-high": ChatModelType.GPT_5_2_HIGH,
    # O-series
    "o1": ChatModelType.O1,
    "o1-mini": ChatModelType.O1_MINI,
    "o3": ChatModelType.O3,
    "o3-mini": ChatModelType.O3_MINI,
    "o3-mini-low": ChatModelType.O3_MINI_LOW,
    "o3-mini-high": ChatModelType.O3_MINI_HIGH,
    "o3-pro": ChatModelType.O3_PRO,
    "o4-mini": ChatModelType.O4_MINI,
    "o4-mini-low": ChatModelType.O4_MINI_LOW,
    "o4-mini-high": ChatModelType.O4_MINI_HIGH,
    # Gemini
    "gemini-2.0-flash": ChatModelType.GEMINI_2_0_FLASH,
    "gemini-2.5-pro": ChatModelType.GEMINI_2_5_PRO,
    "gemini-2.5-flash": ChatModelType.GEMINI_2_5_FLASH,
    "gemini-3-pro": ChatModelType.GEMINI_3_0_PRO_HIGH,
    "gemini-3-flash": ChatModelType.GEMINI_3_0_FLASH_HIGH,
    "gemini-3-flash-low": ChatModelType.GEMINI_3_0_FLASH_LOW,
    "gemini-3-flash-high": ChatModelType.GEMINI_3_0_FLASH_HIGH,
    "gemini-3-pro-low": ChatModelType.GEMINI_3_0_PRO_LOW,
    "gemini-3-pro-high": ChatModelType.GEMINI_3_0_PRO_HIGH,
    # DeepSeek
    "deepseek-v3": ChatModelType.DEEPSEEK_V3,
    "deepseek-v3-2": ChatModelType.DEEPSEEK_V3_2,
    "deepseek-r1": ChatModelType.DEEPSEEK_R1,
    "deepseek-r1-fast": ChatModelType.DEEPSEEK_R1_FAST,
    "deepseek-r1-slow": ChatModelType.DEEPSEEK_R1_SLOW,
    # Llama
    "llama-3.1-8b": ChatModelType.LLAMA_3_1_8B_INSTRUCT,
    "llama-3.1-70b": ChatModelType.LLAMA_3_1_70B_INSTRUCT,
    "llama-3.1-405b": ChatModelType.LLAMA_3_1_405B_INSTRUCT,
    "llama-3.3-70b": ChatModelType.LLAMA_3_3_70B_INSTRUCT,
    # Qwen
    "qwen-2.5-32b": ChatModelType.QWEN_2_5_32B_INSTRUCT,
    "qwen-2.5-72b": ChatModelType.QWEN_2_5_72B_INSTRUCT,
    "qwen-3-235b": ChatModelType.QWEN_3_235B_INSTRUCT,
    "qwen-3-coder": ChatModelType.QWEN_3_CODER_480B_INSTRUCT,
    # Grok
    "grok-2": ChatModelType.GROK_2,
    "grok-3": ChatModelType.GROK_3,
    "grok-3-mini": ChatModelType.GROK_3_MINI_REASONING,
    "grok-code": ChatModelType.GROK_CODE_FAST,
    # Other
    "mistral-7b": ChatModelType.MISTRAL_7B,
    "kimi-k2": ChatModelType.KIMI_K2,
    "glm-4.5": ChatModelType.GLM_4_5,
    "glm-4.6": ChatModelType.GLM_4_6,
    "glm-4.7": ChatModelType.GLM_4_7,
    "minimax-m2": ChatModelType.MINIMAX_M2,
}

# Default model for coding tasks
DEFAULT_MODEL = "claude-4-sonnet"


def resolve_model(name: str) -> tuple[int, str]:
    """Resolve a friendly model name to (enum_value, model_name_string).

    Args:
        name: Friendly model name (e.g., "claude-4-sonnet", "gpt-4o")

    Returns:
        Tuple of (ChatModelType enum int, model name string for gRPC).
        The model name string includes the ``MODEL_`` prefix required by
        the Windsurf language server (e.g., ``MODEL_CLAUDE_4_SONNET``).
    """
    name_lower = name.lower().strip()

    if name_lower in MODEL_NAME_TO_ENUM:
        enum_val = MODEL_NAME_TO_ENUM[name_lower]
        return (int(enum_val), f"MODEL_{enum_val.name}")

    # Try fuzzy matching: remove common prefixes/suffixes
    for key, val in MODEL_NAME_TO_ENUM.items():
        if name_lower in key or key in name_lower:
            logger.debug(
                f"[WindsurfModels] Fuzzy matched '{name}' -> '{key}' ({val.name})"
            )
            return (int(val), f"MODEL_{val.name}")

    # Fallback to default
    logger.warning(
        f"[WindsurfModels] Unknown model '{name}', falling back to {DEFAULT_MODEL}"
    )
    default_enum = MODEL_NAME_TO_ENUM[DEFAULT_MODEL]
    return (int(default_enum), f"MODEL_{default_enum.name}")


def get_available_models() -> list[str]:
    """Return list of all available model friendly names."""
    return sorted(MODEL_NAME_TO_ENUM.keys())
