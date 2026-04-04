#!/usr/bin/env python3
"""
Agent Time Travel Runner — CLI entry point for time travel operations.

Supports:
- Generating checkpoints for a completed session
- Scoring decisions in a session
- Forking a session at a checkpoint and re-executing with any LLM provider
- Listing checkpoints and forks

Works with any LLM provider: the fork context is provider-agnostic, so the
actual re-execution can target Anthropic, OpenAI, Google, Ollama, or any
compatible endpoint.

Example:
    # Generate checkpoints for a session
    python time_travel_runner.py --session-id abc123 --action checkpoints

    # Score decisions
    python time_travel_runner.py --session-id abc123 --action score

    # Fork and re-execute with a different model
    python time_travel_runner.py --session-id abc123 --action fork \\
        --checkpoint-id cp_xyz --modified-prompt "Use async/await instead" \\
        --fork-provider openai --fork-model gpt-4o

    # Get fork context (for external execution)
    python time_travel_runner.py --action fork-context --fork-id fork_abc
"""

import argparse
import json
import sys
from pathlib import Path

# Ensure the backend root is on sys.path
_backend_root = Path(__file__).resolve().parent.parent
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Agent Time Travel Runner")
    parser.add_argument(
        "--action",
        type=str,
        required=True,
        choices=[
            "checkpoints",
            "score",
            "heatmap",
            "fork",
            "fork-context",
            "list-forks",
        ],
        help="Time travel action to perform",
    )
    parser.add_argument("--session-id", type=str, help="Replay session ID")
    parser.add_argument("--checkpoint-id", type=str, help="Checkpoint ID (for fork)")
    parser.add_argument("--fork-id", type=str, help="Fork ID (for fork-context)")
    parser.add_argument(
        "--modified-prompt", type=str, default="", help="Modified prompt for fork"
    )
    parser.add_argument(
        "--additional-instructions", type=str, default="", help="Extra instructions"
    )
    parser.add_argument(
        "--fork-provider", type=str, default="", help="LLM provider for fork"
    )
    parser.add_argument(
        "--fork-model", type=str, default="", help="Model name for fork"
    )
    parser.add_argument(
        "--fork-api-key", type=str, default="", help="API key (optional)"
    )
    parser.add_argument("--fork-base-url", type=str, default="", help="Custom base URL")
    parser.add_argument("--output", type=str, choices=["json", "text"], default="json")

    args = parser.parse_args()

    from replay.models import ForkRequest
    from replay.time_travel import get_time_travel_engine

    engine = get_time_travel_engine()

    if args.action == "checkpoints":
        if not args.session_id:
            print("Error: --session-id required", file=sys.stderr)
            return 1
        checkpoints = engine.create_checkpoints_for_session(args.session_id)
        result = {
            "success": True,
            "action": "checkpoints",
            "session_id": args.session_id,
            "count": len(checkpoints),
            "checkpoints": [cp.to_dict() for cp in checkpoints],
        }

    elif args.action == "score":
        if not args.session_id:
            print("Error: --session-id required", file=sys.stderr)
            return 1
        scores = engine.score_decisions(args.session_id)
        result = {
            "success": True,
            "action": "score",
            "session_id": args.session_id,
            "count": len(scores),
            "critical_count": sum(1 for s in scores if s.is_critical),
            "scores": [s.to_dict() for s in scores],
        }

    elif args.action == "heatmap":
        if not args.session_id:
            print("Error: --session-id required", file=sys.stderr)
            return 1
        heatmap = engine.get_decision_heatmap(args.session_id)
        result = {"success": True, "action": "heatmap", **heatmap}

    elif args.action == "fork":
        if not args.session_id or not args.checkpoint_id:
            print("Error: --session-id and --checkpoint-id required", file=sys.stderr)
            return 1
        fork_request = ForkRequest(
            checkpoint_id=args.checkpoint_id,
            session_id=args.session_id,
            modified_prompt=args.modified_prompt,
            additional_instructions=args.additional_instructions,
            fork_provider=args.fork_provider,
            fork_model=args.fork_model,
            fork_api_key=args.fork_api_key,
            fork_base_url=args.fork_base_url,
        )
        fork = engine.create_fork(fork_request)
        context = engine.get_fork_context(fork.fork_id)
        result = {
            "success": True,
            "action": "fork",
            "fork": fork.to_dict(),
            "context_ready": context is not None,
        }

    elif args.action == "fork-context":
        if not args.fork_id:
            print("Error: --fork-id required", file=sys.stderr)
            return 1
        context = engine.get_fork_context(args.fork_id)
        if not context:
            print(f"Error: Fork not found: {args.fork_id}", file=sys.stderr)
            return 1
        result = {"success": True, "action": "fork-context", "context": context}

    elif args.action == "list-forks":
        forks = engine.list_forks(args.session_id)
        result = {
            "success": True,
            "action": "list-forks",
            "count": len(forks),
            "forks": [f.to_dict() for f in forks],
        }

    else:
        print(f"Error: Unknown action: {args.action}", file=sys.stderr)
        return 1

    if args.output == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        _print_text(result)

    return 0


def _print_text(result: dict) -> None:
    """Print result in human-readable format."""
    action = result.get("action", "")
    print(f"\n{'=' * 60}")
    print(f" Agent Time Travel - {action.upper()}")
    print(f"{'=' * 60}")

    if action == "checkpoints":
        print(f"\nSession: {result['session_id']}")
        print(f"Checkpoints created: {result['count']}")
        for cp in result.get("checkpoints", []):
            print(
                f"  [{cp['step_index']:3d}] {cp['checkpoint_type']:20s} - {cp['label']}"
            )

    elif action == "score":
        print(f"\nSession: {result['session_id']}")
        print(
            f"Decisions scored: {result['count']} ({result['critical_count']} critical)"
        )
        for sc in result.get("scores", []):
            critical = " ** CRITICAL **" if sc["is_critical"] else ""
            print(
                f"  [{sc['step_index']:3d}] confidence={sc['confidence_score']:.2f} "
                f"impact={sc['impact_score']:.2f}{critical}"
            )
            for factor in sc.get("factors", []):
                print(f"        - {factor}")

    elif action == "fork":
        fork = result.get("fork", {})
        print(f"\nFork created: {fork.get('fork_id', 'N/A')}")
        print(f"Original session: {fork.get('original_session_id', 'N/A')}")
        print(f"Checkpoint: {fork.get('checkpoint_id', 'N/A')}")
        print(f"Status: {fork.get('status', 'N/A')}")
        req = fork.get("fork_request", {})
        if req.get("fork_provider"):
            print(f"Target provider: {req['fork_provider']}")
        if req.get("fork_model"):
            print(f"Target model: {req['fork_model']}")

    elif action == "list-forks":
        print(f"\nForks: {result['count']}")
        for f in result.get("forks", []):
            print(
                f"  {f['fork_id'][:12]} - session={f['original_session_id'][:12]} status={f['status']}"
            )

    print()


if __name__ == "__main__":
    exit(main())
