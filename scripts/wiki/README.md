# Wiki automation

Scripts that keep the GitHub Wiki (`WorkPilot-AI.wiki`) in sync with the source repo.

## Philosophy

Two update tracks with different cost and cadence:

| Track | Trigger | Cost | What it updates |
|-------|---------|------|-----------------|
| **Inventories** (deterministic) | every push to `develop` with relevant paths | free | Tables of agents, integrations, providers, modules, CLI |
| **Narrative** (AI) | each GitHub release | ~€1 per run | Prose sections + FR translations |

Every auto-updated block is delimited by markers in the wiki pages:

```markdown
<!-- AUTOGEN:AGENTS:START -->
...table or prose regenerated here...
<!-- AUTOGEN:AGENTS:END -->
```

Anything outside markers is **preserved untouched** — wiki editors can freely hand-edit.

## Files

| File | Role |
|------|------|
| [generate_inventories.py](generate_inventories.py) | Deterministic table regen from source tree |
| [update_narrative.py](update_narrative.py) | Narrative refresh + FR translation via Claude |
| [sync_wiki.py](sync_wiki.py) | Orchestrator: clone wiki, run steps, commit, push |

## Bilingual convention

The wiki uses a flat naming scheme:

- Canonical English: `Page-Name.md`
- French translation: `Page-Name.fr.md`

`Home.md` is a bilingual landing page; `_Sidebar.md` lists both languages.

Translation direction is **EN → FR**. Edit the EN page, then run `translate-fr` (or wait for the release workflow).

## Running locally

```bash
# Dry run (no writes, no API calls)
python scripts/wiki/generate_inventories.py \
    --repo . --wiki /tmp/wp-wiki --dry-run

# Full refresh against a local wiki clone
export ANTHROPIC_API_KEY=sk-...
git clone https://github.com/tleub-ebp/WorkPilot-AI.wiki.git /tmp/wp-wiki
python scripts/wiki/sync_wiki.py --mode full --workdir /tmp/wp-work --no-push
```

## Required secrets

GitHub Actions need:

- `WIKI_PUSH_TOKEN` — PAT with `repo` scope (or fall back to `GITHUB_TOKEN` if wiki pushes are permitted)
- `ANTHROPIC_API_KEY` — used by `update_narrative.py`

## Models

| Task | Model | Why |
|------|-------|-----|
| Narrative rewriting | `claude-sonnet-4-6` | Best quality/cost for structured prose |
| FR translation | `claude-haiku-4-5-20251001` | Cheap, fast, sufficient for translation |

To change models, edit the constants at the top of `update_narrative.py`.

## Adding a new AUTOGEN section

1. Insert the marker pair in the wiki page (EN and/or FR):
   ```markdown
   <!-- AUTOGEN:MYSECTION:START -->
   <!-- AUTOGEN:MYSECTION:END -->
   ```
2. Add a renderer to `generate_inventories.py`:
   ```python
   def render_mysection(repo: Path, lang: str) -> str: ...
   RENDERERS["MYSECTION"] = render_mysection
   ```
3. Push — the inventory workflow will fill it in on the next relevant push.

## Troubleshooting

- **Nothing changed after my push**: check that a path in the workflow's `paths:` filter matches.
- **Push to wiki failed**: the workflow uses `WIKI_PUSH_TOKEN` — ensure the PAT exists and has `repo` scope.
- **Narrative looks off**: review `SOURCE_FILES` in `update_narrative.py` — the model only sees those.
- **Translation drift**: `translate-fr` re-runs when FR is missing or substantially shorter than EN. Force a full retranslation by deleting the `.fr.md` file.
