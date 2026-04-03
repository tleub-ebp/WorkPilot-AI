"""
Context Mesh — Cross-Project Intelligence

Exploits the Graphiti knowledge graph to create cross-project intelligence:
a knowledge network that enriches itself with every interaction and transfers
patterns between all of the user's projects.

Modules:
- types.py: Data models for patterns, handbook entries, recommendations
- mesh_service.py: Main orchestrator for cross-project analysis
- pattern_matcher.py: Cross-project pattern recognition
- handbook_generator.py: Auto-generated engineering handbook
- skill_transfer.py: Cross-project skill/convention transfer
- recommendations.py: Contextual recommendations engine
"""

from .types import (
    ContextMeshConfig,
    ContextualRecommendation,
    CrossProjectPattern,
    HandbookDomain,
    HandbookEntry,
    MeshAnalysisReport,
    PatternCategory,
    ProjectSummary,
    RecommendationType,
    SkillTransfer,
)

__all__ = [
    "ContextMeshConfig",
    "CrossProjectPattern",
    "HandbookEntry",
    "HandbookDomain",
    "SkillTransfer",
    "ContextualRecommendation",
    "RecommendationType",
    "MeshAnalysisReport",
    "PatternCategory",
    "ProjectSummary",
]
