"""
Tech Debt Runner — spawned from the Electron main process.

Commands (one JSON line on stdout):

  scan:       {"result": { ...DebtReport.to_dict()... }}
  list:       {"result": {"items": [...], "trend": [...], "summary": {...}}}
  trend:      {"result": {"trend": [...]}}
  spec:       {"result": {"spec_dir": "..."}}

Usage::

    python tech_debt_runner.py --project-path <root> --command scan
    python tech_debt_runner.py --project-path <root> --command list [--min-score 2.0]
    python tech_debt_runner.py --project-path <root> --command trend
    python tech_debt_runner.py --project-path <root> --command spec --item-id <id>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from tech_debt import scan_project  # noqa: E402
from tech_debt.scanner import DebtItem  # noqa: E402
from tech_debt.spec_generator import generate_spec_from_item  # noqa: E402


def _load_last_report(project_path: Path) -> dict:
    path = project_path / ".workpilot" / "tech_debt" / "last_report.json"
    if not path.exists():
        return {"items": [], "trend": [], "summary": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def _cmd_scan(args: argparse.Namespace) -> int:
    report = scan_project(args.project_path)
    print(json.dumps({"result": report.to_dict()}), flush=True)
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    data = _load_last_report(Path(args.project_path))
    items = data.get("items", [])
    min_score = float(args.min_score or 0)
    items = [i for i in items if float(i.get("roi", 0)) >= min_score]
    print(
        json.dumps(
            {
                "result": {
                    "items": items,
                    "trend": data.get("trend", []),
                    "summary": data.get("summary", {}),
                }
            }
        ),
        flush=True,
    )
    return 0


def _cmd_trend(args: argparse.Namespace) -> int:
    data = _load_last_report(Path(args.project_path))
    print(json.dumps({"result": {"trend": data.get("trend", [])}}), flush=True)
    return 0


def _cmd_spec(args: argparse.Namespace) -> int:
    data = _load_last_report(Path(args.project_path))
    items = data.get("items", [])
    match = next((i for i in items if i.get("id") == args.item_id), None)
    if not match:
        print(json.dumps({"error": f"item not found: {args.item_id}"}), flush=True)
        return 1
    item = DebtItem(**match)
    spec_dir = generate_spec_from_item(args.project_path, item, args.llm_hint)
    print(json.dumps({"result": {"spec_dir": str(spec_dir)}}), flush=True)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Tech Debt Runner")
    parser.add_argument("--project-path", required=True)
    parser.add_argument(
        "--command",
        required=True,
        choices=["scan", "list", "trend", "spec"],
    )
    parser.add_argument("--min-score", default=None)
    parser.add_argument("--item-id", default=None)
    parser.add_argument("--llm-hint", default=None)
    args = parser.parse_args()

    try:
        if args.command == "scan":
            code = _cmd_scan(args)
        elif args.command == "list":
            code = _cmd_list(args)
        elif args.command == "trend":
            code = _cmd_trend(args)
        else:
            code = _cmd_spec(args)
        sys.exit(code)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": str(exc)}), flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
