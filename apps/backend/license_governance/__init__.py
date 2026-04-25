"""Auto-Licensing & Dependency Governance.

Scans a project's dependency manifests (package.json, requirements.txt,
pyproject.toml, Cargo.toml, go.mod) for licences, classifies them by
permissiveness, and flags conflicts (e.g. GPL mixed into a proprietary
codebase, or copyleft transitives sneaking in).

Different from `continuous_ai/dependency_sentinel.py` which focuses on
**vulnerabilities** (CVEs). This module focuses on **licences**.
"""

from .scanner import (
    DependencyRecord,
    LicenseCategory,
    LicenseConflict,
    LicensePolicy,
    LicenseReport,
    LicenseScanner,
    classify_license,
)

__all__ = [
    "DependencyRecord",
    "LicenseCategory",
    "LicenseConflict",
    "LicensePolicy",
    "LicenseReport",
    "LicenseScanner",
    "classify_license",
]
