"""
Injection Scanner — Multi-layer prompt injection detection pipeline.

Layer 1: Regex/heuristic patterns (fast, zero false negatives on known attacks).
Layer 2: ML classifier (local, < 50ms per input).
Layer 3: Optional LLM judge for ambiguous cases.

The scanner is inserted as a hook on tool results before they are
injected into the agent context.
"""

from __future__ import annotations

import base64
import html
import logging
import urllib.parse
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .injection_classifier import InjectionClassifier
from .injection_patterns import scan_text

logger = logging.getLogger(__name__)


class ThreatLevel(str, Enum):
    CLEAN = "clean"
    SUSPECT = "suspect"
    BLOCKED = "blocked"


@dataclass
class ScanFinding:
    """A single finding from the injection scan."""

    layer: str  # "regex", "classifier", "llm_judge"
    description: str
    severity: str
    confidence: float = 1.0


@dataclass
class ScanResult:
    """Aggregate result of the multi-layer scan."""

    threat_level: ThreatLevel
    findings: list[ScanFinding] = field(default_factory=list)
    source: str = ""
    content_length: int = 0
    decoded_content: bool = False

    @property
    def is_safe(self) -> bool:
        return self.threat_level == ThreatLevel.CLEAN

    @property
    def summary(self) -> str:
        if not self.findings:
            return "No injection detected"
        descs = [f.description for f in self.findings]
        return f"{len(self.findings)} finding(s): {'; '.join(descs[:3])}"


class InjectionScanner:
    """Multi-layer prompt injection detection.

    Usage::

        scanner = InjectionScanner()
        result = scanner.scan(tool_result_text, source="read_file")
        if result.threat_level == ThreatLevel.BLOCKED:
            raise SecurityError(result.summary)
    """

    def __init__(
        self,
        classifier: InjectionClassifier | None = None,
        block_threshold: str = "high",
        suspect_threshold: str = "medium",
        enable_decoding: bool = True,
        max_scan_length: int = 200_000,
    ) -> None:
        self._classifier = classifier or InjectionClassifier()
        self._block_threshold = block_threshold
        self._suspect_threshold = suspect_threshold
        self._enable_decoding = enable_decoding
        self._max_scan_length = max_scan_length

    def scan(self, content: str, source: str = "") -> ScanResult:
        """Run the full multi-layer scan on content."""
        if not content:
            return ScanResult(threat_level=ThreatLevel.CLEAN, source=source)

        # Truncate very long content
        truncated = content[: self._max_scan_length]

        # Optionally decode obfuscated content
        decoded = False
        texts_to_scan = [truncated]
        if self._enable_decoding:
            extra = _decode_obfuscated(truncated)
            if extra and extra != truncated:
                texts_to_scan.append(extra)
                decoded = True

        all_findings: list[ScanFinding] = []

        # Layer 1: Regex patterns
        for text in texts_to_scan:
            regex_hits = scan_text(text)
            for hit in regex_hits:
                all_findings.append(
                    ScanFinding(
                        layer="regex",
                        description=hit["description"],
                        severity=hit["severity"],
                    )
                )

        # Layer 2: ML classifier
        for text in texts_to_scan:
            clf_result = self._classifier.classify(text)
            if clf_result.is_injection:
                severity = "high" if clf_result.confidence > 0.7 else "medium"
                all_findings.append(
                    ScanFinding(
                        layer="classifier",
                        description=f"ML classifier: {clf_result.label} (confidence={clf_result.confidence:.2f})",
                        severity=severity,
                        confidence=clf_result.confidence,
                    )
                )

        # Determine threat level
        threat_level = self._determine_threat_level(all_findings)

        return ScanResult(
            threat_level=threat_level,
            findings=all_findings,
            source=source,
            content_length=len(content),
            decoded_content=decoded,
        )

    def scan_tool_result(self, tool_name: str, result: Any) -> ScanResult:
        """Scan a tool call result for injection attempts."""
        text = str(result) if not isinstance(result, str) else result
        return self.scan(text, source=tool_name)

    def _determine_threat_level(self, findings: list[ScanFinding]) -> ThreatLevel:
        if not findings:
            return ThreatLevel.CLEAN

        severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        block_level = severity_order.get(self._block_threshold, 3)
        suspect_level = severity_order.get(self._suspect_threshold, 2)

        highest = max(severity_order.get(f.severity, 0) for f in findings)

        if highest >= block_level:
            return ThreatLevel.BLOCKED
        if highest >= suspect_level:
            return ThreatLevel.SUSPECT
        return ThreatLevel.CLEAN


# ------------------------------------------------------------------
# Decoding helpers
# ------------------------------------------------------------------


def _decode_obfuscated(text: str) -> str:
    """Attempt to decode base64, URL-encoded, and HTML-encoded content."""
    decoded_parts: list[str] = [text]

    # Try base64 segments
    import re

    b64_pattern = re.compile(r"[A-Za-z0-9+/]{20,}={0,2}")
    for match in b64_pattern.finditer(text):
        try:
            decoded = base64.b64decode(match.group()).decode("utf-8", errors="replace")
            if any(c.isalpha() for c in decoded):
                decoded_parts.append(decoded)
        except Exception:
            pass

    # URL decoding
    try:
        url_decoded = urllib.parse.unquote(text)
        if url_decoded != text:
            decoded_parts.append(url_decoded)
    except Exception:
        pass

    # HTML entity decoding
    try:
        html_decoded = html.unescape(text)
        if html_decoded != text:
            decoded_parts.append(html_decoded)
    except Exception:
        pass

    return " ".join(decoded_parts)
