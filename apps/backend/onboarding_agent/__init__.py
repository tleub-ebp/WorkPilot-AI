"""
Onboarding Agent — Contextual onboarding for new team members.

Analyses the codebase to produce architecture overviews, key-file maps,
naming convention guides, and personalised learning paths.
"""

from .onboarding_engine import (
    Convention,
    KeyFile,
    OnboardingEngine,
    OnboardingGuide,
    OnboardingSection,
)
from .tour_builder import (
    FirstTask,
    GlossaryTerm,
    OnboardingPackage,
    OnboardingPackageBuilder,
    QuizQuestion,
    TourStep,
    build_first_tasks,
    build_glossary,
    build_quiz,
    build_tour,
    render_markdown,
)

__all__ = [
    "OnboardingEngine",
    "OnboardingGuide",
    "OnboardingSection",
    "KeyFile",
    "Convention",
    "OnboardingPackage",
    "OnboardingPackageBuilder",
    "TourStep",
    "QuizQuestion",
    "FirstTask",
    "GlossaryTerm",
    "build_tour",
    "build_quiz",
    "build_first_tasks",
    "build_glossary",
    "render_markdown",
]
