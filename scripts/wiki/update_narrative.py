#!/usr/bin/env python3
"""Refresh narrative sections of the WorkPilot AI wiki using the Anthropic API.

Two modes:
  - refresh-narrative  rewrites <!-- AUTOGEN:NARRATIVE --> blocks from
                       canonical source docs (README, docs/CLAUDE.md, prompts).
                       Uses Claude Sonnet 4.6.
  - translate-fr       creates / updates `<Page>.fr.md` by translating the EN
                       canonical page. Uses Claude Haiku 4.5 (cheaper, fast).

Shared CLI:
    python scripts/wiki/update_narrative.py refresh-narrative \\
        --repo . --wiki /tmp/WorkPilot-AI.wiki
    python scripts/wiki/update_narrative.py translate-fr \\
        --repo . --wiki /tmp/WorkPilot-AI.wiki

Expects ANTHROPIC_API_KEY in the environment.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

MARKER = re.compile(
    r"(<!--\s*AUTOGEN:NARRATIVE:START\s*-->)(.*?)(<!--\s*AUTOGEN:NARRATIVE:END\s*-->)",
    re.DOTALL,
)

NARRATIVE_MODEL = "claude-sonnet-4-6"
TRANSLATE_MODEL = "claude-haiku-4-5-20251001"

SOURCE_FILES = [
    "README.md",
    "docs/CLAUDE.md",
    "docs/CLI-USAGE.md",
]


def _anthropic_client():
    try:
        from anthropic import Anthropic
    except ImportError:
        print("error: `anthropic` package required (pip install anthropic)", file=sys.stderr)
        sys.exit(2)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("error: ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(2)
    return Anthropic(api_key=api_key)


def _load_sources(repo: Path) -> str:
    chunks: list[str] = []
    for rel in SOURCE_FILES:
        path = repo / rel
        if path.is_file():
            chunks.append(f"===== {rel} =====\n{path.read_text(encoding='utf-8')}\n")
    return "\n".join(chunks)


def _lang_of(path: Path) -> str:
    return "fr" if path.name.endswith(".fr.md") else "en"


def _canonical_en(wiki: Path, fr_path: Path) -> Path:
    return wiki / fr_path.name.replace(".fr.md", ".md")


def refresh_narrative(client, repo: Path, wiki: Path, dry_run: bool = False) -> int:
    sources = _load_sources(repo)
    changed = 0
    for md in sorted(wiki.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        if "<!-- AUTOGEN:NARRATIVE:START -->" not in text:
            continue

        lang = _lang_of(md)
        topic = md.stem.replace(".fr", "").replace("-", " ")

        def replace(match: re.Match[str]) -> str:
            nonlocal changed
            prompt = _build_narrative_prompt(topic, lang, sources)
            if dry_run:
                body = f"_(would regenerate narrative for {topic} in {lang})_"
            else:
                body = _call_claude(client, NARRATIVE_MODEL, prompt, max_tokens=4000)
            changed += 1
            return f"{match.group(1)}\n{body}\n{match.group(3)}"

        new_text = MARKER.sub(replace, text)
        if new_text != text and not dry_run:
            md.write_text(new_text, encoding="utf-8")
        if new_text != text:
            print(f"[{'DRY' if dry_run else 'OK'}] narrative: {md.name}")
    return changed


def translate_fr(client, repo: Path, wiki: Path, dry_run: bool = False) -> int:
    _ = repo  # unused — translation only needs EN wiki source
    changed = 0
    for en in sorted(wiki.glob("*.md")):
        if en.name.endswith(".fr.md") or en.name in {"_Sidebar.md", "_Footer.md", "Home.md"}:
            continue
        fr_path = wiki / en.name.replace(".md", ".fr.md")

        en_content = en.read_text(encoding="utf-8")
        fr_existing = fr_path.read_text(encoding="utf-8") if fr_path.exists() else ""

        if fr_existing and not _needs_translation(en_content, fr_existing):
            continue

        prompt = _build_translate_prompt(en_content, fr_existing)
        if dry_run:
            body = f"_(would translate {en.name} → {fr_path.name})_"
            print(f"[DRY] translate: {en.name}")
        else:
            body = _call_claude(client, TRANSLATE_MODEL, prompt, max_tokens=8000)
            fr_path.write_text(body, encoding="utf-8")
            print(f"[OK] translate: {en.name} → {fr_path.name}")
        changed += 1
    return changed


def _needs_translation(en_content: str, fr_content: str) -> bool:
    """Heuristic: translate when FR is missing or clearly a stub."""
    if "traduction en cours" in fr_content.lower():
        return True
    if "translation is auto-generated" in fr_content.lower():
        return True
    en_body = MARKER.sub("", en_content).strip()
    fr_body = MARKER.sub("", fr_content).strip()
    # if FR is dramatically shorter than EN, consider it stale
    return len(fr_body) < len(en_body) * 0.4


def _build_narrative_prompt(topic: str, lang: str, sources: str) -> str:
    lang_name = "French" if lang == "fr" else "English"
    return f"""You are updating the WorkPilot AI public wiki.

Write a concise, informative narrative section about **{topic}** in **{lang_name}**,
based only on the source documents below. Do not invent features. Aim for 150–400 words.
Use markdown, include a short table if it helps, and do not repeat the page title.

SOURCE DOCUMENTS:
{sources}

Respond with the markdown body only, no preamble, no code fence."""


def _build_translate_prompt(en_content: str, fr_existing: str) -> str:
    hint = ""
    if fr_existing:
        hint = (
            "\n\nExisting FR version (may be stale — update it rather than writing from scratch):\n"
            f"{fr_existing}"
        )
    return f"""Translate the following English markdown page to French.

Rules:
- Preserve all markdown structure (headings, tables, code blocks, links).
- Do NOT translate code, command names, environment variable names, or file paths.
- Translate user-visible UI labels (e.g. "Settings" → "Paramètres") when WorkPilot AI
  is known to be bilingual (it is).
- Keep internal wiki links of form [Text](Page-Name) unchanged — the page names are
  shared between languages; only the link text should be translated.
- Preserve `<!-- AUTOGEN:... -->` markers and the content between them verbatim.
- Output only the translated markdown, no preamble.
{hint}

ENGLISH PAGE:
{en_content}"""


def _call_claude(client, model: str, prompt: str, max_tokens: int) -> str:
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
    return "\n".join(parts).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("refresh-narrative", "translate-fr"):
        p = sub.add_parser(name)
        p.add_argument("--repo", type=Path, default=Path.cwd())
        p.add_argument("--wiki", type=Path, required=True)
        p.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()
    client = None if args.dry_run else _anthropic_client()

    repo = args.repo.resolve()
    wiki = args.wiki.resolve()

    if args.command == "refresh-narrative":
        n = refresh_narrative(client, repo, wiki, args.dry_run)
    else:
        n = translate_fr(client, repo, wiki, args.dry_run)

    print(f"\n{n} section(s) {'would change' if args.dry_run else 'updated'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
