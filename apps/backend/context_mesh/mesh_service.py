"""
Context Mesh Service — Main orchestrator for cross-project intelligence.

Coordinates analysis across registered projects to detect patterns,
generate handbook entries, identify skill transfers, and produce
contextual recommendations. Uses the Claude Agent SDK (provider-agnostic)
for AI-powered analysis.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .storage import ContextMeshStorage
from .types import (
    ContextualRecommendation,
    CrossProjectPattern,
    HandbookDomain,
    HandbookEntry,
    MeshAnalysisReport,
    PatternCategory,
    ProjectSummary,
    RecommendationType,
    SkillTransfer,
)

logger = logging.getLogger(__name__)

# Prompt for the AI analysis agent
MESH_ANALYSIS_PROMPT = """\
You are a cross-project intelligence analyst. You analyze multiple software projects
to find recurring architectural patterns, conventions, and knowledge that can be
transferred between projects.

## Registered Projects

{projects_context}

## Existing Knowledge

{existing_knowledge}

## Task

Analyze the provided project data and produce a JSON response with the following structure:

```json
{{
  "patterns": [
    {{
      "category": "architecture|auth|api_design|state_management|testing|deployment|error_handling|security|performance|naming_convention|project_structure|database|logging|ci_cd|other",
      "title": "Short descriptive title",
      "description": "Detailed description of the pattern",
      "source_projects": ["project names where this was found"],
      "target_projects": ["project names that could benefit"],
      "confidence": 0.0-1.0,
      "code_example": "Optional code snippet",
      "migration_hint": "How to apply this pattern to target projects"
    }}
  ],
  "handbook_entries": [
    {{
      "domain": "auth|api_design|state_management|testing|deployment|security|performance|database|frontend|backend|devops|general",
      "title": "Decision or convention title",
      "description": "What was decided and how it works",
      "decision_rationale": "Why this approach was chosen",
      "source_projects": ["project names"],
      "tags": ["relevant", "tags"]
    }}
  ],
  "skill_transfers": [
    {{
      "skill_name": "Name of the skill/convention",
      "description": "What can be transferred",
      "source_project": "Project where learned",
      "target_projects": ["Projects that would benefit"],
      "category": "Same categories as patterns",
      "framework_or_api": "Specific framework or API if applicable",
      "convention_details": "Details of the convention to transfer",
      "confidence": 0.0-1.0
    }}
  ],
  "recommendations": [
    {{
      "recommendation_type": "pattern_reuse|convention_adoption|bug_prevention|divergence_alert|complexity_estimate|skill_transfer",
      "title": "Recommendation title",
      "description": "What should be done and why",
      "source_project": "Where this knowledge comes from",
      "target_project": "Which project should act on this",
      "relevance_score": 0.0-1.0,
      "phase": "spec|planning|coding|qa",
      "action_suggestion": "Specific action to take"
    }}
  ]
}}
```

Focus on:
1. **Recurring patterns** — Same approaches used in 2+ projects
2. **Divergences** — Different approaches for the same problem across projects
3. **Transferable skills** — Knowledge from one project useful in others
4. **Bug prevention** — Past mistakes in one project that could happen in others
5. **Convention alignment** — Naming, testing, deployment conventions

Be specific and actionable. Only include findings with confidence >= 0.5.
"""


class ContextMeshService:
    """Main orchestrator for cross-project intelligence analysis."""

    def __init__(
        self,
        storage: ContextMeshStorage | None = None,
        model: str | None = None,
        thinking_level: str | None = None,
    ):
        self.storage = storage or ContextMeshStorage()
        self.model = model or "sonnet"
        self.thinking_level = thinking_level or "medium"

    # ── Project Registration ─────────────────────────────────────

    def register_project(self, project_path: str) -> ProjectSummary:
        """Register a project in the context mesh."""
        path = Path(project_path).resolve()
        project = ProjectSummary(
            project_path=str(path),
            project_name=path.name,
        )

        # Detect tech stack from project files
        project.tech_stack = self._detect_tech_stack(path)
        project.languages = self._detect_languages(path)
        project.frameworks = self._detect_frameworks(path)

        self.storage.save_project(project)
        logger.info(f"Registered project: {project.project_name} at {path}")
        return project

    def unregister_project(self, project_path: str) -> bool:
        """Remove a project from the context mesh."""
        return self.storage.remove_project(project_path)

    def get_projects(self) -> list[ProjectSummary]:
        """Get all registered projects."""
        return self.storage.get_projects()

    # ── Analysis ─────────────────────────────────────────────────

    async def run_analysis(
        self,
        status_callback: Any | None = None,
    ) -> MeshAnalysisReport:
        """Run full cross-project analysis on all registered projects."""
        projects = self.storage.get_projects()
        if not projects:
            return MeshAnalysisReport(
                analyzed_projects=[],
                patterns_found=[],
                handbook_entries=[],
                skill_transfers=[],
                recommendations=[],
            )

        if status_callback:
            status_callback(f"Analyzing {len(projects)} project(s)...")

        # Gather context from all projects
        projects_context = self._gather_projects_context(projects)
        existing_knowledge = self._gather_existing_knowledge()

        # Build prompt
        prompt = MESH_ANALYSIS_PROMPT.format(
            projects_context=projects_context,
            existing_knowledge=existing_knowledge,
        )

        if status_callback:
            status_callback("Running AI analysis across projects...")

        # Call AI via Claude Agent SDK (provider-agnostic)
        ai_result = await self._run_ai_analysis(prompt, projects)

        if status_callback:
            status_callback("Processing analysis results...")

        # Parse results
        report = self._parse_analysis_results(ai_result, projects)

        # Persist everything
        for pattern in report.patterns_found:
            self.storage.add_pattern(pattern)
        for entry in report.handbook_entries:
            self.storage.add_handbook_entry(entry)
        if report.skill_transfers:
            existing = self.storage.get_skill_transfers()
            existing.extend(report.skill_transfers)
            self.storage.save_skill_transfers(existing)
        if report.recommendations:
            existing_recs = self.storage.get_recommendations()
            existing_recs.extend(report.recommendations)
            self.storage.save_recommendations(existing_recs)

        # Update project last_analyzed_at
        now = datetime.now(timezone.utc).isoformat()
        for proj in projects:
            proj.last_analyzed_at = now
            proj.pattern_count = len(
                [
                    p
                    for p in report.patterns_found
                    if proj.project_name in p.source_projects
                ]
            )
            self.storage.save_project(proj)

        self.storage.save_report(report)

        if status_callback:
            status_callback("Analysis complete!")

        return report

    async def get_recommendations_for_project(
        self,
        project_path: str,
        phase: str = "",
        task_description: str = "",
    ) -> list[ContextualRecommendation]:
        """Get contextual recommendations for a specific project and phase."""
        recs = self.storage.get_recommendations(target_project=project_path)
        active_recs = [r for r in recs if r.status == "active"]

        if phase:
            active_recs = [r for r in active_recs if not r.phase or r.phase == phase]

        # Sort by relevance
        active_recs.sort(key=lambda r: r.relevance_score, reverse=True)
        return active_recs

    # ── AI Analysis ──────────────────────────────────────────────

    async def _run_ai_analysis(
        self,
        prompt: str,
        projects: list[ProjectSummary],
    ) -> str:
        """Run AI analysis using the Claude Agent SDK (works with any configured provider)."""
        try:
            from core.client import create_client
            from core.session import run_agent_session
            from phase_config import get_thinking_budget, resolve_model_id

            model_id = resolve_model_id(self.model)
            thinking_budget = get_thinking_budget(self.thinking_level)

            # Use the first project as the project_dir context
            project_dir = projects[0].project_path if projects else "."

            client = create_client(
                project_dir=project_dir,
                model=model_id,
                agent_type="context_mesh_analyzer",
                max_thinking_tokens=thinking_budget,
            )

            async with client:
                status, response = await run_agent_session(client, prompt)

            return response or ""

        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return ""

    # ── Context Gathering ────────────────────────────────────────

    def _gather_projects_context(self, projects: list[ProjectSummary]) -> str:
        """Gather context from all registered projects for analysis."""
        sections = []
        for proj in projects:
            path = Path(proj.project_path)
            section = f"### {proj.project_name}\n"
            section += f"- Path: {proj.project_path}\n"
            section += f"- Tech stack: {', '.join(proj.tech_stack) or 'unknown'}\n"
            section += f"- Languages: {', '.join(proj.languages) or 'unknown'}\n"
            section += f"- Frameworks: {', '.join(proj.frameworks) or 'unknown'}\n"

            # Read package.json if exists
            pkg_json = path / "package.json"
            if pkg_json.exists():
                try:
                    pkg = json.loads(pkg_json.read_text(encoding="utf-8"))
                    deps = list(pkg.get("dependencies", {}).keys())[:20]
                    dev_deps = list(pkg.get("devDependencies", {}).keys())[:15]
                    section += f"- Dependencies: {', '.join(deps)}\n"
                    section += f"- Dev dependencies: {', '.join(dev_deps)}\n"
                except Exception:
                    pass

            # Read requirements.txt / pyproject.toml if exists
            req_file = path / "requirements.txt"
            if req_file.exists():
                try:
                    lines = req_file.read_text(encoding="utf-8").strip().splitlines()
                    deps = [
                        line.split("==")[0].split(">=")[0].strip()
                        for line in lines[:20]
                        if line.strip() and not line.startswith("#")
                    ]
                    section += f"- Python deps: {', '.join(deps)}\n"
                except Exception:
                    pass

            # Read .workpilot learning patterns if available
            patterns_file = path / ".workpilot" / "learning_loop" / "patterns.json"
            if patterns_file.exists():
                try:
                    data = json.loads(patterns_file.read_text(encoding="utf-8"))
                    patterns = data.get("patterns", [])
                    if patterns:
                        section += f"- Learning patterns ({len(patterns)}):\n"
                        for p in patterns[:5]:
                            section += f"  - [{p.get('category', '')}] {p.get('description', '')[:100]}\n"
                except Exception:
                    pass

            # Read project structure (top-level dirs)
            if path.is_dir():
                dirs = sorted(
                    [
                        d.name
                        for d in path.iterdir()
                        if d.is_dir()
                        and not d.name.startswith(".")
                        and d.name
                        not in (
                            "node_modules",
                            "__pycache__",
                            ".git",
                            "venv",
                            ".venv",
                            "dist",
                            "build",
                        )
                    ]
                )[:15]
                section += f"- Top-level dirs: {', '.join(dirs)}\n"

            sections.append(section)

        return "\n".join(sections)

    def _gather_existing_knowledge(self) -> str:
        """Gather existing mesh knowledge for context."""
        patterns = self.storage.get_patterns()
        handbook = self.storage.get_handbook_entries()

        sections = []
        if patterns:
            sections.append("### Existing Patterns")
            for p in patterns[:10]:
                sections.append(
                    f"- [{p.category.value}] {p.title}: {p.description[:100]}"
                )

        if handbook:
            sections.append("\n### Existing Handbook Entries")
            for e in handbook[:10]:
                sections.append(f"- [{e.domain.value}] {e.title}")

        return "\n".join(sections) if sections else "No existing knowledge yet."

    # ── Result Parsing ───────────────────────────────────────────

    def _parse_analysis_results(
        self,
        ai_response: str,
        projects: list[ProjectSummary],
    ) -> MeshAnalysisReport:
        """Parse the AI analysis response into structured data."""
        # Extract JSON from response
        parsed = self._extract_json(ai_response)
        if not parsed:
            return MeshAnalysisReport(
                analyzed_projects=[p.project_name for p in projects],
                patterns_found=[],
                handbook_entries=[],
                skill_transfers=[],
                recommendations=[],
            )

        # Parse patterns
        patterns = []
        for p_data in parsed.get("patterns", []):
            try:
                pattern = CrossProjectPattern(
                    pattern_id=CrossProjectPattern.generate_id(),
                    category=PatternCategory(p_data.get("category", "other")),
                    title=p_data.get("title", ""),
                    description=p_data.get("description", ""),
                    source_projects=p_data.get("source_projects", []),
                    target_projects=p_data.get("target_projects", []),
                    confidence=float(p_data.get("confidence", 0.5)),
                    code_example=p_data.get("code_example", ""),
                    migration_hint=p_data.get("migration_hint", ""),
                )
                if pattern.confidence >= 0.5:
                    patterns.append(pattern)
            except (ValueError, KeyError) as e:
                logger.warning(f"Failed to parse pattern: {e}")

        # Parse handbook entries
        handbook_entries = []
        for e_data in parsed.get("handbook_entries", []):
            try:
                entry = HandbookEntry(
                    entry_id=HandbookEntry.generate_id(),
                    domain=HandbookDomain(e_data.get("domain", "general")),
                    title=e_data.get("title", ""),
                    description=e_data.get("description", ""),
                    decision_rationale=e_data.get("decision_rationale", ""),
                    source_projects=e_data.get("source_projects", []),
                    tags=e_data.get("tags", []),
                )
                handbook_entries.append(entry)
            except (ValueError, KeyError) as e:
                logger.warning(f"Failed to parse handbook entry: {e}")

        # Parse skill transfers
        skill_transfers = []
        for s_data in parsed.get("skill_transfers", []):
            try:
                transfer = SkillTransfer(
                    transfer_id=SkillTransfer.generate_id(),
                    skill_name=s_data.get("skill_name", ""),
                    description=s_data.get("description", ""),
                    source_project=s_data.get("source_project", ""),
                    target_projects=s_data.get("target_projects", []),
                    category=PatternCategory(s_data.get("category", "other")),
                    framework_or_api=s_data.get("framework_or_api", ""),
                    convention_details=s_data.get("convention_details", ""),
                    confidence=float(s_data.get("confidence", 0.5)),
                )
                skill_transfers.append(transfer)
            except (ValueError, KeyError) as e:
                logger.warning(f"Failed to parse skill transfer: {e}")

        # Parse recommendations
        recommendations = []
        for r_data in parsed.get("recommendations", []):
            try:
                rec = ContextualRecommendation(
                    recommendation_id=ContextualRecommendation.generate_id(),
                    recommendation_type=RecommendationType(
                        r_data.get("recommendation_type", "pattern_reuse")
                    ),
                    title=r_data.get("title", ""),
                    description=r_data.get("description", ""),
                    source_project=r_data.get("source_project", ""),
                    target_project=r_data.get("target_project", ""),
                    relevance_score=float(r_data.get("relevance_score", 0.5)),
                    phase=r_data.get("phase", ""),
                    action_suggestion=r_data.get("action_suggestion", ""),
                )
                recommendations.append(rec)
            except (ValueError, KeyError) as e:
                logger.warning(f"Failed to parse recommendation: {e}")

        return MeshAnalysisReport(
            analyzed_projects=[p.project_name for p in projects],
            patterns_found=patterns,
            handbook_entries=handbook_entries,
            skill_transfers=skill_transfers,
            recommendations=recommendations,
            analysis_model=self.model,
        )

    def _extract_json(self, text: str) -> dict | None:
        """Extract JSON from AI response (may be wrapped in markdown code blocks)."""
        if not text:
            return None

        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try extracting from code blocks
        for marker in ("```json", "```"):
            if marker in text:
                start = text.index(marker) + len(marker)
                end = text.find("```", start)
                if end > start:
                    try:
                        return json.loads(text[start:end].strip())
                    except json.JSONDecodeError:
                        pass

        # Try finding first { ... last }
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace >= 0 and last_brace > first_brace:
            try:
                return json.loads(text[first_brace : last_brace + 1])
            except json.JSONDecodeError:
                pass

        return None

    # ── Tech Stack Detection ─────────────────────────────────────

    def _detect_tech_stack(self, path: Path) -> list[str]:
        stack = []
        if (path / "package.json").exists():
            stack.append("node")
        if (path / "requirements.txt").exists() or (path / "pyproject.toml").exists():
            stack.append("python")
        if (path / "Cargo.toml").exists():
            stack.append("rust")
        if (path / "go.mod").exists():
            stack.append("go")
        if (path / "pom.xml").exists() or (path / "build.gradle").exists():
            stack.append("java")
        if (path / "Gemfile").exists():
            stack.append("ruby")
        if (path / "composer.json").exists():
            stack.append("php")
        if (path / ".csproj").exists() or any(path.glob("*.csproj")):
            stack.append("dotnet")
        if (path / "Dockerfile").exists():
            stack.append("docker")
        return stack

    def _detect_languages(self, path: Path) -> list[str]:
        langs = set()
        extensions_map = {
            ".ts": "TypeScript",
            ".tsx": "TypeScript",
            ".js": "JavaScript",
            ".jsx": "JavaScript",
            ".py": "Python",
            ".rs": "Rust",
            ".go": "Go",
            ".java": "Java",
            ".cs": "C#",
            ".rb": "Ruby",
            ".php": "PHP",
            ".swift": "Swift",
            ".kt": "Kotlin",
        }
        # Check top-level + one level deep
        for f in path.iterdir():
            if f.is_file() and f.suffix in extensions_map:
                langs.add(extensions_map[f.suffix])
            elif (
                f.is_dir()
                and not f.name.startswith(".")
                and f.name not in ("node_modules", "__pycache__", "venv", ".venv")
            ):
                try:
                    for sf in f.iterdir():
                        if sf.is_file() and sf.suffix in extensions_map:
                            langs.add(extensions_map[sf.suffix])
                except PermissionError:
                    pass
        return sorted(langs)

    def _detect_frameworks(self, path: Path) -> list[str]:
        frameworks = []
        pkg_json = path / "package.json"
        if pkg_json.exists():
            try:
                pkg = json.loads(pkg_json.read_text(encoding="utf-8"))
                deps = {
                    **pkg.get("dependencies", {}),
                    **pkg.get("devDependencies", {}),
                }
                framework_map = {
                    "react": "React",
                    "next": "Next.js",
                    "vue": "Vue",
                    "nuxt": "Nuxt",
                    "angular": "Angular",
                    "@angular/core": "Angular",
                    "svelte": "Svelte",
                    "express": "Express",
                    "fastify": "Fastify",
                    "nestjs": "NestJS",
                    "@nestjs/core": "NestJS",
                    "electron": "Electron",
                    "tailwindcss": "Tailwind CSS",
                }
                for dep, name in framework_map.items():
                    if dep in deps:
                        frameworks.append(name)
            except Exception:
                pass

        # Python frameworks
        req_file = path / "requirements.txt"
        if req_file.exists():
            try:
                content = req_file.read_text(encoding="utf-8").lower()
                py_frameworks = {
                    "django": "Django",
                    "flask": "Flask",
                    "fastapi": "FastAPI",
                    "pytest": "pytest",
                    "sqlalchemy": "SQLAlchemy",
                }
                for key, name in py_frameworks.items():
                    if key in content:
                        frameworks.append(name)
            except Exception:
                pass

        return frameworks
