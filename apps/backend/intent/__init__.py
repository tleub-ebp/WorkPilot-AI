#!/usr/bin/env python3
"""
Intent Recognition Module
=========================

Advanced intent recognition using LLM to understand the true intent
behind task descriptions, beyond simple keyword matching.

This module provides:
- NLP-based intent classification
- Confidence scoring
- Multi-dimensional intent analysis
- Learning from user feedback
- Proactive recommendations
"""

from .learner import IntentFeedback, IntentLearner, ProjectPatterns
from .models import (
    Intent,
    IntentAnalysis,
    IntentCategory,
    IntentConfidence,
)
from .recognizer import IntentRecognizer
from .recommender import IntentRecommendations, IntentRecommender, TaskRecommendation

__all__ = [
    # Models
    "Intent",
    "IntentAnalysis",
    "IntentCategory",
    "IntentConfidence",
    # Recognizer
    "IntentRecognizer",
    # Learning
    "IntentLearner",
    "IntentFeedback",
    "ProjectPatterns",
    # Recommendations
    "IntentRecommender",
    "IntentRecommendations",
    "TaskRecommendation",
]
