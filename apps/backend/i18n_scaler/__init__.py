"""i18n Auto-Scaling.

Scaffolds and maintains translation files across many locales from a
single source locale. Diffs source vs targets, generates the missing-key
skeleton for each target, and reports translation coverage per locale.

Different from `i18n_agent/i18n_scanner.py` which audits a project for
i18n issues. This module is the **pipeline** that creates and maintains
the locale files themselves.
"""

from .scaler import (
    I18nAutoScaler,
    LocaleCoverage,
    LocaleDiff,
    PlaceholderStrategy,
    ScalingReport,
    flatten,
    unflatten,
)

__all__ = [
    "I18nAutoScaler",
    "LocaleCoverage",
    "LocaleDiff",
    "PlaceholderStrategy",
    "ScalingReport",
    "flatten",
    "unflatten",
]
