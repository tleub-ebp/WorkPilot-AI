"""
Migration Guide Generator — Produce human-readable migration guides
from breaking API contract changes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .breaking_change_detector import ChangeCategory, ContractChange, ContractDiff

logger = logging.getLogger(__name__)


@dataclass
class MigrationGuide:
    """A generated migration guide document."""

    title: str
    markdown: str
    breaking_changes: int
    total_changes: int


class MigrationGuideGenerator:
    """Generate migration guides from contract diffs.

    Usage::

        gen = MigrationGuideGenerator()
        guide = gen.generate(diff, from_version="1.0", to_version="2.0")
        print(guide.markdown)
    """

    def generate(
        self,
        diff: ContractDiff,
        from_version: str = "",
        to_version: str = "",
        api_name: str = "API",
    ) -> MigrationGuide:
        """Generate a Markdown migration guide."""
        title = f"Migration Guide: {api_name}"
        if from_version or to_version:
            title += f" ({from_version} → {to_version})"

        sections: list[str] = [f"# {title}\n"]
        sections.append(f"**Summary:** {diff.summary}\n")

        # Breaking changes
        breaking = [c for c in diff.changes if c.category == ChangeCategory.BREAKING]
        if breaking:
            sections.append("## 🔴 Breaking Changes\n")
            sections.append(
                "These changes **require action** from all API consumers.\n"
            )
            for change in breaking:
                sections.append(self._format_change(change))
                sections.append(self._suggest_action(change))

        # Potentially breaking
        potential = [
            c for c in diff.changes if c.category == ChangeCategory.POTENTIALLY_BREAKING
        ]
        if potential:
            sections.append("\n## 🟡 Potentially Breaking Changes\n")
            sections.append("Review these changes — they may affect some consumers.\n")
            for change in potential:
                sections.append(self._format_change(change))

        # Non-breaking
        non_breaking = [
            c for c in diff.changes if c.category == ChangeCategory.NON_BREAKING
        ]
        if non_breaking:
            sections.append("\n## 🟢 Non-Breaking Changes\n")
            sections.append("These changes are backward-compatible.\n")
            for change in non_breaking:
                sections.append(self._format_change(change))

        markdown = "\n".join(sections)
        return MigrationGuide(
            title=title,
            markdown=markdown,
            breaking_changes=len(breaking),
            total_changes=len(diff.changes),
        )

    @staticmethod
    def _format_change(change: ContractChange) -> str:
        line = f"- **`{change.path}`** — {change.description}"
        if change.old_value and change.new_value:
            line += f" (`{change.old_value}` → `{change.new_value}`)"
        return line

    @staticmethod
    def _suggest_action(change: ContractChange) -> str:
        """Suggest migration action for breaking changes."""
        suggestions = {
            "endpoint_removed": "  - 🔧 **Action:** Update client code to remove calls to this endpoint. Check for alternatives.",
            "field_removed": "  - 🔧 **Action:** Remove references to this field in your client code.",
            "field_type_changed": "  - 🔧 **Action:** Update your type definitions and any validation/parsing logic.",
            "parameter_added_required": "  - 🔧 **Action:** Add the required parameter to all requests to this endpoint.",
            "parameter_removed": "  - 🔧 **Action:** Remove this parameter from your requests.",
            "type_removed": "  - 🔧 **Action:** Replace usages of this type with the new equivalent.",
            "field_required_added": "  - 🔧 **Action:** Ensure this field is always provided in your requests.",
            "response_status_removed": "  - 🔧 **Action:** Update error handling to no longer expect this status code.",
        }
        return suggestions.get(
            change.change_type.value,
            "  - 🔧 **Action:** Review and update client code.",
        )
