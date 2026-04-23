#!/usr/bin/env python3
"""Refresh narrative + translation sections of the WorkPilot AI wiki.

Uses the `claude` CLI (installed from `@anthropic-ai/claude-code`) in
non-interactive print mode. Authentication is OAuth, via the
`CLAUDE_CODE_OAUTH_TOKEN` environment variable — same token system as
`claude setup-token`. Lets the workflow consume a user's claude.ai
subscription instead of a paid API key.

Modes:
  - refresh-narrative  rewrites <!-- AUTOGEN:NARRATIVE --> blocks from
                       canonical source docs (README, docs/CLAUDE.md, prompts).
                       Uses Claude Sonnet 4.6.
  - translate-fr       creates / updates `<Page>.fr.md` from the EN canonical
                       page when FR is missing or a stub. Uses Haiku 4.5.
  - translate-en       bootstrap helper: creates / updates `<Page>.md` from
                       the FR counterpart when EN is a stub. Useful during
                       the initial FR-first phase of the wiki.

Shared CLI:
    python scripts/wiki/update_narrative.py <command> \\
        --repo . --wiki /tmp/WorkPilot-AI.wiki

Expects CLAUDE_CODE_OAUTH_TOKEN in the environment, and the `claude` CLI on PATH.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
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

STUB_MARKERS = (
    "traduction en cours",
    "translation is auto-generated",
    "translation pending",
)


def _ensure_cli() -> str:
    claude = shutil.which("claude")
    if not claude:
        print(
            "error: `claude` CLI not found on PATH. Install with "
            "`npm i -g @anthropic-ai/claude-code`.",
            file=sys.stderr,
        )
        sys.exit(2)
    if not os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        print(
            "error: CLAUDE_CODE_OAUTH_TOKEN not set. Generate one locally with "
            "`claude setup-token` and store it as a repo secret.",
            file=sys.stderr,
        )
        sys.exit(2)
    return claude


def _load_sources(repo: Path) -> str:
    chunks: list[str] = []
    for rel in SOURCE_FILES:
        path = repo / rel
        if path.is_file():
            chunks.append(f"===== {rel} =====\n{path.read_text(encoding='utf-8')}\n")
    return "\n".join(chunks)


def _lang_of(path: Path) -> str:
    return "fr" if path.name.endswith(".fr.md") else "en"


def _is_stub(content: str) -> bool:
    lower = content.lower()
    if any(marker in lower for marker in STUB_MARKERS):
        return True
    body = MARKER.sub("", content).strip()
    return len(body) < 500


def refresh_narrative(claude: str, repo: Path, wiki: Path, dry_run: bool = False) -> int:
    sources = _load_sources(repo)
    changed = 0
    for md in sorted(wiki.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        if "<!-- AUTOGEN:NARRATIVE:START -->" not in text:
            continue

        lang = _lang_of(md)
        topic = md.stem.replace(".fr", "").replace("-", " ")

        def replace(match: re.Match[str], topic=topic, lang=lang) -> str:
            nonlocal changed
            prompt = _build_narrative_prompt(topic, lang, sources)
            if dry_run:
                body = f"_(would regenerate narrative for {topic} in {lang})_"
            else:
                body = _call_claude_cli(claude, NARRATIVE_MODEL, prompt)
            changed += 1
            return f"{match.group(1)}\n{body}\n{match.group(3)}"

        new_text = MARKER.sub(replace, text)
        if new_text != text and not dry_run:
            md.write_text(new_text, encoding="utf-8")
        if new_text != text:
            print(f"[{'DRY' if dry_run else 'OK'}] narrative: {md.name}")
    return changed


def translate_fr(claude: str, repo: Path, wiki: Path, dry_run: bool = False) -> int:
    """Translate EN → FR when the FR page is missing or is a clear stub."""
    _ = repo
    changed = 0
    for en in sorted(wiki.glob("*.md")):
        if en.name.endswith(".fr.md") or en.name in {"_Sidebar.md", "_Footer.md", "Home.md"}:
            continue
        fr_path = wiki / en.name.replace(".md", ".fr.md")

        en_content = en.read_text(encoding="utf-8")
        fr_existing = fr_path.read_text(encoding="utf-8") if fr_path.exists() else ""

        if _is_stub(en_content):
            continue
        if fr_existing and not _is_stub(fr_existing):
            continue

        prompt = _build_translate_prompt(en_content, fr_existing, "fr")
        if dry_run:
            print(f"[DRY] translate EN→FR: {en.name}")
        else:
            body = _call_claude_cli(claude, TRANSLATE_MODEL, prompt)
            fr_path.write_text(body, encoding="utf-8")
            print(f"[OK] translate EN→FR: {en.name} → {fr_path.name}")
        changed += 1
    return changed


def translate_en(claude: str, repo: Path, wiki: Path, dry_run: bool = False) -> int:
    """Translate FR → EN when the EN page is a stub but FR has real content.

    Bootstrap helper for the initial FR-first phase. Normally EN is canonical.
    """
    _ = repo
    changed = 0
    for fr in sorted(wiki.glob("*.fr.md")):
        if fr.name in {"_Sidebar.fr.md", "_Footer.fr.md", "Home.fr.md"}:
            continue
        en_path = wiki / fr.name.replace(".fr.md", ".md")

        fr_content = fr.read_text(encoding="utf-8")
        en_existing = en_path.read_text(encoding="utf-8") if en_path.exists() else ""

        if _is_stub(fr_content):
            continue
        if en_existing and not _is_stub(en_existing):
            continue

        prompt = _build_translate_prompt(fr_content, en_existing, "en")
        if dry_run:
            print(f"[DRY] translate FR→EN: {fr.name}")
        else:
            body = _call_claude_cli(claude, TRANSLATE_MODEL, prompt)
            en_path.write_text(body, encoding="utf-8")
            print(f"[OK] translate FR→EN: {fr.name} → {en_path.name}")
        changed += 1
    return changed


def _build_narrative_prompt(topic: str, lang: str, sources: str) -> str:
    lang_name = "French" if lang == "fr" else "English"
    return f"""You are updating the WorkPilot AI public wiki.

Write a concise, informative narrative section about **{topic}** in **{lang_name}**,
based only on the source documents below. Do not invent features. Aim for 150–400 words.
Use markdown, include a short table if it helps, and do not repeat the page title.

SOURCE DOCUMENTS:
{sources}

Respond with the markdown body only, no preamble, no code fence."""


def _build_translate_prompt(source_content: str, existing_target: str, target_lang: str) -> str:
    source_lang_name = "French" if target_lang == "en" else "English"
    target_lang_name = "English" if target_lang == "en" else "French"
    hint = ""
    if existing_target:
        hint = (
            f"\n\nExisting {target_lang_name} version (may be stale — update it rather "
            f"than writing from scratch):\n{existing_target}"
        )
    example = (
        "'Paramètres' → 'Settings'" if target_lang == "en" else "'Settings' → 'Paramètres'"
    )
    return f"""Translate the following {source_lang_name} markdown page to {target_lang_name}.

Rules:
- Preserve all markdown structure (headings, tables, code blocks, links).
- Do NOT translate code, command names, environment variable names, or file paths.
- Translate user-visible UI labels (e.g. {example}) when WorkPilot AI is known to be bilingual (it is).
- Keep internal wiki links of form [Text](Page-Name) unchanged — the page names are shared between languages; only the link text should be translated.
- Preserve `<!-- AUTOGEN:... -->` markers and the content between them verbatim.
- Output only the translated markdown, no preamble.
{hint}

{source_lang_name.upper()} PAGE:
{source_content}"""


def _call_claude_cli(claude: str, model: str, prompt: str) -> str:
    """Invoke `claude -p` in print mode, capturing stdout as the reply."""
    cmd = [claude, "-p", "--model", model, "--output-format", "text", prompt]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"claude CLI failed ({result.returncode}): {result.stderr.strip()}"
        )
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("refresh-narrative", "translate-fr", "translate-en"):
        p = sub.add_parser(name)
        p.add_argument("--repo", type=Path, default=Path.cwd())
        p.add_argument("--wiki", type=Path, required=True)
        p.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()
    claude = "" if args.dry_run else _ensure_cli()

    repo = args.repo.resolve()
    wiki = args.wiki.resolve()

    if args.command == "refresh-narrative":
        n = refresh_narrative(claude, repo, wiki, args.dry_run)
    elif args.command == "translate-fr":
        n = translate_fr(claude, repo, wiki, args.dry_run)
    else:
        n = translate_en(claude, repo, wiki, args.dry_run)

    print(f"\n{n} section(s) {'would change' if args.dry_run else 'updated'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
