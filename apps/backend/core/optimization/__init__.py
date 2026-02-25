"""
Core Optimization Module
======================

Base classes and utilities for token-aware optimization.
This module provides foundation for GitHub Copilot optimization
without affecting Claude Code agents.
"""

from .token_tracker import TokenTracker
from .token_aware_agent import TokenAwareAgentBase
from .hierarchical_prompt import HierarchicalPrompt
from .dynamic_prompt_template import DynamicPromptTemplate

__all__ = [
    'TokenTracker',
    'TokenAwareAgentBase', 
    'HierarchicalPrompt',
    'DynamicPromptTemplate'
]
