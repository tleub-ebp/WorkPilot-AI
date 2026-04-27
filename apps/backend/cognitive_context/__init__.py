"""Cognitive Context Optimizer.

Given a list of candidate files and a token budget, decides which files
(or which slices of which files) to actually include in the prompt, ranked
by relevance to the user's task.

Different from `skills/context_optimizer.py` (which compacts an already-built
context dict) and from `context/builder.py` (which discovers candidate files).
This module sits *between* them: it takes the candidate files, scores each
one's relevance, then packs them into the budget, optionally truncating
long files in a smart way (keep imports + top-level signatures + the lines
that match the query keywords).
"""

from .optimizer import (
    CognitiveContextOptimizer,
    FileSlice,
    OptimizedContext,
    RelevanceScore,
    estimate_tokens,
)

__all__ = [
    "CognitiveContextOptimizer",
    "FileSlice",
    "OptimizedContext",
    "RelevanceScore",
    "estimate_tokens",
]
