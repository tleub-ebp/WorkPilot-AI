"""Backward compatibility shim — prefer ``from spec.critique import …``.

Emitted ``DeprecationWarning`` helps migrate any remaining callers off
the root import path so this file can eventually be deleted.
"""

import warnings

warnings.warn(
    "apps.backend.critique is deprecated; import from apps.backend.spec.critique instead.",
    DeprecationWarning,
    stacklevel=2,
)

from spec.critique import *  # noqa: F403,E402
