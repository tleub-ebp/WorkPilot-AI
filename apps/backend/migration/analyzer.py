"""
Stack Analyzer: Detects and analyzes technology stacks.
"""

import os
import json
import re
from typing import Dict, Optional, List, Tuple
from pathlib import Path
from dataclasses import asdict

from .models import StackInfo, RiskLevel
from .config import SUPPORTED_MIGRATIONS, RISK_ASSESSMENT_THRESHOLDS


class StackAnalyzer:
    """Analyzes technology stacks in a project."""

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.cache: Dict = {}

    def detect_stack(self) -> StackInfo:
        """Detect the technology stack of the project."""
        framework = self._detect_framework()
        language = self._detect_language()
        version = self._detect_version(framework, language)
        database = self._detect_database()
        db_version = self._detect_db_version(database) if database else None
        dependencies = self._extract_dependencies()
        additional_tools = self._detect_tools()
        package_manager = self._detect_package_manager()

        return StackInfo(
            framework=framework,
            language=language,
            version=version,
            database=database,
            db_version=db_version,
            dependencies=dependencies,
            additional_tools=additional_tools,
            package_manager=package_manager,
        )

    def _detect_framework(self) -> str:
        """Detect primary framework (React, Vue, Django, etc.)."""
        # Check for frontend frameworks
        if self._check_file_exists("node_modules/react"):
            return "react"
        if self._check_file_exists("node_modules/vue"):
            return "vue"
        if self._check_file_exists("node_modules/angular"):
            return "angular"
        if self._check_file_exists("node_modules/svelte"):
            return "svelte"

        # Check package.json
        package_json = self._read_package_json()
        if package_json:
            deps = {**package_json.get("dependencies", {}), 
                    **package_json.get("devDependencies", {})}
            if "react" in deps:
                return "react"
            if "vue" in deps:
                return "vue"
            if "@angular/core" in deps:
                return "angular"
            if "svelte" in deps:
                return "svelte"

        # Check for backend frameworks
        if self._check_file_exists("requirements.txt") or self._check_file_exists("pyproject.toml"):
            reqs = self._read_requirements_txt()
            if "django" in reqs.lower():
                return "django"
            if "flask" in reqs.lower():
                return "flask"
            if "fastapi" in reqs.lower():
                return "fastapi"
            return "python"  # Default Python framework

        # Check for Node.js backends
        if package_json:
            deps = {**package_json.get("dependencies", {}), 
                    **package_json.get("devDependencies", {})}
            if "express" in deps:
                return "express"
            if "fastify" in deps:
                return "fastify"
            if "koa" in deps:
                return "koa"
            return "nodejs"  # Default Node.js

        return "unknown"

    def _detect_language(self) -> str:
        """Detect primary programming language."""
        # Check for TypeScript
        if self._check_file_exists("tsconfig.json"):
            return "typescript"

        # Check for Python
        if self._check_file_exists("setup.py") or self._check_file_exists("pyproject.toml"):
            return "python"

        # Check for Java
        if self._check_file_exists("pom.xml") or self._check_file_exists("build.gradle"):
            return "java"

        # Check for Go
        if self._check_file_exists("go.mod"):
            return "go"

        # Check for Rust
        if self._check_file_exists("Cargo.toml"):
            return "rust"

        # Check file extensions
        py_count = len(list(self.project_dir.rglob("*.py")))
        js_count = len(list(self.project_dir.rglob("*.js")))
        ts_count = len(list(self.project_dir.rglob("*.ts")))
        jsx_count = len(list(self.project_dir.rglob("*.jsx")))
        tsx_count = len(list(self.project_dir.rglob("*.tsx")))
        java_count = len(list(self.project_dir.rglob("*.java")))
        go_count = len(list(self.project_dir.rglob("*.go")))
        rs_count = len(list(self.project_dir.rglob("*.rs")))

        counts = {
            "python": py_count,
            "javascript": js_count + jsx_count,
            "typescript": ts_count + tsx_count,
            "java": java_count,
            "go": go_count,
            "rust": rs_count,
        }

        if max(counts.values()) == 0:
            return "unknown"

        return max(counts, key=counts.get)

    def _detect_version(self, framework: str, language: str) -> str:
        """Detect framework/language version."""
        # Python version
        if language == "python":
            if self._check_python_version_file("python2"):
                return "2.7"
            # Default to 3.x
            pyproject = self._read_pyproject_toml()
            if pyproject:
                requires_python = pyproject.get("project", {}).get("requires-python")
                if requires_python:
                    return self._parse_version_spec(requires_python)
            return "3.8"

        # TypeScript version
        if language == "typescript":
            tsconfig = self._read_tsconfig()
            if tsconfig:
                return tsconfig.get("compilerOptions", {}).get("target", "es2020")

        # Package.json based detection
        package_json = self._read_package_json()
        if package_json:
            if framework == "react":
                return package_json.get("dependencies", {}).get("react", "unknown")
            if framework == "vue":
                return package_json.get("dependencies", {}).get("vue", "unknown")
            if language == "typescript":
                return package_json.get("devDependencies", {}).get("typescript", "unknown")

        return "unknown"

    def _detect_database(self) -> Optional[str]:
        """Detect database technology."""
        package_json = self._read_package_json()
        if package_json:
            deps = {**package_json.get("dependencies", {}), 
                    **package_json.get("devDependencies", {})}
            if "mysql" in deps or "mysql2" in deps:
                return "mysql"
            if "pg" in deps or "postgres" in deps or "postgresql" in deps:
                return "postgresql"
            if "mongodb" in deps:
                return "mongodb"
            if "redis" in deps:
                return "redis"

        # Check requirements.txt
        reqs = self._read_requirements_txt()
        if reqs:
            if "mysql" in reqs.lower() or "mysqlclient" in reqs.lower():
                return "mysql"
            if "psycopg" in reqs.lower() or "postgresql" in reqs.lower():
                return "postgresql"
            if "pymongo" in reqs.lower():
                return "mongodb"
            if "redis" in reqs.lower():
                return "redis"

        # Check for SQL files
        sql_files = list(self.project_dir.rglob("**/*.sql"))
        if sql_files:
            content = "\n".join(f.read_text() for f in sql_files[:5])
            if "PRAGMA" in content or "sqlite" in content.lower():
                return "sqlite"

        return None

    def _detect_db_version(self, database: Optional[str]) -> Optional[str]:
        """Detect database version."""
        if not database:
            return None

        package_json = self._read_package_json()
        if package_json:
            deps = {**package_json.get("dependencies", {}), 
                    **package_json.get("devDependencies", {})}
            if database == "mysql":
                return deps.get("mysql") or deps.get("mysql2")
            if database == "postgresql":
                return deps.get("pg") or deps.get("postgres")

        reqs = self._read_requirements_txt()
        if reqs:
            for line in reqs.split("\n"):
                if database in line.lower():
                    return self._extract_version_from_requirement(line)

        return None

    def _extract_dependencies(self) -> Dict[str, str]:
        """Extract all project dependencies."""
        dependencies = {}

        # From package.json
        package_json = self._read_package_json()
        if package_json:
            dependencies.update(package_json.get("dependencies", {}))
            dependencies.update(package_json.get("devDependencies", {}))

        # From requirements.txt
        reqs = self._read_requirements_txt()
        if reqs:
            for line in reqs.split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    parts = re.split(r"[=<>!]", line)
                    if parts:
                        name = parts[0].strip()
                        version = self._extract_version_from_requirement(line)
                        dependencies[name] = version

        # Limit to top dependencies to avoid bloat
        sorted_deps = sorted(dependencies.items())[:30]
        return dict(sorted_deps)

    def _detect_tools(self) -> List[str]:
        """Detect build tools and additional frameworks."""
        tools = []

        # Check for webpack
        if self._check_file_exists("webpack.config.js"):
            tools.append("webpack")
        # Check for vite
        if self._check_file_exists("vite.config.js"):
            tools.append("vite")
        # Check for babel
        if self._check_file_exists(".babelrc") or self._check_file_exists("babel.config.js"):
            tools.append("babel")
        # Check for docker
        if self._check_file_exists("Dockerfile"):
            tools.append("docker")
        # Check for k8s
        if self._check_file_exists("k8s"):
            tools.append("kubernetes")

        # Check package.json for tools
        package_json = self._read_package_json()
        if package_json:
            scripts = package_json.get("scripts", {})
            if "docker" in str(scripts).lower():
                tools.append("docker")

        return list(set(tools))

    def _detect_package_manager(self) -> str:
        """Detect package manager (npm, pip, etc.)."""
        if self._check_file_exists("package-lock.json"):
            return "npm"
        if self._check_file_exists("pnpm-lock.yaml"):
            return "pnpm"
        if self._check_file_exists("yarn.lock"):
            return "yarn"
        if self._check_file_exists("requirements.txt"):
            return "pip"
        if self._check_file_exists("pyproject.toml"):
            return "poetry"
        if self._check_file_exists("Gemfile.lock"):
            return "bundler"
        if self._check_file_exists("go.sum"):
            return "go"
        if self._check_file_exists("Cargo.lock"):
            return "cargo"

        return "unknown"

    def assess_migration_complexity(self, source: StackInfo, target: StackInfo) -> Dict:
        """Assess complexity of migrating from source to target."""
        key = (source.framework, target.framework)
        if key not in SUPPORTED_MIGRATIONS:
            return {
                "supported": False,
                "reason": f"Migration from {source.framework} to {target.framework} not supported",
            }

        config = SUPPORTED_MIGRATIONS[key]
        
        # Count affected files
        affected_files = self._count_affected_files(key)
        
        # Calculate complexity score
        complexity_score = self._calculate_complexity_score(source, target, affected_files)
        
        # Determine risk level
        risk_level = self._determine_risk_level(affected_files, complexity_score)
        
        return {
            "supported": True,
            "affected_files": affected_files,
            "complexity_score": complexity_score,
            "risk_level": risk_level.value,
            "estimated_effort": config.get("estimated_effort_hours", 0),
            "has_breaking_changes": config.get("breaking_changes", False),
            "data_preservation": config.get("data_preservation", False),
        }

    def _count_affected_files(self, migration_key: Tuple[str, str]) -> int:
        """Count files affected by migration."""
        source_framework, target_framework = migration_key
        
        patterns = []
        if source_framework == "react":
            patterns = ["**/*.jsx", "**/*.tsx"]
        elif source_framework == "vue":
            patterns = ["**/*.vue", "**/*.ts"]
        elif source_framework == "mysql":
            patterns = ["**/*.sql", "**/migrations/**"]
        elif source_framework == "python":
            patterns = ["**/*.py"]

        count = 0
        for pattern in patterns:
            count += len(list(self.project_dir.rglob(pattern)))

        return count

    def _calculate_complexity_score(self, source: StackInfo, target: StackInfo, 
                                   affected_files: int) -> float:
        """Calculate migration complexity score (0-10)."""
        score = 1.0

        # Factor in affected files
        if affected_files > 500:
            score += 3.0
        elif affected_files > 200:
            score += 2.0
        elif affected_files > 50:
            score += 1.0

        # Factor in dependency complexity
        dep_count = len(source.dependencies)
        if dep_count > 50:
            score += 2.0
        elif dep_count > 20:
            score += 1.0

        # Database migration complexity
        if source.database and source.database != target.database:
            score += 2.0

        return min(score, 10.0)

    def _determine_risk_level(self, affected_files: int, complexity_score: float) -> RiskLevel:
        """Determine risk level based on various factors."""
        thresholds = RISK_ASSESSMENT_THRESHOLDS
        
        if affected_files > thresholds["high"]["max_affected_files"]:
            return RiskLevel.CRITICAL
        elif complexity_score > 8.0:
            return RiskLevel.HIGH
        elif complexity_score > 5.0:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    # Helper methods
    def _check_file_exists(self, path: str) -> bool:
        """Check if file or directory exists in project."""
        full_path = self.project_dir / path
        return full_path.exists()

    def _check_python_version_file(self, pattern: str) -> bool:
        """Check for Python version markers."""
        shebang_pattern = f"#!/usr/bin/env {pattern}"
        for py_file in self.project_dir.rglob("*.py"):
            try:
                content = py_file.read_text()[:100]
                if pattern in content:
                    return True
            except Exception:
                pass
        return False

    def _read_package_json(self) -> Optional[Dict]:
        """Read package.json."""
        if "package_json" in self.cache:
            return self.cache["package_json"]

        path = self.project_dir / "package.json"
        if path.exists():
            try:
                data = json.loads(path.read_text())
                self.cache["package_json"] = data
                return data
            except (json.JSONDecodeError, OSError):
                pass
        return None

    def _read_requirements_txt(self) -> str:
        """Read requirements.txt."""
        if "requirements" in self.cache:
            return self.cache["requirements"]

        path = self.project_dir / "requirements.txt"
        if path.exists():
            content = path.read_text()
            self.cache["requirements"] = content
            return content
        return ""

    def _read_pyproject_toml(self) -> Optional[Dict]:
        """Read pyproject.toml."""
        path = self.project_dir / "pyproject.toml"
        if path.exists():
            try:
                import tomllib  # Python 3.11+
                return tomllib.loads(path.read_text())
            except (ImportError, Exception):
                try:
                    import tomli
                    return tomli.loads(path.read_text())
                except Exception:
                    pass
        return None

    def _read_tsconfig(self) -> Optional[Dict]:
        """Read tsconfig.json."""
        path = self.project_dir / "tsconfig.json"
        if path.exists():
            try:
                return json.loads(path.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        return None

    def _parse_version_spec(self, spec: str) -> str:
        """Parse version specification (e.g., '>=3.8')."""
        match = re.search(r"(\d+\.\d+)", spec)
        return match.group(1) if match else "unknown"

    def _extract_version_from_requirement(self, req: str) -> str:
        """Extract version from requirement line."""
        match = re.search(r"(?:==|>=|<=|>|<|~=)([0-9.]+)", req)
        return match.group(1) if match else "unknown"
