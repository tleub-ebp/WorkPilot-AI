"""Tests for the Cognitive Context Optimizer."""

from __future__ import annotations

from pathlib import Path

import pytest
from cognitive_context import (
    CognitiveContextOptimizer,
    estimate_tokens,
)


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


class TestEstimateTokens:
    def test_empty_string_returns_zero(self) -> None:
        assert estimate_tokens("") == 0

    def test_short_string_returns_at_least_one(self) -> None:
        assert estimate_tokens("a") == 1
        assert estimate_tokens("abcd") == 1

    def test_proportional_to_length(self) -> None:
        # 4 chars / token rule
        assert estimate_tokens("a" * 400) == 100


class TestRelevanceScoring:
    def test_empty_prompt_yields_zero_keyword_hits(self, tmp_path: Path) -> None:
        f = _write(tmp_path / "x.py", "def foo(): pass")
        opt = CognitiveContextOptimizer()
        result = opt.optimize(prompt="", candidate_files=[f], token_budget=1000)
        assert result.slices[0].relevance.keyword_hits == 0

    def test_keyword_in_content_boosts_score(self, tmp_path: Path) -> None:
        relevant = _write(tmp_path / "auth.py", "def authenticate_user(token): pass")
        irrelevant = _write(tmp_path / "wow.py", "x = 1\ny = 2\n")
        opt = CognitiveContextOptimizer()
        result = opt.optimize(
            prompt="How does authenticate_user work?",
            candidate_files=[irrelevant, relevant],
            token_budget=1000,
        )
        # Relevant file should score higher and appear first.
        assert result.slices[0].file_path.endswith("auth.py")
        assert result.slices[0].relevance.score > result.slices[1].relevance.score

    def test_keyword_in_path_boosts_score(self, tmp_path: Path) -> None:
        # Two files with identical content; only the path differs.
        a = _write(tmp_path / "auth_helpers.py", "x = 1\n")
        b = _write(tmp_path / "misc.py", "x = 1\n")
        opt = CognitiveContextOptimizer()
        result = opt.optimize(
            prompt="add an authentication helper",
            candidate_files=[b, a],
            token_budget=1000,
        )
        assert result.slices[0].file_path.endswith("auth_helpers.py")

    def test_explicit_mention_dominates(self, tmp_path: Path) -> None:
        boring = _write(tmp_path / "boring.py", "x = 1\n")
        # No keyword overlap, but the user named it explicitly.
        result = CognitiveContextOptimizer().optimize(
            prompt="something",
            candidate_files=[boring],
            token_budget=1000,
            explicit_mentions=["boring.py"],
        )
        assert result.slices[0].relevance.explicit_mention is True
        assert result.slices[0].relevance.score >= 2.0  # W_MENTION

    def test_recency_bonus_applied(self, tmp_path: Path) -> None:
        recent = _write(tmp_path / "recent.py", "x = 1\n")
        opt = CognitiveContextOptimizer()
        result = opt.optimize(
            prompt="anything",
            candidate_files=[recent],
            token_budget=1000,
            recent_files=[str(recent)],
        )
        assert result.slices[0].relevance.recency_score == 1.0


class TestPacking:
    def test_fits_everything_when_budget_is_huge(self, tmp_path: Path) -> None:
        files = [_write(tmp_path / f"f{i}.py", "x = 1\n" * 10) for i in range(3)]
        result = CognitiveContextOptimizer().optimize(
            prompt="anything",
            candidate_files=files,
            token_budget=10_000,
        )
        assert result.summary["included"] == 3
        assert result.summary["truncated"] == 0
        assert result.summary["skipped"] == 0

    def test_skips_files_when_budget_exhausted(self, tmp_path: Path) -> None:
        # Each file ~250 tokens (1000 chars / 4); budget = 200 → only 0 fit whole,
        # below MIN_TOKENS_PER_FILE for partial too once budget < 100.
        files = [_write(tmp_path / f"f{i}.py", "y" * 1_000) for i in range(3)]
        result = CognitiveContextOptimizer().optimize(
            prompt="anything",
            candidate_files=files,
            token_budget=200,
        )
        # First file gets a truncated slice (200 tokens budget ≥ MIN_TOKENS=100).
        assert result.summary["included"] >= 1
        assert result.tokens_used <= 200

    def test_truncates_when_partial_fits(self, tmp_path: Path) -> None:
        # 4000 chars = 1000 tokens, budget 500 → must truncate.
        f = _write(tmp_path / "big.py", "z" * 4_000)
        result = CognitiveContextOptimizer().optimize(
            prompt="anything",
            candidate_files=[f],
            token_budget=500,
        )
        assert result.slices[0].truncated is True
        assert result.slices[0].included_tokens <= 500
        assert result.slices[0].full_size_tokens > 500

    def test_zero_or_negative_budget_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            CognitiveContextOptimizer().optimize(
                prompt="x", candidate_files=[], token_budget=0
            )

    def test_unreadable_file_is_silently_skipped(self, tmp_path: Path) -> None:
        ghost = tmp_path / "does-not-exist.py"
        result = CognitiveContextOptimizer().optimize(
            prompt="anything", candidate_files=[ghost], token_budget=1_000
        )
        # No crash, but no slices either.
        assert result.summary["included"] == 0


class TestSmartTruncation:
    def test_keeps_imports_and_signatures(self, tmp_path: Path) -> None:
        content = (
            "import os\nimport sys\n\n"
            "def helper():\n    return 1\n\n"
            "def authenticate_user(token):\n"
            + "    pass\n"
            * 200  # filler to force truncation
        )
        f = _write(tmp_path / "auth.py", content)
        result = CognitiveContextOptimizer().optimize(
            prompt="How does authenticate_user verify the token?",
            candidate_files=[f],
            token_budget=200,  # forces truncation
        )
        sliced = result.slices[0]
        assert sliced.truncated is True
        assert "import os" in sliced.content
        assert "def authenticate_user" in sliced.content
        # Filler should be mostly gone.
        assert sliced.content.count("    pass") < 50

    def test_truncation_respects_token_target(self, tmp_path: Path) -> None:
        # Even when the whole file would be huge, the truncated slice
        # must not blow past the budget.
        content = "x" * 50_000  # ~12500 tokens
        f = _write(tmp_path / "blob.txt", content)
        result = CognitiveContextOptimizer().optimize(
            prompt="anything",
            candidate_files=[f],
            token_budget=300,
        )
        assert result.tokens_used <= 300

    def test_to_dict_serialisable(self, tmp_path: Path) -> None:
        import json

        f = _write(tmp_path / "x.py", "def foo(): pass")
        result = CognitiveContextOptimizer().optimize(
            prompt="foo",
            candidate_files=[f],
            token_budget=1000,
        )
        decoded = json.loads(json.dumps(result.to_dict()))
        assert "slices" in decoded
        assert decoded["summary"]["included"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
