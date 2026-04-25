"""Architecture Drift Detection.

Compares an architecture validation snapshot against a stored baseline
to surface regressions ("drift"). Built on top of `architecture/`.

See `detector.py` for the public API.
"""

from .detector import (
    DriftDetector,
    DriftReport,
    DriftSeverity,
    ViolationDelta,
    detect_drift,
)

__all__ = [
    "DriftDetector",
    "DriftReport",
    "DriftSeverity",
    "ViolationDelta",
    "detect_drift",
]
