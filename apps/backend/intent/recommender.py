#!/usr/bin/env python3
"""
Intent Recommendations Module
==============================

Provides proactive recommendations based on intent analysis,
similar tasks, and learned patterns.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .learner import IntentLearner
from .models import IntentAnalysis, IntentCategory

logger = logging.getLogger(__name__)


@dataclass
class TaskRecommendation:
    """A single recommendation for a task."""

    type: str  # "similar_task", "tool", "pattern", "warning", "tip"
    title: str
    description: str
    confidence: float  # 0.0 to 1.0
    source: str  # Where this recommendation comes from
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type,
            "title": self.title,
            "description": self.description,
            "confidence": self.confidence,
            "source": self.source,
            "metadata": self.metadata,
        }


@dataclass
class IntentRecommendations:
    """Complete set of recommendations for a task."""

    task_description: str
    intent_category: IntentCategory
    recommendations: list[TaskRecommendation] = field(default_factory=list)
    estimated_complexity: str = "medium"  # simple, medium, high, very_high
    estimated_duration_hours: tuple[float, float] = (2.0, 6.0)  # min, max
    required_skills: list[str] = field(default_factory=list)
    suggested_tests: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_description": self.task_description,
            "intent_category": self.intent_category.value,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "estimated_complexity": self.estimated_complexity,
            "estimated_duration_hours": {
                "min": self.estimated_duration_hours[0],
                "max": self.estimated_duration_hours[1],
            },
            "required_skills": self.required_skills,
            "suggested_tests": self.suggested_tests,
        }


class IntentRecommender:
    """
    Generates proactive recommendations based on intent analysis.

    Provides:
    - Similar tasks from project history
    - Recommended tools and libraries
    - Common patterns for this intent
    - Potential risks and warnings
    - Estimated complexity and duration
    """

    def __init__(self, learner: IntentLearner | None = None):
        """
        Initialize the recommender.

        Args:
            learner: IntentLearner instance for historical data
        """
        self.learner = learner or IntentLearner()

    def generate_recommendations(
        self,
        analysis: IntentAnalysis,
        project_id: str = "",
        project_dir: Path | None = None,
    ) -> IntentRecommendations:
        """
        Generate comprehensive recommendations for a task.

        Args:
            analysis: IntentAnalysis from intent recognition
            project_id: Project identifier for context
            project_dir: Project directory for codebase analysis

        Returns:
            IntentRecommendations with actionable suggestions
        """
        intent = analysis.primary_intent
        recommendations = []

        # Add category-specific recommendations
        recommendations.extend(
            self._get_category_recommendations(intent.category, project_id)
        )

        # Add risk warnings
        if intent.confidence_score < 0.6:
            recommendations.append(
                TaskRecommendation(
                    type="warning",
                    title="Low Confidence Detection",
                    description=(
                        f"Intent was detected with {intent.confidence_score:.0%} confidence. "
                        "Consider clarifying the task description."
                    ),
                    confidence=1.0 - intent.confidence_score,
                    source="confidence_check",
                    metadata={"alternatives": len(analysis.alternative_intents)},
                )
            )

        # Add security scan recommendation for security-related tasks
        if intent.category == IntentCategory.SECURITY_FIX:
            recommendations.append(
                TaskRecommendation(
                    type="tool",
                    title="Security Scan Required",
                    description="Run security scanner before and after changes to verify fix.",
                    confidence=1.0,
                    source="security_policy",
                    metadata={"required": True},
                )
            )

        # Add test recommendations
        test_recs = self._get_test_recommendations(intent.category)
        recommendations.extend(test_recs)

        # Estimate complexity and duration
        complexity, duration = self._estimate_effort(intent.category, analysis)

        # Required skills
        skills = self._get_required_skills(intent.category)

        # Suggested tests
        tests = self._get_suggested_test_types(intent.category)

        return IntentRecommendations(
            task_description=analysis.task_description,
            intent_category=intent.category,
            recommendations=recommendations,
            estimated_complexity=complexity,
            estimated_duration_hours=duration,
            required_skills=skills,
            suggested_tests=tests,
        )

    def _get_category_recommendations(
        self, category: IntentCategory, project_id: str
    ) -> list[TaskRecommendation]:
        """Get recommendations specific to intent category."""
        recommendations = []

        # Check project patterns
        if project_id:
            patterns = self.learner.get_project_patterns(project_id)
            if category.value in patterns.common_intents:
                count = patterns.common_intents[category.value]
                recommendations.append(
                    TaskRecommendation(
                        type="pattern",
                        title="Common Task Type",
                        description=f"This type of task appears frequently in this project ({count} times).",
                        confidence=0.8,
                        source="project_history",
                        metadata={"frequency": count},
                    )
                )

        # Category-specific recommendations
        if category == IntentCategory.PERFORMANCE:
            recommendations.append(
                TaskRecommendation(
                    type="tip",
                    title="Benchmark Before & After",
                    description="Establish baseline metrics before optimization to measure impact.",
                    confidence=0.9,
                    source="best_practice",
                    metadata={"tools": ["pytest-benchmark", "locust"]},
                )
            )

        elif category == IntentCategory.REFACTORING:
            recommendations.append(
                TaskRecommendation(
                    type="tip",
                    title="Test Coverage Check",
                    description="Ensure good test coverage exists before refactoring.",
                    confidence=0.95,
                    source="best_practice",
                    metadata={"min_coverage": 70},
                )
            )

        elif category == IntentCategory.API_DESIGN:
            recommendations.append(
                TaskRecommendation(
                    type="pattern",
                    title="RESTful Best Practices",
                    description="Follow REST conventions: proper HTTP methods, status codes, and resource naming.",
                    confidence=0.85,
                    source="api_guidelines",
                    metadata={
                        "resources": [
                            "https://restfulapi.net/",
                            "OpenAPI Specification",
                        ]
                    },
                )
            )

        elif category == IntentCategory.DATA_MIGRATION:
            recommendations.append(
                TaskRecommendation(
                    type="warning",
                    title="Backup Required",
                    description="Always backup data before migration. Test on staging first.",
                    confidence=1.0,
                    source="data_safety",
                    metadata={"required": True, "critical": True},
                )
            )

        elif category == IntentCategory.UI_UX:
            recommendations.append(
                TaskRecommendation(
                    type="tip",
                    title="Accessibility Check",
                    description="Ensure changes meet accessibility standards (WCAG 2.1).",
                    confidence=0.8,
                    source="accessibility_guidelines",
                    metadata={"standards": ["WCAG 2.1", "ARIA"]},
                )
            )

        return recommendations

    def _get_test_recommendations(
        self, category: IntentCategory
    ) -> list[TaskRecommendation]:
        """Get test recommendations based on intent."""
        recommendations = []

        if category in [
            IntentCategory.BUG_FIX,
            IntentCategory.SECURITY_FIX,
            IntentCategory.HOTFIX,
        ]:
            recommendations.append(
                TaskRecommendation(
                    type="tool",
                    title="Regression Test Required",
                    description="Add a test that reproduces the bug to prevent regression.",
                    confidence=1.0,
                    source="testing_policy",
                    metadata={"test_type": "regression"},
                )
            )

        elif category == IntentCategory.NEW_FEATURE:
            recommendations.append(
                TaskRecommendation(
                    type="tool",
                    title="Comprehensive Testing",
                    description="New features should have unit, integration, and E2E tests.",
                    confidence=0.9,
                    source="testing_policy",
                    metadata={"test_types": ["unit", "integration", "e2e"]},
                )
            )

        return recommendations

    def _estimate_effort(
        self, category: IntentCategory, analysis: IntentAnalysis
    ) -> tuple[str, tuple[float, float]]:
        """
        Estimate complexity and duration.

        Returns:
            Tuple of (complexity_level, (min_hours, max_hours))
        """
        # Base estimates by category
        estimates = {
            IntentCategory.HOTFIX: ("simple", (1.0, 3.0)),
            IntentCategory.BUG_FIX: ("simple", (2.0, 6.0)),
            IntentCategory.DOCUMENTATION: ("simple", (1.0, 4.0)),
            IntentCategory.TESTING: ("simple", (2.0, 5.0)),
            IntentCategory.ENHANCEMENT: ("medium", (4.0, 12.0)),
            IntentCategory.NEW_FEATURE: ("medium", (8.0, 24.0)),
            IntentCategory.REFACTORING: ("medium", (6.0, 16.0)),
            IntentCategory.PERFORMANCE: ("medium", (6.0, 20.0)),
            IntentCategory.API_DESIGN: ("medium", (8.0, 20.0)),
            IntentCategory.SECURITY_FIX: ("high", (4.0, 16.0)),
            IntentCategory.DATA_MIGRATION: ("high", (12.0, 40.0)),
            IntentCategory.INFRASTRUCTURE: ("high", (8.0, 32.0)),
            IntentCategory.INVESTIGATION: ("medium", (4.0, 16.0)),
            IntentCategory.SPIKE: ("simple", (2.0, 8.0)),
            IntentCategory.RESEARCH: ("medium", (4.0, 12.0)),
        }

        complexity, duration = estimates.get(
            category, ("medium", (4.0, 12.0))
        )

        # Adjust based on confidence
        if analysis.primary_intent.confidence_score < 0.5:
            # Low confidence = higher uncertainty = wider range
            duration = (duration[0], duration[1] * 1.5)

        return complexity, duration

    def _get_required_skills(self, category: IntentCategory) -> list[str]:
        """Get required skills based on intent category."""
        skills_map = {
            IntentCategory.SECURITY_FIX: [
                "Security",
                "Authentication",
                "Encryption",
            ],
            IntentCategory.PERFORMANCE: ["Profiling", "Optimization", "Caching"],
            IntentCategory.API_DESIGN: ["REST", "API Design", "OpenAPI"],
            IntentCategory.UI_UX: ["Frontend", "Design", "Accessibility"],
            IntentCategory.DATA_MIGRATION: ["Databases", "SQL", "Data Modeling"],
            IntentCategory.INFRASTRUCTURE: ["DevOps", "Docker", "CI/CD"],
            IntentCategory.TESTING: ["Testing", "Test Automation", "QA"],
        }

        return skills_map.get(category, [])

    def _get_suggested_test_types(self, category: IntentCategory) -> list[str]:
        """Get suggested test types based on intent."""
        if category in [IntentCategory.BUG_FIX, IntentCategory.HOTFIX]:
            return ["unit", "regression"]
        elif category == IntentCategory.NEW_FEATURE:
            return ["unit", "integration", "e2e"]
        elif category == IntentCategory.API_DESIGN:
            return ["unit", "integration", "contract"]
        elif category == IntentCategory.PERFORMANCE:
            return ["unit", "performance", "load"]
        elif category == IntentCategory.SECURITY_FIX:
            return ["unit", "security", "penetration"]
        elif category == IntentCategory.UI_UX:
            return ["unit", "visual", "e2e"]
        else:
            return ["unit", "integration"]

