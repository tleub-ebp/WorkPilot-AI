"""
Test Coverage Analysis
======================

Analyse la couverture de tests (même sans runtime data).
Détecte les fonctions/classes non testées par analyse statique.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from .quality_scorer import IssueSeverity, QualityCategory, QualityIssue


class TestCoverageAnalyzer:
    """Analyseur de couverture de tests (statique)."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.test_patterns = ["test_*.py", "*_test.py", "tests/*.py", "test/*.py"]

    def analyze_coverage(
        self,
        source_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Analyse la couverture de tests de manière statique.

        Returns:
            Dict avec statistiques de couverture
        """
        # Set defaults
        if source_patterns is None:
            source_patterns = ["**/*.py"]
        if exclude_patterns is None:
            exclude_patterns = ["test*.py", "*_test.py", "setup.py"]

        # Collecter fichiers source
        source_files = []
        for pattern in source_patterns:
            for file in self.project_dir.glob(pattern):
                # Exclure les tests et patterns exclus
                if any(file.match(excl) for excl in exclude_patterns):
                    continue
                if "test" in str(file).lower() and "test" not in file.name:
                    continue
                source_files.append(file)

        # Collecter fichiers de test
        test_files = []
        for pattern in self.test_patterns:
            test_files.extend(self.project_dir.glob(pattern))

        # Extraire les fonctions/classes des sources
        source_entities = self._extract_entities(source_files)

        # Extraire les tests
        test_entities = self._extract_test_references(test_files)

        # Calculer couverture
        coverage_stats = self._calculate_coverage(source_entities, test_entities)

        return coverage_stats

    def _extract_entities(self, files: list[Path]) -> dict[str, list[dict]]:
        """Extrait les fonctions et classes des fichiers source."""
        entities = {}

        for file in files:
            try:
                content = file.read_text(encoding="utf-8")
                tree = ast.parse(content)

                file_entities = []

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # Ignorer les fonctions privées et magic methods
                        if (
                            not node.name.startswith("_")
                            or node.name.startswith("__")
                            and node.name.endswith("__")
                        ):
                            file_entities.append(
                                {
                                    "type": "function",
                                    "name": node.name,
                                    "line": node.lineno,
                                    "is_public": not node.name.startswith("_"),
                                }
                            )

                    elif isinstance(node, ast.ClassDef):
                        file_entities.append(
                            {
                                "type": "class",
                                "name": node.name,
                                "line": node.lineno,
                                "is_public": not node.name.startswith("_"),
                            }
                        )

                if file_entities:
                    entities[str(file)] = file_entities

            except Exception:
                continue

        return entities

    def _extract_test_references(self, test_files: list[Path]) -> set[str]:
        """Extrait les références testées des fichiers de test."""
        tested = set()

        for file in test_files:
            try:
                content = file.read_text(encoding="utf-8")

                # Rechercher imports
                import_pattern = r"from\s+[\w.]+\s+import\s+([\w,\s]+)"
                for match in re.finditer(import_pattern, content):
                    imports = match.group(1).split(",")
                    for imp in imports:
                        tested.add(imp.strip())

                # Rechercher noms de fonctions/classes dans les tests
                test_pattern = r"def\s+test_(\w+)"
                for match in re.finditer(test_pattern, content):
                    tested_name = match.group(1)
                    # Retirer test_ prefix
                    tested.add(tested_name)

                # Rechercher mentions dans le code de test
                for line in content.split("\n"):
                    # Ignorer commentaires et strings
                    if "#" in line:
                        line = line[: line.index("#")]

                    # Rechercher appels de fonctions
                    call_pattern = r"(\w+)\s*\("
                    for match in re.finditer(call_pattern, line):
                        func_name = match.group(1)
                        if not func_name.startswith("test_"):
                            tested.add(func_name)

            except Exception:
                continue

        return tested

    def _calculate_coverage(
        self, source_entities: dict[str, list[dict]], tested: set[str]
    ) -> dict[str, Any]:
        """Calcule les statistiques de couverture."""
        total_entities = 0
        total_public = 0
        tested_entities = 0
        untested_entities = []

        for file, entities in source_entities.items():
            for entity in entities:
                total_entities += 1

                if entity["is_public"]:
                    total_public += 1

                    # Vérifier si testé
                    if entity["name"] in tested:
                        tested_entities += 1
                    else:
                        untested_entities.append(
                            {
                                "file": file,
                                "name": entity["name"],
                                "type": entity["type"],
                                "line": entity["line"],
                            }
                        )

        coverage_pct = (tested_entities / total_public * 100) if total_public > 0 else 0

        return {
            "total_entities": total_entities,
            "total_public": total_public,
            "tested_entities": tested_entities,
            "untested_entities": untested_entities,
            "coverage_percentage": coverage_pct,
            "test_files_found": len(tested),
        }

    def generate_issues(self, coverage_stats: dict[str, Any]) -> list[QualityIssue]:
        """Génère des QualityIssue pour les entités non testées."""
        issues = []

        untested = coverage_stats.get("untested_entities", [])

        # Limiter le nombre d'issues pour ne pas surcharger
        for entity in untested[:20]:
            severity = (
                IssueSeverity.HIGH
                if entity["type"] == "class"
                else IssueSeverity.MEDIUM
            )

            issues.append(
                QualityIssue(
                    category=QualityCategory.MAINTAINABILITY,
                    severity=severity,
                    title=f"Untested {entity['type']}: {entity['name']}",
                    description=f"This {entity['type']} appears to have no test coverage",
                    file=entity["file"],
                    line=entity["line"],
                    suggestion=f"Add tests for {entity['name']} in test_{Path(entity['file']).stem}.py",
                )
            )

        return issues

    def generate_report(self, coverage_stats: dict[str, Any]) -> str:
        """Génère un rapport de couverture."""
        coverage_pct = coverage_stats["coverage_percentage"]

        if coverage_pct >= 80:
            status = "✅ EXCELLENT"
            color = "green"
        elif coverage_pct >= 60:
            status = "👍 GOOD"
            color = "yellow"
        elif coverage_pct >= 40:
            status = "⚠️ FAIR"
            color = "orange"
        else:
            status = "❌ POOR"
            color = "red"

        report = f"""## 🧪 Test Coverage Analysis

**Status**: {status}
**Coverage**: {coverage_pct:.1f}%

### Statistics
- **Total public entities**: {coverage_stats["total_public"]}
- **Tested entities**: {coverage_stats["tested_entities"]}
- **Untested entities**: {len(coverage_stats["untested_entities"])}
- **Test files found**: {coverage_stats["test_files_found"]}

"""

        if coverage_stats["untested_entities"]:
            report += "### ⚠️ Untested Entities\n\n"

            # Grouper par fichier
            by_file = {}
            for entity in coverage_stats["untested_entities"][:10]:
                file = entity["file"]
                if file not in by_file:
                    by_file[file] = []
                by_file[file].append(entity)

            for file, entities in list(by_file.items())[:5]:
                report += f"**`{Path(file).name}`**:\n"
                for entity in entities[:5]:
                    report += f"- {entity['type']}: `{entity['name']}` (line {entity['line']})\n"
                report += "\n"

            if len(coverage_stats["untested_entities"]) > 10:
                report += f"*... and {len(coverage_stats['untested_entities']) - 10} more untested entities*\n\n"
        else:
            report += "### 🎉 All Public Functions/Classes Have Tests!\n\n"

        report += (
            "\n---\n*Note: Static analysis - may not reflect actual runtime coverage*\n"
        )

        return report


def analyze_project_coverage(
    project_dir: Path,
) -> tuple[dict[str, Any], list[QualityIssue]]:
    """
    Analyse la couverture de tests d'un projet.

    Returns:
        Tuple (stats, issues)
    """
    analyzer = TestCoverageAnalyzer(project_dir)
    stats = analyzer.analyze_coverage()
    issues = analyzer.generate_issues(stats)

    return stats, issues
