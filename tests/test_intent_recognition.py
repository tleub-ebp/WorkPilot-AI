#!/usr/bin/env python3
"""
Tests for Intent Recognition Module
====================================

Tests the complete intent recognition system including:
- LLM-based intent analysis
- Confidence scoring
- Learning from feedback
- Recommendations
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from apps.backend.intent import (
    Intent,
    IntentAnalysis,
    IntentCategory,
    IntentConfidence,
    IntentFeedback,
    IntentLearner,
    IntentRecommender,
    IntentRecognizer,
)
from apps.backend.implementation_plan import WorkflowType


class TestIntentModels:
    """Test intent data models."""

    def test_intent_creation(self):
        """Test creating an Intent object."""
        intent = Intent(
            category=IntentCategory.BUG_FIX,
            workflow_type=WorkflowType.INVESTIGATION,
            confidence_score=0.85,
            confidence_level=IntentConfidence.HIGH,
            reasoning="Clear bug report with reproduction steps",
            keywords_found=["bug", "error", "broken"],
            context_clues=["500 error", "login page"],
        )

        assert intent.category == IntentCategory.BUG_FIX
        assert intent.workflow_type == WorkflowType.INVESTIGATION
        assert intent.confidence_score == 0.85
        assert len(intent.keywords_found) == 3

    def test_intent_analysis_serialization(self):
        """Test IntentAnalysis to_dict and from_dict."""
        primary = Intent(
            category=IntentCategory.NEW_FEATURE,
            workflow_type=WorkflowType.FEATURE,
            confidence_score=0.92,
            confidence_level=IntentConfidence.VERY_HIGH,
            reasoning="Clear feature request",
            keywords_found=["add", "new"],
        )

        analysis = IntentAnalysis(
            primary_intent=primary,
            task_description="Add OAuth2 authentication",
            requires_clarification=False,
        )

        # Serialize and deserialize
        data = analysis.to_dict()
        restored = IntentAnalysis.from_dict(data)

        assert restored.primary_intent.category == IntentCategory.NEW_FEATURE
        assert restored.primary_intent.confidence_score == 0.92
        assert restored.task_description == "Add OAuth2 authentication"


class TestIntentRecognizer:
    """Test intent recognition with LLM."""

    @patch("apps.backend.intent.recognizer.create_simple_client")
    def test_analyze_intent_bug_fix(self, mock_create_client):
        """Test analyzing a bug fix intent."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps(
                    {
                        "primary_intent": {
                            "category": "bug_fix",
                            "workflow_type": "investigation",
                            "confidence_score": 0.95,
                            "confidence_level": "very_high",
                            "reasoning": "Clear bug report",
                            "keywords_found": ["error", "broken"],
                            "context_clues": ["login page"],
                        },
                        "alternative_intents": [],
                        "requires_clarification": False,
                        "clarification_questions": [],
                    }
                )
            )
        ]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_create_client.return_value = mock_client

        recognizer = IntentRecognizer()
        analysis = recognizer.analyze_intent(
            "Login page returns 500 error when password has special characters"
        )

        assert analysis.primary_intent.category == IntentCategory.BUG_FIX
        assert analysis.primary_intent.workflow_type == WorkflowType.INVESTIGATION
        assert analysis.primary_intent.confidence_score == 0.95
        assert not analysis.requires_clarification

    @patch("apps.backend.intent.recognizer.create_simple_client")
    def test_analyze_intent_performance(self, mock_create_client):
        """Test analyzing a performance intent."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps(
                    {
                        "primary_intent": {
                            "category": "performance",
                            "workflow_type": "investigation",
                            "confidence_score": 0.70,
                            "confidence_level": "medium",
                            "reasoning": "Performance issue but needs investigation",
                            "keywords_found": ["slow"],
                            "context_clues": ["dashboard"],
                        },
                        "alternative_intents": [
                            {
                                "category": "bug_fix",
                                "workflow_type": "investigation",
                                "confidence_score": 0.30,
                                "confidence_level": "low",
                                "reasoning": "Could be a bug causing slowness",
                            }
                        ],
                        "requires_clarification": True,
                        "clarification_questions": [
                            "Is this a recent regression or long-standing issue?"
                        ],
                    }
                )
            )
        ]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_create_client.return_value = mock_client

        recognizer = IntentRecognizer()
        analysis = recognizer.analyze_intent("Users complain dashboard is slow")

        assert analysis.primary_intent.category == IntentCategory.PERFORMANCE
        assert analysis.primary_intent.confidence_score == 0.70
        assert analysis.requires_clarification
        assert len(analysis.alternative_intents) == 1
        assert len(analysis.clarification_questions) == 1

    def test_fallback_on_error(self):
        """Test fallback intent when LLM fails."""
        recognizer = IntentRecognizer()

        with patch(
            "apps.backend.intent.recognizer.create_simple_client",
            side_effect=Exception("API error"),
        ):
            analysis = recognizer.analyze_intent("Some task")

            assert analysis.primary_intent.category == IntentCategory.UNCLEAR
            assert analysis.primary_intent.confidence_score == 0.1
            assert analysis.requires_clarification

    def test_caching(self):
        """Test that intent analysis is cached."""
        recognizer = IntentRecognizer()

        with patch("apps.backend.intent.recognizer.create_simple_client") as mock:
            mock_response = MagicMock()
            mock_response.content = [
                MagicMock(
                    text=json.dumps(
                        {
                            "primary_intent": {
                                "category": "new_feature",
                                "workflow_type": "feature",
                                "confidence_score": 0.9,
                                "confidence_level": "very_high",
                                "reasoning": "Feature",
                                "keywords_found": [],
                                "context_clues": [],
                            },
                            "alternative_intents": [],
                            "requires_clarification": False,
                            "clarification_questions": [],
                        }
                    )
                )
            ]
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock.return_value = mock_client

            # First call
            recognizer.analyze_intent("Add feature X")

            # Second call (should use cache)
            recognizer.analyze_intent("Add feature X")

            # Should only call LLM once
            assert mock_client.messages.create.call_count == 1


class TestIntentLearner:
    """Test intent learning and feedback."""

    def test_record_feedback(self, tmp_path):
        """Test recording feedback."""
        learner = IntentLearner(storage_dir=tmp_path)

        learner.record_feedback(
            task_id="task-001",
            task_description="Fix login bug",
            detected_category=IntentCategory.NEW_FEATURE,
            detected_confidence=0.7,
            actual_category=IntentCategory.BUG_FIX,
            user_notes="This was clearly a bug fix",
            project_id="proj-123",
        )

        # Check feedback file exists
        assert (tmp_path / "feedback.jsonl").exists()

        # Check patterns updated
        patterns = learner.get_project_patterns("proj-123")
        assert patterns.common_intents.get("bug_fix", 0) == 1

    def test_accuracy_metrics(self, tmp_path):
        """Test calculating accuracy metrics."""
        learner = IntentLearner(storage_dir=tmp_path)

        # Record correct prediction
        learner.record_feedback(
            task_id="task-001",
            task_description="Fix bug",
            detected_category=IntentCategory.BUG_FIX,
            detected_confidence=0.9,
            actual_category=IntentCategory.BUG_FIX,
        )

        # Record incorrect prediction
        learner.record_feedback(
            task_id="task-002",
            task_description="Add feature",
            detected_category=IntentCategory.ENHANCEMENT,
            detected_confidence=0.7,
            actual_category=IntentCategory.NEW_FEATURE,
        )

        metrics = learner.get_accuracy_metrics()

        assert metrics["total_feedbacks"] == 2
        assert metrics["correct_predictions"] == 1
        assert metrics["overall_accuracy"] == 0.5

    def test_common_misclassifications(self, tmp_path):
        """Test identifying common misclassifications."""
        learner = IntentLearner(storage_dir=tmp_path)

        # Record same misclassification twice
        for i in range(2):
            learner.record_feedback(
                task_id=f"task-{i}",
                task_description="Task",
                detected_category=IntentCategory.ENHANCEMENT,
                detected_confidence=0.7,
                actual_category=IntentCategory.NEW_FEATURE,
            )

        misclass = learner.get_common_misclassifications()

        assert len(misclass) == 1
        assert misclass[0]["detected"] == "enhancement"
        assert misclass[0]["actual"] == "new_feature"
        assert misclass[0]["count"] == 2


class TestIntentRecommender:
    """Test recommendation generation."""

    def test_generate_recommendations_bug_fix(self):
        """Test recommendations for bug fix."""
        intent = Intent(
            category=IntentCategory.BUG_FIX,
            workflow_type=WorkflowType.INVESTIGATION,
            confidence_score=0.9,
            confidence_level=IntentConfidence.VERY_HIGH,
            reasoning="Bug fix",
        )

        analysis = IntentAnalysis(
            primary_intent=intent, task_description="Fix login bug"
        )

        recommender = IntentRecommender()
        recs = recommender.generate_recommendations(analysis)

        assert recs.intent_category == IntentCategory.BUG_FIX
        assert recs.estimated_complexity == "simple"
        assert "unit" in recs.suggested_tests
        assert "regression" in recs.suggested_tests

        # Should have regression test recommendation
        test_rec = next(
            (r for r in recs.recommendations if r.type == "tool"), None
        )
        assert test_rec is not None
        assert "regression" in test_rec.description.lower()

    def test_generate_recommendations_security(self):
        """Test recommendations for security fix."""
        intent = Intent(
            category=IntentCategory.SECURITY_FIX,
            workflow_type=WorkflowType.FEATURE,
            confidence_score=0.95,
            confidence_level=IntentConfidence.VERY_HIGH,
            reasoning="Security issue",
        )

        analysis = IntentAnalysis(
            primary_intent=intent, task_description="Fix XSS vulnerability"
        )

        recommender = IntentRecommender()
        recs = recommender.generate_recommendations(analysis)

        assert recs.intent_category == IntentCategory.SECURITY_FIX

        # Should require security scan
        security_rec = next(
            (r for r in recs.recommendations if "security scan" in r.title.lower()),
            None,
        )
        assert security_rec is not None
        assert security_rec.metadata.get("required") is True

    def test_low_confidence_warning(self):
        """Test warning for low confidence detection."""
        intent = Intent(
            category=IntentCategory.UNCLEAR,
            workflow_type=WorkflowType.DEVELOPMENT,
            confidence_score=0.4,
            confidence_level=IntentConfidence.LOW,
            reasoning="Unclear",
        )

        analysis = IntentAnalysis(
            primary_intent=intent, task_description="Do something"
        )

        recommender = IntentRecommender()
        recs = recommender.generate_recommendations(analysis)

        # Should have low confidence warning
        warning = next(
            (r for r in recs.recommendations if r.type == "warning"), None
        )
        assert warning is not None
        assert "confidence" in warning.title.lower()

    def test_estimate_effort(self):
        """Test effort estimation."""
        recommender = IntentRecommender()

        # Hotfix should be simple and quick
        intent = Intent(
            category=IntentCategory.HOTFIX,
            workflow_type=WorkflowType.INVESTIGATION,
            confidence_score=0.9,
            confidence_level=IntentConfidence.VERY_HIGH,
            reasoning="",
        )
        analysis = IntentAnalysis(primary_intent=intent, task_description="")
        recs = recommender.generate_recommendations(analysis)

        assert recs.estimated_complexity == "simple"
        assert recs.estimated_duration_hours[0] <= 3.0

        # Data migration should be high complexity
        intent = Intent(
            category=IntentCategory.DATA_MIGRATION,
            workflow_type=WorkflowType.MIGRATION,
            confidence_score=0.9,
            confidence_level=IntentConfidence.VERY_HIGH,
            reasoning="",
        )
        analysis = IntentAnalysis(primary_intent=intent, task_description="")
        recs = recommender.generate_recommendations(analysis)

        assert recs.estimated_complexity == "high"
        assert recs.estimated_duration_hours[1] >= 20.0

