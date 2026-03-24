"""
Fragility Analyzer
===================

Analyzes code fragility by combining:
- Cyclomatic complexity (via AST analysis)
- Git churn (commit frequency per file)
- Test coverage correlation

Produces per-file FragilityReport with composite risk scores.
"""

from __future__ import annotations

import ast
import json
import logging
import subprocess
from pathlib import Path

from .models import FragilityReport

logger = logging.getLogger(__name__)

# Weight factors for composite risk score
WEIGHT_COMPLEXITY = 0.4
WEIGHT_CHURN = 0.3
WEIGHT_COVERAGE = 0.3

# Normalization constants
MAX_COMPLEXITY = 50  # Complexity above this maps to 100
MAX_CHURN = 30  # Commits in 30 days above this maps to 100

# Default excluded directories
DEFAULT_EXCLUDED = {
    "node_modules",
    ".venv",
    "__pycache__",
    ".git",
    "dist",
    "build",
    ".workpilot",
    ".next",
    "coverage",
    ".tox",
    "egg-info",
}


class FragilityAnalyzer:
    """Analyzes code fragility across multiple dimensions."""

    def __init__(
        self,
        project_dir: str | Path,
        churn_days: int = 30,
        excluded_dirs: set[str] | None = None,
    ):
        self.project_dir = Path(project_dir)
        self.churn_days = churn_days
        self.excluded_dirs = excluded_dirs or DEFAULT_EXCLUDED

    async def analyze(
        self,
        max_files: int = 100,
        risk_threshold: float = 30.0,
    ) -> list[FragilityReport]:
        """Run full fragility analysis on the project.

        Args:
            max_files: Maximum number of files to analyze.
            risk_threshold: Only return files above this risk score.

        Returns:
            List of FragilityReport sorted by risk_score descending.
        """
        source_files = self._find_source_files(max_files)
        if not source_files:
            logger.warning("No source files found for fragility analysis")
            return []

        churn_map = self._compute_git_churn(source_files)
        coverage_map = self._load_coverage_data()

        reports: list[FragilityReport] = []
        for file_path in source_files:
            rel_path = str(file_path.relative_to(self.project_dir))
            complexity = self._compute_cyclomatic_complexity(file_path)
            churn = churn_map.get(rel_path, 0)
            coverage = coverage_map.get(rel_path, 0.0)

            # Normalize to 0-100
            norm_complexity = min(complexity / MAX_COMPLEXITY * 100, 100)
            norm_churn = min(churn / MAX_CHURN * 100, 100)
            uncovered = 100 - coverage

            risk_score = (
                WEIGHT_COMPLEXITY * norm_complexity
                + WEIGHT_CHURN * norm_churn
                + WEIGHT_COVERAGE * uncovered
            )
            risk_score = round(min(risk_score, 100), 1)

            if risk_score >= risk_threshold:
                reports.append(
                    FragilityReport(
                        file_path=rel_path,
                        risk_score=risk_score,
                        cyclomatic_complexity=round(complexity, 1),
                        git_churn_count=churn,
                        test_coverage_percent=round(coverage, 1),
                    )
                )

        reports.sort(key=lambda r: r.risk_score, reverse=True)
        return reports

    def _find_source_files(self, max_files: int) -> list[Path]:
        """Find analyzable source files in the project."""
        extensions = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs", ".rb"}
        files: list[Path] = []

        for ext in extensions:
            for f in self.project_dir.rglob(f"*{ext}"):
                if any(part in self.excluded_dirs for part in f.parts):
                    continue
                # Skip test files for fragility analysis
                name_lower = f.name.lower()
                if name_lower.startswith("test_") or name_lower.endswith(
                    (
                        "_test.py",
                        ".test.ts",
                        ".test.tsx",
                        ".test.js",
                        ".test.jsx",
                        ".spec.ts",
                        ".spec.tsx",
                        ".spec.js",
                    )
                ):
                    continue
                files.append(f)
                if len(files) >= max_files:
                    return files

        return files

    def _compute_cyclomatic_complexity(self, file_path: Path) -> float:
        """Compute cyclomatic complexity for a Python file via AST.

        For non-Python files, returns a heuristic based on control flow keywords.
        """
        if file_path.suffix == ".py":
            return self._python_complexity(file_path)
        return self._heuristic_complexity(file_path)

    def _python_complexity(self, file_path: Path) -> float:
        """Compute cyclomatic complexity for Python files using AST."""
        try:
            source = file_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(file_path))
        except (SyntaxError, ValueError):
            return 0.0

        complexity = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                # Each and/or adds a decision point
                complexity += len(node.values) - 1
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                complexity += 1  # Base complexity per function
            elif isinstance(node, ast.Assert):
                complexity += 1

        return float(complexity)

    def _heuristic_complexity(self, file_path: Path) -> float:
        """Heuristic complexity for non-Python files based on keyword counting."""
        control_keywords = {
            "if",
            "else",
            "elif",
            "for",
            "while",
            "switch",
            "case",
            "catch",
            "try",
            "throw",
            "&&",
            "||",
            "?",
        }
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return 0.0

        complexity = 0
        for line in content.splitlines():
            stripped = line.strip()
            for kw in control_keywords:
                if kw in stripped:
                    complexity += 1
                    break  # Count once per line

        return float(complexity)

    def _compute_git_churn(self, files: list[Path]) -> dict[str, int]:
        """Compute git commit count per file in the last N days."""
        churn: dict[str, int] = {}

        try:
            result = subprocess.run(
                [
                    "git",
                    "log",
                    f"--since={self.churn_days} days ago",
                    "--format=",
                    "--name-only",
                    "--diff-filter=ACMR",
                ],
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    line = line.strip()
                    if line:
                        churn[line] = churn.get(line, 0) + 1
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            logger.warning(f"Git churn analysis failed: {e}")

        return churn

    def _load_coverage_data(self) -> dict[str, float]:
        """Load test coverage data from common coverage report formats."""
        coverage: dict[str, float] = {}

        # Try coverage.json (Python coverage.py format)
        coverage_json = self.project_dir / "coverage.json"
        if coverage_json.exists():
            try:
                data = json.loads(coverage_json.read_text(encoding="utf-8"))
                if "files" in data:
                    for file_path, file_data in data["files"].items():
                        if "summary" in file_data:
                            coverage[file_path] = file_data["summary"].get(
                                "percent_covered", 0.0
                            )
            except (json.JSONDecodeError, KeyError):
                pass

        # Try lcov-style coverage-summary.json (Jest/Istanbul)
        for summary_path in [
            self.project_dir / "coverage" / "coverage-summary.json",
            self.project_dir / "coverage" / "coverage-final.json",
        ]:
            if summary_path.exists():
                try:
                    data = json.loads(summary_path.read_text(encoding="utf-8"))
                    for file_path, file_data in data.items():
                        if file_path == "total":
                            continue
                        rel_path = file_path
                        try:
                            rel_path = str(
                                Path(file_path).relative_to(self.project_dir)
                            )
                        except ValueError:
                            pass
                        if isinstance(file_data, dict) and "lines" in file_data:
                            coverage[rel_path] = file_data["lines"].get("pct", 0.0)
                except (json.JSONDecodeError, KeyError):
                    pass

        return coverage

    def _find_test_file(self, source_file: Path) -> Path | None:
        """Find the corresponding test file for a source file."""
        stem = source_file.stem
        suffix = source_file.suffix

        test_patterns = [
            f"test_{stem}{suffix}",
            f"{stem}_test{suffix}",
            f"{stem}.test{suffix}",
            f"{stem}.spec{suffix}",
        ]

        # Search in common test directories
        test_dirs = [
            source_file.parent,
            source_file.parent / "__tests__",
            source_file.parent / "tests",
            self.project_dir / "tests",
            self.project_dir / "test",
        ]

        for test_dir in test_dirs:
            for pattern in test_patterns:
                test_file = test_dir / pattern
                if test_file.exists():
                    return test_file

        return None
