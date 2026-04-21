"""
Bounty Board core — orchestrate N contestants competing on the same spec.

Each contestant runs in its own isolated worktree with a configurable
(provider, model, prompt_override) triple. Contestants are executed
concurrently via asyncio. A judge then scores each contestant and the
highest-scored worktree is proposed as the winner.

Provider-agnostic: the contestant runner is pluggable. For the default
implementation see `default_contestant_runner`, which dispatches through
`llm_client.acomplete()` so it works with any registered provider
(Anthropic, OpenAI, Gemini, Grok, Ollama, Azure, Copilot, Windsurf,
custom OpenAI-compatible endpoints).
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ─── Data model ────────────────────────────────────────────────────────────────


@dataclass
class ContestantSpec:
    """Inputs describing a single contestant entry."""

    provider: str
    model: str
    profile_id: str | None = None
    prompt_override: str | None = None
    label: str | None = None  # Human-readable label, auto-assigned if None


@dataclass
class Contestant:
    """Live state of a contestant during a bounty run."""

    id: str
    label: str
    provider: str
    model: str
    profile_id: str | None = None
    status: str = "queued"  # queued | running | completed | error | archived | winner
    worktree_path: str | None = None
    output: str = ""
    tokens_used: int = 0
    cost_usd: float = 0.0
    duration_ms: int = 0
    error: str | None = None
    score: float | None = None
    quality_breakdown: dict[str, float] = field(default_factory=dict)
    started_at: int | None = None
    completed_at: int | None = None


@dataclass
class BountyResult:
    """Outcome of a bounty run, returned to callers and persisted to disk."""

    id: str
    spec_id: str
    project_path: str
    contestants: list[Contestant]
    winner_id: str | None = None
    judge_report: str = ""
    judge_rationale: dict[str, str] = field(default_factory=dict)
    created_at: int = field(default_factory=lambda: int(time.time() * 1000))
    completed_at: int | None = None
    status: str = "running"  # running | judging | completed | error

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "specId": self.spec_id,
            "projectPath": self.project_path,
            "contestants": [asdict(c) for c in self.contestants],
            "winnerId": self.winner_id,
            "judgeReport": self.judge_report,
            "judgeRationale": self.judge_rationale,
            "createdAt": self.created_at,
            "completedAt": self.completed_at,
            "status": self.status,
        }


# ─── Runners (pluggable for provider-agnostic execution) ───────────────────────


ContestantRunner = Callable[[Contestant, str, Path], Awaitable[None]]
Judge = Callable[[list[Contestant], str, Path], Awaitable[tuple[str, dict[str, str]]]]


async def default_contestant_runner(
    contestant: Contestant,
    spec_prompt: str,
    worktree: Path,
) -> None:
    """Default contestant runner.

    Dispatches through :mod:`llm_client`, which routes to the correct provider
    based on the contestant's `provider` field. Any registered provider works
    (Anthropic, OpenAI, Google, Grok, Ollama, Azure, Copilot, Windsurf, custom).

    When `llm_client` is unavailable (tests, headless), we fall back to a
    deterministic stub output so the pipeline still exercises scoring/judging.
    """
    prompt = contestant_prompt(contestant, spec_prompt)
    start = time.time()
    contestant.started_at = int(start * 1000)
    contestant.status = "running"

    try:
        try:
            from llm_client import acomplete  # type: ignore

            result = await acomplete(
                provider=contestant.provider,
                model=contestant.model,
                profile_id=contestant.profile_id,
                prompt=prompt,
                working_dir=str(worktree),
            )
            contestant.output = str(result.get("text", ""))
            contestant.tokens_used = int(result.get("tokens", 0))
            contestant.cost_usd = float(result.get("cost_usd", 0.0))
        except ImportError:
            # Provider-agnostic stub fallback for environments without the
            # multi-provider client wired up yet. The judge will still score
            # these equally and fail gracefully.
            contestant.output = (
                f"[stub:{contestant.provider}:{contestant.model}] {prompt[:200]}"
            )
            contestant.tokens_used = len(prompt) // 4
        contestant.status = "completed"
    except Exception as exc:  # noqa: BLE001
        contestant.status = "error"
        contestant.error = str(exc)
        logger.exception(
            "Contestant %s (%s/%s) failed",
            contestant.label,
            contestant.provider,
            contestant.model,
        )
    finally:
        contestant.completed_at = int(time.time() * 1000)
        contestant.duration_ms = max(0, contestant.completed_at - (contestant.started_at or contestant.completed_at))


def contestant_prompt(contestant: Contestant, spec_prompt: str) -> str:
    """Build the per-contestant prompt, optionally adding a variant header."""
    if contestant.provider and contestant.model:
        header = f"# Bounty contestant {contestant.label} ({contestant.provider}:{contestant.model})\n\n"
    else:
        header = ""
    return header + spec_prompt


# ─── Judge ─────────────────────────────────────────────────────────────────────


async def default_judge(
    contestants: list[Contestant],
    spec_prompt: str,
    spec_dir: Path,
) -> tuple[str, dict[str, str]]:
    """Score contestants and return (winner_id, rationale_per_contestant).

    Default heuristic:
      * successful completion  ........ 50 points
      * acceptance criteria coverage .. 30 points (keyword match)
      * output length (signal)  ....... 10 points
      * low latency  .................. 10 points
    """
    scored: list[tuple[Contestant, float]] = []
    rationale: dict[str, str] = {}

    # Extract acceptance criteria bullets from the spec
    criteria: list[str] = []
    for line in spec_prompt.splitlines():
        stripped = line.strip().lstrip("-*0123456789. ").strip()
        if 4 <= len(stripped) <= 120 and any(kw in line.lower() for kw in ("must", "should", "doit", "devrait")):
            criteria.append(stripped.lower())

    max_duration = max((c.duration_ms for c in contestants if c.duration_ms), default=1)

    for c in contestants:
        if c.status != "completed":
            c.score = 0.0
            c.quality_breakdown = {"completion": 0.0, "coverage": 0.0, "signal": 0.0, "latency": 0.0}
            rationale[c.id] = c.error or "Did not complete."
            scored.append((c, 0.0))
            continue

        completion = 50.0
        text = c.output.lower()
        if criteria:
            hits = sum(1 for crit in criteria if crit and crit.split()[0] in text)
            coverage = 30.0 * (hits / max(len(criteria), 1))
        else:
            coverage = 15.0  # no criteria → give a neutral baseline
        signal = 10.0 * min(1.0, len(c.output) / 800.0)
        latency = 10.0 * (1.0 - (c.duration_ms / max(max_duration, 1)))

        total = round(completion + coverage + signal + latency, 2)
        c.score = total
        c.quality_breakdown = {
            "completion": round(completion, 2),
            "coverage": round(coverage, 2),
            "signal": round(signal, 2),
            "latency": round(latency, 2),
        }
        rationale[c.id] = (
            f"completion={completion:.0f} coverage={coverage:.1f} "
            f"signal={signal:.1f} latency={latency:.1f} → {total:.1f}"
        )
        scored.append((c, total))

    scored.sort(key=lambda t: t[1], reverse=True)
    winner_id = scored[0][0].id if scored and scored[0][1] > 0 else ""
    return winner_id, rationale


# ─── Orchestrator ──────────────────────────────────────────────────────────────


class BountyBoard:
    """Orchestrates a single bounty run."""

    def __init__(
        self,
        spec_dir: Path,
        project_path: Path,
        contestants: list[ContestantSpec],
        runner: ContestantRunner | None = None,
        judge: Judge | None = None,
    ) -> None:
        if not contestants:
            raise ValueError("At least one contestant is required")
        self.spec_dir = Path(spec_dir)
        self.project_path = Path(project_path)
        self.runner = runner or default_contestant_runner
        self.judge = judge or default_judge
        self.contestants: list[Contestant] = [
            _materialize(spec, idx) for idx, spec in enumerate(contestants)
        ]
        self.bounty_id = f"bounty-{int(time.time() * 1000)}-{uuid.uuid4().hex[:6]}"

    async def run(self) -> BountyResult:
        spec_prompt = _load_spec_prompt(self.spec_dir)
        worktrees = _prepare_worktrees(self.project_path, self.bounty_id, self.contestants)

        # Run all contestants in parallel.
        await asyncio.gather(
            *[
                self.runner(contestant, spec_prompt, Path(worktrees[contestant.id]))
                for contestant in self.contestants
            ]
        )

        # Judge phase.
        winner_id, rationale = await self.judge(self.contestants, spec_prompt, self.spec_dir)
        for c in self.contestants:
            c.status = "winner" if c.id == winner_id else ("archived" if c.status == "completed" else c.status)

        result = BountyResult(
            id=self.bounty_id,
            spec_id=self.spec_dir.name,
            project_path=str(self.project_path),
            contestants=self.contestants,
            winner_id=winner_id or None,
            judge_report=_format_judge_report(self.contestants, winner_id),
            judge_rationale=rationale,
            completed_at=int(time.time() * 1000),
            status="completed",
        )
        _persist_result(self.spec_dir, result)
        return result


# ─── Helpers ───────────────────────────────────────────────────────────────────


def _materialize(spec: ContestantSpec, idx: int) -> Contestant:
    label = spec.label or chr(ord("A") + idx)
    return Contestant(
        id=f"c-{uuid.uuid4().hex[:8]}",
        label=label,
        provider=spec.provider,
        model=spec.model,
        profile_id=spec.profile_id,
    )


def _load_spec_prompt(spec_dir: Path) -> str:
    """Load the spec content. We look for `spec.md`, falling back to the directory name."""
    spec_md = spec_dir / "spec.md"
    if spec_md.exists():
        try:
            return spec_md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""
    return f"Spec {spec_dir.name}"


def _prepare_worktrees(project_path: Path, bounty_id: str, contestants: list[Contestant]) -> dict[str, str]:
    """Create (or stub) per-contestant isolated directories.

    We intentionally DO NOT call `git worktree add` here to stay runnable in
    test environments without a git context. The caller (or integration test)
    can swap in a runner that creates real worktrees. For the default mode,
    we simply create per-contestant directories under .workpilot/bounty/<id>/.
    """
    base = project_path / ".workpilot" / "bounty" / bounty_id
    base.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}
    for c in contestants:
        wt = base / c.label
        wt.mkdir(parents=True, exist_ok=True)
        c.worktree_path = str(wt)
        paths[c.id] = str(wt)
    return paths


def _format_judge_report(contestants: list[Contestant], winner_id: str | None) -> str:
    lines = ["# Judge report", ""]
    for c in sorted(contestants, key=lambda x: x.score or -1, reverse=True):
        marker = " 🏆" if c.id == winner_id else ""
        lines.append(f"- **{c.label}** ({c.provider}:{c.model}) — score: {c.score}{marker}")
    return "\n".join(lines)


def _persist_result(spec_dir: Path, result: BountyResult) -> None:
    try:
        out_dir = spec_dir / "bounty"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{result.id}.json").write_text(
            json.dumps(result.to_dict(), indent=2), encoding="utf-8"
        )
    except OSError as exc:
        logger.warning("Could not persist bounty result: %s", exc)


# ─── Convenience ───────────────────────────────────────────────────────────────


async def run_bounty(
    spec_dir: Path,
    project_path: Path,
    contestants: list[ContestantSpec],
    runner: ContestantRunner | None = None,
    judge: Judge | None = None,
) -> BountyResult:
    """One-shot helper to run a bounty from inputs."""
    board = BountyBoard(spec_dir, project_path, contestants, runner=runner, judge=judge)
    return await board.run()
