"""
User-defined Agent Guardrails
==============================

Lets teams encode their own policies that agents must respect, evaluated on
every Write/Edit/Bash attempt.

Rules live in ``<project>/.workpilot/guardrails.yaml`` (or .json as fallback).
Schema::

    version: 1
    rules:
      - id: no-migrations
        description: Block writes to migrations/ unless human approves
        when:
          tool: [Write, Edit]
          path_prefix: migrations/
        action: require_approval

      - id: max-file-size
        description: Reject writes longer than 500 lines
        when:
          tool: [Write, Edit]
          content_max_lines: 500
        action: deny

      - id: no-gpl
        description: Reject installation of GPL-licensed packages
        when:
          tool: Bash
          command_pattern: "(pnpm|npm|pip) install .*(gpl|agpl)"
        action: deny

      - id: require-tests
        description: Warn when new Python function added without matching test
        when:
          tool: Write
          path_regex: "\\\\.py$"
          content_regex: "^def [a-z_]+\\\\("
        action: warn

Actions:
  - ``allow``  — explicit pass (used to whitelist exceptions)
  - ``warn``   — let it through but log a structured event
  - ``deny``   — block and surface the rule id/description to the agent
  - ``require_approval`` — block with a message asking for human approval

The evaluator returns a ``GuardrailDecision`` that callers convert to the SDK
hook response shape.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class GuardrailAction(str, Enum):
    ALLOW = "allow"
    WARN = "warn"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


@dataclass
class GuardrailRule:
    """A single user-defined rule."""

    id: str
    description: str
    action: GuardrailAction
    tools: list[str] = field(default_factory=list)
    path_prefix: str | None = None
    path_regex: re.Pattern[str] | None = None
    content_regex: re.Pattern[str] | None = None
    command_pattern: re.Pattern[str] | None = None
    content_max_lines: int | None = None
    content_max_bytes: int | None = None
    forbidden_strings: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> GuardrailRule:
        when = raw.get("when", {}) or {}
        tools = when.get("tool", [])
        if isinstance(tools, str):
            tools = [tools]

        def _compile(pattern: str | None) -> re.Pattern[str] | None:
            if not pattern:
                return None
            try:
                return re.compile(pattern)
            except re.error as exc:
                logger.warning("Invalid regex in rule %s: %s", raw.get("id"), exc)
                return None

        action_raw = raw.get("action", "deny")
        try:
            action = GuardrailAction(action_raw)
        except ValueError:
            logger.warning(
                "Unknown action '%s' in rule %s, defaulting to deny",
                action_raw,
                raw.get("id"),
            )
            action = GuardrailAction.DENY

        return cls(
            id=str(raw.get("id", "unnamed")),
            description=str(raw.get("description", "")),
            action=action,
            tools=[str(t) for t in tools],
            path_prefix=when.get("path_prefix"),
            path_regex=_compile(when.get("path_regex")),
            content_regex=_compile(when.get("content_regex")),
            command_pattern=_compile(when.get("command_pattern")),
            content_max_lines=when.get("content_max_lines"),
            content_max_bytes=when.get("content_max_bytes"),
            forbidden_strings=list(when.get("forbidden_strings", []) or []),
        )

    def matches_tool(self, tool_name: str) -> bool:
        return not self.tools or tool_name in self.tools


@dataclass
class GuardrailDecision:
    """Outcome of evaluating all rules against one tool call."""

    action: GuardrailAction
    triggered: list[GuardrailRule] = field(default_factory=list)
    message: str = ""

    def should_block(self) -> bool:
        return self.action in (GuardrailAction.DENY, GuardrailAction.REQUIRE_APPROVAL)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def _load_yaml_or_json(path: Path) -> dict[str, Any] | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.debug("Could not read guardrails file %s: %s", path, exc)
        return None

    # Try YAML first (optional dependency), fall back to JSON.
    try:
        import yaml  # type: ignore[import-untyped]

        parsed = yaml.safe_load(text)
        return parsed if isinstance(parsed, dict) else None
    except ImportError:
        pass
    except Exception as exc:
        logger.warning("YAML parse error in %s: %s", path, exc)
        return None

    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError as exc:
        logger.warning("JSON parse error in %s: %s", path, exc)
        return None


def load_guardrails(project_root: Path) -> list[GuardrailRule]:
    """Load the list of user-defined rules for ``project_root``.

    Searches ``.workpilot/guardrails.yaml`` then ``.workpilot/guardrails.json``.
    Returns an empty list when no config is found.
    """
    for filename in ("guardrails.yaml", "guardrails.yml", "guardrails.json"):
        path = project_root / ".workpilot" / filename
        if not path.exists():
            continue
        data = _load_yaml_or_json(path)
        if not data:
            continue
        rules_raw = data.get("rules", []) or []
        rules = [GuardrailRule.from_dict(r) for r in rules_raw if isinstance(r, dict)]
        logger.info("Loaded %d guardrail rule(s) from %s", len(rules), path)
        return rules
    return []


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------


def _get_path(tool_input: dict[str, Any]) -> str:
    return str(tool_input.get("file_path") or tool_input.get("path") or "")


def _get_content(tool_input: dict[str, Any]) -> str:
    return str(
        tool_input.get("content")
        or tool_input.get("new_string")
        or tool_input.get("new_str")
        or ""
    )


def _rule_matches(
    rule: GuardrailRule, tool_name: str, tool_input: dict[str, Any]
) -> bool:
    if not rule.matches_tool(tool_name):
        return False

    path = _get_path(tool_input)
    if rule.path_prefix and not path.startswith(rule.path_prefix):
        return False
    if rule.path_regex and not rule.path_regex.search(path):
        return False

    if tool_name == "Bash":
        command = str(tool_input.get("command", ""))
        if rule.command_pattern and not rule.command_pattern.search(command):
            return False
    else:
        content = _get_content(tool_input)
        if rule.content_regex and not rule.content_regex.search(content):
            return False
        if rule.content_max_lines is not None:
            if content.count("\n") + 1 <= rule.content_max_lines:
                return False
        if rule.content_max_bytes is not None:
            if len(content.encode("utf-8")) <= rule.content_max_bytes:
                return False
        if rule.forbidden_strings:
            if not any(needle in content for needle in rule.forbidden_strings):
                return False

    return True


_ACTION_PRIORITY = {
    GuardrailAction.ALLOW: 0,
    GuardrailAction.WARN: 1,
    GuardrailAction.REQUIRE_APPROVAL: 2,
    GuardrailAction.DENY: 3,
}


def evaluate_rules(
    rules: list[GuardrailRule],
    tool_name: str,
    tool_input: dict[str, Any],
) -> GuardrailDecision:
    """Evaluate all rules and return the strictest decision."""
    triggered: list[GuardrailRule] = [
        r for r in rules if _rule_matches(r, tool_name, tool_input)
    ]
    if not triggered:
        return GuardrailDecision(action=GuardrailAction.ALLOW)

    strongest = max(triggered, key=lambda r: _ACTION_PRIORITY[r.action])
    parts = [f"[{r.id}] {r.description or '(no description)'}" for r in triggered]
    return GuardrailDecision(
        action=strongest.action,
        triggered=triggered,
        message="Guardrail triggered:\n  " + "\n  ".join(parts),
    )


# ---------------------------------------------------------------------------
# SDK hook integration
# ---------------------------------------------------------------------------


async def guardrails_hook(
    input_data: dict[str, Any],
    tool_use_id: str | None = None,
    context: Any | None = None,
    *,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Pre-tool-use hook that enforces user-defined guardrails.

    Returns an empty dict when the call is allowed or only triggers warnings.
    Returns a ``hookSpecificOutput`` with ``permissionDecision: deny`` when a
    rule blocks the call.
    """
    tool_name = input_data.get("tool_name")
    tool_input = input_data.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return {}

    root = Path(project_root) if project_root else Path.cwd()
    rules = load_guardrails(root)
    if not rules:
        return {}

    decision = evaluate_rules(rules, str(tool_name or ""), tool_input)

    if decision.action == GuardrailAction.WARN:
        logger.warning("Guardrail WARN: %s", decision.message)
        return {}

    if decision.should_block():
        reason = decision.message
        if decision.action == GuardrailAction.REQUIRE_APPROVAL:
            reason = "Human approval required before this action.\n" + reason
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }

    return {}
