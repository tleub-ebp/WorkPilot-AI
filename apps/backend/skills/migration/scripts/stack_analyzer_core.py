"""
Core Stack Analyzer Module

Contains the complex logic for stack analysis, separated from the lightweight
entry point to enable progressive loading and token optimization.
"""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# Re-export data classes for compatibility
from analyze_stack import STACK_INDICATORS, DetectedDependency, StackAnalysis


class StackAnalyzerCore:
    """Core stack analysis logic with optimized performance."""

    def __init__(self):
        self._cache = {}

    def analyze(self, project_root: str) -> StackAnalysis:
        """Perform full stack analysis with caching."""
        cache_key = f"analyze_{project_root}"

        if cache_key in self._cache:
            logger.debug("Using cached analysis result")
            return self._cache[cache_key]

        analysis = self._perform_analysis(project_root)
        self._cache[cache_key] = analysis
        return analysis

    def analyze_from_data(
        self, languages=None, frameworks=None, dependencies=None
    ) -> StackAnalysis:
        """Create analysis from provided data (for testing)."""
        analysis = StackAnalysis(
            project_root="test",
            analysis_timestamp=datetime.now(timezone.utc).isoformat(),
            detected_languages=languages or [],
            detected_frameworks=frameworks or [],
        )

        if dependencies:
            for dep_data in dependencies:
                analysis.dependencies.append(DetectedDependency(**dep_data))

        return analysis

    def _perform_analysis(self, project_root: str) -> StackAnalysis:
        """Perform the actual analysis logic."""
        analysis = StackAnalysis(
            project_root=project_root,
            analysis_timestamp=datetime.now(timezone.utc).isoformat(),
        )

        root = Path(project_root)
        if not root.exists():
            logger.error(f"Project root {project_root} does not exist")
            return analysis

        # Optimized analysis with early returns
        self._detect_languages(root, analysis)
        self._detect_frameworks(root, analysis)
        self._parse_dependencies(root, analysis)
        self._find_config_files(root, analysis)

        return analysis

    def _detect_languages(self, root: Path, analysis: StackAnalysis) -> None:
        """Detect programming languages with optimized scanning."""
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
            # Optimized scanning with early break
            for fp in root.rglob("*"):
                if file_count > 1000:  # Limit scan for performance
                    break

                if fp.is_file() and self._should_scan_file(fp):
                    file_count += 1
                    ext = fp.suffix.lower()
                    if ext in lang_map:
                        detected_langs.add(lang_map[ext])
                        # Early break if we have enough languages
                        if len(detected_langs) >= 5:
                            break
        except (PermissionError, OSError) as e:
            logger.warning(f"Error scanning files: {e}")

        analysis.detected_languages = sorted(detected_langs)
        analysis.total_files_scanned = file_count

    def _detect_frameworks(self, root: Path, analysis: StackAnalysis) -> None:
        """Detect frameworks with optimized pattern matching."""
        for framework, indicators in STACK_INDICATORS.items():
            if framework in analysis.detected_frameworks:
                continue  # Skip if already detected

            for indicator in indicators:
                if self._check_indicator(root, indicator, framework):
                    analysis.detected_frameworks.append(framework)
                    break

    def _check_indicator(self, root: Path, indicator: str, framework: str) -> bool:
        """Check if a framework indicator exists."""
        if ":" in indicator:
            fname, pkg = indicator.split(":", 1)
            config_path = root / fname
            if (
                config_path.exists() and config_path.stat().st_size < 1024 * 1024
            ):  # < 1MB
                try:
                    content = config_path.read_text(encoding="utf-8", errors="ignore")
                    return pkg in content
                except (OSError, PermissionError):
                    pass
        else:
            matches = list(root.glob(indicator))
            return len(matches) > 0
        return False

    def _parse_dependencies(self, root: Path, analysis: StackAnalysis) -> None:
        """Parse dependencies with error handling."""
        # Parse package.json
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

        # Parse requirements.txt
        req_txt = root / "requirements.txt"
        if req_txt.exists():
            analysis.detected_build_tools.append("pip")
            try:
                content = req_txt.read_text(encoding="utf-8")
                for line in content.splitlines():
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

    def _find_config_files(self, root: Path, analysis: StackAnalysis) -> None:
        """Find configuration files efficiently."""
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
            try:
                matches = list(root.glob(pattern))
                for match in matches:
                    analysis.config_files.append(str(match.relative_to(root)))
            except OSError:
                continue

    def _should_scan_file(self, path: Path) -> bool:
        """Check if file should be scanned (exclude common ignores)."""
        path_str = str(path)
        return (
            "node_modules" not in path_str
            and ".git" not in path_str
            and "dist" not in path_str
            and "build" not in path_str
            and "__pycache__" not in path_str
        )
