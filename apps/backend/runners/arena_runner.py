"""
Arena Mode Runner — Blind A/B model comparison across the full pipeline.

Runs the same task against multiple configured AI models in parallel,
streams results anonymously (Model A / B / C / D), accumulates votes,
and provides auto-routing recommendations based on accumulated data.

Usage (CLI):
    python arena_runner.py --task-type coding --prompt "Write a binary search function" \
                           --profiles profile-1,profile-2

Usage (from agent):
    from runners.arena_runner import run_arena_battle
    result = await run_arena_battle(task_type, prompt, profile_ids, project_dir)
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections.abc import AsyncGenerator
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

# ─── Types ─────────────────────────────────────────────────────────────────────

ArenaTaskType = Literal["coding", "review", "test", "planning", "spec", "insights"]
ArenaLabel = Literal["A", "B", "C", "D"]
LABELS: list[ArenaLabel] = ["A", "B", "C", "D"]


@dataclass
class ArenaParticipant:
    label: ArenaLabel
    profile_id: str
    model_name: str
    provider: str
    status: str = "waiting"  # waiting | running | completed | error
    output: str = ""
    tokens_used: int = 0
    cost_usd: float = 0.0
    duration_ms: int = 0
    error: str | None = None


@dataclass
class ArenaBattle:
    id: str
    task_type: ArenaTaskType
    prompt: str
    participants: list[ArenaParticipant]
    status: str = "running"  # running | voting | completed | error
    created_at: int = field(default_factory=lambda: int(time.time() * 1000))
    completed_at: int | None = None
    voted_at: int | None = None
    winner_label: ArenaLabel | None = None
    revealed: bool = False


@dataclass
class ArenaVote:
    battle_id: str
    task_type: ArenaTaskType
    winner_label: ArenaLabel
    winner_profile_id: str
    voted_at: int = field(default_factory=lambda: int(time.time() * 1000))


@dataclass
class ArenaModelStats:
    profile_id: str
    model_name: str
    provider: str
    wins: int = 0
    losses: int = 0
    total: int = 0
    win_rate: float = 0.0
    avg_cost_per_battle: float = 0.0
    total_cost_usd: float = 0.0
    avg_duration_ms: float = 0.0
    by_task_type: dict[str, dict] = field(default_factory=dict)


# ─── Storage ────────────────────────────────────────────────────────────────────


def _get_arena_data_dir() -> Path:
    """Returns the arena data directory, creating it if needed."""
    data_dir = Path.home() / ".auto-claude" / "arena"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def _load_battles() -> list[dict]:
    path = _get_arena_data_dir() / "battles.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text())
    except Exception:
        return []


def _save_battles(battles: list[dict]) -> None:
    path = _get_arena_data_dir() / "battles.json"
    path.write_text(json.dumps(battles[:100], indent=2))


def _load_votes() -> list[dict]:
    path = _get_arena_data_dir() / "votes.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text())
    except Exception:
        return []


def _save_votes(votes: list[dict]) -> None:
    path = _get_arena_data_dir() / "votes.json"
    path.write_text(json.dumps(votes, indent=2))


# ─── Analytics ──────────────────────────────────────────────────────────────────

TASK_TYPES: list[ArenaTaskType] = [
    "coding",
    "review",
    "test",
    "planning",
    "spec",
    "insights",
]


def _get_or_create_model_stats(
    model_map: dict[str, ArenaModelStats], participant: dict
) -> ArenaModelStats:
    """Get existing model stats or create new ones for a participant."""
    pid = participant["profile_id"]
    if pid not in model_map:
        model_map[pid] = ArenaModelStats(
            profile_id=pid,
            model_name=participant.get("model_name", pid),
            provider=participant.get("provider", "unknown"),
        )
    return model_map[pid]


def _update_participant_stats(
    stats: ArenaModelStats, participant: dict, is_winner: bool
) -> None:
    """Update basic statistics for a participant."""
    stats.total += 1
    if is_winner:
        stats.wins += 1
    else:
        stats.losses += 1

    cost = participant.get("cost_usd", 0.0)
    dur = participant.get("duration_ms", 0)
    stats.total_cost_usd += cost
    stats.avg_duration_ms = (
        stats.avg_duration_ms * (stats.total - 1) + dur
    ) / stats.total


def _update_task_type_stats(
    stats: ArenaModelStats, task_type: str, participant: dict, is_winner: bool
) -> None:
    """Update task type specific statistics."""
    if task_type not in stats.by_task_type:
        stats.by_task_type[task_type] = {
            "wins": 0,
            "total": 0,
            "win_rate": 0.0,
            "avg_cost_usd": 0.0,
        }

    tt_data = stats.by_task_type[task_type]
    tt_data["total"] += 1
    if is_winner:
        tt_data["wins"] += 1

    tt_data["win_rate"] = tt_data["wins"] / tt_data["total"]
    cost = participant.get("cost_usd", 0.0)
    tt_data["avg_cost_usd"] = (
        tt_data["avg_cost_usd"] * (tt_data["total"] - 1) + cost
    ) / tt_data["total"]


def _finalize_model_stats(model_map: dict[str, ArenaModelStats]) -> None:
    """Calculate final derived statistics for all models."""
    for stats in model_map.values():
        stats.win_rate = stats.wins / stats.total if stats.total > 0 else 0.0
        stats.avg_cost_per_battle = (
            stats.total_cost_usd / stats.total if stats.total > 0 else 0.0
        )


def _determine_confidence_level(sample_size: int) -> str:
    """Determine confidence level based on sample size."""
    if sample_size >= 10:
        return "high"
    elif sample_size >= 5:
        return "medium"
    else:
        return "low"


def _build_auto_routing_recommendations(
    model_map: dict[str, ArenaModelStats],
) -> dict[str, dict]:
    """Build auto-routing recommendations for each task type."""
    auto_routing: dict[str, dict] = {}

    for task_type in TASK_TYPES:
        best: ArenaModelStats | None = None
        best_wins = 0

        for stats in model_map.values():
            tt_data = stats.by_task_type.get(task_type)
            if not tt_data or tt_data["total"] < 2:
                continue
            if tt_data["wins"] > best_wins:
                best_wins = tt_data["wins"]
                best = stats

        if best:
            tt_data = best.by_task_type[task_type]
            confidence = _determine_confidence_level(tt_data["total"])

            auto_routing[task_type] = {
                "profile_id": best.profile_id,
                "model_name": best.model_name,
                "win_rate": tt_data["win_rate"],
                "confidence": confidence,
            }

    return auto_routing


def compute_analytics(battles: list[dict], votes: list[dict]) -> dict:
    """Build win-rate analytics from persisted battles and votes."""
    model_map: dict[str, ArenaModelStats] = {}

    # Process battles and collect statistics
    for battle in battles:
        if battle.get("status") != "completed" or not battle.get("winner_label"):
            continue

        task_type = battle.get("task_type", "coding")

        for participant in battle.get("participants", []):
            is_winner = participant["label"] == battle["winner_label"]
            stats = _get_or_create_model_stats(model_map, participant)
            _update_participant_stats(stats, participant, is_winner)
            _update_task_type_stats(stats, task_type, participant, is_winner)

    # Finalize statistics
    _finalize_model_stats(model_map)

    # Build recommendations
    auto_routing = _build_auto_routing_recommendations(model_map)

    return {
        "total_battles": len(battles),
        "total_votes": len(votes),
        "by_model": [
            asdict(s) for s in sorted(model_map.values(), key=lambda x: -x.win_rate)
        ],
        "auto_routing_recommendations": auto_routing,
        "last_updated": int(time.time() * 1000),
    }


# ─── Battle Execution ────────────────────────────────────────────────────────────

SYSTEM_PROMPTS: dict[str, str] = {
    "coding": (
        "You are an expert software engineer. Provide clean, well-commented, production-ready code. "
        "Explain your approach and any trade-offs."
    ),
    "review": (
        "You are a senior code reviewer with 10+ years of experience. Provide a thorough, constructive review "
        "covering correctness, performance, security, maintainability, and best practices."
    ),
    "test": (
        "You are a QA engineer specializing in test-driven development. Write comprehensive test suites "
        "covering happy paths, edge cases, and error scenarios."
    ),
    "planning": (
        "You are a technical architect and project planner. Create detailed, actionable implementation plans "
        "with clear phases, milestones, and risk considerations."
    ),
    "spec": (
        "You are a product manager and solutions architect. Write comprehensive technical specifications "
        "covering requirements, architecture, API contracts, and acceptance criteria."
    ),
    "insights": (
        "You are a codebase analyst and technical advisor. Provide deep insights about code architecture, "
        "design patterns, anti-patterns, and concrete improvement recommendations."
    ),
}


async def run_participant(
    participant: ArenaParticipant,
    task_type: ArenaTaskType,
    prompt: str,
    project_dir: str | None = None,
) -> AsyncGenerator[dict, None]:
    """
    Run a single arena participant and yield streaming events.

    In production this integrates with core.client (Claude Agent SDK) using
    the participant's profile_id to select credentials/model.
    The generator yields dicts with keys: type, label, chunk, tokens_used, cost_usd
    """
    start_time = time.time()

    try:
        # Import the client factory — uses the configured profile
        from core.client import create_client

        system_prompt = SYSTEM_PROMPTS.get(task_type, SYSTEM_PROMPTS["coding"])

        # In a real run, we'd pass profile_id to select model/credentials.
        # For now we use the default client which reads from project settings.
        async with create_client(
            project_dir=project_dir or ".",
            spec_dir=None,
            agent_type="insights",  # lightweight agent type
        ) as client:
            full_response = ""
            async for chunk in client.stream(
                system=system_prompt,
                user=prompt,
            ):
                full_response += chunk
                tokens_so_far = len(full_response.split()) * 1.3  # rough estimate
                cost_so_far = tokens_so_far * 0.000003
                yield {
                    "type": "chunk",
                    "label": participant.label,
                    "chunk": chunk,
                    "tokens_used": int(tokens_so_far),
                    "cost_usd": cost_so_far,
                }

            duration_ms = int((time.time() - start_time) * 1000)
            tokens_used = int(len(full_response.split()) * 1.3)
            cost_usd = tokens_used * 0.000003

            yield {
                "type": "result",
                "label": participant.label,
                "output": full_response,
                "tokens_used": tokens_used,
                "cost_usd": cost_usd,
                "duration_ms": duration_ms,
            }

    except ImportError:
        # Fallback when running outside of the full backend environment
        logger.warning("[Arena] Core client not available, using fallback mode")
        await asyncio.sleep(0.5)
        mock_output = _generate_mock_output(task_type, prompt, participant.label)

        for chunk in mock_output.split("\n"):
            chunk += "\n"
            await asyncio.sleep(0.1)
            yield {
                "type": "chunk",
                "label": participant.label,
                "chunk": chunk,
                "tokens_used": len(chunk.split()),
                "cost_usd": len(chunk.split()) * 0.000003,
            }

        duration_ms = int((time.time() - start_time) * 1000)
        tokens_used = int(len(mock_output.split()) * 1.3)
        yield {
            "type": "result",
            "label": participant.label,
            "output": mock_output,
            "tokens_used": tokens_used,
            "cost_usd": tokens_used * 0.000003,
            "duration_ms": duration_ms,
        }

    except Exception as exc:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error("[Arena] Participant %s failed: %s", participant.label, exc)
        yield {
            "type": "error",
            "label": participant.label,
            "error": str(exc),
            "duration_ms": duration_ms,
        }


def _generate_mock_output(
    task_type: ArenaTaskType, prompt: str, label: ArenaLabel
) -> str:
    """Generate deterministic mock output for testing/demo mode."""
    templates = {
        "coding": f"```python\n# Solution for: {prompt[:50]}\ndef solution():\n    # Implementation by Model {label}\n    result = []\n    # ... core logic ...\n    return result\n```\n\nThis implementation uses an efficient approach with O(n) time complexity.",
        "review": f"## Code Review — Model {label}\n\n### Strengths\n- Clean structure\n- Good naming conventions\n\n### Issues Found\n1. Missing input validation\n2. No error handling for edge cases\n3. Consider adding type hints\n\n### Recommendation\nAdd comprehensive error handling and input validation.",
        "test": f"```python\nimport pytest\n\nclass TestSolution:\n    # Tests by Model {label}\n    def test_happy_path(self):\n        assert solution([1, 2, 3]) == [1, 2, 3]\n\n    def test_empty_input(self):\n        assert solution([]) == []\n\n    def test_edge_case(self):\n        with pytest.raises(ValueError):\n            solution(None)\n```",
        "planning": f"## Implementation Plan — Model {label}\n\n### Phase 1: Foundation\n1. Set up project structure\n2. Define data models\n3. Configure dependencies\n\n### Phase 2: Core Implementation\n1. Build business logic layer\n2. Implement API endpoints\n3. Add data persistence\n\n### Phase 3: Quality\n1. Write unit tests\n2. Add integration tests\n3. Performance optimization",
        "spec": f"## Technical Specification — Model {label}\n\n### Overview\nThis feature addresses: {prompt[:80]}\n\n### Functional Requirements\n- FR-01: System must...\n- FR-02: Users should be able to...\n\n### Non-Functional Requirements\n- Performance: < 200ms response time\n- Reliability: 99.9% uptime\n\n### Architecture\nLayered architecture with clear separation of concerns.",
        "insights": f"## Codebase Analysis — Model {label}\n\n### Key Patterns Detected\n- Event-driven architecture\n- Repository pattern for data access\n- Command/Query separation\n\n### Improvement Opportunities\n1. **Performance**: Add caching for frequent queries\n2. **Security**: Validate all user inputs at boundaries\n3. **Maintainability**: Extract shared utilities to reduce duplication\n\n### Metrics\n- Estimated technical debt: Medium\n- Test coverage: Needs improvement",
    }
    return templates.get(task_type, f"Response from Model {label}")


async def run_arena_battle(
    task_type: ArenaTaskType,
    prompt: str,
    profile_ids: list[str],
    project_dir: str | None = None,
    on_progress=None,
) -> ArenaBattle:
    """
    Run an arena battle with multiple models in parallel.

    Args:
        task_type: Category of task being evaluated
        prompt: The prompt to send to all models
        profile_ids: List of profile IDs to use (2-4)
        project_dir: Optional project directory for context
        on_progress: Optional async callback(event_dict) for streaming

    Returns:
        Completed ArenaBattle with all participant results
    """
    if len(profile_ids) < 2:
        raise ValueError("At least 2 profiles required for an arena battle")

    battle_id = f"arena-{int(time.time() * 1000)}-{uuid.uuid4().hex[:6]}"
    participants = [
        ArenaParticipant(
            label=LABELS[i],
            profile_id=pid,
            model_name=f"Model {LABELS[i]}",  # Anonymized until vote
            provider="unknown",
        )
        for i, pid in enumerate(profile_ids[:4])
    ]

    battle = ArenaBattle(
        id=battle_id,
        task_type=task_type,
        prompt=prompt,
        participants=participants,
    )

    logger.info(
        "[Arena] Starting battle %s with %d models", battle_id, len(participants)
    )

    # Run all participants in parallel
    async def run_one(participant: ArenaParticipant) -> None:
        async for event in run_participant(participant, task_type, prompt, project_dir):
            if on_progress:
                await on_progress(event)
            if event["type"] == "result":
                participant.output = event["output"]
                participant.tokens_used = event["tokens_used"]
                participant.cost_usd = event["cost_usd"]
                participant.duration_ms = event["duration_ms"]
                participant.status = "completed"
            elif event["type"] == "error":
                participant.error = event.get("error")
                participant.duration_ms = event.get("duration_ms", 0)
                participant.status = "error"

    await asyncio.gather(*[run_one(p) for p in participants])

    battle.status = "voting"
    battle.completed_at = int(time.time() * 1000)

    # Persist the battle (pre-vote)
    battles = _load_battles()
    battles.insert(0, {**asdict(battle)})
    _save_battles(battles)

    logger.info("[Arena] Battle %s completed, awaiting vote", battle_id)
    return battle


def record_vote(
    battle_id: str,
    winner_label: ArenaLabel,
    winner_profile_id: str,
    task_type: ArenaTaskType,
) -> None:
    """Record a user vote and update the battle record."""
    # Update battle
    battles = _load_battles()
    for b in battles:
        if b["id"] == battle_id:
            b["status"] = "completed"
            b["winner_label"] = winner_label
            b["voted_at"] = int(time.time() * 1000)
            b["revealed"] = True
            break
    _save_battles(battles)

    # Persist vote
    vote = ArenaVote(
        battle_id=battle_id,
        task_type=task_type,
        winner_label=winner_label,
        winner_profile_id=winner_profile_id,
    )
    votes = _load_votes()
    votes.insert(0, asdict(vote))
    _save_votes(votes)

    logger.info("[Arena] Vote recorded: battle=%s, winner=%s", battle_id, winner_label)


def get_analytics() -> dict:
    """Return aggregated analytics from all battles and votes."""
    battles = _load_battles()
    votes = _load_votes()
    return compute_analytics(battles, votes)


# ─── CLI entry-point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Arena Mode — Blind A/B model comparison"
    )
    parser.add_argument(
        "--task-type", choices=list(SYSTEM_PROMPTS.keys()), default="coding"
    )
    parser.add_argument("--prompt", required=True, help="Prompt to send to all models")
    parser.add_argument(
        "--profiles",
        required=True,
        help="Comma-separated list of profile IDs (min 2, max 4)",
    )
    parser.add_argument(
        "--project-dir", default=None, help="Project directory for context"
    )
    args = parser.parse_args()

    profile_ids = [p.strip() for p in args.profiles.split(",")]

    async def main():
        def on_progress(event: dict) -> None:
            if event["type"] == "chunk":
                print(f"[Model {event['label']}] {event['chunk']}", end="", flush=True)
            elif event["type"] == "result":
                print(
                    f"\n[Model {event['label']}] DONE — {event['tokens_used']} tokens, ${event['cost_usd']:.5f}"
                )
            elif event["type"] == "error":
                print(f"\n[Model {event['label']}] ERROR: {event.get('error')}")

        def async_progress(event: dict) -> None:
            on_progress(event)

        battle = await run_arena_battle(
            task_type=args.task_type,
            prompt=args.prompt,
            profile_ids=profile_ids,
            project_dir=args.project_dir,
            on_progress=async_progress,
        )

        print("\n\n=== BATTLE COMPLETE ===")
        for p in battle.participants:
            print(
                f"Model {p.label}: {p.tokens_used} tokens, ${p.cost_usd:.5f}, {p.duration_ms}ms"
            )

        print("\nAnalytics summary:")
        analytics = get_analytics()
        print(json.dumps(analytics, indent=2))

    asyncio.run(main())
