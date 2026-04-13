"""
Injection Patterns — Catalog of regex patterns for prompt injection detection.

Multi-language patterns covering English, French, Chinese, Arabic, and
common encoding evasions (base64, URL-encoded, unicode escapes).
"""

from __future__ import annotations

import re

INJECTION_PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    # (compiled pattern, description, severity)

    # Direct instruction overrides
    (re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE), "Direct instruction override", "high"),
    (re.compile(r"disregard\s+(all\s+)?(prior|previous|above)\s+", re.IGNORECASE), "Disregard prior context", "high"),
    (re.compile(r"forget\s+(everything|all|what)\s+(you|I)\s+", re.IGNORECASE), "Memory reset attempt", "high"),

    # Role reassignment
    (re.compile(r"you\s+are\s+now\s+(a|an|the)\s+", re.IGNORECASE), "Role reassignment", "high"),
    (re.compile(r"act\s+as\s+(a|an|if)\s+", re.IGNORECASE), "Role injection", "medium"),
    (re.compile(r"pretend\s+(to\s+be|you\s+are)", re.IGNORECASE), "Persona injection", "high"),

    # System prompt extraction
    (re.compile(r"(print|show|reveal|output|display)\s+(your\s+)?(system\s+prompt|instructions|rules)", re.IGNORECASE), "System prompt extraction", "critical"),
    (re.compile(r"what\s+(are|is)\s+your\s+(system\s+)?(prompt|instructions|rules)", re.IGNORECASE), "System prompt query", "high"),
    (re.compile(r"repeat\s+(the\s+)?(text|words|instructions)\s+above", re.IGNORECASE), "Context extraction", "high"),

    # Delimiter injection
    (re.compile(r"<\s*system\s*>", re.IGNORECASE), "XML system tag injection", "critical"),
    (re.compile(r"<\s*/?\s*instructions?\s*>", re.IGNORECASE), "XML instruction tag injection", "critical"),
    (re.compile(r"\[INST\]|\[/INST\]", re.IGNORECASE), "Llama instruction tag injection", "critical"),
    (re.compile(r"<\|im_start\|>|<\|im_end\|>", re.IGNORECASE), "ChatML delimiter injection", "critical"),
    (re.compile(r"Human:|Assistant:|System:", re.IGNORECASE), "Conversation role injection", "high"),

    # Encoding evasion
    (re.compile(r"(?:aWdub3Jl|aWdub3JlIGFsbCBw)", re.IGNORECASE), "Base64-encoded injection", "high"),

    # French patterns
    (re.compile(r"ignore[rz]?\s+(toutes?\s+)?(les\s+)?instructions?\s+pr[eé]c[eé]dentes?", re.IGNORECASE), "French instruction override", "high"),
    (re.compile(r"oublie[rz]?\s+tout\s+ce\s+qui", re.IGNORECASE), "French memory reset", "high"),
    (re.compile(r"tu\s+es\s+maintenant\s+(un|une)", re.IGNORECASE), "French role reassignment", "high"),

    # Jailbreak markers
    (re.compile(r"DAN\s*(mode)?|Do\s+Anything\s+Now", re.IGNORECASE), "DAN jailbreak attempt", "critical"),
    (re.compile(r"developer\s+mode\s+(enabled|on|activated)", re.IGNORECASE), "Developer mode jailbreak", "critical"),
]

SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def scan_text(text: str) -> list[dict[str, str]]:
    """Scan text for injection patterns. Returns list of matches."""
    findings: list[dict[str, str]] = []
    for pattern, description, severity in INJECTION_PATTERNS:
        if pattern.search(text):
            findings.append({
                "pattern": pattern.pattern,
                "description": description,
                "severity": severity,
            })
    return findings


def max_severity(findings: list[dict[str, str]]) -> str:
    """Return the highest severity among findings."""
    if not findings:
        return "none"
    return max(findings, key=lambda f: SEVERITY_ORDER.get(f["severity"], 0))["severity"]
