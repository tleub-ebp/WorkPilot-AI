"""
Prompt Injection Guard — Detect prompt injection attempts in inputs.

Multi-layer scanner with regex, obfuscation decoding, and basic heuristic
classifier to detect direct instruction override, system-role confusion,
tool/shell injection, data exfiltration, and encoded payloads.
"""

from .middleware import (
    PromptInjectionBlocked,
    get_default_scanner,
    guard_async_runner,
    guard_runner,
    guarded_prompt,
)
from .scanner import (
    InjectionScanner,
    ScanFinding,
    ScanResult,
    ThreatLevel,
)

__all__ = [
    "InjectionScanner",
    "PromptInjectionBlocked",
    "ScanFinding",
    "ScanResult",
    "ThreatLevel",
    "get_default_scanner",
    "guard_async_runner",
    "guard_runner",
    "guarded_prompt",
]
