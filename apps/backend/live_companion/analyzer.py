"""
Incremental Code Analyzer for the Live Companion.

Analyzes file diffs (not entire files) to detect potential bugs,
missing updates, convention mismatches, and refactoring opportunities.
Uses the Claude Agent SDK for AI-powered analysis (provider-agnostic).
"""

import json
import logging
from pathlib import Path

from .types import (
    FileChangeEvent,
    LiveSuggestion,
    SuggestionPriority,
    SuggestionType,
)

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """\
You are a real-time code analysis companion. A developer just modified a file.
Analyze the diff and produce actionable suggestions.

## File Changed
- Path: {file_path}
- Language: {language}
- Change type: {change_type}

## Diff
```
{diff}
```

## Project Context
{project_context}

## Instructions

Analyze this change and look for:
1. **Bugs** — Null pointers, race conditions, off-by-one errors, unhandled exceptions
2. **Missing updates** — Interface changes without implementation updates, schema changes without migration
3. **Security issues** — Injection risks, hardcoded secrets, unsafe operations
4. **Performance** — N+1 queries, unnecessary re-renders, missing memoization
5. **Convention mismatches** — Naming, patterns, or styles that diverge from the codebase
6. **Missing tests** — Modified logic without corresponding test updates
7. **Duplicate code** — Reimplemented existing utilities

Return JSON array of suggestions (empty array if nothing noteworthy):
```json
[
  {{
    "suggestion_type": "bug_detection|duplicate_code|missing_update|contract_violation|performance_issue|security_issue|missing_test|refactor_opportunity|import_suggestion|convention_mismatch|general",
    "priority": "critical|high|medium|low|info",
    "title": "Short title",
    "description": "What the issue is and why it matters",
    "line_start": 0,
    "line_end": 0,
    "code_fix": "Optional fix snippet",
    "related_files": ["paths that may need changes too"],
    "confidence": 0.0-1.0
  }}
]
```

Only include suggestions with confidence >= 0.5. Be specific and actionable.
Keep it concise — the developer will see these in real-time.
"""


class IncrementalAnalyzer:
    """Analyzes file diffs incrementally to generate real-time suggestions."""

    def __init__(
        self,
        project_dir: str | Path,
        model: str | None = None,
        thinking_level: str | None = None,
    ):
        self.project_dir = Path(project_dir)
        self.model = model or "sonnet"
        self.thinking_level = thinking_level or "low"

    async def analyze_change(
        self,
        event: FileChangeEvent,
        project_context: str = "",
    ) -> list[LiveSuggestion]:
        """Analyze a file change and return suggestions."""
        if not event.diff and event.change_type != "created":
            return []

        prompt = ANALYSIS_PROMPT.format(
            file_path=event.file_path,
            language=event.language or self._detect_language(event.file_path),
            change_type=event.change_type,
            diff=event.diff[:4000],  # Truncate large diffs
            project_context=project_context or "No additional context available.",
        )

        try:
            response = await self._call_ai(prompt)
            return self._parse_suggestions(response, event.file_path)
        except Exception as e:
            logger.warning(f"Analysis failed for {event.file_path}: {e}")
            return []

    async def _call_ai(self, prompt: str) -> str:
        """Call the AI model via Claude Agent SDK (provider-agnostic)."""
        try:
            from core.client import create_client
            from core.session import run_agent_session
            from phase_config import get_thinking_budget, resolve_model_id

            model_id = resolve_model_id(self.model)
            thinking_budget = get_thinking_budget(self.thinking_level)

            client = create_client(
                project_dir=str(self.project_dir),
                model=model_id,
                agent_type="live_companion_analyzer",
                max_thinking_tokens=thinking_budget,
            )

            async with client:
                status, response = await run_agent_session(client, prompt)

            return response or ""

        except Exception as e:
            logger.error(f"AI call failed: {e}")
            return "[]"

    def _parse_suggestions(self, response: str, file_path: str) -> list[LiveSuggestion]:
        """Parse AI response into LiveSuggestion objects."""
        suggestions = []
        parsed = self._extract_json_array(response)
        if not parsed:
            return []

        for item in parsed:
            try:
                suggestion = LiveSuggestion(
                    suggestion_id=LiveSuggestion.generate_id(),
                    suggestion_type=SuggestionType(
                        item.get("suggestion_type", "general")
                    ),
                    priority=SuggestionPriority(item.get("priority", "medium")),
                    title=item.get("title", ""),
                    description=item.get("description", ""),
                    file_path=file_path,
                    line_start=int(item.get("line_start", 0)),
                    line_end=int(item.get("line_end", 0)),
                    code_fix=item.get("code_fix", ""),
                    related_files=item.get("related_files", []),
                    confidence=float(item.get("confidence", 0.5)),
                )
                if suggestion.confidence >= 0.5:
                    suggestions.append(suggestion)
            except (ValueError, KeyError) as e:
                logger.warning(f"Failed to parse suggestion: {e}")

        return suggestions

    def _extract_json_array(self, text: str) -> list[dict] | None:
        """Extract a JSON array from AI response."""
        if not text:
            return None

        # Try direct parse
        try:
            result = json.loads(text)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

        # Try extracting from code blocks
        for marker in ("```json", "```"):
            if marker in text:
                start = text.index(marker) + len(marker)
                end = text.find("```", start)
                if end > start:
                    try:
                        result = json.loads(text[start:end].strip())
                        if isinstance(result, list):
                            return result
                    except json.JSONDecodeError:
                        pass

        # Try finding first [ ... last ]
        first = text.find("[")
        last = text.rfind("]")
        if first >= 0 and last > first:
            try:
                result = json.loads(text[first : last + 1])
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass

        return None

    def _detect_language(self, file_path: str) -> str:
        """Detect language from file extension."""
        ext_map = {
            ".ts": "TypeScript",
            ".tsx": "TypeScript (React)",
            ".js": "JavaScript",
            ".jsx": "JavaScript (React)",
            ".py": "Python",
            ".rs": "Rust",
            ".go": "Go",
            ".java": "Java",
            ".cs": "C#",
            ".rb": "Ruby",
            ".php": "PHP",
            ".vue": "Vue",
            ".svelte": "Svelte",
            ".swift": "Swift",
            ".kt": "Kotlin",
        }
        ext = Path(file_path).suffix.lower()
        return ext_map.get(ext, "Unknown")
