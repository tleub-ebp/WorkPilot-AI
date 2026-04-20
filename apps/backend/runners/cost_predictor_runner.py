"""
Cost Predictor Runner
=====================

Thin wrapper around :class:`cost_intelligence.CostPredictor` that emits a
single JSON object on stdout. Designed to be spawned from the Electron main
process.

Usage::

    python cost_predictor_runner.py \
        --project-path <root> \
        --spec-id <id> \
        --provider anthropic \
        --model claude-sonnet-4-6 \
        [--compare provider:model,provider:model]

Output protocol (one line of JSON)::

    {"report": { ... PredictionReport.to_dict() ... }}

On failure a single line is emitted with a non-zero exit code::

    {"error": "..."}
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from cost_intelligence import CostPredictor  # noqa: E402


def _parse_compare(raw: str | None) -> list[tuple[str, str]]:
    if not raw:
        return []
    pairs: list[tuple[str, str]] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        if ":" in token:
            provider, model = token.split(":", 1)
        else:
            provider, model = "anthropic", token
        pairs.append((provider.strip(), model.strip()))
    return pairs


def main() -> None:
    parser = argparse.ArgumentParser(description="Cost Predictor Runner")
    parser.add_argument("--project-path", required=True)
    parser.add_argument("--spec-id", required=True)
    parser.add_argument("--provider", default="anthropic")
    parser.add_argument("--model", default="claude-sonnet-4-6")
    parser.add_argument("--compare", default=None)
    parser.add_argument(
        "--no-thinking",
        dest="thinking",
        action="store_false",
        default=True,
    )
    args = parser.parse_args()

    project_root = Path(args.project_path)
    spec_dir = project_root / ".autonomousbuild" / "specs" / args.spec_id
    if not spec_dir.exists():
        print(json.dumps({"error": f"Spec not found: {spec_dir}"}), flush=True)
        sys.exit(1)

    try:
        predictor = CostPredictor()
        report = predictor.predict(
            spec_dir,
            project_root=project_root,
            selected_model=args.model,
            selected_provider=args.provider,
            alternative_models=_parse_compare(args.compare),
            thinking_enabled=args.thinking,
        )
        print(json.dumps({"report": asdict(report)}, default=str), flush=True)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": str(exc)}), flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
