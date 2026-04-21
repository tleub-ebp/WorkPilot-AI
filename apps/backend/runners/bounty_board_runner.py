"""
Bounty Board Runner — spawned from the Electron main process.

Emits ONE JSON line on stdout::

    {"result": { ...BountyResult.to_dict()... }}

On failure a single JSON line is emitted and the process exits non-zero::

    {"error": "<message>"}

Usage::

    python bounty_board_runner.py \
        --project-path <root> \
        --spec-id <id> \
        --contestants "anthropic:claude-sonnet-4-6,openai:gpt-4o,ollama:llama3.3"
        [--profiles "profile-1,profile-2,profile-3"]
        [--prompt-overrides "Refactor aggressively||Prioritize readability||Match existing style"]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from bounty_board import ContestantSpec, run_bounty  # noqa: E402


def _parse_contestants(raw: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for token in (raw or "").split(","):
        token = token.strip()
        if not token:
            continue
        if ":" in token:
            provider, model = token.split(":", 1)
        else:
            provider, model = "anthropic", token
        pairs.append((provider.strip(), model.strip()))
    return pairs


def _parse_list(raw: str | None, sep: str) -> list[str]:
    if not raw:
        return []
    return [t.strip() for t in raw.split(sep)]


def _resolve_spec_dir(project_path: Path, spec_id: str) -> Path:
    candidates = [
        project_path / ".workpilot" / "specs" / spec_id,
        project_path / ".autonomousbuild" / "specs" / spec_id,
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


async def _main_async(args: argparse.Namespace) -> int:
    project_root = Path(args.project_path)
    spec_dir = _resolve_spec_dir(project_root, args.spec_id)

    providers_models = _parse_contestants(args.contestants)
    if not providers_models:
        print(
            json.dumps({"error": "No contestants provided (--contestants)"}), flush=True
        )
        return 1

    profiles = _parse_list(args.profiles, ",")
    overrides = _parse_list(args.prompt_overrides, "||")

    specs: list[ContestantSpec] = []
    for idx, (provider, model) in enumerate(providers_models):
        specs.append(
            ContestantSpec(
                provider=provider,
                model=model,
                profile_id=profiles[idx] if idx < len(profiles) else None,
                prompt_override=overrides[idx] if idx < len(overrides) else None,
            )
        )

    result = await run_bounty(
        spec_dir=spec_dir, project_path=project_root, contestants=specs
    )
    print(json.dumps({"result": result.to_dict()}), flush=True)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Bounty Board Runner")
    parser.add_argument("--project-path", required=True)
    parser.add_argument("--spec-id", required=True)
    parser.add_argument(
        "--contestants",
        required=True,
        help="Comma-separated provider:model pairs (e.g. 'anthropic:claude-sonnet-4-6,openai:gpt-4o')",
    )
    parser.add_argument("--profiles", default=None, help="Comma-separated profile IDs")
    parser.add_argument(
        "--prompt-overrides",
        default=None,
        help="Per-contestant prompt overrides separated by ||",
    )
    args = parser.parse_args()
    try:
        code = asyncio.run(_main_async(args))
        sys.exit(code)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": str(exc)}), flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
