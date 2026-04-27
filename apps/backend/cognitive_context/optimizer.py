"""Cognitive Context Optimizer — file relevance + token packing.

Heuristics
----------
* **Relevance score per file** = α·keyword_overlap + β·path_score
  + γ·explicit_mention + δ·recency_score
* **Smart truncation** when a file is too large to include whole:
  imports + top-level signatures + the lines containing query keywords +
  a small surrounding window. Bullet-point everything else.
* **Greedy knapsack** packs files into the token budget by descending score,
  truncating the lowest-scoring fitting candidate when needed.

The optimizer is intentionally provider-agnostic: it doesn't call out to
any LLM. Token counts are estimated with a 4-chars/token rule that's
within ~10% of tiktoken for typical code, which is plenty for budget
allocation.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# 4 chars/token is the rough Anthropic/OpenAI rule for English+code.
_CHARS_PER_TOKEN = 4

_KEYWORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")
_SIGNATURE_PREFIXES = (
    "def ",
    "class ",
    "async def ",
    "function ",
    "export function ",
    "export const ",
    "export class ",
    "interface ",
    "type ",
    "@",
)
_IMPORT_PREFIXES = ("import ", "from ", "require(", "use ")


def estimate_tokens(text: str) -> int:
    """4-chars-per-token approximation."""
    if not text:
        return 0
    return max(1, len(text) // _CHARS_PER_TOKEN)


def _extract_keywords(text: str, max_keywords: int = 30) -> set[str]:
    """Pull identifier-like tokens out of the prompt for matching."""
    if not text:
        return set()
    seen: dict[str, int] = {}
    for m in _KEYWORD_RE.findall(text):
        lowered = m.lower()
        if len(lowered) < 3:
            continue
        seen[lowered] = seen.get(lowered, 0) + 1
    # Most-frequent first, capped.
    return set(sorted(seen, key=seen.get, reverse=True)[:max_keywords])  # type: ignore[arg-type]


@dataclass
class RelevanceScore:
    """Why a file scored what it did — useful for debugging / UI explanation."""

    file_path: str
    score: float
    keyword_hits: int
    path_score: float
    explicit_mention: bool
    recency_score: float
    breakdown: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "score": round(self.score, 4),
            "keyword_hits": self.keyword_hits,
            "path_score": round(self.path_score, 4),
            "explicit_mention": self.explicit_mention,
            "recency_score": round(self.recency_score, 4),
            "breakdown": {k: round(v, 4) for k, v in self.breakdown.items()},
        }


@dataclass
class FileSlice:
    """A (possibly truncated) chunk of a file selected for inclusion."""

    file_path: str
    content: str
    full_size_tokens: int  # what the whole file would have cost
    included_tokens: int  # what we actually included
    truncated: bool
    relevance: RelevanceScore

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "content": self.content,
            "full_size_tokens": self.full_size_tokens,
            "included_tokens": self.included_tokens,
            "truncated": self.truncated,
            "relevance": self.relevance.to_dict(),
        }


@dataclass
class OptimizedContext:
    slices: list[FileSlice]
    token_budget: int
    tokens_used: int
    files_skipped: list[str]
    summary: dict

    def to_dict(self) -> dict:
        return {
            "slices": [s.to_dict() for s in self.slices],
            "token_budget": self.token_budget,
            "tokens_used": self.tokens_used,
            "files_skipped": self.files_skipped,
            "summary": self.summary,
        }


class CognitiveContextOptimizer:
    """Score, slice, and pack files into a token budget."""

    # Score weights — tunable.
    W_KEYWORD = 1.0
    W_PATH = 0.4
    W_MENTION = 2.0
    W_RECENCY = 0.5

    # Smart truncation: how much surrounding context to keep around each
    # keyword-matching line.
    TRUNCATE_WINDOW_LINES = 2
    # Reserve at least this many tokens per file we include (imports +
    # signatures); below that we'd be including useless dust.
    MIN_TOKENS_PER_FILE = 100

    def __init__(self, project_dir: Path | str | None = None) -> None:
        self.project_dir = Path(project_dir) if project_dir else None

    # ------------------------------------------------------------------
    # Public API

    def optimize(
        self,
        prompt: str,
        candidate_files: Iterable[Path | str],
        token_budget: int = 8_000,
        explicit_mentions: Iterable[str] | None = None,
        recent_files: Iterable[str] | None = None,
    ) -> OptimizedContext:
        """Pick + slice + pack candidate files to fit the token budget.

        Args:
            prompt: the user task / instruction.
            candidate_files: files the caller already discovered as plausible.
            token_budget: max total tokens (rough estimate) for the included
                content. Reserve ~10–15% for the prompt itself outside this.
            explicit_mentions: filenames the prompt explicitly names — these
                get a strong score boost.
            recent_files: paths from recent edits/commits — modest boost.
        """
        if token_budget <= 0:
            raise ValueError("token_budget must be positive")

        keywords = _extract_keywords(prompt)
        explicit_set = {Path(p).name.lower() for p in (explicit_mentions or [])}
        recent_set = {str(Path(p)) for p in (recent_files or [])}

        candidates = list(candidate_files)

        # 1. Score every candidate file
        scored: list[tuple[RelevanceScore, Path | None, str]] = []
        for raw in candidates:
            path = Path(raw)
            try:
                content = self._read_file(path)
            except OSError as e:
                logger.debug("Skipping unreadable file %s: %s", path, e)
                continue
            score = self._score_file(
                file_path=str(path),
                content=content,
                keywords=keywords,
                explicit_set=explicit_set,
                recent_set=recent_set,
            )
            scored.append((score, path, content))

        # 2. Pack greedily (highest score first) into the budget
        scored.sort(key=lambda t: t[0].score, reverse=True)

        tokens_used = 0
        slices: list[FileSlice] = []
        skipped: list[str] = []

        for score, _path, content in scored:
            full_tokens = estimate_tokens(content)
            remaining = token_budget - tokens_used

            if remaining <= 0:
                skipped.append(score.file_path)
                continue

            if full_tokens <= remaining:
                # Fits as-is.
                slices.append(
                    FileSlice(
                        file_path=score.file_path,
                        content=content,
                        full_size_tokens=full_tokens,
                        included_tokens=full_tokens,
                        truncated=False,
                        relevance=score,
                    )
                )
                tokens_used += full_tokens
            elif remaining >= self.MIN_TOKENS_PER_FILE:
                # Truncate to fit.
                truncated = self._truncate_smart(
                    content, target_tokens=remaining, keywords=keywords
                )
                included_tokens = estimate_tokens(truncated)
                slices.append(
                    FileSlice(
                        file_path=score.file_path,
                        content=truncated,
                        full_size_tokens=full_tokens,
                        included_tokens=included_tokens,
                        truncated=True,
                        relevance=score,
                    )
                )
                tokens_used += included_tokens
            else:
                # Not enough room left for even a useful slice.
                skipped.append(score.file_path)

        summary = {
            "candidates": len(candidates),
            "included": len(slices),
            "truncated": sum(1 for s in slices if s.truncated),
            "skipped": len(skipped),
            "fill_ratio": round(tokens_used / token_budget, 3) if token_budget else 0.0,
            "keywords_detected": sorted(keywords),
        }
        return OptimizedContext(
            slices=slices,
            token_budget=token_budget,
            tokens_used=tokens_used,
            files_skipped=skipped,
            summary=summary,
        )

    # ------------------------------------------------------------------
    # Internals

    def _read_file(self, path: Path) -> str:
        if self.project_dir and not path.is_absolute():
            path = self.project_dir / path
        return path.read_text(encoding="utf-8", errors="ignore")

    def _score_file(
        self,
        file_path: str,
        content: str,
        keywords: set[str],
        explicit_set: set[str],
        recent_set: set[str],
    ) -> RelevanceScore:
        # 1. Keyword overlap — count distinct keywords present in the file.
        lowered = content.lower()
        keyword_hits = sum(1 for kw in keywords if kw in lowered)
        keyword_norm = keyword_hits / max(len(keywords), 1)

        # 2. Path score — keywords in the file path are strong evidence
        # the file is on-topic.
        path_lower = file_path.lower()
        path_hits = sum(1 for kw in keywords if kw in path_lower)
        path_score = path_hits / max(len(keywords), 1)

        # 3. Explicit mention by basename (the user said "look at foo.py").
        basename = Path(file_path).name.lower()
        explicit = basename in explicit_set

        # 4. Recency bonus.
        recency = (
            1.0
            if file_path in recent_set or str(Path(file_path)) in recent_set
            else 0.0
        )

        score = (
            self.W_KEYWORD * keyword_norm
            + self.W_PATH * path_score
            + self.W_MENTION * (1.0 if explicit else 0.0)
            + self.W_RECENCY * recency
        )

        return RelevanceScore(
            file_path=file_path,
            score=score,
            keyword_hits=keyword_hits,
            path_score=path_score,
            explicit_mention=explicit,
            recency_score=recency,
            breakdown={
                "keyword_norm": keyword_norm,
                "path_score": path_score,
                "mention_bonus": self.W_MENTION if explicit else 0.0,
                "recency_bonus": self.W_RECENCY * recency,
            },
        )

    def _truncate_smart(
        self, content: str, target_tokens: int, keywords: set[str]
    ) -> str:
        """Keep imports + signatures + keyword-matching windows.

        We assemble three pools:
          1. import statements
          2. top-level def/class/function/interface/type lines
          3. lines containing any keyword + N lines around them
        Then we greedily concatenate within the budget.
        """
        lines = content.splitlines()
        imports: list[str] = []
        signatures: list[tuple[int, str]] = []
        for idx, line in enumerate(lines):
            stripped = line.lstrip()
            if any(stripped.startswith(p) for p in _IMPORT_PREFIXES):
                imports.append(line)
            if any(stripped.startswith(p) for p in _SIGNATURE_PREFIXES):
                signatures.append((idx, line))

        # Lines matching keywords + window
        matching_idx: set[int] = set()
        if keywords:
            lowered_lines = [line.lower() for line in lines]
            for idx, line in enumerate(lowered_lines):
                if any(kw in line for kw in keywords):
                    for off in range(
                        -self.TRUNCATE_WINDOW_LINES,
                        self.TRUNCATE_WINDOW_LINES + 1,
                    ):
                        if 0 <= idx + off < len(lines):
                            matching_idx.add(idx + off)

        # Assemble, keeping order
        # Header: imports
        # Then a separator
        # Then signatures + matching ranges, in original line order.
        kept_indices: set[int] = set()
        kept_indices.update(idx for idx, _ in signatures)
        kept_indices.update(matching_idx)

        header = "\n".join(imports)
        if header:
            header += "\n\n"

        body_lines: list[str] = []
        prev_idx = -2
        for idx in sorted(kept_indices):
            if idx > prev_idx + 1 and body_lines:
                body_lines.append("# ...")
            body_lines.append(lines[idx])
            prev_idx = idx

        result = header + "\n".join(body_lines)

        # Hard cap to budget — if even the trimmed version is too long,
        # truncate by characters as a last resort.
        target_chars = target_tokens * _CHARS_PER_TOKEN
        if len(result) > target_chars:
            result = result[: target_chars - 20] + "\n# [truncated]"
        return result
