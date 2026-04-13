"""
Policy Loader — Parse, validate and manage workpilot.policy.yaml files.

The policy file is expected at the project root and defines rules that
constrain what AI agents can do.  Rules are loaded once per session and
cached until the file changes (mtime check).

Supports policy inheritance: organisation → project → branch.
Child policies can only *tighten* parent rules, never loosen them.
"""

from __future__ import annotations

import fnmatch
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

POLICY_FILENAME = "workpilot.policy.yaml"

# Supported schema versions
SUPPORTED_VERSIONS = {"1.0"}


class PolicyValidationError(Exception):
    """Raised when a policy file is malformed or contains invalid rules."""


class RuleScope(str, Enum):
    FILE_PATH = "file_path"
    CODE_PATTERN = "code_pattern"
    DIFF_SEMANTIC = "diff_semantic"
    FILE_METRIC = "file_metric"


class RuleAction(str, Enum):
    BLOCK = "block"
    WARN = "warn"
    REQUIRE_APPROVAL = "require_approval"

    @property
    def severity_rank(self) -> int:
        """Higher rank = more restrictive."""
        return {
            RuleAction.WARN: 1,
            RuleAction.REQUIRE_APPROVAL: 2,
            RuleAction.BLOCK: 3,
        }[self]


@dataclass(frozen=True)
class PolicyRule:
    """Single policy rule parsed from the YAML file."""

    id: str
    description: str
    scope: RuleScope
    action: RuleAction
    pattern: str | None = None
    condition: str | None = None
    message: str | None = None
    severity: str | None = None
    approvers: list[str] = field(default_factory=list)

    def matches_file_path(self, file_path: str) -> bool:
        """Return True if the rule's pattern matches *file_path* (glob)."""
        if self.scope != RuleScope.FILE_PATH or self.pattern is None:
            return False
        return fnmatch.fnmatch(file_path, self.pattern)

    def matches_code_pattern(self, content: str) -> bool:
        """Return True if the rule's pattern is found inside *content*."""
        if self.scope != RuleScope.CODE_PATTERN or self.pattern is None:
            return False
        parts = self.pattern.split("|")
        return any(re.search(re.escape(p), content) for p in parts)

    def evaluate_file_metric(self, new_file_lines: int) -> bool:
        """Return True (violation) if the metric condition is breached."""
        if self.scope != RuleScope.FILE_METRIC or self.condition is None:
            return False
        match = re.match(r"new_file_lines\s*>\s*(\d+)", self.condition)
        if match:
            threshold = int(match.group(1))
            return new_file_lines > threshold
        return False


@dataclass
class PolicyFile:
    """Represents a fully loaded and validated policy file."""

    version: str
    rules: list[PolicyRule]
    source_path: Path | None = None

    def get_rule(self, rule_id: str) -> PolicyRule | None:
        """Lookup a rule by id."""
        for r in self.rules:
            if r.id == rule_id:
                return r
        return None


class PolicyLoader:
    """Load and validate ``workpilot.policy.yaml`` files."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, PolicyFile]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, project_dir: Path) -> PolicyFile:
        """Load (or return cached) policy file for *project_dir*.

        Raises ``PolicyValidationError`` on invalid content.
        Returns an *empty* ``PolicyFile`` when no file exists.
        """
        policy_path = Path(project_dir) / POLICY_FILENAME

        if not policy_path.is_file():
            logger.debug("No policy file found at %s", policy_path)
            return PolicyFile(version="1.0", rules=[], source_path=None)

        mtime = policy_path.stat().st_mtime
        cache_key = str(policy_path.resolve())
        if cache_key in self._cache:
            cached_mtime, cached_file = self._cache[cache_key]
            if cached_mtime == mtime:
                return cached_file

        raw = self._read_yaml(policy_path)
        policy_file = self._validate_and_parse(raw, policy_path)
        self._cache[cache_key] = (mtime, policy_file)
        logger.info(
            "Loaded %d policy rules from %s", len(policy_file.rules), policy_path
        )
        return policy_file

    def load_from_dict(self, data: dict[str, Any]) -> PolicyFile:
        """Load a policy file from an already-parsed dict (useful for tests)."""
        return self._validate_and_parse(data, source_path=None)

    def merge(self, parent: PolicyFile, child: PolicyFile) -> PolicyFile:
        """Merge parent + child policies. Child cannot weaken parent rules."""
        merged_rules = list(parent.rules)
        parent_ids = {r.id for r in parent.rules}

        for rule in child.rules:
            if rule.id in parent_ids:
                parent_rule = parent.get_rule(rule.id)
                if parent_rule and rule.action.severity_rank < parent_rule.action.severity_rank:
                    raise PolicyValidationError(
                        f"Child policy cannot weaken rule '{rule.id}': "
                        f"parent={parent_rule.action.value} > child={rule.action.value}"
                    )
                # Replace with (possibly stricter) child rule
                merged_rules = [r for r in merged_rules if r.id != rule.id]
                merged_rules.append(rule)
            else:
                merged_rules.append(rule)

        return PolicyFile(
            version=child.version,
            rules=merged_rules,
            source_path=child.source_path,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _read_yaml(path: Path) -> dict[str, Any]:
        try:
            import yaml  # type: ignore[import-untyped]
        except ImportError:
            raise PolicyValidationError(
                "PyYAML is required to load policy files. "
                "Install it with: pip install pyyaml"
            )
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if not isinstance(data, dict):
            raise PolicyValidationError(
                f"Policy file {path} must contain a YAML mapping at the root level."
            )
        return data

    @staticmethod
    def _validate_and_parse(
        data: dict[str, Any], source_path: Path | None
    ) -> PolicyFile:
        version = str(data.get("version", ""))
        if version not in SUPPORTED_VERSIONS:
            raise PolicyValidationError(
                f"Unsupported policy version '{version}'. "
                f"Supported: {SUPPORTED_VERSIONS}"
            )

        raw_rules = data.get("rules")
        if raw_rules is None:
            raw_rules = []
        if not isinstance(raw_rules, list):
            raise PolicyValidationError("'rules' must be a list.")

        rules: list[PolicyRule] = []
        seen_ids: set[str] = set()

        for idx, raw in enumerate(raw_rules):
            if not isinstance(raw, dict):
                raise PolicyValidationError(
                    f"Rule #{idx} must be a mapping, got {type(raw).__name__}"
                )

            rule_id = raw.get("id")
            if not rule_id or not isinstance(rule_id, str):
                raise PolicyValidationError(f"Rule #{idx} is missing a valid 'id'.")
            if rule_id in seen_ids:
                raise PolicyValidationError(f"Duplicate rule id '{rule_id}'.")
            seen_ids.add(rule_id)

            try:
                scope = RuleScope(raw.get("scope", ""))
            except ValueError:
                raise PolicyValidationError(
                    f"Rule '{rule_id}': invalid scope '{raw.get('scope')}'. "
                    f"Expected one of {[s.value for s in RuleScope]}"
                )

            try:
                action = RuleAction(raw.get("action", ""))
            except ValueError:
                raise PolicyValidationError(
                    f"Rule '{rule_id}': invalid action '{raw.get('action')}'. "
                    f"Expected one of {[a.value for a in RuleAction]}"
                )

            rules.append(
                PolicyRule(
                    id=rule_id,
                    description=raw.get("description", ""),
                    scope=scope,
                    action=action,
                    pattern=raw.get("pattern"),
                    condition=raw.get("condition"),
                    message=raw.get("message"),
                    severity=raw.get("severity"),
                    approvers=raw.get("approvers", []),
                )
            )

        return PolicyFile(version=version, rules=rules, source_path=source_path)
