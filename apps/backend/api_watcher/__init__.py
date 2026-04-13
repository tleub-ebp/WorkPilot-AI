"""
API Contract Watcher — Detect breaking API changes between branches.

Compares OpenAPI/GraphQL/gRPC contracts, classifies changes as
non-breaking / potentially-breaking / breaking, and generates
migration guides for consuming teams.

Modules:
    - contract_parser: parse OpenAPI, GraphQL, protobuf specs
    - breaking_change_detector: semantic diff and classification
    - migration_guide_generator: produce Markdown migration guides
"""

from .breaking_change_detector import (
    BreakingChangeDetector,
    ChangeCategory,
    ChangeType,
    ContractChange,
    ContractDiff,
)
from .contract_parser import (
    ApiContract,
    ApiEndpoint,
    ApiField,
    ContractFormat,
    ContractParser,
)
from .migration_guide_generator import MigrationGuide, MigrationGuideGenerator

__all__ = [
    "ContractParser",
    "ContractFormat",
    "ApiContract",
    "ApiEndpoint",
    "ApiField",
    "BreakingChangeDetector",
    "ContractDiff",
    "ContractChange",
    "ChangeCategory",
    "ChangeType",
    "MigrationGuideGenerator",
    "MigrationGuide",
]
