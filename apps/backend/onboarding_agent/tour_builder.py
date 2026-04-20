"""
Onboarding Tour Builder
========================

Turns a codebase into a sequenced, interactive onboarding experience:

- **Tour**: 5–10 ordered steps pointing at the key files, with a short
  explanation of why each matters.
- **Quiz**: multiple-choice questions generated from the tour to verify
  comprehension.
- **First tasks**: trivial "good first issue"–style suggestions surfaced from
  existing TODO/FIXME markers in the repo.
- **Glossary**: domain terms extracted from file names, top-level identifiers,
  and recent commit messages.

The module is deterministic — it does NOT call any LLM. Upstream callers can
feed the result to an agent prompt if they want richer prose.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .onboarding_engine import OnboardingEngine, OnboardingGuide

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class TourStep:
    """A single step in the guided tour."""

    order: int
    title: str
    file_path: str
    reason: str
    suggested_questions: list[str] = field(default_factory=list)


@dataclass
class QuizQuestion:
    """A multiple-choice question generated from tour content."""

    question: str
    choices: list[str]
    correct_index: int
    rationale: str = ""


@dataclass
class FirstTask:
    """A suggested first task for the newcomer."""

    title: str
    file_path: str
    line: int
    source_comment: str


@dataclass
class GlossaryTerm:
    """A domain term detected in the codebase."""

    term: str
    occurrences: int
    sources: list[str] = field(default_factory=list)


@dataclass
class OnboardingPackage:
    """Full onboarding bundle for a newcomer."""

    guide: OnboardingGuide
    tour: list[TourStep] = field(default_factory=list)
    quiz: list[QuizQuestion] = field(default_factory=list)
    first_tasks: list[FirstTask] = field(default_factory=list)
    glossary: list[GlossaryTerm] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "guide": {
                "project_name": self.guide.project_name,
                "tech_stack": self.guide.tech_stack,
                "key_files": [asdict(kf) for kf in self.guide.key_files],
                "conventions": [asdict(c) for c in self.guide.conventions],
                "sections": self.guide.sections,
                "estimated_reading_time_min": self.guide.estimated_reading_time_min,
            },
            "tour": [asdict(s) for s in self.tour],
            "quiz": [asdict(q) for q in self.quiz],
            "first_tasks": [asdict(t) for t in self.first_tasks],
            "glossary": [asdict(g) for g in self.glossary],
        }


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TODO_PATTERN = re.compile(
    r"(?:#|//|/\*|\*)\s*(TODO|FIXME|XXX|HACK)[: ]+(.*)", re.IGNORECASE
)

_COMMON_STOP_WORDS = {
    "the",
    "and",
    "for",
    "with",
    "this",
    "that",
    "from",
    "into",
    "when",
    "then",
    "some",
    "have",
    "will",
    "been",
    "your",
    "more",
    "them",
    "than",
    "also",
    "just",
    "does",
    "like",
    "over",
    "main",
    "test",
    "tests",
    "index",
    "utils",
    "util",
    "helper",
    "helpers",
    "core",
    "app",
    "src",
    "lib",
    "data",
    "type",
    "types",
    "file",
    "files",
    "class",
    "func",
    "function",
    "method",
    "module",
    "package",
}

_IGNORED_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
    "coverage",
    ".next",
    ".nuxt",
    "target",
    ".idea",
    ".vscode",
}


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _iter_code_files(root: Path, *, limit: int = 400) -> list[Path]:
    """Yield up to ``limit`` source files, skipping vendored and binary dirs."""
    out: list[Path] = []
    for path in root.rglob("*"):
        if len(out) >= limit:
            break
        if not path.is_file():
            continue
        parts = set(path.relative_to(root).parts)
        if parts & _IGNORED_DIRS:
            continue
        if path.suffix.lower() in {
            ".py",
            ".ts",
            ".tsx",
            ".js",
            ".jsx",
            ".go",
            ".rs",
            ".java",
            ".kt",
            ".rb",
            ".cs",
            ".php",
        }:
            out.append(path)
    return out


def build_tour(guide: OnboardingGuide, root: Path) -> list[TourStep]:
    """Build a sequenced tour from the guide's key files."""
    steps: list[TourStep] = []
    for idx, kf in enumerate(guide.key_files[:8], start=1):
        questions = [
            f"What problem does {kf.path} solve?",
            f"Which other files in {root.name} depend on {kf.path}?",
        ]
        steps.append(
            TourStep(
                order=idx,
                title=f"Step {idx}: {kf.path}",
                file_path=kf.path,
                reason=kf.reason,
                suggested_questions=questions,
            )
        )
    return steps


def build_quiz(tour: list[TourStep], guide: OnboardingGuide) -> list[QuizQuestion]:
    """Generate simple multiple-choice questions from the tour + stack."""
    quiz: list[QuizQuestion] = []

    if guide.tech_stack:
        correct = guide.tech_stack[0]
        distractors = [t for t in ("Rust", "Go", "Ruby", "C++") if t != correct][:3]
        choices = [correct, *distractors]
        quiz.append(
            QuizQuestion(
                question=f"What is the primary tech stack of {guide.project_name}?",
                choices=choices,
                correct_index=0,
                rationale=f"Detected from indicator files: {', '.join(guide.tech_stack)}",
            )
        )

    for step in tour[:3]:
        correct = step.file_path
        other_paths = [s.file_path for s in tour if s.file_path != correct]
        distractors = (
            other_paths[:3]
            if len(other_paths) >= 3
            else other_paths
            + ["src/unknown.py", "tests/old.py", "legacy/deprecated.md"][
                : 3 - len(other_paths)
            ]
        )
        choices = [correct, *distractors]
        quiz.append(
            QuizQuestion(
                question=f"Which file's purpose is: {step.reason!r}?",
                choices=choices,
                correct_index=0,
                rationale=step.reason,
            )
        )

    return quiz


def build_first_tasks(root: Path, *, limit: int = 8) -> list[FirstTask]:
    """Surface TODO/FIXME comments as suggested first tasks."""
    tasks: list[FirstTask] = []
    for path in _iter_code_files(root):
        if len(tasks) >= limit:
            break
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for lineno, line in enumerate(lines, start=1):
            match = _TODO_PATTERN.search(line)
            if not match:
                continue
            tag, note = match.group(1), match.group(2).strip()
            if len(note) < 4:
                continue
            tasks.append(
                FirstTask(
                    title=f"{tag}: {note[:80]}",
                    file_path=str(path.relative_to(root)),
                    line=lineno,
                    source_comment=line.strip(),
                )
            )
            if len(tasks) >= limit:
                break
    return tasks


_IDENT_PATTERN = re.compile(r"\b([A-Z][A-Za-z0-9]{4,}|[a-z]{5,}_[a-z]+)\b")


def build_glossary(root: Path, *, top_n: int = 15) -> list[GlossaryTerm]:
    """Extract domain-sounding terms from filenames and top-level identifiers."""
    counter: Counter[str] = Counter()
    sources: dict[str, list[str]] = {}

    for path in _iter_code_files(root):
        stem_tokens = re.split(r"[_\-\s]", path.stem)
        for token in stem_tokens:
            if len(token) >= 5 and token.lower() not in _COMMON_STOP_WORDS:
                t = token.lower()
                counter[t] += 1
                sources.setdefault(t, []).append(str(path.relative_to(root)))

        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for match in _IDENT_PATTERN.finditer(text[:4000]):
            ident = match.group(1).lower()
            if ident in _COMMON_STOP_WORDS or len(ident) < 5:
                continue
            counter[ident] += 1
            sources.setdefault(ident, []).append(str(path.relative_to(root)))

    entries: list[GlossaryTerm] = []
    for term, count in counter.most_common(top_n):
        entries.append(
            GlossaryTerm(
                term=term,
                occurrences=count,
                sources=list(dict.fromkeys(sources.get(term, [])))[:3],
            )
        )
    return entries


# ---------------------------------------------------------------------------
# Facade
# ---------------------------------------------------------------------------


class OnboardingPackageBuilder:
    """High-level API — call ``build(repo_root)`` to get the full package."""

    def __init__(self, engine: OnboardingEngine | None = None) -> None:
        self.engine = engine or OnboardingEngine()

    def build(self, repo_root: Path) -> OnboardingPackage:
        root = Path(repo_root)
        guide = self.engine.generate(root)
        tour = build_tour(guide, root)
        quiz = build_quiz(tour, guide)
        first_tasks = build_first_tasks(root)
        glossary = build_glossary(root)
        return OnboardingPackage(
            guide=guide,
            tour=tour,
            quiz=quiz,
            first_tasks=first_tasks,
            glossary=glossary,
        )


def render_markdown(package: OnboardingPackage) -> str:
    """Render the package as a single markdown document."""
    g = package.guide
    out: list[str] = [f"# Onboarding — {g.project_name}\n"]
    if g.tech_stack:
        out.append(f"**Tech stack:** {', '.join(g.tech_stack)}\n")
    out.append(f"**Estimated reading time:** {g.estimated_reading_time_min} min\n")

    out.append("\n## Guided Tour\n")
    for step in package.tour:
        out.append(f"### {step.title}")
        out.append(f"- **File:** `{step.file_path}`")
        out.append(f"- **Why:** {step.reason}")
        if step.suggested_questions:
            out.append("- **Ask yourself:**")
            for q in step.suggested_questions:
                out.append(f"  - {q}")
        out.append("")

    if package.quiz:
        out.append("\n## Comprehension Check\n")
        for i, q in enumerate(package.quiz, start=1):
            out.append(f"**Q{i}. {q.question}**")
            for j, choice in enumerate(q.choices):
                out.append(f"  {chr(ord('a') + j)}) {choice}")
            out.append(
                f"  _Answer: {chr(ord('a') + q.correct_index)} — {q.rationale}_\n"
            )

    if package.first_tasks:
        out.append("\n## Good First Tasks\n")
        for t in package.first_tasks:
            out.append(f"- `{t.file_path}:{t.line}` — {t.title}")
        out.append("")

    if package.glossary:
        out.append("\n## Glossary\n")
        for term in package.glossary:
            srcs = ", ".join(f"`{s}`" for s in term.sources) or "—"
            out.append(f"- **{term.term}** ({term.occurrences}×) — seen in {srcs}")

    return "\n".join(out)
