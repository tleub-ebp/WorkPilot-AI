"""
Deep Context Provider
=====================

Enriches PR reviews with deep codebase context by integrating:
- Context Builder: project patterns, conventions, related code
- Graphiti Memory: historical insights, past bugs, regression patterns
- Architecture Enforcement: architectural rule validation

This provider is called during PR review to give the AI reviewer
the knowledge of a senior dev who knows the entire project.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path

try:
    from .io_utils import safe_print
except (ImportError, ValueError, SystemError):
    from services.io_utils import safe_print


@dataclass
class DeepContext:
    """Deep codebase context for enriched PR reviews."""

    # Project conventions and patterns
    project_patterns: dict[str, str] = field(default_factory=dict)
    project_conventions: list[str] = field(default_factory=list)
    related_code: list[dict] = field(default_factory=list)

    # Historical insights from memory
    historical_insights: list[dict] = field(default_factory=list)
    past_bugs_in_area: list[dict] = field(default_factory=list)
    regression_risks: list[str] = field(default_factory=list)

    # Architecture analysis
    architecture_style: str = ""
    architecture_layers: list[dict] = field(default_factory=list)
    architecture_violations: list[dict] = field(default_factory=list)

    # Metadata
    gathering_duration_ms: int = 0
    context_available: bool = False

    def to_dict(self) -> dict:
        return {
            "project_patterns": self.project_patterns,
            "project_conventions": self.project_conventions,
            "related_code": self.related_code,
            "historical_insights": self.historical_insights,
            "past_bugs_in_area": self.past_bugs_in_area,
            "regression_risks": self.regression_risks,
            "architecture_style": self.architecture_style,
            "architecture_layers": self.architecture_layers,
            "architecture_violations": self.architecture_violations,
            "gathering_duration_ms": self.gathering_duration_ms,
            "context_available": self.context_available,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DeepContext:
        return cls(
            project_patterns=data.get("project_patterns", {}),
            project_conventions=data.get("project_conventions", []),
            related_code=data.get("related_code", []),
            historical_insights=data.get("historical_insights", []),
            past_bugs_in_area=data.get("past_bugs_in_area", []),
            regression_risks=data.get("regression_risks", []),
            architecture_style=data.get("architecture_style", ""),
            architecture_layers=data.get("architecture_layers", []),
            architecture_violations=data.get("architecture_violations", []),
            gathering_duration_ms=data.get("gathering_duration_ms", 0),
            context_available=data.get("context_available", False),
        )

    def to_prompt_section(self) -> str:
        """Format deep context as a markdown section for injection into prompts."""
        if not self.context_available:
            return ""

        sections = []
        sections.append("## Deep Codebase Context")
        sections.append("")
        sections.append(
            "The following context was gathered from the project's codebase, "
            "architecture rules, and historical memory. Use this to review the PR "
            "like a senior developer who deeply knows the project."
        )
        sections.append("")

        # Architecture
        if self.architecture_style or self.architecture_layers:
            sections.append("### Project Architecture")
            if self.architecture_style:
                sections.append(f"**Style:** {self.architecture_style}")
            if self.architecture_layers:
                sections.append("**Layers:**")
                for layer in self.architecture_layers:
                    name = layer.get("name", "unknown")
                    patterns = ", ".join(layer.get("patterns", [])[:3])
                    allowed = ", ".join(layer.get("allowed_imports", [])[:3])
                    sections.append(f"- **{name}** ({patterns})")
                    if allowed:
                        sections.append(f"  - Can import from: {allowed}")
            sections.append("")

        if self.architecture_violations:
            sections.append("### Architecture Violations Detected")
            sections.append(
                "The following violations were found by static analysis. "
                "Verify these in your review and include them in findings."
            )
            for v in self.architecture_violations[:5]:
                sections.append(
                    f"- **{v.get('type', 'violation')}** in `{v.get('file', '?')}`: "
                    f"{v.get('description', '')}"
                )
                if v.get("suggestion"):
                    sections.append(f"  - Fix: {v['suggestion']}")
            sections.append("")

        # Project patterns and conventions
        if self.project_patterns:
            sections.append("### Established Code Patterns")
            sections.append(
                "These patterns are used consistently in this codebase. "
                "Flag deviations in the PR."
            )
            for key, snippet in list(self.project_patterns.items())[:5]:
                sections.append(f"**{key}:**")
                # Truncate long snippets
                truncated = snippet[:300] + "..." if len(snippet) > 300 else snippet
                sections.append(f"```\n{truncated}\n```")
            sections.append("")

        if self.project_conventions:
            sections.append("### Project Conventions")
            for conv in self.project_conventions[:10]:
                sections.append(f"- {conv}")
            sections.append("")

        # Related code
        if self.related_code:
            sections.append("### Related Code in the Codebase")
            sections.append(
                "These files are related to the PR's changes. "
                "Check for consistency and potential impact."
            )
            for item in self.related_code[:8]:
                path = item.get("path", "unknown")
                reason = item.get("reason", "")
                sections.append(f"- `{path}` — {reason}")
            sections.append("")

        # Historical insights
        if self.historical_insights:
            sections.append("### Historical Insights (from project memory)")
            sections.append(
                "Past learnings relevant to this PR's area. Watch for similar issues."
            )
            for hint in self.historical_insights[:5]:
                if isinstance(hint, dict):
                    fact = hint.get("fact", hint.get("content", str(hint)))
                    sections.append(f"- {fact}")
                else:
                    sections.append(f"- {hint}")
            sections.append("")

        if self.past_bugs_in_area:
            sections.append("### Past Bugs in This Area")
            sections.append(
                "These bugs were previously found in similar code. "
                "Check if this PR could reintroduce them."
            )
            for bug in self.past_bugs_in_area[:5]:
                if isinstance(bug, dict):
                    desc = bug.get("description", bug.get("fact", str(bug)))
                    sections.append(f"- {desc}")
                else:
                    sections.append(f"- {bug}")
            sections.append("")

        if self.regression_risks:
            sections.append("### Regression Risks")
            for risk in self.regression_risks[:5]:
                sections.append(f"- {risk}")
            sections.append("")

        return "\n".join(sections)


class DeepContextProvider:
    """
    Gathers deep codebase context for PR reviews.

    Integrates:
    1. Context Builder — finds related code, patterns, conventions
    2. Graphiti Memory — retrieves historical insights and past bugs
    3. Architecture Enforcement — checks architectural rules
    """

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir).resolve()

    async def gather_deep_context(
        self,
        pr_title: str,
        pr_description: str,
        changed_file_paths: list[str],
        timeout: float = 30.0,
    ) -> DeepContext:
        """
        Gather deep context for a PR review.

        Runs all context gathering in parallel with a timeout to avoid
        slowing down the review pipeline.

        Args:
            pr_title: Title of the pull request
            pr_description: Description/body of the PR
            changed_file_paths: List of file paths changed in the PR
            timeout: Maximum time for context gathering (seconds)

        Returns:
            DeepContext with all available information
        """
        start_time = time.time()
        context = DeepContext()

        # Build a search query from PR title + file paths
        search_query = self._build_search_query(
            pr_title, pr_description, changed_file_paths
        )

        safe_print(
            f"[Deep Context] Gathering deep codebase context for: {search_query[:80]}...",
            flush=True,
        )

        try:
            # Run all providers in parallel with overall timeout
            results = await asyncio.wait_for(
                asyncio.gather(
                    self._gather_project_context(search_query, changed_file_paths),
                    self._gather_memory_context(search_query, changed_file_paths),
                    self._gather_architecture_context(changed_file_paths),
                    return_exceptions=True,
                ),
                timeout=timeout,
            )

            # Process project context
            if isinstance(results[0], dict):
                context.project_patterns = results[0].get("patterns", {})
                context.project_conventions = results[0].get("conventions", [])
                context.related_code = results[0].get("related_code", [])

            # Process memory context
            if isinstance(results[1], dict):
                context.historical_insights = results[1].get("insights", [])
                context.past_bugs_in_area = results[1].get("past_bugs", [])
                context.regression_risks = results[1].get("regression_risks", [])

            # Process architecture context
            if isinstance(results[2], dict):
                context.architecture_style = results[2].get("style", "")
                context.architecture_layers = results[2].get("layers", [])
                context.architecture_violations = results[2].get("violations", [])

            # Log any errors from parallel execution
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    provider_names = ["project_context", "memory", "architecture"]
                    safe_print(
                        f"[Deep Context] {provider_names[i]} failed (non-blocking): {result}",
                        flush=True,
                    )

            context.context_available = True

        except asyncio.TimeoutError:
            safe_print(
                f"[Deep Context] Timed out after {timeout}s, using partial results",
                flush=True,
            )
            context.context_available = bool(
                context.project_patterns
                or context.historical_insights
                or context.architecture_style
            )
        except Exception as e:
            safe_print(
                f"[Deep Context] Failed to gather context (non-blocking): {e}",
                flush=True,
            )

        duration_ms = int((time.time() - start_time) * 1000)
        context.gathering_duration_ms = duration_ms
        safe_print(
            f"[Deep Context] Context gathered in {duration_ms}ms "
            f"(patterns={len(context.project_patterns)}, "
            f"insights={len(context.historical_insights)}, "
            f"arch_violations={len(context.architecture_violations)})",
            flush=True,
        )

        return context

    def _build_search_query(
        self,
        pr_title: str,
        pr_description: str,
        changed_files: list[str],
    ) -> str:
        """Build a search query from PR metadata."""
        # Combine title and relevant file areas
        parts = [pr_title]

        # Add directory hints from changed files
        dirs_seen = set()
        for path in changed_files[:10]:
            dir_name = "/".join(path.split("/")[:-1])
            if dir_name and dir_name not in dirs_seen:
                dirs_seen.add(dir_name)
                parts.append(dir_name)

        # Add first 200 chars of description
        if pr_description:
            parts.append(pr_description[:200])

        return " ".join(parts)

    async def _gather_project_context(
        self,
        search_query: str,
        changed_files: list[str],
    ) -> dict:
        """Gather project patterns and conventions using the Context Builder."""
        try:
            import sys

            backend_dir = self.project_dir / "apps" / "backend"
            if backend_dir.exists():
                sys.path.insert(0, str(backend_dir))

            from context.builder import ContextBuilder

            builder = ContextBuilder(self.project_dir)
            task_context = builder.build_context(
                task=search_query,
                include_graph_hints=False,  # We handle graph hints separately
            )

            # Extract patterns
            patterns = task_context.patterns_discovered or {}

            # Build conventions from service contexts
            conventions = []
            for svc_name, svc_ctx in task_context.service_contexts.items():
                if svc_ctx.get("framework"):
                    conventions.append(
                        f"Service '{svc_name}' uses {svc_ctx['framework']} framework"
                    )
                if svc_ctx.get("language"):
                    conventions.append(
                        f"Service '{svc_name}' is written in {svc_ctx['language']}"
                    )

            # Build related code list
            related_code = []
            for f in task_context.files_to_reference[:10]:
                path = (
                    f.get("path", "") if isinstance(f, dict) else getattr(f, "path", "")
                )
                reason = (
                    f.get("reason", "")
                    if isinstance(f, dict)
                    else getattr(f, "reason", "")
                )
                if path:
                    related_code.append({"path": path, "reason": reason})

            return {
                "patterns": patterns,
                "conventions": conventions,
                "related_code": related_code,
            }

        except Exception as e:
            safe_print(
                f"[Deep Context] Project context gathering failed: {e}", flush=True
            )
            return {"patterns": {}, "conventions": [], "related_code": []}

    async def _gather_memory_context(
        self,
        search_query: str,
        changed_files: list[str],
    ) -> dict:
        """Query Graphiti memory for historical insights."""
        try:
            from context.graphiti_integration import (
                fetch_graph_hints,
                is_graphiti_enabled,
            )

            if not is_graphiti_enabled():
                return {"insights": [], "past_bugs": [], "regression_risks": []}

            # Query for general insights about this area
            hints = await fetch_graph_hints(
                query=search_query,
                project_id=str(self.project_dir),
                max_results=10,
            )

            # Categorize hints
            insights = []
            past_bugs = []
            regression_risks = []

            for hint in hints:
                if isinstance(hint, dict):
                    episode_type = hint.get("type", hint.get("episode_type", ""))
                    fact = hint.get("fact", hint.get("content", str(hint)))

                    if episode_type in ("gotcha", "qa_result"):
                        past_bugs.append(hint)
                    elif (
                        "regression" in str(fact).lower()
                        or "broke" in str(fact).lower()
                    ):
                        regression_risks.append(fact)
                    else:
                        insights.append(hint)
                else:
                    insights.append({"fact": str(hint)})

            # Build regression risks from changed file patterns
            file_dirs = set()
            for path in changed_files:
                parts = path.split("/")
                if len(parts) > 1:
                    file_dirs.add("/".join(parts[:2]))

            for dir_path in file_dirs:
                # Query for bugs specifically in this directory
                dir_hints = await fetch_graph_hints(
                    query=f"bugs issues problems in {dir_path}",
                    project_id=str(self.project_dir),
                    max_results=3,
                )
                for hint in dir_hints:
                    if isinstance(hint, dict):
                        fact = hint.get("fact", hint.get("content", str(hint)))
                        regression_risks.append(f"In `{dir_path}`: {fact}")
                    elif hint:
                        regression_risks.append(f"In `{dir_path}`: {hint}")

            return {
                "insights": insights[:5],
                "past_bugs": past_bugs[:5],
                "regression_risks": regression_risks[:5],
            }

        except Exception as e:
            safe_print(
                f"[Deep Context] Memory context gathering failed: {e}", flush=True
            )
            return {"insights": [], "past_bugs": [], "regression_risks": []}

    async def _gather_architecture_context(
        self,
        changed_files: list[str],
    ) -> dict:
        """Run lightweight architecture analysis on changed files."""
        try:
            from architecture.config import (
                infer_architecture_config,
                load_architecture_config,
            )
            from architecture.rules_engine import ArchitectureRulesEngine

            # Load or infer config
            config = load_architecture_config(self.project_dir)
            if not config:
                config = infer_architecture_config(self.project_dir)

            if not config.layers and not config.bounded_contexts:
                return {"style": "", "layers": [], "violations": []}

            # Run deterministic rules (fast, no AI)
            engine = ArchitectureRulesEngine(self.project_dir, config)
            report = engine.validate(changed_files if changed_files else None)

            # Format layers
            layers = []
            for layer in config.layers:
                layers.append(
                    {
                        "name": layer.name,
                        "patterns": layer.patterns[:3],
                        "allowed_imports": layer.allowed_imports[:3],
                        "forbidden_imports": layer.forbidden_imports[:3],
                    }
                )

            # Format violations
            violations = []
            for v in report.violations:
                violations.append(
                    {
                        "type": v.type,
                        "severity": v.severity,
                        "file": v.file,
                        "line": v.line,
                        "description": v.description,
                        "suggestion": v.suggestion,
                    }
                )
            for w in report.warnings:
                violations.append(
                    {
                        "type": w.type,
                        "severity": "warning",
                        "file": w.file,
                        "description": w.description,
                        "suggestion": w.suggestion,
                    }
                )

            return {
                "style": config.architecture_style,
                "layers": layers,
                "violations": violations,
            }

        except Exception as e:
            safe_print(
                f"[Deep Context] Architecture context gathering failed: {e}",
                flush=True,
            )
            return {"style": "", "layers": [], "violations": []}


async def store_review_learnings(
    project_dir: Path,
    pr_number: int,
    findings: list[dict],
    pr_title: str,
    changed_files: list[str],
) -> None:
    """
    Store review findings as learnings in Graphiti memory.

    Called after a review completes to build up project knowledge
    for future reviews.

    Args:
        project_dir: Project root directory
        pr_number: PR number
        findings: List of review findings (as dicts)
        pr_title: PR title for context
        changed_files: Files changed in the PR
    """
    try:
        from context.graphiti_integration import is_graphiti_enabled

        if not is_graphiti_enabled():
            return

        from integrations.graphiti.memory import get_graphiti_memory

        # Create a temporary spec dir for memory scoping
        github_dir = project_dir / ".auto-claude" / "github"
        github_dir.mkdir(parents=True, exist_ok=True)

        memory = get_graphiti_memory(github_dir, project_dir)

        # Store significant findings as learnings
        for finding in findings:
            severity = finding.get("severity", "low")
            if severity not in ("critical", "high"):
                continue

            category = finding.get("category", "unknown")
            file_path = finding.get("file", "unknown")
            title = finding.get("title", "")
            description = finding.get("description", "")

            episode_data = {
                "pr_number": pr_number,
                "pr_title": pr_title,
                "finding_severity": severity,
                "finding_category": category,
                "file": file_path,
                "title": title,
                "description": description[:500],
                "changed_files": changed_files[:10],
            }

            episode_type = "qa_result" if category == "security" else "gotcha"
            memory.store_episode(episode_type, episode_data)

        safe_print(
            f"[Deep Context] Stored {len([f for f in findings if f.get('severity') in ('critical', 'high')])} "
            f"review learnings to memory",
            flush=True,
        )

    except Exception as e:
        safe_print(
            f"[Deep Context] Failed to store review learnings (non-blocking): {e}",
            flush=True,
        )
