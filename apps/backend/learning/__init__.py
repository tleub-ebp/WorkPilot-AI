"""
Learning Mode & Onboarding AI Module

This module provides educational features to help developers learn from
the codebase and understand what Auto-Claude is doing.
"""

from .learning_mode import LearningMode, LearningModeConfig, ExplanationLevel
from .documentation_generator import DocumentationGenerator, DocType
from .tutorial_generator import TutorialGenerator, TutorialTopic
from .onboarding_assistant import OnboardingAssistant, OnboardingStep

__all__ = [
    "LearningMode",
    "LearningModeConfig",
    "ExplanationLevel",
    "DocumentationGenerator",
    "DocType",
    "TutorialGenerator",
    "TutorialTopic",
    "OnboardingAssistant",
    "OnboardingStep",
]
