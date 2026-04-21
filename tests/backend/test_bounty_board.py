"""
Bounty Board — unit tests.

Cover:
  - Orchestrator runs N contestants concurrently.
  - Judge picks the best-scored completed contestant.
  - Errored contestants score 0 and do not win.
  - Runner is provider-agnostic: same orchestrator works with heterogeneous
    (provider, model) pairs.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2] / "apps" / "backend"
sys.path.insert(0, str(BACKEND))

from bounty_board import (  # noqa: E402
    BountyBoard,
    Contestant,
    ContestantSpec,
    run_bounty,
)
from bounty_board.board import default_judge  # noqa: E402


def _make_runner(outputs: dict[str, str], fail: set[str] | None = None):
    """Return a fake contestant runner that fills outputs deterministically."""
    fail = fail or set()

    async def _runner(contestant: Contestant, spec_prompt: str, worktree: Path) -> None:
        # ensure spec prompt made it through
        assert spec_prompt
        assert worktree.exists()
        if contestant.label in fail:
            contestant.status = "error"
            contestant.error = "forced failure"
            return
        contestant.status = "completed"
        contestant.output = outputs.get(contestant.label, "")
        contestant.tokens_used = len(contestant.output) // 4
        contestant.duration_ms = 10

    return _runner


@pytest.fixture()
def spec_dir(tmp_path: Path) -> Path:
    spec = tmp_path / "specs" / "001-demo"
    spec.mkdir(parents=True)
    (spec / "spec.md").write_text(
        "# Demo spec\n\n"
        "- The system must emit a hello message.\n"
        "- Tests should pass.\n",
        encoding="utf-8",
    )
    return spec


@pytest.fixture()
def project_path(tmp_path: Path) -> Path:
    return tmp_path


def test_bounty_runs_all_contestants_in_parallel(spec_dir, project_path):
    contestants = [
        ContestantSpec(provider="anthropic", model="claude-sonnet-4-6"),
        ContestantSpec(provider="openai", model="gpt-4o"),
        ContestantSpec(provider="ollama", model="llama3.3"),
    ]
    outputs = {
        "A": "The system will emit a hello message and tests will pass cleanly with proper coverage.",
        "B": "Short.",
        "C": "hello",
    }
    board = BountyBoard(
        spec_dir=spec_dir,
        project_path=project_path,
        contestants=contestants,
        runner=_make_runner(outputs),
    )
    result = asyncio.run(board.run())

    assert result.status == "completed"
    assert len(result.contestants) == 3
    assert all(c.worktree_path and Path(c.worktree_path).exists() for c in result.contestants)
    assert all(c.score is not None for c in result.contestants)
    # winner should be the most substantive one (A)
    assert result.winner_id is not None
    winner = next(c for c in result.contestants if c.id == result.winner_id)
    assert winner.label == "A"
    assert winner.status == "winner"


def test_errored_contestants_do_not_win(spec_dir, project_path):
    contestants = [
        ContestantSpec(provider="anthropic", model="claude-sonnet-4-6", label="A"),
        ContestantSpec(provider="openai", model="gpt-4o", label="B"),
    ]
    outputs = {"A": "", "B": "This is a valid completion with must-have behaviour."}
    runner = _make_runner(outputs, fail={"A"})
    result = asyncio.run(
        run_bounty(spec_dir, project_path, contestants, runner=runner)
    )
    winner = next(c for c in result.contestants if c.id == result.winner_id)
    assert winner.label == "B"
    loser = next(c for c in result.contestants if c.label == "A")
    assert loser.status == "error"
    assert (loser.score or 0) == 0


def test_bounty_provider_agnostic_mix(spec_dir, project_path):
    """Orchestrator accepts any (provider, model) — no provider-specific code path."""
    contestants = [
        ContestantSpec(provider=p, model=m)
        for p, m in [
            ("anthropic", "claude-sonnet-4-6"),
            ("openai", "gpt-4o"),
            ("google", "gemini-2.5-pro"),
            ("grok", "grok-2"),
            ("ollama", "llama3.3"),
            ("copilot", "gpt-4o"),
            ("windsurf", "swe-1.5"),
        ]
    ]
    outputs = {c.label or chr(ord("A") + i): "result must pass." for i, c in enumerate(contestants)}
    # ContestantSpec labels auto-assigned by the orchestrator; build by index.
    outputs_by_index = {chr(ord("A") + i): f"result {i} must pass." for i in range(len(contestants))}
    runner = _make_runner(outputs_by_index)
    result = asyncio.run(run_bounty(spec_dir, project_path, contestants, runner=runner))
    assert len(result.contestants) == 7
    providers = {c.provider for c in result.contestants}
    assert providers == {
        "anthropic", "openai", "google", "grok", "ollama", "copilot", "windsurf",
    }


def test_persists_result_to_spec_dir(spec_dir, project_path):
    contestants = [ContestantSpec(provider="anthropic", model="claude-haiku-4-6")]
    runner = _make_runner({"A": "must pass."})
    result = asyncio.run(run_bounty(spec_dir, project_path, contestants, runner=runner))

    archive_dir = spec_dir / "bounty"
    assert archive_dir.exists()
    files = list(archive_dir.glob("*.json"))
    assert len(files) == 1
    payload = json.loads(files[0].read_text(encoding="utf-8"))
    assert payload["id"] == result.id
    assert payload["status"] == "completed"
    assert len(payload["contestants"]) == 1


def test_default_judge_ranks_longer_more_relevant_output_higher(spec_dir):
    a = Contestant(id="a", label="A", provider="x", model="m", status="completed",
                   output="must", duration_ms=10)
    b = Contestant(id="b", label="B", provider="y", model="n", status="completed",
                   output="must " * 200 + " should " * 40, duration_ms=5)
    spec = (spec_dir / "spec.md").read_text(encoding="utf-8")
    winner_id, rationale = asyncio.run(default_judge([a, b], spec, spec_dir))
    assert winner_id == "b"
    assert "a" in rationale and "b" in rationale


def test_empty_contestants_rejected(spec_dir, project_path):
    with pytest.raises(ValueError):
        BountyBoard(spec_dir, project_path, contestants=[])
