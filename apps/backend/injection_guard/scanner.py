"""
Prompt Injection Scanner — Multi-layer detection for LLM inputs.

Layers:
    1. Regex: well-known injection phrasings and jailbreaks
    2. Decode: detect and decode base64/hex/zero-width obfuscation
    3. Classifier: lightweight heuristic scoring

The scanner is intentionally dependency-free and deterministic so it can
be embedded in any Python runner without external model downloads.
"""

from __future__ import annotations

import base64
import binascii
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class ThreatLevel(str, Enum):
    SAFE = "safe"
    SUSPECT = "suspect"
    BLOCKED = "blocked"


@dataclass
class ScanFinding:
    layer: str  # "regex" | "classifier" | "decode"
    description: str
    severity: str  # "low" | "medium" | "high" | "critical"
    confidence: float  # 0.0 - 1.0


@dataclass
class ScanResult:
    threat_level: ThreatLevel
    findings: list[ScanFinding] = field(default_factory=list)
    scanned_text: str = ""
    source: str = ""
    decoded_content: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


_INJECTION_PATTERNS: list[tuple[str, str, str]] = [
    (
        r"ignore (?:all |previous |above |the )+instructions",
        "Direct instruction override attempt",
        "critical",
    ),
    (
        r"disregard (?:all |previous |the )?(?:rules|instructions|system)",
        "Instruction disregard attempt",
        "critical",
    ),
    (
        r"you are now (?:a |an )?(?:different|new|unrestricted)",
        "Role reassignment attempt",
        "high",
    ),
    (
        r"(?:system|assistant)\s*[:>]",
        "System/assistant role spoofing marker",
        "high",
    ),
    (
        r"<\s*/?\s*(?:system|assistant|user)\s*>",
        "XML-style role injection",
        "high",
    ),
    (
        r"reveal (?:the |your )?(?:system )?prompt",
        "Prompt extraction attempt",
        "high",
    ),
    (
        r"print (?:the |your )?(?:initial |system )?prompt",
        "Prompt extraction attempt",
        "high",
    ),
    (
        r"developer mode|jailbreak|DAN mode",
        "Jailbreak trigger phrase",
        "critical",
    ),
    (
        r"execute\s+(?:shell|system|os|subprocess)",
        "Shell execution attempt",
        "critical",
    ),
    (
        r"\beval\s*\(|\bexec\s*\(",
        "Code execution primitive",
        "high",
    ),
    (
        r"(?:rm\s+-rf|del\s+/[fs])",
        "Destructive shell command",
        "critical",
    ),
    (
        r"(?:aws|api)[-_ ]?(?:key|token|secret)",
        "Credential exfiltration request",
        "medium",
    ),
]

_ZERO_WIDTH = re.compile(r"[\u200b-\u200f\u202a-\u202e\ufeff]")
_BASE64_HINT = re.compile(r"(?:^|[^A-Za-z0-9+/])([A-Za-z0-9+/]{24,}={0,2})")
_HEX_HINT = re.compile(r"\\x[0-9a-fA-F]{2}")


class InjectionScanner:
    """Deterministic multi-layer prompt injection scanner."""

    def __init__(
        self,
        block_threshold: float = 0.8,
        suspect_threshold: float = 0.4,
    ) -> None:
        self._block_threshold = block_threshold
        self._suspect_threshold = suspect_threshold
        self._compiled = [
            (re.compile(pat, re.IGNORECASE), desc, sev)
            for pat, desc, sev in _INJECTION_PATTERNS
        ]

    def scan(self, text: str, source: str = "unknown") -> ScanResult:
        result = ScanResult(
            threat_level=ThreatLevel.SAFE,
            scanned_text=text,
            source=source,
        )

        # Layer 2: decode first so regex can also see decoded content
        decoded = self._decode_obfuscation(text, result)
        result.decoded_content = decoded
        combined = f"{text}\n{decoded}" if decoded and decoded != text else text

        # Layer 1: regex
        for pattern, description, severity in self._compiled:
            if pattern.search(combined):
                result.findings.append(
                    ScanFinding(
                        layer="regex",
                        description=description,
                        severity=severity,
                        confidence=0.9 if severity == "critical" else 0.75,
                    )
                )

        # Layer 3: heuristic classifier
        self._heuristic_score(combined, result)

        result.threat_level = self._aggregate_level(result.findings)
        return result

    def _decode_obfuscation(self, text: str, result: ScanResult) -> str:
        pieces: list[str] = []

        if _ZERO_WIDTH.search(text):
            result.findings.append(
                ScanFinding(
                    layer="decode",
                    description="Zero-width unicode characters detected",
                    severity="medium",
                    confidence=0.6,
                )
            )
            pieces.append(_ZERO_WIDTH.sub("", text))

        for match in _BASE64_HINT.finditer(text):
            candidate = match.group(1)
            try:
                decoded_bytes = base64.b64decode(candidate, validate=True)
                decoded_str = decoded_bytes.decode("utf-8", errors="ignore")
                if decoded_str.isprintable() and len(decoded_str) >= 8:
                    result.findings.append(
                        ScanFinding(
                            layer="decode",
                            description="Base64-encoded payload decoded",
                            severity="medium",
                            confidence=0.5,
                        )
                    )
                    pieces.append(decoded_str)
            except (binascii.Error, ValueError):
                continue

        if _HEX_HINT.search(text):
            result.findings.append(
                ScanFinding(
                    layer="decode",
                    description="Hex-escaped bytes detected",
                    severity="low",
                    confidence=0.4,
                )
            )

        return "\n".join(pieces) if pieces else ""

    def _heuristic_score(self, text: str, result: ScanResult) -> None:
        lowered = text.lower()
        suspicious_tokens = [
            "override",
            "bypass",
            "forbidden",
            "confidential",
            "do not refuse",
            "simulate",
            "roleplay",
            "without restriction",
        ]
        hits = sum(1 for t in suspicious_tokens if t in lowered)
        if hits >= 2:
            result.findings.append(
                ScanFinding(
                    layer="classifier",
                    description=f"Heuristic classifier flagged {hits} suspicious tokens",
                    severity="medium" if hits < 4 else "high",
                    confidence=min(0.3 + 0.15 * hits, 0.9),
                )
            )

    def _aggregate_level(self, findings: list[ScanFinding]) -> ThreatLevel:
        if not findings:
            return ThreatLevel.SAFE
        max_conf = max(f.confidence for f in findings)
        has_critical = any(f.severity == "critical" for f in findings)
        if has_critical or max_conf >= self._block_threshold:
            return ThreatLevel.BLOCKED
        if max_conf >= self._suspect_threshold:
            return ThreatLevel.SUSPECT
        return ThreatLevel.SAFE
