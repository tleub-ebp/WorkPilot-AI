"""
Swarm Mode Runner — Multi-Agent Parallel Execution
===================================================

Entry point for the Electron frontend to launch swarm execution.
Analyzes subtask dependencies, schedules waves, and orchestrates
parallel agent execution with semantic merge between waves.

Usage (CLI):
    python swarm_runner.py --spec 001-feature --project-dir /path/to/project

Usage (from Electron):
    Spawned as subprocess via agent-queue.ts with stdout event parsing.

Events emitted (stdout):
    __SWARM_EVENT__:{...}  — Swarm-specific events
    __EXEC_PHASE__:{...}   — Standard phase events for progress tracking
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

# Add the backend directory to sys.path for imports
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from agents.swarm.dependency_analyzer import DependencyAnalyzer
from agents.swarm.orchestrator import SwarmOrchestrator
from agents.swarm.types import SwarmConfig, SwarmPhase
from agents.swarm.wave_executor import emit_swarm_event

logger = logging.getLogger(__name__)


def find_spec_dir(project_dir: Path, spec_id: str) -> Path | None:
    """Find the spec directory by ID or name."""
    specs_dir = project_dir / ".workpilot" / "specs"
    if not specs_dir.exists():
        return None

    # Direct match
    direct = specs_dir / spec_id
    if direct.exists():
        return direct

    # Prefix match (e.g., "001" matches "001-implement-feature")
    for child in sorted(specs_dir.iterdir()):
        if child.is_dir() and child.name.startswith(spec_id):
            return child

    return None


async def run_swarm(
    project_dir: Path,
    spec_dir: Path,
    config: SwarmConfig | None = None,
    model: str | None = None,
    analyze_only: bool = False,
) -> dict:
    """
    Run the swarm execution pipeline.

    Args:
        project_dir: Root directory of the project
        spec_dir: Spec directory containing implementation_plan.json
        config: Swarm configuration (uses defaults if None)
        model: Model override for agents
        analyze_only: If True, only analyze dependencies without executing

    Returns:
        Dict with execution results
    """
    config = config or SwarmConfig()
    started_at = time.time()

    emit_swarm_event(
        "swarm_started",
        {
            "project_dir": str(project_dir),
            "spec_dir": str(spec_dir),
            "config": config.to_dict(),
            "analyze_only": analyze_only,
        },
    )

    # ── Analyze dependencies ─────────────────────────────────────
    plan_file = spec_dir / "implementation_plan.json"
    if not plan_file.exists():
        emit_swarm_event("swarm_failed", {"error": "No implementation_plan.json found"})
        return {"success": False, "error": "No implementation_plan.json found"}

    with open(plan_file, encoding="utf-8") as f:
        plan = json.load(f)

    analyzer = DependencyAnalyzer(max_parallel=config.max_parallel_agents)
    waves, nodes = analyzer.analyze(plan)
    stats = analyzer.get_parallelism_stats(waves)

    print(f"\n{'=' * 60}", flush=True)
    print("  SWARM MODE — Dependency Analysis", flush=True)
    print(f"{'=' * 60}", flush=True)
    print(f"  Subtasks:      {stats['total_subtasks']}", flush=True)
    print(f"  Waves:         {stats['total_waves']}", flush=True)
    print(f"  Max parallel:  {stats['max_parallelism']}", flush=True)
    print(f"  Avg parallel:  {stats['avg_parallelism']:.1f}", flush=True)
    print(f"  Est. speedup:  {stats['speedup_estimate']:.1f}x", flush=True)
    print(f"{'=' * 60}\n", flush=True)

    for wave in waves:
        subtask_names = []
        for sid in wave.subtask_ids:
            node = nodes.get(sid)
            desc = node.description[:50] if node else sid
            subtask_names.append(f"    [{sid}] {desc}")
        print(f"  Wave {wave.index + 1}:", flush=True)
        for name in subtask_names:
            print(name, flush=True)
        print(flush=True)

    emit_swarm_event(
        "analysis_complete",
        {
            "total_subtasks": stats["total_subtasks"],
            "total_waves": stats["total_waves"],
            "parallelism_stats": stats,
            "waves": [w.to_dict() for w in waves],
        },
    )

    if analyze_only:
        return {
            "success": True,
            "analyze_only": True,
            "stats": stats,
            "waves": [w.to_dict() for w in waves],
            "nodes": {k: v.to_dict() for k, v in nodes.items()},
        }

    # ── Execute swarm ────────────────────────────────────────────
    orchestrator = SwarmOrchestrator(
        project_dir=project_dir,
        spec_dir=spec_dir,
        config=config,
        model=model,
    )

    status = await orchestrator.run()

    duration = time.time() - started_at

    print(f"\n{'=' * 60}", flush=True)
    print("  SWARM MODE — Execution Complete", flush=True)
    print(f"{'=' * 60}", flush=True)
    print(f"  Status:    {status.phase.value}", flush=True)
    print(
        f"  Completed: {status.completed_subtasks}/{status.total_subtasks}", flush=True
    )
    print(f"  Failed:    {status.failed_subtasks}", flush=True)
    print(f"  Duration:  {duration:.1f}s", flush=True)
    print(f"{'=' * 60}\n", flush=True)

    return {
        "success": status.phase == SwarmPhase.COMPLETE,
        "status": status.to_dict(),
        "duration_seconds": duration,
    }


# ─── CLI entry-point ─────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Swarm Mode — Multi-Agent Parallel Execution"
    )
    parser.add_argument(
        "--spec",
        required=True,
        help="Spec ID or name (e.g., '001' or '001-implement-feature')",
    )
    parser.add_argument(
        "--project-dir",
        default=os.getcwd(),
        help="Project root directory (default: cwd)",
    )
    parser.add_argument(
        "--max-parallel",
        type=int,
        default=4,
        help="Maximum parallel agents per wave (default: 4)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model override for all agents",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on first subtask failure",
    )
    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="Only analyze dependencies, don't execute",
    )
    parser.add_argument(
        "--no-merge",
        action="store_true",
        help="Skip semantic merge between waves",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run — don't write any files during merge",
    )

    args = parser.parse_args()
    project_dir = Path(args.project_dir).resolve()

    # Find spec directory
    spec_dir = find_spec_dir(project_dir, args.spec)
    if not spec_dir:
        print(
            f"Error: Spec '{args.spec}' not found in {project_dir / '.workpilot' / 'specs'}"
        )
        sys.exit(1)

    config = SwarmConfig(
        max_parallel_agents=args.max_parallel,
        fail_fast=args.fail_fast,
        merge_after_each_wave=not args.no_merge,
        dry_run=args.dry_run,
    )

    result = asyncio.run(
        run_swarm(
            project_dir=project_dir,
            spec_dir=spec_dir,
            config=config,
            model=args.model,
            analyze_only=args.analyze_only,
        )
    )

    if not result.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()
