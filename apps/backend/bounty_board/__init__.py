"""
Bounty Board — Competitive multi-agent mode.

Runs N contestants in parallel against the same spec, each with a
(provider, model, prompt) combination. A judge scores each worktree
against acceptance criteria, code quality and performance signals,
then picks a winner.

Public surface:
    from bounty_board import (
        BountyBoard,
        Contestant,
        BountyResult,
        ContestantSpec,
        run_bounty,
    )
"""

from .board import BountyBoard, BountyResult, Contestant, ContestantSpec, run_bounty

__all__ = [
    "BountyBoard",
    "Contestant",
    "ContestantSpec",
    "BountyResult",
    "run_bounty",
]
