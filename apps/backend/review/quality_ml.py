"""
ML-Based Pattern Detection
===========================

Système d'apprentissage automatique pour détecter des patterns personnalisés.
Utilise des techniques simples (pas besoin d'infrastructure lourde).
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .quality_scorer import IssueSeverity, QualityCategory, QualityIssue


@dataclass
class LearnedPattern:
    """Un pattern appris par le système ML."""

    pattern_id: str
    pattern_type: str  # 'naming', 'structure', 'import', 'comment'
    description: str
    example: str
    frequency: int
    confidence: float  # 0.0-1.0


class MLPatternDetector:
    """Détecteur de patterns basé sur ML simple."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.cache_dir = project_dir / ".auto-claude" / "ml-cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.patterns: list[LearnedPattern] = []
        self.learned_data: dict[str, Any] = {}

    def learn_from_codebase(
        self,
        file_patterns: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Apprend les patterns d'un projet.

        Returns:
            Dict avec statistiques d'apprentissage
        """
        if file_patterns is None:
            file_patterns = ["**/*.py", "**/*.js", "**/*.ts", "**/*.java"]

        print("🧠 Learning patterns from codebase...")

        # Collecter les fichiers
        files = []
        for pattern in file_patterns:
            files.extend(self.project_dir.glob(pattern))

        # Analyser chaque fichier
        naming_patterns = defaultdict(int)
        import_patterns = defaultdict(int)
        function_lengths = []
        indentation_styles = defaultdict(int)

        for file in files:
            try:
                content = file.read_text(encoding="utf-8")
                lines = content.split("\n")

                # Apprendre naming conventions
                self._learn_naming_patterns(content, naming_patterns)

                # Apprendre import patterns
                self._learn_import_patterns(lines, import_patterns)

                # Apprendre function lengths
                self._learn_function_metrics(content, function_lengths)

                # Apprendre indentation
                self._learn_indentation(lines, indentation_styles)

            except Exception:
                continue

        # Créer des patterns appris
        self.learned_data = {
            "naming": dict(naming_patterns),
            "imports": dict(import_patterns),
            "function_lengths": function_lengths,
            "indentation": dict(indentation_styles),
            "total_files": len(files),
        }

        # Générer les patterns
        self._generate_patterns()

        # Sauvegarder
        self._save_learned_data()

        return {
            "files_analyzed": len(files),
            "patterns_learned": len(self.patterns),
            "naming_conventions": len(naming_patterns),
            "import_patterns": len(import_patterns),
        }

    def _learn_naming_patterns(self, content: str, patterns: dict) -> None:
        """Apprend les conventions de nommage."""
        # Variables
        var_pattern = r"\b([a-z_][a-z0-9_]*)\s*="
        for match in re.finditer(var_pattern, content):
            name = match.group(1)
            if "_" in name:
                patterns["snake_case"] += 1
            elif name.islower():
                patterns["lowercase"] += 1

        # Classes
        class_pattern = r"\bclass\s+([A-Z][a-zA-Z0-9]*)"
        for match in re.finditer(class_pattern, content):
            name = match.group(1)
            if name[0].isupper():
                patterns["PascalCase"] += 1

        # Functions
        func_pattern = r"\bdef\s+([a-z_][a-z0-9_]*)\s*\("
        for match in re.finditer(func_pattern, content):
            name = match.group(1)
            if "_" in name:
                patterns["function_snake_case"] += 1

    def _learn_import_patterns(self, lines: list[str], patterns: dict) -> None:
        """Apprend les patterns d'imports."""
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("import "):
                patterns["absolute_import"] += 1
            elif stripped.startswith("from "):
                if "import *" in stripped:
                    patterns["wildcard_import"] += 1
                else:
                    patterns["from_import"] += 1

    def _learn_function_metrics(self, content: str, lengths: list) -> None:
        """Apprend les métriques de fonctions."""
        # Simple heuristic: compter les lignes entre def et prochain def
        func_starts = [m.start() for m in re.finditer(r"\bdef\s+\w+", content)]

        for i, start in enumerate(func_starts):
            end = func_starts[i + 1] if i + 1 < len(func_starts) else len(content)
            func_content = content[start:end]
            line_count = func_content.count("\n")
            if 1 < line_count < 100:  # Filtrer les valeurs aberrantes
                lengths.append(line_count)

    def _learn_indentation(self, lines: list[str], styles: dict) -> None:
        """Apprend le style d'indentation."""
        for line in lines:
            if line and line[0] in " \t":
                indent = len(line) - len(line.lstrip())
                if line.startswith("    "):
                    styles["4_spaces"] += 1
                elif line.startswith("  "):
                    styles["2_spaces"] += 1
                elif line.startswith("\t"):
                    styles["tabs"] += 1

    def _generate_patterns(self) -> None:
        """Génère des patterns détectables à partir des données apprises."""
        self.patterns = []

        # Naming convention pattern
        if "naming" in self.learned_data:
            naming = self.learned_data["naming"]
            total = sum(naming.values())
            if total > 0:
                dominant_style = max(naming.items(), key=lambda x: x[1])
                confidence = dominant_style[1] / total

                if confidence > 0.7:
                    self.patterns.append(
                        LearnedPattern(
                            pattern_id="naming_convention",
                            pattern_type="naming",
                            description=f"Project uses {dominant_style[0]} naming convention",
                            example=f"Expected: {dominant_style[0]}",
                            frequency=dominant_style[1],
                            confidence=confidence,
                        )
                    )

        # Function length pattern
        if self.learned_data.get("function_lengths"):
            lengths = self.learned_data["function_lengths"]
            if lengths:
                avg_length = sum(lengths) / len(lengths)
                self.patterns.append(
                    LearnedPattern(
                        pattern_id="function_length",
                        pattern_type="structure",
                        description=f"Project functions average {avg_length:.0f} lines",
                        example=f"Keep functions around {avg_length:.0f} lines",
                        frequency=len(lengths),
                        confidence=0.8,
                    )
                )

        # Indentation pattern
        if "indentation" in self.learned_data:
            indent = self.learned_data["indentation"]
            if indent:
                dominant = max(indent.items(), key=lambda x: x[1])
                total = sum(indent.values())
                confidence = dominant[1] / total

                if confidence > 0.8:
                    self.patterns.append(
                        LearnedPattern(
                            pattern_id="indentation_style",
                            pattern_type="structure",
                            description=f"Project uses {dominant[0]} for indentation",
                            example=dominant[0].replace("_", " "),
                            frequency=dominant[1],
                            confidence=confidence,
                        )
                    )

    def detect_violations(self, file_path: Path, content: str) -> list[QualityIssue]:
        """Détecte les violations des patterns appris."""
        if not self.patterns:
            self._load_learned_data()

        if not self.patterns:
            return []

        issues = []
        lines = content.split("\n")

        for pattern in self.patterns:
            if pattern.confidence < 0.7:
                continue

            if pattern.pattern_id == "naming_convention":
                violations = self._check_naming_violations(file_path, lines, pattern)
                issues.extend(violations)

            elif pattern.pattern_id == "function_length":
                violations = self._check_function_length_violations(
                    file_path, content, pattern
                )
                issues.extend(violations)

            elif pattern.pattern_id == "indentation_style":
                violations = self._check_indentation_violations(
                    file_path, lines, pattern
                )
                issues.extend(violations)

        return issues

    def _check_naming_violations(
        self, file_path: Path, lines: list[str], pattern: LearnedPattern
    ) -> list[QualityIssue]:
        """Vérifie les violations de naming convention."""
        issues = []
        expected_style = pattern.example.replace("Expected: ", "")

        for i, line in enumerate(lines, 1):
            # Vérifier variables
            if "snake_case" in expected_style and re.search(r"\b([a-z]+[A-Z])", line):
                issues.append(
                    QualityIssue(
                        category=QualityCategory.MAINTAINABILITY,
                        severity=IssueSeverity.LOW,
                        title=f"Naming convention violation (expected {expected_style})",
                        description=f"Project uses {expected_style} but found camelCase",
                        file=str(file_path),
                        line=i,
                        suggestion=f"Follow project convention: {expected_style}",
                    )
                )

        return issues[:5]  # Limiter à 5

    def _check_function_length_violations(
        self, file_path: Path, content: str, pattern: LearnedPattern
    ) -> list[QualityIssue]:
        """Vérifie la longueur des fonctions."""
        issues = []
        expected_length = float(pattern.example.split()[-2])
        threshold = expected_length * 2  # 2x la moyenne

        func_starts = [
            (m.start(), m.group(), content[: m.start()].count("\n") + 1)
            for m in re.finditer(r"def\s+(\w+)", content)
        ]

        for i, (start, func_name, line_num) in enumerate(func_starts):
            end = func_starts[i + 1][0] if i + 1 < len(func_starts) else len(content)
            func_length = content[start:end].count("\n")

            if func_length > threshold:
                issues.append(
                    QualityIssue(
                        category=QualityCategory.MAINTAINABILITY,
                        severity=IssueSeverity.MEDIUM,
                        title=f"Function longer than project average ({func_length} vs {expected_length:.0f} lines)",
                        description=f"This function is {func_length / expected_length:.1f}x the project average",
                        file=str(file_path),
                        line=line_num,
                        suggestion=f"Consider breaking down into smaller functions (project avg: {expected_length:.0f} lines)",
                    )
                )

        return issues

    def _check_indentation_violations(
        self, file_path: Path, lines: list[str], pattern: LearnedPattern
    ) -> list[QualityIssue]:
        """Vérifie le style d'indentation."""
        issues = []
        expected_style = pattern.example

        for i, line in enumerate(lines, 1):
            if line and line[0] in " \t":
                if (
                    "4 spaces" in expected_style
                    and line.startswith("  ")
                    and not line.startswith("    ")
                ):
                    issues.append(
                        QualityIssue(
                            category=QualityCategory.MAINTAINABILITY,
                            severity=IssueSeverity.LOW,
                            title="Inconsistent indentation style",
                            description=f"Project uses {expected_style}",
                            file=str(file_path),
                            line=i,
                            suggestion=f"Use {expected_style}",
                        )
                    )
                    break  # Une seule issue par fichier

        return issues

    def _save_learned_data(self) -> None:
        """Sauvegarde les données apprises."""
        data_file = self.cache_dir / "learned_patterns.json"

        data = {
            "learned_data": self.learned_data,
            "patterns": [asdict(p) for p in self.patterns],
        }

        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _load_learned_data(self) -> None:
        """Charge les données apprises."""
        data_file = self.cache_dir / "learned_patterns.json"

        if not data_file.exists():
            return

        try:
            with open(data_file, encoding="utf-8") as f:
                data = json.load(f)

            self.learned_data = data.get("learned_data", {})
            self.patterns = [LearnedPattern(**p) for p in data.get("patterns", [])]
        except Exception:
            pass

    def get_report(self) -> str:
        """Génère un rapport des patterns appris."""
        if not self.patterns:
            return "No patterns learned yet. Run learn_from_codebase() first."

        report = "## 🧠 ML-Learned Patterns\n\n"
        report += f"**Total patterns**: {len(self.patterns)}\n\n"

        for pattern in self.patterns:
            confidence_pct = pattern.confidence * 100
            report += f"### {pattern.description}\n"
            report += f"- **Type**: {pattern.pattern_type}\n"
            report += f"- **Confidence**: {confidence_pct:.0f}%\n"
            report += f"- **Frequency**: {pattern.frequency} occurrences\n"
            report += f"- **Example**: {pattern.example}\n\n"

        return report


def learn_and_detect(
    project_dir: Path,
    files_to_check: list[Path],
) -> tuple[dict[str, Any], list[QualityIssue]]:
    """
    Apprend des patterns et détecte les violations.

    Returns:
        Tuple (stats, issues)
    """
    detector = MLPatternDetector(project_dir)

    # Apprendre
    stats = detector.learn_from_codebase()

    # Détecter violations
    all_issues = []
    for file in files_to_check:
        if file.exists():
            content = file.read_text(encoding="utf-8")
            issues = detector.detect_violations(file, content)
            all_issues.extend(issues)

    return stats, all_issues
