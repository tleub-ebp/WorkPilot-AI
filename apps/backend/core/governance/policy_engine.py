"""
Policy Engine — Evaluate agent actions against loaded policy rules.

The engine sits between an agent's *intent* (planned tool call) and its
*execution* (actual tool call dispatch).  Every action is evaluated against
all rules before it is allowed to proceed.

Three verdicts are possible:
  - ALLOW  – no rule triggered, action proceeds.
  - WARN   – at least one rule triggered a warning; action proceeds but the
              violation is logged and surfaced in the UI.
  - BLOCK  – at least one rule blocks the action; the agent receives the
              rule's message and must find an alternative.
  - REQUIRE_APPROVAL – action is suspended until a human approves it.

When multiple rules fire, the most restrictive verdict wins (principle of
least privilege).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from .policy_loader import (
    PolicyFile,
    PolicyLoader,
    PolicyRule,
    PolicyValidationError,
    RuleAction,
    RuleScope,
)

logger = logging.getLogger(__name__)


class PolicyVerdict(str, Enum):
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"
    REQUIRE_APPROVAL = "require_approval"


@dataclass
class PolicyViolation:
    """A single rule violation produced during evaluation."""

    rule: PolicyRule
    verdict: PolicyVerdict
    details: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class PolicyEvaluation:
    """Result of evaluating an action against the full policy set."""

    verdict: PolicyVerdict
    violations: list[PolicyViolation] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)

    @property
    def is_allowed(self) -> bool:
        return self.verdict in (PolicyVerdict.ALLOW, PolicyVerdict.WARN)

    @property
    def is_blocked(self) -> bool:
        return self.verdict == PolicyVerdict.BLOCK

    @property
    def requires_approval(self) -> bool:
        return self.verdict == PolicyVerdict.REQUIRE_APPROVAL


@dataclass
class AgentAction:
    """Describes an action that an agent wants to perform."""

    tool_name: str
    file_path: str | None = None
    file_content: str | None = None
    diff_added: list[str] = field(default_factory=list)
    diff_removed: list[str] = field(default_factory=list)
    new_file_lines: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class PolicyEngine:
    """Evaluate agent actions against project policy rules.

    Usage::

        engine = PolicyEngine()
        engine.load_policies(project_dir)
        evaluation = engine.evaluate(action)
        if evaluation.is_blocked:
            # reject the action, return messages to agent
            ...
    """

    def __init__(self, loader: PolicyLoader | None = None) -> None:
        self._loader = loader or PolicyLoader()
        self._policy: PolicyFile | None = None
        self._violation_log: list[PolicyViolation] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_policies(self, project_dir: Path) -> PolicyFile:
        """Load policies for the given project. Raises on invalid file."""
        self._policy = self._loader.load(project_dir)
        return self._policy

    def load_from_dict(self, data: dict[str, Any]) -> PolicyFile:
        """Load policies from a dict (convenience for tests)."""
        self._policy = self._loader.load_from_dict(data)
        return self._policy

    @property
    def policy(self) -> PolicyFile | None:
        return self._policy

    @property
    def violation_log(self) -> list[PolicyViolation]:
        return list(self._violation_log)

    def evaluate(self, action: AgentAction) -> PolicyEvaluation:
        """Evaluate *action* against all loaded rules.

        Returns a ``PolicyEvaluation`` whose ``verdict`` is the most
        restrictive triggered rule (block > require_approval > warn > allow).
        """
        if self._policy is None or not self._policy.rules:
            return PolicyEvaluation(verdict=PolicyVerdict.ALLOW)

        violations: list[PolicyViolation] = []

        for rule in self._policy.rules:
            violation = self._check_rule(rule, action)
            if violation is not None:
                violations.append(violation)

        if not violations:
            return PolicyEvaluation(verdict=PolicyVerdict.ALLOW)

        # Determine overall verdict (most restrictive wins)
        verdict = self._most_restrictive(violations)
        messages = [
            v.rule.message or v.rule.description or f"Rule {v.rule.id} violated"
            for v in violations
        ]

        evaluation = PolicyEvaluation(
            verdict=verdict,
            violations=violations,
            messages=messages,
        )

        # Persist to log
        self._violation_log.extend(violations)

        logger.info(
            "Policy evaluation: %s (%d violations)",
            verdict.value,
            len(violations),
        )
        return evaluation

    def dry_run(self, actions: list[AgentAction]) -> list[PolicyEvaluation]:
        """Evaluate multiple actions without recording violations."""
        results = []
        for action in actions:
            if self._policy is None or not self._policy.rules:
                results.append(PolicyEvaluation(verdict=PolicyVerdict.ALLOW))
                continue

            violations: list[PolicyViolation] = []
            for rule in self._policy.rules:
                violation = self._check_rule(rule, action)
                if violation is not None:
                    violations.append(violation)

            if not violations:
                results.append(PolicyEvaluation(verdict=PolicyVerdict.ALLOW))
            else:
                verdict = self._most_restrictive(violations)
                messages = [
                    v.rule.message or v.rule.description
                    for v in violations
                ]
                results.append(
                    PolicyEvaluation(
                        verdict=verdict, violations=violations, messages=messages
                    )
                )
        return results

    def get_violation_stats(self) -> dict[str, int]:
        """Return counts of violations by action type."""
        stats: dict[str, int] = {"block": 0, "warn": 0, "require_approval": 0}
        for v in self._violation_log:
            key = v.verdict.value
            if key in stats:
                stats[key] += 1
        return stats

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _check_rule(
        self, rule: PolicyRule, action: AgentAction
    ) -> PolicyViolation | None:
        """Check a single rule against the action. Return violation or None."""

        if rule.scope == RuleScope.FILE_PATH:
            if action.file_path and rule.matches_file_path(action.file_path):
                # If there's an additional condition, evaluate it
                if rule.condition:
                    if not self._evaluate_condition(rule.condition, action):
                        return None
                return PolicyViolation(
                    rule=rule,
                    verdict=self._action_to_verdict(rule.action),
                    details=f"File path matches pattern: {rule.pattern}",
                )

        elif rule.scope == RuleScope.CODE_PATTERN:
            content = action.file_content or ""
            # Also check added diff lines
            if action.diff_added:
                content += "\n".join(action.diff_added)
            if rule.matches_code_pattern(content):
                return PolicyViolation(
                    rule=rule,
                    verdict=self._action_to_verdict(rule.action),
                    details=f"Code pattern found: {rule.pattern}",
                )

        elif rule.scope == RuleScope.DIFF_SEMANTIC:
            if self._check_diff_semantic(rule, action):
                return PolicyViolation(
                    rule=rule,
                    verdict=self._action_to_verdict(rule.action),
                    details=f"Semantic diff violation: {rule.condition}",
                )

        elif rule.scope == RuleScope.FILE_METRIC:
            if rule.evaluate_file_metric(action.new_file_lines):
                return PolicyViolation(
                    rule=rule,
                    verdict=self._action_to_verdict(rule.action),
                    details=f"Metric violation: {rule.condition} (actual={action.new_file_lines})",
                )

        return None

    @staticmethod
    def _check_diff_semantic(rule: PolicyRule, action: AgentAction) -> bool:
        """Basic semantic diff check — looks for deleted test definitions."""
        condition = rule.condition or ""

        if "deleted_lines contain test function definition" in condition:
            test_pattern = re.compile(
                r"^\s*(def test_|class Test|it\(|describe\(|test\()", re.MULTILINE
            )
            for line in action.diff_removed:
                if test_pattern.search(line):
                    return True

        return False

    @staticmethod
    def _evaluate_condition(condition: str, action: AgentAction) -> bool:
        """Evaluate a simple condition string against the action context."""
        if "diff adds new dependency" in condition:
            for line in action.diff_added:
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and not stripped.startswith("//"):
                    return True
        return False

    @staticmethod
    def _action_to_verdict(action: RuleAction) -> PolicyVerdict:
        return {
            RuleAction.BLOCK: PolicyVerdict.BLOCK,
            RuleAction.WARN: PolicyVerdict.WARN,
            RuleAction.REQUIRE_APPROVAL: PolicyVerdict.REQUIRE_APPROVAL,
        }[action]

    @staticmethod
    def _most_restrictive(violations: list[PolicyViolation]) -> PolicyVerdict:
        """Return the most restrictive verdict among violations."""
        priority = {
            PolicyVerdict.WARN: 1,
            PolicyVerdict.REQUIRE_APPROVAL: 2,
            PolicyVerdict.BLOCK: 3,
        }
        best = PolicyVerdict.WARN
        for v in violations:
            if priority.get(v.verdict, 0) > priority.get(best, 0):
                best = v.verdict
        return best
