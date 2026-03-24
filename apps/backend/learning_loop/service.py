"""
Learning Loop Service — orchestrates the full learning loop lifecycle.

Provides the main interface for:
- Running post-build analysis
- Running full project analysis
- Generating prompt augmentations
- Managing patterns (CRUD, export/import)
- Generating dashboard summaries
"""

import json
import logging
from collections import Counter
from pathlib import Path
from typing import Any

from .models import (
    ImprovementMetrics,
    LearningPattern,
    LearningReport,
    PatternCategory,
)
from .pattern_applicator import PatternApplicator
from .pattern_extractor import PatternExtractor
from .pattern_storage import PatternStorage

logger = logging.getLogger(__name__)


class LearningLoopService:
    """Main orchestrator for the Autonomous Agent Learning Loop."""

    def __init__(
        self,
        project_dir: Path,
        model: str | None = None,
        thinking_level: str | None = None,
    ):
        self.project_dir = Path(project_dir)
        self.storage = PatternStorage(self.project_dir)
        self.extractor = PatternExtractor(
            self.project_dir, model=model, thinking_level=thinking_level
        )
        self.applicator = PatternApplicator(self.storage)

    async def run_post_build_analysis(
        self,
        spec_dir: Path,
        status_callback: Any | None = None,
    ) -> LearningReport:
        """Run analysis on a single completed build.

        This is called automatically after each build completes.
        """
        if status_callback:
            status_callback("Gathering build data...")

        build_data = self.extractor.gather_build_data(spec_dir)
        builds_data = [build_data]

        return await self._run_analysis(builds_data, status_callback)

    async def run_full_analysis(
        self,
        limit: int = 20,
        status_callback: Any | None = None,
    ) -> LearningReport:
        """Run analysis across all historical builds for the project.

        This is triggered manually from the UI dashboard.
        """
        if status_callback:
            status_callback("Gathering data from all builds...")

        builds_data = self.extractor.gather_all_builds_data(limit=limit)
        if not builds_data:
            return LearningReport(
                project_path=str(self.project_dir),
                analyzed_builds=0,
                patterns_found=[],
            )

        return await self._run_analysis(builds_data, status_callback)

    async def _run_analysis(
        self,
        builds_data: list[dict[str, Any]],
        status_callback: Any | None = None,
    ) -> LearningReport:
        """Core analysis logic using Claude Agent SDK."""
        if status_callback:
            status_callback(f"Analyzing {len(builds_data)} build(s) with AI...")

        # Build the analysis prompt
        prompt = self.extractor.build_analysis_prompt(builds_data)

        # Run the meta-agent
        try:
            from core.client import create_client
            from core.session import run_agent_session
            from phase_config import get_thinking_budget, resolve_model_id

            model_id = resolve_model_id(self.extractor.model)
            thinking_budget = get_thinking_budget(self.extractor.thinking_level)

            client = create_client(
                project_dir=str(self.project_dir),
                model=model_id,
                agent_type="learning_analyzer",
                max_thinking_tokens=thinking_budget,
            )

            async with client:
                status, response = await run_agent_session(client, prompt)

            if status_callback:
                status_callback("Extracting patterns from analysis...")

            patterns = self.extractor.parse_patterns_from_response(
                response, builds_data
            )
        except ImportError:
            # Fallback: if SDK is not available, use basic heuristic extraction
            logger.warning("Claude Agent SDK not available, using heuristic extraction")
            patterns = self._heuristic_extract(builds_data)
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            patterns = self._heuristic_extract(builds_data)

        # Store patterns (with deduplication)
        if patterns:
            self.storage.add_patterns(patterns)
            if status_callback:
                status_callback(f"Stored {len(patterns)} patterns")

        # Compute improvement metrics
        metrics = self._compute_improvement_metrics()

        report = LearningReport(
            project_path=str(self.project_dir),
            analyzed_builds=len(builds_data),
            patterns_found=patterns,
            improvement_metrics=metrics,
            analysis_model=self.extractor.model,
        )

        if status_callback:
            status_callback("Analysis complete")

        return report

    def get_prompt_augmentation(
        self, phase: str, task_context: dict | None = None
    ) -> str:
        """Get learning-based prompt augmentation for an agent phase."""
        return self.applicator.get_instructions_for_phase(
            phase, task_context=task_context
        )

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all learning data for the dashboard."""
        patterns = self.storage.load_patterns()
        if not patterns:
            return {
                "total_patterns": 0,
                "by_category": {},
                "by_phase": {},
                "by_type": {},
                "average_confidence": 0.0,
                "total_builds_analyzed": 0,
                "last_analyzed_at": None,
                "improvement_metrics": None,
                "enabled_count": 0,
                "disabled_count": 0,
            }

        by_category = Counter(p.category.value for p in patterns)
        by_phase = Counter(p.agent_phase for p in patterns)
        by_type = Counter(p.pattern_type.value for p in patterns)
        avg_confidence = sum(p.confidence for p in patterns) / len(patterns)
        all_build_ids = set()
        for p in patterns:
            all_build_ids.update(p.source_build_ids)
        last_seen = max(p.last_seen for p in patterns) if patterns else None

        metrics = self._compute_improvement_metrics()

        return {
            "total_patterns": len(patterns),
            "by_category": dict(by_category),
            "by_phase": dict(by_phase),
            "by_type": dict(by_type),
            "average_confidence": round(avg_confidence, 3),
            "total_builds_analyzed": len(all_build_ids),
            "last_analyzed_at": last_seen,
            "improvement_metrics": metrics.to_dict() if metrics else None,
            "enabled_count": sum(1 for p in patterns if p.enabled),
            "disabled_count": sum(1 for p in patterns if not p.enabled),
        }

    def get_patterns(self, filters: dict | None = None) -> list[dict[str, Any]]:
        """Get all patterns, optionally filtered."""
        patterns = self.storage.load_patterns()

        if filters:
            if "category" in filters:
                patterns = [
                    p for p in patterns if p.category.value == filters["category"]
                ]
            if "phase" in filters:
                patterns = [p for p in patterns if p.agent_phase == filters["phase"]]
            if "type" in filters:
                patterns = [
                    p for p in patterns if p.pattern_type.value == filters["type"]
                ]
            if "enabled" in filters:
                patterns = [p for p in patterns if p.enabled == filters["enabled"]]

        return [p.to_dict() for p in patterns]

    def delete_pattern(self, pattern_id: str) -> bool:
        return self.storage.delete_pattern(pattern_id)

    def toggle_pattern(self, pattern_id: str) -> bool | None:
        return self.storage.toggle_pattern(pattern_id)

    def export_patterns(self) -> str:
        """Export all patterns as JSON string."""
        patterns = self.storage.load_patterns()
        return json.dumps([p.to_dict() for p in patterns], indent=2, ensure_ascii=False)

    def import_patterns(self, json_str: str) -> int:
        """Import patterns from JSON string. Returns number of patterns imported."""
        try:
            raw = json.loads(json_str)
            patterns = [LearningPattern.from_dict(p) for p in raw]
            self.storage.add_patterns(patterns)
            return len(patterns)
        except Exception as e:
            logger.error(f"Failed to import patterns: {e}")
            return 0

    def _compute_improvement_metrics(self) -> ImprovementMetrics | None:
        """Compute before/after metrics based on pattern application data."""
        patterns = self.storage.load_patterns()
        applied = [p for p in patterns if p.applied_count > 0]
        if not applied:
            return None

        total_applied = sum(p.applied_count for p in applied)
        total_success = sum(p.success_after_apply for p in applied)
        if total_applied == 0:
            return None

        success_rate = total_success / total_applied
        return ImprovementMetrics(
            qa_first_pass_rate={"before": 0.0, "after": round(success_rate, 3)},
            avg_qa_iterations={"before": 0.0, "after": 0.0},
            error_rate={"before": 0.0, "after": 0.0},
        )

    def _heuristic_extract(
        self, builds_data: list[dict[str, Any]]
    ) -> list[LearningPattern]:
        """Basic heuristic pattern extraction as fallback when AI is not available."""
        patterns = []

        # Extract QA patterns from iteration history
        high_qa_iter_builds = 0
        first_pass_builds = 0
        total_builds = len(builds_data)

        for build in builds_data:
            plan = build.get("implementation_plan", {})
            qa_stats = plan.get("qa_stats", {})
            total_iter = qa_stats.get("total_iterations", 0)

            if total_iter > 3:
                high_qa_iter_builds += 1
            if total_iter <= 1:
                first_pass_builds += 1

            if build.get("had_escalation"):
                patterns.append(
                    LearningPattern(
                        pattern_id=LearningPattern.generate_id(),
                        category=PatternCategory.QA_PATTERN,
                        pattern_type="failure",
                        source="build_analysis",
                        description=f"Build {build.get('spec_id', '')} required human escalation due to recurring issues",
                        confidence=0.7,
                        occurrence_count=1,
                        agent_phase="qa_fixing",
                        context_tags=build.get("context_tags", [])[:5],
                        actionable_instruction="When fixing QA issues, verify the fix addresses the root cause, not just symptoms. Check for similar issues in adjacent code.",
                        source_build_ids=[build.get("spec_id", "")],
                    )
                )

        if total_builds >= 3 and high_qa_iter_builds / total_builds > 0.5:
            patterns.append(
                LearningPattern(
                    pattern_id=LearningPattern.generate_id(),
                    category=PatternCategory.QA_PATTERN,
                    pattern_type="failure",
                    source="build_analysis",
                    description="More than half of builds require 3+ QA iterations",
                    confidence=0.75,
                    occurrence_count=high_qa_iter_builds,
                    agent_phase="coding",
                    context_tags=[],
                    actionable_instruction="Before submitting code for QA, run all existing tests locally and verify edge cases. Ensure error handling is comprehensive.",
                    source_build_ids=[b.get("spec_id", "") for b in builds_data],
                )
            )

        return patterns
