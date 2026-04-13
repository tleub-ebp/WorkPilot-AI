"""
Diff Predictor — Preview and analyse the changes an agent *would* make.

After an agent runs in sandbox mode, this module compares the original
snapshot with the modified worktree to produce a structured diff that
can be displayed for user approval.
"""

from __future__ import annotations

import difflib
import logging
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class ChangeType(str, Enum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


@dataclass
class FileDiff:
    """Diff for a single file."""

    path: str
    change_type: ChangeType
    old_content: str = ""
    new_content: str = ""
    unified_diff: str = ""
    lines_added: int = 0
    lines_removed: int = 0


@dataclass
class DiffPrediction:
    """Full prediction of an agent run — the aggregate set of file diffs."""

    files: list[FileDiff] = field(default_factory=list)
    total_added: int = 0
    total_removed: int = 0
    new_files: int = 0
    modified_files: int = 0
    deleted_files: int = 0

    @property
    def total_files(self) -> int:
        return len(self.files)

    @property
    def summary(self) -> str:
        parts = []
        if self.new_files:
            parts.append(f"+{self.new_files} new")
        if self.modified_files:
            parts.append(f"~{self.modified_files} modified")
        if self.deleted_files:
            parts.append(f"-{self.deleted_files} deleted")
        return ", ".join(parts) or "no changes"


class DiffPredictor:
    """Compare an original snapshot with a sandbox worktree to predict diffs.

    Usage::

        predictor = DiffPredictor()
        prediction = predictor.predict(original_root, sandbox_root)
    """

    def predict(self, original_root: Path, sandbox_root: Path) -> DiffPrediction:
        """Produce a ``DiffPrediction`` comparing two directory trees."""
        prediction = DiffPrediction()

        original_files = self._collect_files(original_root)
        sandbox_files = self._collect_files(sandbox_root)

        all_paths = sorted(set(original_files) | set(sandbox_files))

        for rel_path in all_paths:
            orig = original_files.get(rel_path)
            sand = sandbox_files.get(rel_path)

            if orig is None and sand is not None:
                # New file
                content = self._read_safe(sand)
                diff_text = self._unified_diff("", content, rel_path)
                added = content.count("\n") + (
                    1 if content and not content.endswith("\n") else 0
                )
                fd = FileDiff(
                    path=rel_path,
                    change_type=ChangeType.ADDED,
                    new_content=content,
                    unified_diff=diff_text,
                    lines_added=added,
                )
                prediction.files.append(fd)
                prediction.new_files += 1
                prediction.total_added += added

            elif orig is not None and sand is None:
                # Deleted file
                content = self._read_safe(orig)
                diff_text = self._unified_diff(content, "", rel_path)
                removed = content.count("\n") + (1 if content else 0)
                fd = FileDiff(
                    path=rel_path,
                    change_type=ChangeType.DELETED,
                    old_content=content,
                    unified_diff=diff_text,
                    lines_removed=removed,
                )
                prediction.files.append(fd)
                prediction.deleted_files += 1
                prediction.total_removed += removed

            elif orig is not None and sand is not None:
                old_text = self._read_safe(orig)
                new_text = self._read_safe(sand)
                if old_text != new_text:
                    diff_text = self._unified_diff(old_text, new_text, rel_path)
                    added = sum(
                        1
                        for l in diff_text.splitlines()
                        if l.startswith("+") and not l.startswith("+++")
                    )
                    removed = sum(
                        1
                        for l in diff_text.splitlines()
                        if l.startswith("-") and not l.startswith("---")
                    )
                    fd = FileDiff(
                        path=rel_path,
                        change_type=ChangeType.MODIFIED,
                        old_content=old_text,
                        new_content=new_text,
                        unified_diff=diff_text,
                        lines_added=added,
                        lines_removed=removed,
                    )
                    prediction.files.append(fd)
                    prediction.modified_files += 1
                    prediction.total_added += added
                    prediction.total_removed += removed

        return prediction

    def predict_with_git(self, worktree_path: Path) -> DiffPrediction:
        """Use ``git diff`` inside a worktree for a faster diff."""
        try:
            result = subprocess.run(
                ["git", "diff", "--stat"],
                cwd=str(worktree_path),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return DiffPrediction()

            full_diff = subprocess.run(
                ["git", "diff"],
                cwd=str(worktree_path),
                capture_output=True,
                text=True,
                timeout=30,
            )

            prediction = DiffPrediction()
            if full_diff.stdout:
                for line in full_diff.stdout.splitlines():
                    if line.startswith("+") and not line.startswith("+++"):
                        prediction.total_added += 1
                    elif line.startswith("-") and not line.startswith("---"):
                        prediction.total_removed += 1
            return prediction

        except (subprocess.SubprocessError, OSError):
            return DiffPrediction()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _collect_files(root: Path) -> dict[str, Path]:
        """Walk a directory, returning {relative_path: absolute_path}."""
        skip = {".git", "node_modules", "__pycache__", ".venv", "venv"}
        result: dict[str, Path] = {}
        if not root.exists():
            return result
        for p in root.rglob("*"):
            if p.is_file() and not any(part in skip for part in p.parts):
                rel = str(p.relative_to(root)).replace("\\", "/")
                result[rel] = p
        return result

    @staticmethod
    def _read_safe(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    @staticmethod
    def _unified_diff(old: str, new: str, filename: str) -> str:
        old_lines = old.splitlines(keepends=True)
        new_lines = new.splitlines(keepends=True)
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
        )
        return "".join(diff)
