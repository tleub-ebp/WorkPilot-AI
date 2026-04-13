"""
Onboarding Engine — Generate contextual onboarding material for new team members.

Analyses the codebase and produces architecture overviews, key-file maps,
dependency graphs, naming convention guides, and personalised learning paths.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class OnboardingSection(str, Enum):
    ARCHITECTURE = "architecture"
    KEY_FILES = "key_files"
    CONVENTIONS = "conventions"
    DEPENDENCIES = "dependencies"
    GETTING_STARTED = "getting_started"
    TESTING = "testing"
    DEPLOYMENT = "deployment"


@dataclass
class KeyFile:
    """A file highlighted as important for onboarding."""

    path: str
    reason: str
    category: str = ""
    lines: int = 0


@dataclass
class Convention:
    """A detected or documented coding convention."""

    name: str
    description: str
    examples: list[str] = field(default_factory=list)


@dataclass
class OnboardingGuide:
    """A generated onboarding guide."""

    project_name: str
    sections: dict[str, str] = field(default_factory=dict)
    key_files: list[KeyFile] = field(default_factory=list)
    conventions: list[Convention] = field(default_factory=list)
    tech_stack: list[str] = field(default_factory=list)
    estimated_reading_time_min: int = 0


class OnboardingEngine:
    """Analyse a codebase and generate onboarding material.

    Usage::

        engine = OnboardingEngine()
        guide = engine.generate(Path("/my/repo"))
    """

    def generate(self, repo_root: Path) -> OnboardingGuide:
        """Generate a full onboarding guide from the repo."""
        guide = OnboardingGuide(project_name=repo_root.name)

        guide.tech_stack = self._detect_tech_stack(repo_root)
        guide.key_files = self._identify_key_files(repo_root)
        guide.conventions = self._detect_conventions(repo_root)
        guide.sections[OnboardingSection.GETTING_STARTED.value] = self._getting_started(
            repo_root
        )
        guide.estimated_reading_time_min = max(5, len(guide.key_files) * 2)

        return guide

    def _detect_tech_stack(self, root: Path) -> list[str]:
        stack: list[str] = []
        indicators = {
            "package.json": "Node.js",
            "tsconfig.json": "TypeScript",
            "pyproject.toml": "Python",
            "requirements.txt": "Python",
            "Cargo.toml": "Rust",
            "go.mod": "Go",
            "pom.xml": "Java",
            "build.gradle": "Java/Kotlin",
            "Gemfile": "Ruby",
            "docker-compose.yml": "Docker",
            "Dockerfile": "Docker",
            ".github/workflows": "GitHub Actions",
        }
        for indicator, tech in indicators.items():
            if (root / indicator).exists():
                if tech not in stack:
                    stack.append(tech)
        return stack

    def _identify_key_files(self, root: Path) -> list[KeyFile]:
        key_files: list[KeyFile] = []
        candidates = [
            ("README.md", "Project documentation entry point", "docs"),
            ("CONTRIBUTING.md", "Contribution guidelines", "docs"),
            ("package.json", "Node.js dependencies and scripts", "config"),
            ("pyproject.toml", "Python project configuration", "config"),
            ("docker-compose.yml", "Service orchestration", "infra"),
            (".env.example", "Environment variables template", "config"),
        ]
        for filename, reason, category in candidates:
            path = root / filename
            if path.exists():
                try:
                    lines = len(
                        path.read_text(encoding="utf-8", errors="replace").splitlines()
                    )
                except OSError:
                    lines = 0
                key_files.append(
                    KeyFile(
                        path=filename, reason=reason, category=category, lines=lines
                    )
                )

        return key_files

    def _detect_conventions(self, root: Path) -> list[Convention]:
        conventions: list[Convention] = []

        # Check for linter configs
        linter_files = {
            ".eslintrc.js": "ESLint code style",
            ".eslintrc.json": "ESLint code style",
            ".prettierrc": "Prettier formatting",
            "ruff.toml": "Ruff Python linting",
            ".flake8": "Flake8 Python linting",
            ".editorconfig": "Editor configuration",
        }
        for f, desc in linter_files.items():
            if (root / f).exists():
                conventions.append(
                    Convention(name=desc, description=f"Configured via {f}")
                )

        return conventions

    def _getting_started(self, root: Path) -> str:
        """Generate a getting started section."""
        steps: list[str] = ["## Getting Started\n"]
        if (root / "package.json").exists():
            steps.append("1. `npm install` or `yarn install`")
            steps.append("2. `npm run dev` or `yarn dev`")
        elif (root / "requirements.txt").exists():
            steps.append("1. `python -m venv .venv && source .venv/bin/activate`")
            steps.append("2. `pip install -r requirements.txt`")
        elif (root / "pyproject.toml").exists():
            steps.append("1. `pip install -e .` or `poetry install`")
        else:
            steps.append("1. Check README.md for setup instructions")
        return "\n".join(steps)
