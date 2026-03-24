"""
Custom Rule Engine
==================

Permet de définir des règles personnalisées par projet.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .quality_scorer import IssueSeverity, QualityCategory, QualityIssue


@dataclass
class CustomRule:
    """Une règle personnalisée."""

    id: str
    name: str
    description: str
    category: QualityCategory
    severity: IssueSeverity
    pattern: str  # Regex pattern
    file_patterns: list[str]  # Glob patterns pour fichiers
    suggestion: str
    enabled: bool = True


class CustomRuleEngine:
    """Moteur de règles personnalisées."""

    def __init__(self, config_path: Path | None = None):
        """
        Initialize rule engine.

        Args:
            config_path: Chemin vers fichier de config YAML
        """
        self.rules: list[CustomRule] = []
        self.config_path = config_path

        if config_path and config_path.exists():
            self.load_rules(config_path)

    def load_rules(self, config_path: Path) -> None:
        """Charge les règles depuis un fichier YAML."""
        try:
            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if not config or "rules" not in config:
                return

            for rule_data in config["rules"]:
                rule = self._parse_rule(rule_data)
                if rule:
                    self.rules.append(rule)

        except Exception as e:
            print(f"Warning: Failed to load custom rules: {e}")

    def _parse_rule(self, data: dict[str, Any]) -> CustomRule | None:
        """Parse une règle depuis YAML."""
        try:
            return CustomRule(
                id=data["id"],
                name=data["name"],
                description=data.get("description", ""),
                category=QualityCategory(data.get("category", "maintainability")),
                severity=IssueSeverity(data.get("severity", "medium")),
                pattern=data["pattern"],
                file_patterns=data.get("file_patterns", ["**/*"]),
                suggestion=data.get("suggestion", ""),
                enabled=data.get("enabled", True),
            )
        except Exception:
            return None

    def add_rule(self, rule: CustomRule) -> None:
        """Ajoute une règle."""
        self.rules.append(rule)

    def analyze_file(self, file_path: Path, content: str) -> list[QualityIssue]:
        """Analyse un fichier avec les règles personnalisées."""
        issues = []

        for rule in self.rules:
            if not rule.enabled:
                continue

            # Vérifier si le fichier matche les patterns
            if not self._file_matches(file_path, rule.file_patterns):
                continue

            # Appliquer la règle
            rule_issues = self._apply_rule(rule, file_path, content)
            issues.extend(rule_issues)

        return issues

    def _file_matches(self, file_path: Path, patterns: list[str]) -> bool:
        """Vérifie si un fichier matche les patterns."""
        for pattern in patterns:
            if file_path.match(pattern):
                return True
        return False

    def _apply_rule(
        self, rule: CustomRule, file_path: Path, content: str
    ) -> list[QualityIssue]:
        """Applique une règle sur un fichier."""
        issues = []

        try:
            pattern = re.compile(rule.pattern, re.MULTILINE)
            lines = content.split("\n")

            for i, line in enumerate(lines, 1):
                if pattern.search(line):
                    issues.append(
                        QualityIssue(
                            category=rule.category,
                            severity=rule.severity,
                            title=rule.name,
                            description=rule.description,
                            file=str(file_path),
                            line=i,
                            suggestion=rule.suggestion,
                        )
                    )

        except Exception:
            pass

        return issues

    def save_rules(self, output_path: Path) -> None:
        """Sauvegarde les règles dans un fichier YAML."""
        config = {
            "rules": [
                {
                    "id": rule.id,
                    "name": rule.name,
                    "description": rule.description,
                    "category": rule.category.value,
                    "severity": rule.severity.value,
                    "pattern": rule.pattern,
                    "file_patterns": rule.file_patterns,
                    "suggestion": rule.suggestion,
                    "enabled": rule.enabled,
                }
                for rule in self.rules
            ]
        }

        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    def generate_template(self, output_path: Path) -> None:
        """Génère un fichier template de configuration."""
        template = {
            "rules": [
                {
                    "id": "no-todo-comments",
                    "name": "TODO comments detected",
                    "description": "TODO comments should be converted to issues",
                    "category": "maintainability",
                    "severity": "low",
                    "pattern": r"#\s*TODO|//\s*TODO",
                    "file_patterns": ["**/*.py", "**/*.js", "**/*.java"],
                    "suggestion": "Create an issue tracker entry instead of TODO",
                    "enabled": True,
                },
                {
                    "id": "no-fixme-comments",
                    "name": "FIXME comments detected",
                    "description": "FIXME indicates code that needs attention",
                    "category": "bugs",
                    "severity": "medium",
                    "pattern": r"#\s*FIXME|//\s*FIXME",
                    "file_patterns": ["**/*.py", "**/*.js", "**/*.java"],
                    "suggestion": "Fix the issue or create a tracking ticket",
                    "enabled": True,
                },
                {
                    "id": "no-debugger",
                    "name": "Debugger statement detected",
                    "description": "Debugger statements should not be in production",
                    "category": "bugs",
                    "severity": "high",
                    "pattern": r"debugger\s*;",
                    "file_patterns": ["**/*.js", "**/*.ts"],
                    "suggestion": "Remove debugger statement",
                    "enabled": True,
                },
                {
                    "id": "no-magic-numbers",
                    "name": "Magic number detected",
                    "description": "Use named constants instead of magic numbers",
                    "category": "maintainability",
                    "severity": "low",
                    "pattern": r"=\s*\d{3,}",  # Numbers with 3+ digits
                    "file_patterns": ["**/*.py", "**/*.js"],
                    "suggestion": "Define as a named constant",
                    "enabled": False,  # Peut générer beaucoup de faux positifs
                },
            ]
        }

        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(template, f, default_flow_style=False, sort_keys=False)


def load_project_rules(project_dir: Path) -> CustomRuleEngine:
    """
    Charge les règles personnalisées d'un projet.

    Cherche dans:
    - .quality-rules.yml
    - .auto-claude/quality-rules.yml
    """
    engine = CustomRuleEngine()

    # Essayer les différents emplacements
    locations = [
        project_dir / ".quality-rules.yml",
        project_dir / ".quality-rules.yaml",
        project_dir / ".auto-claude" / "quality-rules.yml",
        project_dir / ".auto-claude" / "quality-rules.yaml",
    ]

    for location in locations:
        if location.exists():
            engine.load_rules(location)
            return engine

    return engine
