"""
Breaking Change Detector — Semantic diff between two API contracts.

Classifies changes as non-breaking, potentially breaking, or breaking
and generates migration guides.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

from .contract_parser import ApiContract, ApiEndpoint, ApiField

logger = logging.getLogger(__name__)


class ChangeCategory(str, Enum):
    NON_BREAKING = "non_breaking"
    POTENTIALLY_BREAKING = "potentially_breaking"
    BREAKING = "breaking"


class ChangeType(str, Enum):
    ENDPOINT_ADDED = "endpoint_added"
    ENDPOINT_REMOVED = "endpoint_removed"
    ENDPOINT_DEPRECATED = "endpoint_deprecated"
    FIELD_ADDED = "field_added"
    FIELD_REMOVED = "field_removed"
    FIELD_TYPE_CHANGED = "field_type_changed"
    FIELD_REQUIRED_ADDED = "field_required_added"
    FIELD_DEPRECATED = "field_deprecated"
    TYPE_ADDED = "type_added"
    TYPE_REMOVED = "type_removed"
    PARAMETER_ADDED_REQUIRED = "parameter_added_required"
    PARAMETER_REMOVED = "parameter_removed"
    RESPONSE_STATUS_REMOVED = "response_status_removed"


@dataclass
class ContractChange:
    """A single detected change between two contract versions."""

    change_type: ChangeType
    category: ChangeCategory
    path: str
    description: str
    old_value: str = ""
    new_value: str = ""


@dataclass
class ContractDiff:
    """Full diff result between two API contract versions."""

    changes: list[ContractChange] = field(default_factory=list)
    breaking_count: int = 0
    potentially_breaking_count: int = 0
    non_breaking_count: int = 0

    @property
    def has_breaking_changes(self) -> bool:
        return self.breaking_count > 0

    @property
    def summary(self) -> str:
        parts = []
        if self.breaking_count:
            parts.append(f"🔴 {self.breaking_count} breaking")
        if self.potentially_breaking_count:
            parts.append(f"🟡 {self.potentially_breaking_count} potentially breaking")
        if self.non_breaking_count:
            parts.append(f"🟢 {self.non_breaking_count} non-breaking")
        return ", ".join(parts) or "No changes detected"


class BreakingChangeDetector:
    """Detect breaking changes between two API contract versions.

    Usage::

        detector = BreakingChangeDetector()
        diff = detector.diff(old_contract, new_contract)
        if diff.has_breaking_changes:
            alert_consumers(diff)
    """

    def diff(self, old: ApiContract, new: ApiContract) -> ContractDiff:
        """Compare two contracts and return a structured diff."""
        result = ContractDiff()

        self._diff_endpoints(old, new, result)
        self._diff_types(old, new, result)

        result.breaking_count = sum(
            1 for c in result.changes if c.category == ChangeCategory.BREAKING
        )
        result.potentially_breaking_count = sum(
            1
            for c in result.changes
            if c.category == ChangeCategory.POTENTIALLY_BREAKING
        )
        result.non_breaking_count = sum(
            1 for c in result.changes if c.category == ChangeCategory.NON_BREAKING
        )

        return result

    def _diff_endpoints(
        self, old: ApiContract, new: ApiContract, result: ContractDiff
    ) -> None:
        old_eps = {f"{e.method} {e.path}": e for e in old.endpoints}
        new_eps = {f"{e.method} {e.path}": e for e in new.endpoints}

        # Removed endpoints
        for key in old_eps:
            if key not in new_eps:
                result.changes.append(
                    ContractChange(
                        change_type=ChangeType.ENDPOINT_REMOVED,
                        category=ChangeCategory.BREAKING,
                        path=key,
                        description=f"Endpoint {key} was removed",
                    )
                )

        # Added endpoints
        for key in new_eps:
            if key not in old_eps:
                result.changes.append(
                    ContractChange(
                        change_type=ChangeType.ENDPOINT_ADDED,
                        category=ChangeCategory.NON_BREAKING,
                        path=key,
                        description=f"Endpoint {key} was added",
                    )
                )

        # Modified endpoints
        for key in old_eps:
            if key in new_eps:
                self._diff_endpoint_detail(old_eps[key], new_eps[key], key, result)

    def _diff_endpoint_detail(
        self,
        old_ep: ApiEndpoint,
        new_ep: ApiEndpoint,
        path: str,
        result: ContractDiff,
    ) -> None:
        if not old_ep.deprecated and new_ep.deprecated:
            result.changes.append(
                ContractChange(
                    change_type=ChangeType.ENDPOINT_DEPRECATED,
                    category=ChangeCategory.POTENTIALLY_BREAKING,
                    path=path,
                    description=f"Endpoint {path} was deprecated",
                )
            )

        old_params = {p.name: p for p in old_ep.parameters}
        new_params = {p.name: p for p in new_ep.parameters}

        for name in new_params:
            if name not in old_params and new_params[name].required:
                result.changes.append(
                    ContractChange(
                        change_type=ChangeType.PARAMETER_ADDED_REQUIRED,
                        category=ChangeCategory.BREAKING,
                        path=f"{path}.params.{name}",
                        description=f"Required parameter '{name}' was added to {path}",
                    )
                )

        for name in old_params:
            if name not in new_params:
                result.changes.append(
                    ContractChange(
                        change_type=ChangeType.PARAMETER_REMOVED,
                        category=ChangeCategory.BREAKING,
                        path=f"{path}.params.{name}",
                        description=f"Parameter '{name}' was removed from {path}",
                    )
                )

    def _diff_types(
        self, old: ApiContract, new: ApiContract, result: ContractDiff
    ) -> None:
        for type_name in old.types:
            if type_name not in new.types:
                result.changes.append(
                    ContractChange(
                        change_type=ChangeType.TYPE_REMOVED,
                        category=ChangeCategory.BREAKING,
                        path=type_name,
                        description=f"Type '{type_name}' was removed",
                    )
                )
            else:
                self._diff_fields(
                    old.types[type_name],
                    new.types[type_name],
                    type_name,
                    result,
                )

        for type_name in new.types:
            if type_name not in old.types:
                result.changes.append(
                    ContractChange(
                        change_type=ChangeType.TYPE_ADDED,
                        category=ChangeCategory.NON_BREAKING,
                        path=type_name,
                        description=f"Type '{type_name}' was added",
                    )
                )

    def _diff_fields(
        self,
        old_fields: list[ApiField],
        new_fields: list[ApiField],
        parent: str,
        result: ContractDiff,
    ) -> None:
        old_map = {f.name: f for f in old_fields}
        new_map = {f.name: f for f in new_fields}

        for name in old_map:
            if name not in new_map:
                result.changes.append(
                    ContractChange(
                        change_type=ChangeType.FIELD_REMOVED,
                        category=ChangeCategory.BREAKING,
                        path=f"{parent}.{name}",
                        description=f"Field '{name}' was removed from {parent}",
                    )
                )
            else:
                old_f, new_f = old_map[name], new_map[name]
                if old_f.type != new_f.type:
                    result.changes.append(
                        ContractChange(
                            change_type=ChangeType.FIELD_TYPE_CHANGED,
                            category=ChangeCategory.BREAKING,
                            path=f"{parent}.{name}",
                            description=f"Field '{name}' type changed from '{old_f.type}' to '{new_f.type}'",
                            old_value=old_f.type,
                            new_value=new_f.type,
                        )
                    )
                if not old_f.required and new_f.required:
                    result.changes.append(
                        ContractChange(
                            change_type=ChangeType.FIELD_REQUIRED_ADDED,
                            category=ChangeCategory.BREAKING,
                            path=f"{parent}.{name}",
                            description=f"Field '{name}' in {parent} became required",
                        )
                    )

        for name in new_map:
            if name not in old_map:
                result.changes.append(
                    ContractChange(
                        change_type=ChangeType.FIELD_ADDED,
                        category=ChangeCategory.NON_BREAKING,
                        path=f"{parent}.{name}",
                        description=f"Field '{name}' was added to {parent}",
                    )
                )
