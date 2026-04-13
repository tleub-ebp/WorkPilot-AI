"""
Webhook Handler — Receive and dispatch APM incident webhooks.

Provides an endpoint-agnostic handler that receives webhook payloads,
auto-detects the source, and feeds them through the Regression Guardian
pipeline.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .dedup_checker import DedupChecker, DedupResult
from .fixture_builder import Fixture, FixtureBuilder
from .incident_parser import Incident, IncidentParser, IncidentSource
from .test_generator import GeneratedTest, TestFramework, TestGenerator

logger = logging.getLogger(__name__)


class PipelineStatus(str, Enum):
    RECEIVED = "received"
    PARSED = "parsed"
    DEDUPLICATED = "deduplicated"
    GENERATED = "generated"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class PipelineResult:
    """Result of processing a single incident through the pipeline."""

    status: PipelineStatus
    incident: Incident | None = None
    dedup: DedupResult | None = None
    test: GeneratedTest | None = None
    fixtures: list[Fixture] = field(default_factory=list)
    error: str | None = None
    duration_ms: float = 0.0


class WebhookHandler:
    """End-to-end handler: webhook → parse → dedup → generate.

    Usage::

        handler = WebhookHandler(framework=TestFramework.PYTEST)
        result = handler.handle(payload)
        if result.test:
            write(result.test.file_path, result.test.test_code)
    """

    def __init__(
        self,
        framework: TestFramework = TestFramework.PYTEST,
        dedup_checker: DedupChecker | None = None,
        redact_pii: bool = True,
    ) -> None:
        self._parser = IncidentParser()
        self._generator = TestGenerator()
        self._fixture_builder = FixtureBuilder(redact_pii=redact_pii)
        self._dedup = dedup_checker
        self._framework = framework
        self._history: list[PipelineResult] = []

    @property
    def history(self) -> list[PipelineResult]:
        return list(self._history)

    def handle(
        self,
        payload: dict[str, Any],
        source: IncidentSource | None = None,
    ) -> PipelineResult:
        """Process a webhook payload through the full pipeline."""
        start = time.time()

        # 1. Parse
        try:
            detected = source or self._parser.detect_source(payload)
            incident = self._parser.parse(payload, detected)
        except Exception as exc:
            result = PipelineResult(
                status=PipelineStatus.FAILED,
                error=f"Parse error: {exc}",
            )
            self._history.append(result)
            return result

        # 2. Dedup
        dedup_result = None
        if self._dedup:
            dedup_result = self._dedup.check(incident)
            if dedup_result.is_duplicate:
                result = PipelineResult(
                    status=PipelineStatus.SKIPPED,
                    incident=incident,
                    dedup=dedup_result,
                    duration_ms=(time.time() - start) * 1000,
                )
                self._history.append(result)
                logger.info(
                    "Incident %s skipped — duplicate of %s",
                    incident.id,
                    dedup_result.similar_test_path,
                )
                return result

        # 3. Generate test
        try:
            test = self._generator.generate(incident, self._framework)
        except Exception as exc:
            result = PipelineResult(
                status=PipelineStatus.FAILED,
                incident=incident,
                dedup=dedup_result,
                error=f"Generation error: {exc}",
                duration_ms=(time.time() - start) * 1000,
            )
            self._history.append(result)
            return result

        # 4. Generate fixtures
        fixtures = self._fixture_builder.build(incident)

        result = PipelineResult(
            status=PipelineStatus.GENERATED,
            incident=incident,
            dedup=dedup_result,
            test=test,
            fixtures=fixtures,
            duration_ms=(time.time() - start) * 1000,
        )
        self._history.append(result)
        logger.info(
            "Incident %s → test %s (%d fixtures)",
            incident.id,
            test.file_path,
            len(fixtures),
        )
        return result

    def get_stats(self) -> dict[str, int]:
        """Return pipeline statistics."""
        stats: dict[str, int] = {s.value: 0 for s in PipelineStatus}
        for r in self._history:
            stats[r.status.value] += 1
        return stats
