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

__all__ = ["OnboardingEngine", "OnboardingGuide", "OnboardingSection", "KeyFile", "Convention"]
