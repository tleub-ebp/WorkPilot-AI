"""
Edge Case Generator — Systematic edge case enumeration.

Generates edge cases for functions based on parameter types and
domain knowledge.  100% algorithmic — no LLM dependency.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class EdgeCaseCategory(str, Enum):
    EMPTY_INPUT = "empty_input"
    BOUNDARY = "boundary"
    NULL_UNDEFINED = "null_undefined"
    TYPE_MISMATCH = "type_mismatch"
    RACE_CONDITION = "race_condition"
    TIMEZONE = "timezone"
    LOCALE = "locale"
    PERMISSION = "permission"
    STATE_TRANSITION = "state_transition"
    CONCURRENCY = "concurrency"


@dataclass
class EdgeCase:
    """A single edge case test scenario."""

    category: EdgeCaseCategory
    description: str
    inputs: dict[str, Any] = field(default_factory=dict)
    expected_behavior: str = "should handle gracefully"
    severity: str = "medium"  # low, medium, high, critical
    tags: list[str] = field(default_factory=list)


class EdgeCaseGenerator:
    """Generate edge cases for function signatures.

    Usage::

        gen = EdgeCaseGenerator()
        cases = gen.for_function(
            name="create_user",
            params={"name": "str", "age": "int", "email": "str"},
        )
    """

    def for_function(
        self, name: str, params: dict[str, str]
    ) -> list[EdgeCase]:
        """Generate edge cases based on parameter names and types."""
        cases: list[EdgeCase] = []

        for param, ptype in params.items():
            cases.extend(self._for_param(param, ptype))

        # Cross-parameter edge cases
        cases.extend(self._cross_param_cases(name, params))

        return cases

    def for_api_endpoint(
        self,
        method: str,
        path: str,
        params: dict[str, str] | None = None,
        body_fields: dict[str, str] | None = None,
    ) -> list[EdgeCase]:
        """Generate edge cases for an API endpoint."""
        cases: list[EdgeCase] = []

        # Method-specific
        if method.upper() in ("POST", "PUT", "PATCH"):
            cases.append(EdgeCase(
                category=EdgeCaseCategory.EMPTY_INPUT,
                description=f"{method} {path} with empty body",
                inputs={"body": {}},
            ))
            cases.append(EdgeCase(
                category=EdgeCaseCategory.TYPE_MISMATCH,
                description=f"{method} {path} with string body instead of JSON",
                inputs={"body": "not json"},
            ))

        # Query params
        if params:
            for param, ptype in params.items():
                cases.extend(self._for_param(param, ptype))

        # Body fields
        if body_fields:
            for fld, ftype in body_fields.items():
                cases.extend(self._for_param(fld, ftype))

        # Auth edge cases
        cases.append(EdgeCase(
            category=EdgeCaseCategory.PERMISSION,
            description=f"{method} {path} with expired token",
            inputs={"auth": "expired_token"},
            severity="high",
        ))
        cases.append(EdgeCase(
            category=EdgeCaseCategory.PERMISSION,
            description=f"{method} {path} with no auth header",
            inputs={"auth": None},
            severity="high",
        ))

        return cases

    def for_state_machine(
        self, states: list[str], transitions: list[tuple[str, str, str]]
    ) -> list[EdgeCase]:
        """Generate edge cases for state machine transitions.

        Args:
            states: List of valid state names.
            transitions: List of (from_state, action, to_state) tuples.
        """
        cases: list[EdgeCase] = []
        valid_from: dict[str, list[str]] = {}
        for from_s, action, _ in transitions:
            valid_from.setdefault(from_s, []).append(action)

        # Invalid transitions
        all_actions = {t[1] for t in transitions}
        for state in states:
            valid_actions = set(valid_from.get(state, []))
            invalid_actions = all_actions - valid_actions
            for action in invalid_actions:
                cases.append(EdgeCase(
                    category=EdgeCaseCategory.STATE_TRANSITION,
                    description=f"Invalid transition: '{action}' from state '{state}'",
                    inputs={"current_state": state, "action": action},
                    severity="high",
                ))

        # Self-transitions
        for state in states:
            for _, action, to_s in transitions:
                if to_s == state:
                    cases.append(EdgeCase(
                        category=EdgeCaseCategory.STATE_TRANSITION,
                        description=f"Re-enter state '{state}' via '{action}'",
                        inputs={"current_state": state, "action": action},
                        severity="low",
                    ))
                    break

        return cases

    def _for_param(self, name: str, ptype: str) -> list[EdgeCase]:
        """Generate edge cases for a single parameter."""
        cases: list[EdgeCase] = []
        ptype_lower = ptype.lower()

        # Null/undefined
        cases.append(EdgeCase(
            category=EdgeCaseCategory.NULL_UNDEFINED,
            description=f"'{name}' is None",
            inputs={name: None},
        ))

        if "str" in ptype_lower:
            cases.extend(self._string_edge_cases(name))
        elif "int" in ptype_lower or "float" in ptype_lower or "number" in ptype_lower:
            cases.extend(self._numeric_edge_cases(name))
        elif "bool" in ptype_lower:
            cases.extend(self._boolean_edge_cases(name))
        elif "list" in ptype_lower or "array" in ptype_lower:
            cases.extend(self._list_edge_cases(name))
        elif "date" in ptype_lower or "time" in ptype_lower:
            cases.extend(self._datetime_edge_cases(name))

        return cases

    @staticmethod
    def _string_edge_cases(name: str) -> list[EdgeCase]:
        return [
            EdgeCase(EdgeCaseCategory.EMPTY_INPUT, f"'{name}' is empty string", {name: ""}),
            EdgeCase(EdgeCaseCategory.BOUNDARY, f"'{name}' is whitespace only", {name: "   "}),
            EdgeCase(EdgeCaseCategory.BOUNDARY, f"'{name}' has leading/trailing spaces", {name: "  value  "}),
            EdgeCase(EdgeCaseCategory.TYPE_MISMATCH, f"'{name}' is a number", {name: 12345}),
        ]

    @staticmethod
    def _numeric_edge_cases(name: str) -> list[EdgeCase]:
        return [
            EdgeCase(EdgeCaseCategory.BOUNDARY, f"'{name}' is zero", {name: 0}),
            EdgeCase(EdgeCaseCategory.BOUNDARY, f"'{name}' is negative", {name: -1}),
            EdgeCase(EdgeCaseCategory.BOUNDARY, f"'{name}' is very large", {name: 2**53}),
            EdgeCase(EdgeCaseCategory.TYPE_MISMATCH, f"'{name}' is string", {name: "abc"}),
        ]

    @staticmethod
    def _boolean_edge_cases(name: str) -> list[EdgeCase]:
        return [
            EdgeCase(EdgeCaseCategory.TYPE_MISMATCH, f"'{name}' is string 'true'", {name: "true"}),
            EdgeCase(EdgeCaseCategory.TYPE_MISMATCH, f"'{name}' is int 1", {name: 1}),
            EdgeCase(EdgeCaseCategory.TYPE_MISMATCH, f"'{name}' is int 0", {name: 0}),
        ]

    @staticmethod
    def _list_edge_cases(name: str) -> list[EdgeCase]:
        return [
            EdgeCase(EdgeCaseCategory.EMPTY_INPUT, f"'{name}' is empty list", {name: []}),
            EdgeCase(EdgeCaseCategory.BOUNDARY, f"'{name}' has one element", {name: ["single"]}),
            EdgeCase(EdgeCaseCategory.BOUNDARY, f"'{name}' has duplicates", {name: ["a", "a", "a"]}),
            EdgeCase(EdgeCaseCategory.BOUNDARY, f"'{name}' has 1000 elements", {name: list(range(1000))}),
        ]

    @staticmethod
    def _datetime_edge_cases(name: str) -> list[EdgeCase]:
        return [
            EdgeCase(EdgeCaseCategory.TIMEZONE, f"'{name}' at midnight UTC", {name: "2025-01-01T00:00:00Z"}),
            EdgeCase(EdgeCaseCategory.TIMEZONE, f"'{name}' at DST boundary", {name: "2025-03-09T02:30:00-05:00"}),
            EdgeCase(EdgeCaseCategory.BOUNDARY, f"'{name}' is epoch", {name: "1970-01-01T00:00:00Z"}),
            EdgeCase(EdgeCaseCategory.BOUNDARY, f"'{name}' is far future", {name: "2099-12-31T23:59:59Z"}),
            EdgeCase(EdgeCaseCategory.TYPE_MISMATCH, f"'{name}' is invalid date", {name: "not-a-date"}),
        ]

    @staticmethod
    def _cross_param_cases(name: str, params: dict[str, str]) -> list[EdgeCase]:
        """Generate edge cases that involve multiple parameters."""
        cases: list[EdgeCase] = []
        if len(params) >= 2:
            cases.append(EdgeCase(
                category=EdgeCaseCategory.EMPTY_INPUT,
                description=f"All params of '{name}' are None",
                inputs={p: None for p in params},
                severity="high",
            ))
        return cases
