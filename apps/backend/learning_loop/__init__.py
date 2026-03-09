"""
Autonomous Agent Learning Loop

Extracts success/failure patterns from completed builds and injects them
into future agent prompts to make agents progressively smarter.
"""

from .models import (
    LearningPattern,
    LearningReport,
    PatternCategory,
    PatternSource,
    PatternType,
)
from .pattern_applicator import PatternApplicator
from .pattern_extractor import PatternExtractor
from .pattern_storage import PatternStorage
from .service import LearningLoopService

__all__ = [
    "LearningPattern",
    "LearningReport",
    "PatternCategory",
    "PatternType",
    "PatternSource",
    "PatternStorage",
    "PatternExtractor",
    "PatternApplicator",
    "LearningLoopService",
]
