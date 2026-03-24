"""
Convention Enforcement Engine

This module provides intelligent convention enforcement for AI agents,
ensuring consistent adherence to project standards and patterns.
"""

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ConventionViolation:
    """Represents a convention violation with context and suggestions."""

    rule_type: str
    severity: str  # 'error', 'warning', 'info'
    message: str
    file_path: str | None = None
    line_number: int | None = None
    suggestion: str | None = None
    auto_fixable: bool = False


@dataclass
class ConventionRule:
    """Defines a convention rule with validation logic."""

    name: str
    description: str
    file_patterns: list[str]
    validation_function: callable
    severity: str = "warning"
    auto_fix_available: bool = False


class ConventionEngine:
    """
    Intelligent convention enforcement engine that validates code against
    project conventions and provides automated fixes where possible.
    """

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.workpilot_dir = self.project_root / ".workpilot"
        self.conventions_file = self.workpilot_dir / "conventions.md"
        self.architecture_file = self.workpilot_dir / "architecture.md"
        self.patterns_file = self.workpilot_dir / "patterns.md"

        self.rules: list[ConventionRule] = []
        self.conventions_data: dict[str, Any] = {}
        self.patterns_data: dict[str, Any] = {}

        self._load_conventions()
        self._initialize_rules()

    def _load_conventions(self):
        """Load convention data from steering files."""
        try:
            # Load conventions
            if self.conventions_file.exists():
                self.conventions_data = self._parse_markdown_file(self.conventions_file)

            # Load patterns
            if self.patterns_file.exists():
                self.patterns_data = self._parse_markdown_file(self.patterns_file)

        except Exception as e:
            logger.warning(f"Failed to load conventions: {e}")

    def _parse_markdown_file(self, file_path: Path) -> dict[str, Any]:
        """Parse markdown file to extract structured data."""
        content = file_path.read_text(encoding="utf-8")

        # Simple parsing - extract sections and their content
        sections = {}
        current_section = None
        current_content = []

        for line in content.split("\n"):
            if line.startswith("# "):
                if current_section:
                    sections[current_section] = "\n".join(current_content)
                current_section = line[2:].strip()
                current_content = []
            else:
                current_content.append(line)

        if current_section:
            sections[current_section] = "\n".join(current_content)

        return sections

    def _initialize_rules(self):
        """Initialize built-in convention rules."""
        self.rules = [
            # Python naming conventions
            ConventionRule(
                name="python_file_naming",
                description="Python files must use snake_case naming",
                file_patterns=["*.py"],
                validation_function=self._validate_python_file_naming,
                severity="warning",
            ),
            # TypeScript component naming
            ConventionRule(
                name="typescript_component_naming",
                description="React components must use PascalCase",
                file_patterns=["*.tsx"],
                validation_function=self._validate_tsx_component_naming,
                severity="warning",
            ),
            # Import organization
            ConventionRule(
                name="python_import_organization",
                description="Python imports must be organized and grouped",
                file_patterns=["*.py"],
                validation_function=self._validate_python_imports,
                severity="info",
            ),
            # TypeScript strict mode
            ConventionRule(
                name="typescript_strict_mode",
                description="TypeScript files must use strict mode",
                file_patterns=["*.ts", "*.tsx"],
                validation_function=self._validate_typescript_strict_mode,
                severity="error",
            ),
            # Docstring requirements
            ConventionRule(
                name="python_docstrings",
                description="Public functions must have docstrings",
                file_patterns=["*.py"],
                validation_function=self._validate_python_docstrings,
                severity="warning",
            ),
            # i18n requirements for frontend
            ConventionRule(
                name="frontend_i18n",
                description="Frontend text must use translation keys",
                file_patterns=["*.tsx", "*.ts"],
                validation_function=self._validate_frontend_i18n,
                severity="error",
            ),
            # Claude SDK usage
            ConventionRule(
                name="claude_sdk_usage",
                description="Must use Claude Agent SDK, not direct Anthropic API",
                file_patterns=["*.py"],
                validation_function=self._validate_claude_sdk_usage,
                severity="error",
            ),
            # Platform abstraction
            ConventionRule(
                name="platform_abstraction",
                description="Use platform abstraction functions",
                file_patterns=["*.py", "*.ts", "*.tsx"],
                validation_function=self._validate_platform_abstraction,
                severity="warning",
            ),
        ]

    def validate_file(self, file_path: str) -> list[ConventionViolation]:
        """Validate a single file against all applicable rules."""
        violations = []
        file_path_obj = Path(file_path)

        if not file_path_obj.exists():
            return violations

        # Find applicable rules
        applicable_rules = [
            rule
            for rule in self.rules
            if any(file_path_obj.match(pattern) for pattern in rule.file_patterns)
        ]

        # Apply each rule
        for rule in applicable_rules:
            try:
                rule_violations = rule.validation_function(file_path_obj)
                violations.extend(rule_violations)
            except Exception as e:
                logger.warning(f"Rule {rule.name} failed on {file_path}: {e}")

        return violations

    def validate_project(
        self, file_paths: list[str] | None = None
    ) -> dict[str, list[ConventionViolation]]:
        """Validate multiple files or entire project."""
        if file_paths is None:
            # Scan project for relevant files
            file_paths = []
            for pattern in set().union(*[rule.file_patterns for rule in self.rules]):
                file_paths.extend(self.project_root.rglob(pattern))

        results = {}
        for file_path in file_paths:
            violations = self.validate_file(str(file_path))
            if violations:
                results[str(file_path)] = violations

        return results

    def _validate_python_file_naming(
        self, file_path: Path
    ) -> list[ConventionViolation]:
        """Validate Python file naming convention."""
        violations = []
        filename = file_path.name

        if not filename.endswith(".py"):
            return violations

        base_name = filename[:-3]  # Remove .py extension

        # Check snake_case pattern
        if not re.match(r"^[a-z][a-z0-9_]*$", base_name):
            violations.append(
                ConventionViolation(
                    rule_type="python_file_naming",
                    severity="warning",
                    message=f"Python file '{filename}' should use snake_case naming",
                    file_path=str(file_path),
                    suggestion=f"Rename to '{self._to_snake_case(base_name)}.py'",
                    auto_fixable=True,
                )
            )

        return violations

    def _validate_tsx_component_naming(
        self, file_path: Path
    ) -> list[ConventionViolation]:
        """Validate TypeScript React component naming."""
        violations = []
        filename = file_path.name

        if not filename.endswith(".tsx"):
            return violations

        content = file_path.read_text(encoding="utf-8")

        # Look for React component exports
        component_exports = re.findall(
            r"export\s+(?:function|const)\s+([A-Z][a-zA-Z0-9]*)", content
        )

        for component_name in component_exports:
            # Check if filename matches component name
            expected_filename = f"{component_name}.tsx"
            if filename != expected_filename:
                violations.append(
                    ConventionViolation(
                        rule_type="typescript_component_naming",
                        severity="warning",
                        message=f"Component '{component_name}' should be in file '{expected_filename}'",
                        file_path=str(file_path),
                        suggestion=f"Rename file to '{expected_filename}'",
                        auto_fixable=True,
                    )
                )

        return violations

    def _validate_python_imports(self, file_path: Path) -> list[ConventionViolation]:
        """Validate Python import organization."""
        violations = []
        content = file_path.read_text(encoding="utf-8")

        lines = content.split("\n")
        import_section_start = None
        import_section_end = None

        # Find import section
        for i, line in enumerate(lines):
            if line.strip().startswith(("import ", "from ")):
                if import_section_start is None:
                    import_section_start = i
                import_section_end = i
            elif (
                import_section_start is not None
                and line.strip()
                and not line.strip().startswith(("import ", "from ", "#"))
            ):
                break

        if import_section_start is None:
            return violations

        # Check import organization
        import_lines = lines[import_section_start : import_section_end + 1]
        current_group = None

        for i, line in enumerate(import_lines):
            if line.strip().startswith("import "):
                # Standard library imports should come first
                if line.strip().startswith("import os") or line.strip().startswith(
                    "import sys"
                ):
                    group = "stdlib"
                else:
                    group = "third_party"

                if current_group and group != current_group:
                    violations.append(
                        ConventionViolation(
                            rule_type="python_import_organization",
                            severity="info",
                            message="Import groups should be separated by blank lines",
                            file_path=str(file_path),
                            line_number=import_section_start + i + 1,
                        )
                    )

                current_group = group

        return violations

    def _validate_typescript_strict_mode(
        self, file_path: Path
    ) -> list[ConventionViolation]:
        """Validate TypeScript strict mode usage."""
        violations = []

        if file_path.suffix not in [".ts", ".tsx"]:
            return violations

        # Check if in a TypeScript project with strict mode
        tsconfig_path = self.project_root / "tsconfig.json"
        if tsconfig_path.exists():
            try:
                tsconfig = json.loads(tsconfig_path.read_text(encoding="utf-8"))
                if tsconfig.get("compilerOptions", {}).get("strict") is True:
                    # File should comply with strict mode rules
                    content = file_path.read_text(encoding="utf-8")

                    # Check for any type issues (basic checks)
                    if "any" in content and ": any" in content:
                        violations.append(
                            ConventionViolation(
                                rule_type="typescript_strict_mode",
                                severity="warning",
                                message="Avoid using 'any' type in strict mode",
                                file_path=str(file_path),
                                suggestion="Use specific types instead of 'any'",
                            )
                        )
            except Exception:
                pass

        return violations

    def _validate_python_docstrings(self, file_path: Path) -> list[ConventionViolation]:
        """Validate Python docstring requirements."""
        violations = []
        content = file_path.read_text(encoding="utf-8")

        # Find public function definitions
        function_pattern = r"^def\s+([a-z][a-z0-9_]*)\s*\([^)]*\)\s*->\s*\w+:"
        functions = re.finditer(function_pattern, content, re.MULTILINE)

        for func_match in functions:
            func_name = func_match.group(1)
            func_start = func_match.start()

            # Skip private functions
            if func_name.startswith("_"):
                continue

            # Find the function body start
            lines_after_func = content[func_start:].split("\n")
            docstring_found = False

            for line in lines_after_func[1:5]:  # Check first few lines
                if '"""' in line or "'''" in line:
                    docstring_found = True
                    break
                elif line.strip() and not line.strip().startswith("#"):
                    # Non-comment, non-empty line without docstring
                    break

            if not docstring_found:
                line_number = content[:func_start].count("\n") + 1
                violations.append(
                    ConventionViolation(
                        rule_type="python_docstrings",
                        severity="warning",
                        message=f"Public function '{func_name}' missing docstring",
                        file_path=str(file_path),
                        line_number=line_number,
                        suggestion=f'Add docstring: """{func_name} function description."""',
                        auto_fixable=False,
                    )
                )

        return violations

    def _validate_frontend_i18n(self, file_path: Path) -> list[ConventionViolation]:
        """Validate frontend internationalization usage."""
        violations = []

        if file_path.suffix not in [".ts", ".tsx"]:
            return violations

        content = file_path.read_text(encoding="utf-8")

        # Look for hardcoded strings in JSX/TSX
        if file_path.suffix == ".tsx":
            # Find text content in JSX that should use i18n
            hardcoded_pattern = r">[^<]*[a-zA-Z][^<]*<"
            matches = re.finditer(hardcoded_pattern, content)

            for match in matches:
                text_content = match.group()[1:-1].strip()

                # Skip if it's just numbers, symbols, or very short
                if len(text_content) < 3 or not re.search(r"[a-zA-Z]", text_content):
                    continue

                # Skip if it looks like a variable or expression
                if "{" in text_content or "}" in text_content:
                    continue

                line_number = content[: match.start()].count("\n") + 1
                violations.append(
                    ConventionViolation(
                        rule_type="frontend_i18n",
                        severity="error",
                        message=f"Hardcoded text '{text_content}' should use i18n",
                        file_path=str(file_path),
                        line_number=line_number,
                        suggestion="Use translation key instead of hardcoded text",
                    )
                )

        return violations

    def _validate_claude_sdk_usage(self, file_path: Path) -> list[ConventionViolation]:
        """Validate Claude SDK usage (no direct Anthropic API)."""
        violations = []
        content = file_path.read_text(encoding="utf-8")

        # Check for direct Anthropic API usage
        if (
            "anthropic.Anthropic(" in content
            or "from anthropic import Anthropic" in content
        ):
            violations.append(
                ConventionViolation(
                    rule_type="claude_sdk_usage",
                    severity="error",
                    message="Direct Anthropic API usage detected. Use Claude Agent SDK instead.",
                    file_path=str(file_path),
                    suggestion="Replace with 'from core.client import create_client'",
                )
            )

        # Check for proper SDK usage
        if "create_client" in content and "core.client" in content:
            # This is good - no violation
            pass

        return violations

    def _validate_platform_abstraction(
        self, file_path: Path
    ) -> list[ConventionViolation]:
        """Validate platform abstraction usage."""
        violations = []
        content = file_path.read_text(encoding="utf-8")

        if file_path.suffix == ".py":
            # Check for direct platform usage
            if "process.platform" in content:
                violations.append(
                    ConventionViolation(
                        rule_type="platform_abstraction",
                        severity="warning",
                        message="Use platform abstraction functions instead of process.platform",
                        file_path=str(file_path),
                        suggestion="Import from core.platform instead",
                    )
                )

        return violations

    def _to_snake_case(self, name: str) -> str:
        """Convert string to snake_case."""
        # Insert underscores before capital letters
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)
        return s2.lower()

    def add_custom_rule(self, rule: ConventionRule):
        """Add a custom convention rule."""
        self.rules.append(rule)

    def remove_rule(self, rule_name: str) -> bool:
        """Remove a rule by name."""
        for i, rule in enumerate(self.rules):
            if rule.name == rule_name:
                del self.rules[i]
                return True
        return False

    def get_rules_summary(self) -> dict[str, Any]:
        """Get summary of all rules."""
        return {
            "total_rules": len(self.rules),
            "rule_types": [rule.name for rule in self.rules],
            "severity_distribution": {
                severity: len([r for r in self.rules if r.severity == severity])
                for severity in ["error", "warning", "info"]
            },
            "auto_fixable_count": len([r for r in self.rules if r.auto_fix_available]),
        }


def create_convention_engine(project_root: str) -> ConventionEngine:
    """Factory function to create convention engine."""
    return ConventionEngine(project_root)
