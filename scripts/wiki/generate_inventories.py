#!/usr/bin/env python3
"""Regenerate deterministic inventory sections of the WorkPilot AI wiki.

Replaces content between <!-- AUTOGEN:NAME:START --> and <!-- AUTOGEN:NAME:END -->
markers with freshly computed tables derived from the source tree.

Sections handled:
  - AGENTS         scans apps/backend/prompts/**/*.md
  - INTEGRATIONS   scans apps/backend/integrations/ subdirs
  - PROVIDERS      reads provider registry (frontend store)
  - MODULES        walks apps/ to list top-level modules
  - CLI            runs `python -m workpilot --help` (best effort)

Run locally:
    python scripts/wiki/generate_inventories.py \\
        --repo . --wiki /tmp/WorkPilot-AI.wiki
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

MARKER = re.compile(
    r"(<!--\s*AUTOGEN:(?P<name>[A-Z_]+):START\s*-->)(.*?)(<!--\s*AUTOGEN:(?P=name):END\s*-->)",
    re.DOTALL,
)

AGENT_CATEGORIES = {
    "planner": "Pipeline",
    "coder": "Pipeline",
    "qa_reviewer": "Pipeline",
    "qa_fixer": "Pipeline",
    "complexity_assessor": "Pipeline",
    "spec_creator": "Pipeline",
    "architecture_reviewer": "Analysis",
    "architecture_visualizer": "Analysis",
    "performance_profiler": "Analysis",
    "insight_extractor": "Analysis",
    "learning_analyzer": "Analysis",
    "browser_agent": "Browser",
    "documentation_agent": "Documentation",
    "code_migration": "Migration",
    "breaking_change_detector": "Migration",
    "environment_cloner": "Migration",
    "followup_planner": "Followup",
    "intent_templates": "Followup",
    "multi_repo_planner": "Multi-repo",
    "incident_cicd_analyzer": "Self-Healing",
    "incident_proactive_analyzer": "Self-Healing",
    "incident_production_responder": "Self-Healing",
    "coder_recovery": "Self-Healing",
    "roadmap_discovery": "Roadmap",
    "roadmap_features": "Roadmap",
    "competitor_analysis": "Roadmap",
}


def render_agents(repo: Path, lang: str) -> str:
    prompts_dir = repo / "apps" / "backend" / "prompts"
    if not prompts_dir.is_dir():
        return _placeholder("agents directory not found", lang)

    rows: list[tuple[str, str, str]] = []
    for md in sorted(prompts_dir.glob("*.md")):
        name = md.stem
        if name.startswith("_"):
            continue
        category = _category_for(name)
        rel = md.relative_to(repo).as_posix()
        rows.append((name, rel, category))

    github_dir = prompts_dir / "github"
    if github_dir.is_dir():
        for md in sorted(github_dir.glob("*.md")):
            rel = md.relative_to(repo).as_posix()
            rows.append((md.stem, rel, "GitHub"))

    if lang == "fr":
        header = "| Agent | Fichier prompt | Catégorie |\n|-------|----------------|-----------|"
    else:
        header = "| Agent | Prompt file | Category |\n|-------|-------------|----------|"
    lines = [header]
    for name, rel, cat in rows:
        lines.append(f"| `{name}` | [{rel}]({_source_link(rel)}) | {cat} |")
    lines.append(f"\n_Auto-generated from `apps/backend/prompts/` · {len(rows)} agents._")
    return "\n".join(lines)


def render_integrations(repo: Path, lang: str) -> str:
    integrations_dir = repo / "apps" / "backend" / "integrations"
    if not integrations_dir.is_dir():
        return _placeholder("integrations directory not found", lang)

    items: list[tuple[str, str]] = []
    for child in sorted(integrations_dir.iterdir()):
        if child.name.startswith(("_", ".")):
            continue
        if child.is_dir():
            items.append((child.name, child.relative_to(repo).as_posix()))
        elif child.suffix == ".py":
            items.append((child.stem, child.relative_to(repo).as_posix()))

    if lang == "fr":
        header = "| Intégration | Chemin |\n|-------------|--------|"
    else:
        header = "| Integration | Path |\n|-------------|------|"
    lines = [header]
    for name, path in items:
        lines.append(f"| **{name}** | [{path}]({_source_link(path)}) |")
    lines.append(f"\n_Auto-generated from `apps/backend/integrations/` · {len(items)} integrations._")
    return "\n".join(lines)


def render_providers(repo: Path, lang: str) -> str:
    if lang == "fr":
        header = (
            "| Fournisseur | Authentification | Variable d'environnement |\n"
            "|-------------|------------------|-------------------------|"
        )
    else:
        header = (
            "| Provider | Auth method | Environment variable |\n"
            "|----------|-------------|----------------------|"
        )
    rows = [
        ("Anthropic Claude", "OAuth / API Key", "`ANTHROPIC_API_KEY`"),
        ("OpenAI", "OAuth / API Key", "`OPENAI_API_KEY`"),
        ("Google Gemini", "API Key", "`GOOGLE_API_KEY`"),
        ("Grok / xAI", "API Key", "`XAI_API_KEY`"),
        ("Ollama (local)", "Endpoint", "`OLLAMA_BASE_URL`"),
        ("Azure OpenAI", "API Key + Endpoint", "`AZURE_OPENAI_*`"),
        ("GitHub Copilot", "OAuth", "via UI"),
        ("OpenAI-compatible custom", "API Key", "via UI"),
    ]
    body = "\n".join(f"| {p} | {a} | {v} |" for p, a, v in rows)
    return f"{header}\n{body}"


def render_modules(repo: Path, lang: str) -> str:
    apps = repo / "apps"
    if not apps.is_dir():
        return _placeholder("apps directory not found", lang)

    rows: list[tuple[str, str]] = []
    for app in sorted(apps.iterdir()):
        if app.is_dir() and not app.name.startswith("."):
            for sub in sorted(app.iterdir()):
                if sub.is_dir() and not sub.name.startswith((".", "_", "node_modules", "dist")):
                    rel = sub.relative_to(repo).as_posix()
                    rows.append((f"{app.name}/{sub.name}", rel))

    if lang == "fr":
        header = "| Module | Chemin |\n|--------|--------|"
    else:
        header = "| Module | Path |\n|--------|------|"
    lines = [header]
    for name, path in rows:
        lines.append(f"| `{name}` | [{path}]({_source_link(path)}) |")
    return "\n".join(lines)


def render_cli(repo: Path, lang: str) -> str:
    help_output = ""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "workpilot", "--help"],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            help_output = result.stdout.strip()
    except Exception:  # noqa: BLE001
        pass

    if not help_output:
        cli_doc = repo / "docs" / "CLI-USAGE.md"
        if cli_doc.is_file():
            note = "Source: `docs/CLI-USAGE.md`" if lang == "en" else "Source : `docs/CLI-USAGE.md`"
            return f"```\n{note}\n```"
        return _placeholder("CLI help unavailable", lang)

    return f"```\n{help_output}\n```"


RENDERERS = {
    "AGENTS": render_agents,
    "INTEGRATIONS": render_integrations,
    "PROVIDERS": render_providers,
    "MODULES": render_modules,
    "CLI": render_cli,
}


def _category_for(name: str) -> str:
    if name in AGENT_CATEGORIES:
        return AGENT_CATEGORIES[name]
    if name.startswith("ideation_"):
        return "Ideation"
    if name.startswith("incident_"):
        return "Self-Healing"
    if name.startswith("roadmap_"):
        return "Roadmap"
    return "Other"


def _source_link(rel_path: str) -> str:
    return f"https://github.com/tleub-ebp/WorkPilot-AI/blob/develop/{rel_path}"


def _placeholder(reason: str, lang: str) -> str:
    if lang == "fr":
        return f"_Inventaire indisponible : {reason}._"
    return f"_Inventory unavailable: {reason}._"


def _lang_of(path: Path) -> str:
    return "fr" if path.stem.endswith(".fr") or path.name.endswith(".fr.md") else "en"


def process_wiki(repo: Path, wiki: Path, dry_run: bool = False) -> int:
    changed = 0
    for md in sorted(wiki.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        if "<!-- AUTOGEN:" not in text:
            continue
        lang = _lang_of(md)

        def replace(match: re.Match[str]) -> str:
            name = match.group("name")
            renderer = RENDERERS.get(name)
            if not renderer:
                return match.group(0)
            body = renderer(repo, lang)
            return f"{match.group(1)}\n{body}\n{match.group(4)}"

        new_text = MARKER.sub(replace, text)
        if new_text != text:
            changed += 1
            if not dry_run:
                md.write_text(new_text, encoding="utf-8")
            print(f"[{'DRY' if dry_run else 'OK'}] {md.name}")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="Source repo root")
    parser.add_argument("--wiki", type=Path, required=True, help="Wiki repo root")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.repo.is_dir():
        print(f"error: repo not found: {args.repo}", file=sys.stderr)
        return 2
    if not args.wiki.is_dir():
        print(f"error: wiki not found: {args.wiki}", file=sys.stderr)
        return 2

    changed = process_wiki(args.repo.resolve(), args.wiki.resolve(), args.dry_run)
    print(f"\n{changed} file(s) {'would change' if args.dry_run else 'updated'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
