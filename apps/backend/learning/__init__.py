"""
Learning Mode & Onboarding AI Module

This module provides educational features to help developers learn from
the codebase and understand what WorkPilot AI is doing.
"""

from .documentation_generator import DocType, DocumentationGenerator
from .learning_mode import ExplanationLevel, LearningMode, LearningModeConfig
from .onboarding_assistant import OnboardingAssistant, OnboardingStep
from .tutorial_generator import TutorialGenerator, TutorialTopic

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
