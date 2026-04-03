"""
Live Development Companion — Real-Time Pair Programming

A real-time AI companion that watches file changes, analyzes diffs
incrementally, provides proactive suggestions, and offers intelligent
takeover when the developer appears blocked.

Modules:
- types.py: Data models for suggestions, file events, takeover state
- analyzer.py: Incremental diff-based code analyzer
- suggestion_engine.py: AI-powered suggestion generation
- takeover_detector.py: Inactivity and complexity detection
"""

from .types import (
    CompanionConfig,
    CompanionState,
    FileChangeEvent,
    LiveSuggestion,
    SuggestionPriority,
    SuggestionType,
    TakeoverProposal,
    TakeoverStatus,
)

__all__ = [
    "CompanionConfig",
    "CompanionState",
    "FileChangeEvent",
    "LiveSuggestion",
    "SuggestionPriority",
    "SuggestionType",
    "TakeoverProposal",
    "TakeoverStatus",
]
