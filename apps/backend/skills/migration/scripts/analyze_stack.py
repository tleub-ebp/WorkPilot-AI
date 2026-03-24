#!/usr/bin/env python3
"""
Stack Analysis Script for Framework Migration Skill

Analyzes a project to detect its current technology stack including:
- Programming languages
- Frameworks and libraries
- Build tools
- Configuration files
- Dependencies

Usage:
    python analyze_stack.py --project-root /path/to/project
    python analyze_stack.py --languages python,javascript --frameworks react,express
"""

import argparse
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DetectedDependency:
    """A dependency detected in the project."""

    name: str
    current_version: str
    latest_version: str | None = None
    dep_type: str = "production"  # production, dev, peer
    has_breaking_update: bool = False
    ecosystem: str = "npm"  # npm, pip, cargo, etc.

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class StackAnalysis:
    """Result of analyzing the project's current technology stack."""

    project_root: str
    detected_languages: list[str] = field(default_factory=list)
    detected_frameworks: list[str] = field(default_factory=list)
    detected_build_tools: list[str] = field(default_factory=list)
    dependencies: list[DetectedDependency] = field(default_factory=list)
    config_files: list[str] = field(default_factory=list)
    total_files_scanned: int = 0
    analysis_timestamp: str = ""

    def to_dict(self) -> dict:
        result = asdict(self)
        return result


# File patterns for stack detection
STACK_INDICATORS = {
    "react": ["package.json:react", "*.jsx", "*.tsx"],
    "vue": ["package.json:vue", "*.vue"],
    "angular": ["angular.json", "package.json:@angular/core"],
    "express": ["package.json:express"],
    "fastify": ["package.json:fastify"],
    "django": ["manage.py", "requirements.txt:django", "settings.py"],
    "flask": ["requirements.txt:flask"],
    "nextjs": [
        "next.config.js",
        "next.config.mjs",
        "next.config.ts",
        "package.json:next",
    ],
    "typescript": ["tsconfig.json"],
    "webpack": ["webpack.config.js", "webpack.config.ts"],
    "vite": ["vite.config.js", "vite.config.ts", "vite.config.mjs"],
}


class StackAnalyzer:
    """Analyzes a project to detect its technology stack."""

    def __init__(self, project_root: str = ".") -> None:
        self.project_root = project_root

    def analyze(self) -> StackAnalysis:
        """Perform a full stack analysis."""
        analysis = StackAnalysis(
            project_root=self.project_root,
            analysis_timestamp=datetime.now(timezone.utc).isoformat(),
        )

        root = Path(self.project_root)
        if not root.exists():
            logger.error(f"Project root {self.project_root} does not exist")
            return analysis

        # Detect languages by file extension
        lang_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript-react",
            ".tsx": "typescript-react",
            ".vue": "vue",
            ".rb": "ruby",
            ".go": "go",
            ".rs": "rust",
            ".java": "java",
            ".kt": "kotlin",
            ".swift": "swift",
        }

        detected_langs = set()
        file_count = 0

        try:
            for fp in root.rglob("*"):
                if (
                    fp.is_file()
                    and "node_modules" not in str(fp)
                    and ".git" not in str(fp)
                ):
                    file_count += 1
                    ext = fp.suffix.lower()
                    if ext in lang_map:
                        detected_langs.add(lang_map[ext])
        except (PermissionError, OSError) as e:
            logger.warning(f"Error scanning files: {e}")

        analysis.detected_languages = sorted(detected_langs)
        analysis.total_files_scanned = file_count

        # Detect frameworks from known indicators
        for framework, indicators in STACK_INDICATORS.items():
            for indicator in indicators:
                if ":" in indicator:
                    fname, pkg = indicator.split(":", 1)
                    config_path = root / fname
                    if config_path.exists():
                        try:
                            content = config_path.read_text(
                                encoding="utf-8", errors="ignore"
                            )
                            if pkg in content:
                                analysis.detected_frameworks.append(framework)
                                break
                        except (OSError, PermissionError):
                            pass
                else:
                    matches = list(root.glob(indicator))
                    if matches:
                        analysis.detected_frameworks.append(framework)
                        break

        # Detect config files
        config_patterns = [
            "package.json",
            "tsconfig.json",
            "webpack.config.*",
            "vite.config.*",
            ".babelrc",
            "babel.config.*",
            "requirements.txt",
            "setup.py",
            "pyproject.toml",
            "Cargo.toml",
            "go.mod",
            "Gemfile",
        ]
        for pattern in config_patterns:
            for match in root.glob(pattern):
                analysis.config_files.append(str(match.relative_to(root)))

        # Parse dependencies from package.json
        pkg_json = root / "package.json"
        if pkg_json.exists():
            analysis.detected_build_tools.append("npm")
            try:
                pkg_data = json.loads(pkg_json.read_text(encoding="utf-8"))
                for section in ("dependencies", "devDependencies"):
                    deps = pkg_data.get(section, {})
                    for name, version in deps.items():
                        dep = DetectedDependency(
                            name=name,
                            current_version=version,
                            dep_type="production"
                            if section == "dependencies"
                            else "dev",
                            ecosystem="npm",
                        )
                        analysis.dependencies.append(dep)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Error parsing package.json: {e}")

        # Parse dependencies from requirements.txt
        req_txt = root / "requirements.txt"
        if req_txt.exists():
            analysis.detected_build_tools.append("pip")
            try:
                for line in req_txt.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        match = re.match(
                            r"^([a-zA-Z0-9_-]+)\s*([><=!~]+\s*[\d.]+)?", line
                        )
                        if match:
                            dep = DetectedDependency(
                                name=match.group(1),
                                current_version=match.group(2).strip()
                                if match.group(2)
                                else "any",
                                ecosystem="pip",
                            )
                            analysis.dependencies.append(dep)
            except OSError as e:
                logger.warning(f"Error reading requirements.txt: {e}")

        logger.info(
            f"Analysis complete: {len(analysis.detected_languages)} languages, "
            f"{len(analysis.detected_frameworks)} frameworks, "
            f"{len(analysis.dependencies)} dependencies"
        )

        return analysis

    def analyze_from_data(
        self,
        languages: list[str] | None = None,
        frameworks: list[str] | None = None,
        dependencies: list[dict] | None = None,
    ) -> StackAnalysis:
        """Create a stack analysis from provided data (for testing or when filesystem is unavailable)."""
        analysis = StackAnalysis(
            project_root=self.project_root,
            analysis_timestamp=datetime.now(timezone.utc).isoformat(),
            detected_languages=languages or [],
            detected_frameworks=frameworks or [],
        )
        if dependencies:
            for dep_data in dependencies:
                analysis.dependencies.append(DetectedDependency(**dep_data))
        return analysis


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Analyze project technology stack")
    parser.add_argument(
        "--project-root", default=".", help="Path to project root directory"
    )
    parser.add_argument(
        "--output", help="Output file for analysis results (JSON format)"
    )
    parser.add_argument(
        "--languages", help="Comma-separated list of languages (for testing)"
    )
    parser.add_argument(
        "--frameworks", help="Comma-separated list of frameworks (for testing)"
    )
    parser.add_argument(
        "--dependencies", help="JSON string of dependencies (for testing)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    analyzer = StackAnalyzer(args.project_root)

    # Use provided data for testing if available
    if args.languages or args.frameworks or args.dependencies:
        languages = args.languages.split(",") if args.languages else None
        frameworks = args.frameworks.split(",") if args.frameworks else None
        dependencies = json.loads(args.dependencies) if args.dependencies else None
        analysis = analyzer.analyze_from_data(languages, frameworks, dependencies)
    else:
        analysis = analyzer.analyze()

    # Output results
    if args.output:
        with open(args.output, "w") as f:
            json.dump(analysis.to_dict(), f, indent=2)
        logger.info(f"Analysis results saved to {args.output}")
    else:
        print(json.dumps(analysis.to_dict(), indent=2))


if __name__ == "__main__":
    main()
