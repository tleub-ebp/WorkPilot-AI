"""Adaptive Model Router — pick the best model per task class.

See `router.py` for the public API.
"""

from .router import (
    ModelChoice,
    ModelRouter,
    QualityTier,
    RoutingPolicy,
    TaskClass,
    classify_task,
)

__all__ = [
    "ModelChoice",
    "ModelRouter",
    "QualityTier",
    "RoutingPolicy",
    "TaskClass",
    "classify_task",
]
