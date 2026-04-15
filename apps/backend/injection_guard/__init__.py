"""
Prompt Injection Guard — Detect prompt injection attempts in inputs.

Multi-layer scanner with regex, obfuscation decoding, and basic heuristic
classifier to detect direct instruction override, system-role confusion,
tool/shell injection, data exfiltration, and encoded payloads.
"""

from .scanner import (
    InjectionScanner,
    ScanFinding,
    ScanResult,
    ThreatLevel,
)

__all__ = [
    "InjectionScanner",
    "ScanFinding",
    "ScanResult",
    "ThreatLevel",
]
