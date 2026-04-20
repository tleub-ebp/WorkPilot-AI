"""Blast Radius Runner — JSON stdout wrapper.

Provider-agnostic: performs a deterministic import-graph analysis. No
LLM calls; works regardless of which AI provider the user is using.

Usage::

    python -m runners.blast_radius_runner \
        --project-root /path/to/repo \
        --targets "apps/backend/core/client.py,apps/backend/cli/main.py"

Output (last line of stdout) is the JSON-serialized ``BlastRadiusReport``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from analysis.blast_radius import analyze_blast_radius


def main() -> int:
    parser = argparse.ArgumentParser(prog="blast_radius_runner")
    parser.add_argument("--project-root", required=True)
    parser.add_argument(
        "--targets",
        required=True,
        help="Comma-separated list of target paths (relative to project root)",
    )
    args = parser.parse_args()

    root = Path(args.project_root)
    targets = [t.strip() for t in args.targets.split(",") if t.strip()]

    try:
        report = analyze_blast_radius(root, targets)
        sys.stdout.write(json.dumps(report.to_dict()) + "\n")
        return 0
    except Exception as exc:  # noqa: BLE001
        sys.stdout.write(json.dumps({"error": str(exc)}) + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
