#!/usr/bin/env python3
"""
Intent Recognizer
=================

Main intent recognition engine using LLM for semantic analysis.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.simple_client import create_simple_client
from implementation_plan import WorkflowType

from .models import Intent, IntentAnalysis, IntentCategory, IntentConfidence
from .prompt import format_intent_prompt

logger = logging.getLogger(__name__)


class IntentRecognizer:
    """
    Recognizes intent from task descriptions using LLM analysis.

    This goes beyond keyword matching to understand the true intent
    behind a task, considering context, implicit signals, and nuance.
    """

    def __init__(self, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize the intent recognizer.

        Args:
            model: Claude model to use for analysis
        """
        self.model = model
        self._cache: dict[str, IntentAnalysis] = {}

    def analyze_intent(
        self,
        task_description: str,
        additional_context: str = "",
        use_cache: bool = True,
    ) -> IntentAnalysis:
        """
        Analyze task intent using LLM.

        Args:
            task_description: The task description to analyze
            additional_context: Optional additional context (spec content, requirements)
            use_cache: Whether to use cached results

        Returns:
            IntentAnalysis with primary intent and alternatives
        """
        # Check cache
        cache_key = self._make_cache_key(task_description, additional_context)
        if use_cache and cache_key in self._cache:
            logger.debug(f"Using cached intent analysis for: {task_description[:50]}")
            return self._cache[cache_key]

        logger.info(f"Analyzing intent for task: {task_description[:100]}...")

        # Format prompt
        prompt = format_intent_prompt(task_description, additional_context)

        try:
            # Call LLM
            client = create_simple_client()
            response = client.messages.create(
                model=self.model,
                max_tokens=2048,
                temperature=0.0,  # Deterministic for classification
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract JSON from response
            response_text = response.content[0].text.strip()
            analysis_data = self._extract_json(response_text)

            # Parse into IntentAnalysis
            analysis = self._parse_analysis(analysis_data, task_description)

            # Cache result
            if use_cache:
                self._cache[cache_key] = analysis

            logger.info(
                f"Intent detected: {analysis.primary_intent.category.value} "
                f"(confidence: {analysis.primary_intent.confidence_score:.2f})"
            )

            return analysis

        except Exception as e:
            logger.error(f"Failed to analyze intent: {e}", exc_info=True)
            # Return fallback intent
            return self._create_fallback_intent(task_description)

    def analyze_from_spec_dir(self, spec_dir: Path) -> IntentAnalysis:
        """
        Analyze intent from a spec directory with full context.

        Args:
            spec_dir: Path to spec directory containing spec.md, requirements.json, etc.

        Returns:
            IntentAnalysis with primary intent and alternatives
        """
        spec_dir = Path(spec_dir)

        # Load task description
        task_description = ""
        requirements_file = spec_dir / "requirements.json"
        if requirements_file.exists():
            try:
                with open(requirements_file, encoding="utf-8") as f:
                    requirements = json.load(f)
                    task_description = requirements.get("task_description", "")
            except (json.JSONDecodeError, OSError):
                pass

        # Load additional context
        additional_context = ""
        spec_file = spec_dir / "spec.md"
        if spec_file.exists():
            try:
                additional_context = spec_file.read_text(encoding="utf-8")
            except OSError:
                pass

        if not task_description and not additional_context:
            logger.warning(f"No task description found in {spec_dir}")
            return self._create_fallback_intent("Unknown task")

        return self.analyze_intent(
            task_description or additional_context[:500], additional_context
        )

    def _extract_json(self, response_text: str) -> dict:
        """Extract JSON from LLM response, handling markdown code blocks."""
        # Remove markdown code blocks if present
        text = response_text.strip()
        if text.startswith("```"):
            # Find the first { and last }
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                text = text[start : end + 1]

        return json.loads(text)

    def _parse_analysis(
        self, data: dict, task_description: str
    ) -> IntentAnalysis:
        """Parse raw JSON response into IntentAnalysis object."""
        primary_data = data["primary_intent"]
        primary_intent = Intent(
            category=IntentCategory(primary_data["category"]),
            workflow_type=WorkflowType(primary_data["workflow_type"]),
            confidence_score=float(primary_data["confidence_score"]),
            confidence_level=IntentConfidence(primary_data["confidence_level"]),
            reasoning=primary_data["reasoning"],
            keywords_found=primary_data.get("keywords_found", []),
            context_clues=primary_data.get("context_clues", []),
        )

        alternatives = []
        for alt_data in data.get("alternative_intents", []):
            alt = Intent(
                category=IntentCategory(alt_data["category"]),
                workflow_type=WorkflowType(alt_data["workflow_type"]),
                confidence_score=float(alt_data["confidence_score"]),
                confidence_level=IntentConfidence(alt_data["confidence_level"]),
                reasoning=alt_data["reasoning"],
                keywords_found=alt_data.get("keywords_found", []),
                context_clues=alt_data.get("context_clues", []),
            )
            alternatives.append(alt)

        return IntentAnalysis(
            primary_intent=primary_intent,
            alternative_intents=alternatives,
            task_description=task_description,
            model_used=self.model,
            requires_clarification=data.get("requires_clarification", False),
            clarification_questions=data.get("clarification_questions", []),
        )

    def _create_fallback_intent(self, task_description: str) -> IntentAnalysis:
        """Create a fallback intent when LLM analysis fails."""
        fallback = Intent(
            category=IntentCategory.UNCLEAR,
            workflow_type=WorkflowType.DEVELOPMENT,
            confidence_score=0.1,
            confidence_level=IntentConfidence.VERY_LOW,
            reasoning="Failed to analyze intent, using fallback",
            keywords_found=[],
            context_clues=[],
        )

        return IntentAnalysis(
            primary_intent=fallback,
            alternative_intents=[],
            task_description=task_description,
            model_used=self.model,
            requires_clarification=True,
            clarification_questions=[
                "Could you provide more details about what you're trying to accomplish?",
                "Is this a new feature, bug fix, or something else?",
            ],
        )

    def _make_cache_key(self, task_description: str, additional_context: str) -> str:
        """Generate cache key from inputs."""
        import hashlib

        combined = f"{task_description}:{additional_context}"
        return hashlib.md5(combined.encode()).hexdigest()

    def clear_cache(self) -> None:
        """Clear the intent analysis cache."""
        self._cache.clear()
        logger.debug("Cleared intent recognition cache")

