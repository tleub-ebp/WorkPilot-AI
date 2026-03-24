#!/usr/bin/env python3
"""
Angular Project Analyzer

Analyzes Angular projects to detect version, structure, dependencies, and configuration.
Provides detailed insights for Angular development and migration planning.
"""

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AngularProjectAnalysis:
    """Result of analyzing an Angular project."""

    project_root: str
    angular_version: str = ""
    cli_version: str = ""
    typescript_version: str = ""
    project_type: str = "unknown"
    is_standalone: bool = False
    uses_signals: bool = False
    routing: bool = False
    testing_framework: str = ""
    build_tool: str = ""
    dependencies: list[dict[str, str]] = field(default_factory=list)
    dev_dependencies: list[dict[str, str]] = field(default_factory=list)
    components: list[str] = field(default_factory=list)
    modules: list[str] = field(default_factory=list)
    services: list[str] = field(default_factory=list)
    config_files: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class AngularProjectAnalyzer:
    """Analyzes Angular projects and provides development insights."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.angular_version_pattern = re.compile(r"^@angular/core@(\d+\.\d+\.\d+)")
        self.cli_version_pattern = re.compile(r"^@angular/cli@(\d+\.\d+\.\d+)")

    def analyze(self) -> AngularProjectAnalysis:
        """Perform comprehensive Angular project analysis."""
        analysis = AngularProjectAnalysis(project_root=str(self.project_root))

        # Check if this is an Angular project
        if not self._is_angular_project():
            analysis.issues.append("Not an Angular project - no angular.json found")
            return analysis

        # Analyze package.json
        self._analyze_package_json(analysis)

        # Analyze angular.json
        self._analyze_angular_json(analysis)

        # Scan project structure
        self._scan_project_structure(analysis)

        # Generate recommendations
        self._generate_recommendations(analysis)

        return analysis

    def _is_angular_project(self) -> bool:
        """Check if the project has Angular configuration."""
        return (self.project_root / "angular.json").exists()

    def _analyze_package_json(self, analysis: AngularProjectAnalysis):
        """Analyze package.json for Angular dependencies."""
        package_json_path = self.project_root / "package.json"

        if not package_json_path.exists():
            analysis.issues.append("package.json not found")
            return

        try:
            with open(package_json_path) as f:
                package_data = json.load(f)

            # Analyze dependencies
            deps = package_data.get("dependencies", {})
            dev_deps = package_data.get("devDependencies", {})

            # Extract Angular versions
            if "@angular/core" in deps:
                analysis.angular_version = deps["@angular/core"]

            if "@angular/cli" in dev_deps:
                analysis.cli_version = dev_deps["@angular/cli"]

            if "typescript" in dev_deps:
                analysis.typescript_version = dev_deps["typescript"]

            # Collect all dependencies
            for name, version in deps.items():
                if name.startswith("@angular/"):
                    analysis.dependencies.append({"name": name, "version": version})

            for name, version in dev_deps.items():
                if name.startswith("@angular/") or name in [
                    "typescript",
                    "ts-node",
                    "@types/node",
                ]:
                    analysis.dev_dependencies.append({"name": name, "version": version})

            # Detect project type and features
            if "@angular/platform-browser-dynamic" in deps:
                analysis.project_type = "module-based"
            elif "@angular/common" in deps and "@angular/core" in deps:
                analysis.project_type = "standalone"

            # Detect testing framework
            if "jasmine" in dev_deps or "@types/jasmine" in dev_deps:
                analysis.testing_framework = "jasmine"
            elif "jest" in dev_deps or "@types/jest" in dev_deps:
                analysis.testing_framework = "jest"

            # Detect build tool
            if "webpack" in dev_deps:
                analysis.build_tool = "webpack"
            elif "vite" in dev_deps or "@vitejs/plugin-angular" in dev_deps:
                analysis.build_tool = "vite"
            elif "esbuild" in dev_deps:
                analysis.build_tool = "esbuild"

        except Exception as e:
            analysis.issues.append(f"Error reading package.json: {e}")

    def _analyze_angular_json(self, analysis: AngularProjectAnalysis):
        """Analyze angular.json configuration."""
        angular_json_path = self.project_root / "angular.json"

        if not angular_json_path.exists():
            return

        try:
            with open(angular_json_path) as f:
                angular_config = json.load(f)

            analysis.config_files.append("angular.json")

            # Check for routing
            projects = angular_config.get("projects", {})
            for project_name, project_config in projects.items():
                if "architect" in project_config:
                    if "build" in project_config["architect"]:
                        build_config = project_config["architect"]["build"]
                        if "options" in build_config:
                            # Check for routing in styles/scripts
                            if (
                                "styles" in build_config["options"]
                                or "scripts" in build_config["options"]
                            ):
                                analysis.routing = True

        except Exception as e:
            analysis.issues.append(f"Error reading angular.json: {e}")

    def _scan_project_structure(self, analysis: AngularProjectAnalysis):
        """Scan project structure for Angular artifacts."""
        src_dir = self.project_root / "src"

        if not src_dir.exists():
            analysis.issues.append("src directory not found")
            return

        # Scan for Angular files
        for file_path in src_dir.rglob("*.ts"):
            if file_path.is_file():
                relative_path = file_path.relative_to(self.project_root)
                path_str = str(relative_path)

                if path_str.endswith(".component.ts"):
                    analysis.components.append(path_str)
                    # Check if standalone
                    try:
                        with open(file_path) as f:
                            content = f.read()
                            if (
                                "@Component" in content
                                and "standalone: true" in content
                            ):
                                analysis.is_standalone = True
                            if "signal(" in content or "Signal(" in content:
                                analysis.uses_signals = True
                    except Exception:
                        pass

                elif path_str.endswith(".module.ts"):
                    analysis.modules.append(path_str)

                elif path_str.endswith(".service.ts"):
                    analysis.services.append(path_str)

        # Check for routing module
        app_dir = src_dir / "app"
        if app_dir.exists():
            for file_path in app_dir.glob("*routing*.ts"):
                analysis.routing = True
                break

    def _generate_recommendations(self, analysis: AngularProjectAnalysis):
        """Generate development recommendations based on analysis."""
        recommendations = []

        # Version recommendations
        if analysis.angular_version:
            major_version = int(analysis.angular_version.split(".")[0])
            if major_version < 16:
                recommendations.append(
                    "Consider upgrading to Angular 16+ for better performance and signals support"
                )
            if major_version >= 17 and not analysis.is_standalone:
                recommendations.append(
                    "Consider migrating to standalone components for better tree-shaking"
                )

        # Architecture recommendations
        if analysis.project_type == "module-based" and analysis.is_standalone:
            recommendations.append(
                "Mixed architecture detected - consider fully migrating to standalone components"
            )

        if not analysis.routing:
            recommendations.append("Consider adding Angular Router for navigation")

        # Performance recommendations
        if analysis.build_tool == "webpack":
            recommendations.append(
                "Consider migrating to Vite for faster development builds"
            )

        if (
            not analysis.uses_signals
            and analysis.angular_version
            and int(analysis.angular_version.split(".")[0]) >= 16
        ):
            recommendations.append(
                "Consider using Angular Signals for reactive state management"
            )

        # Testing recommendations
        if not analysis.testing_framework:
            recommendations.append("Set up a testing framework (Jasmine or Jest)")

        analysis.recommendations = recommendations


def main():
    """Main entry point for the script."""
    if len(sys.argv) < 2:
        print("Usage: python analyze_angular_project.py <project_root>")
        sys.exit(1)

    project_root = sys.argv[1]
    analyzer = AngularProjectAnalyzer(project_root)

    try:
        analysis = analyzer.analyze()

        # Output results as JSON
        result = {
            "project_root": analysis.project_root,
            "angular_version": analysis.angular_version,
            "cli_version": analysis.cli_version,
            "typescript_version": analysis.typescript_version,
            "project_type": analysis.project_type,
            "is_standalone": analysis.is_standalone,
            "uses_signals": analysis.uses_signals,
            "routing": analysis.routing,
            "testing_framework": analysis.testing_framework,
            "build_tool": analysis.build_tool,
            "dependencies": analysis.dependencies,
            "dev_dependencies": analysis.dev_dependencies,
            "components_count": len(analysis.components),
            "modules_count": len(analysis.modules),
            "services_count": len(analysis.services),
            "config_files": analysis.config_files,
            "issues": analysis.issues,
            "recommendations": analysis.recommendations,
        }

        print(json.dumps(result, indent=2))

    except Exception as e:
        error_result = {"error": str(e), "project_root": project_root}
        print(json.dumps(error_result, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
