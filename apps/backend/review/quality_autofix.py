"""
Auto-Fix Engine
===============

Engine pour appliquer automatiquement des fixes aux problèmes détectés.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.connectors.base import GrepaiConnector

from .quality_scorer import QualityIssue


class AutoFix:
    """Représente un fix automatique."""

    def __init__(
        self,
        issue: QualityIssue,
        original_line: str,
        fixed_line: str,
        confidence: float = 1.0,
    ):
        self.issue = issue
        self.original_line = original_line
        self.fixed_line = fixed_line
        self.confidence = confidence  # 0.0 à 1.0


class AutoFixEngine:
    """Engine pour générer et appliquer des fixes automatiques."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.fixes: list[AutoFix] = []

    def generate_fixes(self, issues: list[QualityIssue]) -> list[AutoFix]:
        """Génère des fixes automatiques pour les issues."""
        fixes = []

        for issue in issues:
            if issue.line is None:
                continue

            # Essayer de générer un fix selon le type d'issue
            fix = self._generate_fix_for_issue(issue)
            if fix:
                fixes.append(fix)

        # Injection Grepai : suggestions de fixes
        grepai = GrepaiConnector()
        for issue in issues:
            if issue.line is None:
                continue
            grepai_result = grepai.search_code(
                f"issue:{issue.description} file:{issue.file} line:{issue.line}"
            )
            if grepai_result and "error" not in grepai_result:
                self._process_grepai_fix_suggestion(issue, grepai_result)

        self.fixes = fixes
        return fixes

    def _process_grepai_fix_suggestion(self, issue: QualityIssue, result: dict) -> None:
        """Traite les suggestions de fixes Grepai pour enrichir les auto-fixes."""
        print(f"[Grepai] Suggestion de fix pour {issue.file}:{issue.line} : {result}")

    def _generate_fix_for_issue(self, issue: QualityIssue) -> AutoFix | None:
        """Génère un fix pour une issue spécifique."""
        file_path = self.project_dir / issue.file
        if not file_path.exists():
            return None

        try:
            lines = file_path.read_text(encoding="utf-8").split("\n")
            if issue.line < 1 or issue.line > len(lines):
                return None

            original_line = lines[issue.line - 1]

            # Python: bare except -> except Exception
            if "bare except" in issue.title.lower() and issue.file.endswith(".py"):
                fixed_line = re.sub(r"except\s*:", "except Exception:", original_line)
                if fixed_line != original_line:
                    return AutoFix(issue, original_line, fixed_line, confidence=0.9)

            # Python/JS: console.log -> logger
            if "console.log" in original_line:
                fixed_line = original_line.replace("console.log", "// console.log")
                return AutoFix(issue, original_line, fixed_line, confidence=0.8)

            # Java: System.out.println -> logger
            if "System.out.println" in original_line:
                fixed_line = original_line.replace(
                    "System.out.println", "// System.out.println"
                )
                return AutoFix(issue, original_line, fixed_line, confidence=0.8)

            # Go: fmt.Println -> logger
            if "fmt.Println" in original_line:
                fixed_line = original_line.replace("fmt.Println", "// fmt.Println")
                return AutoFix(issue, original_line, fixed_line, confidence=0.8)

            # Rust: println! -> logger
            if "println!" in original_line:
                fixed_line = original_line.replace("println!", "// println!")
                return AutoFix(issue, original_line, fixed_line, confidence=0.8)

            # Kotlin: !! -> ?. (plus complexe, confidence plus basse)
            if "!!" in original_line and issue.file.endswith(".kt"):
                # Remplacer !! par ?. avec let
                fixed_line = original_line.replace("!!", "?.")
                return AutoFix(issue, original_line, fixed_line, confidence=0.5)

            # Rust: unwrap() -> ? (nécessite contexte fonction)
            if ".unwrap()" in original_line and issue.file.endswith(".rs"):
                fixed_line = original_line.replace(".unwrap()", "?")
                return AutoFix(issue, original_line, fixed_line, confidence=0.6)

        except Exception:
            return None

        return None

    def apply_fixes(
        self,
        fixes: list[AutoFix] | None = None,
        min_confidence: float = 0.8,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """
        Applique les fixes automatiques.

        Args:
            fixes: Liste des fixes à appliquer (None = tous)
            min_confidence: Confidence minimum pour appliquer (0.0-1.0)
            dry_run: Si True, ne modifie pas les fichiers

        Returns:
            Dict avec statistiques
        """
        if fixes is None:
            fixes = self.fixes

        # Filtrer par confidence
        applicable_fixes = [f for f in fixes if f.confidence >= min_confidence]

        # Grouper par fichier
        fixes_by_file: dict[str, list[AutoFix]] = {}
        for fix in applicable_fixes:
            file = fix.issue.file
            if file not in fixes_by_file:
                fixes_by_file[file] = []
            fixes_by_file[file].append(fix)

        applied_count = 0
        skipped_count = 0
        error_count = 0

        # Appliquer les fixes par fichier
        for file, file_fixes in fixes_by_file.items():
            file_path = self.project_dir / file

            if not file_path.exists():
                skipped_count += len(file_fixes)
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
                lines = content.split("\n")

                # Appliquer les fixes (en ordre inverse pour ne pas décaler les numéros de ligne)
                for fix in sorted(
                    file_fixes, key=lambda f: f.issue.line or 0, reverse=True
                ):
                    if fix.issue.line and 1 <= fix.issue.line <= len(lines):
                        line_idx = fix.issue.line - 1
                        if lines[line_idx].strip() == fix.original_line.strip():
                            lines[line_idx] = fix.fixed_line
                            applied_count += 1
                        else:
                            skipped_count += 1
                    else:
                        skipped_count += 1

                # Sauvegarder si pas dry run
                if not dry_run:
                    file_path.write_text("\n".join(lines), encoding="utf-8")

            except Exception:
                error_count += len(file_fixes)

        return {
            "total_fixes": len(applicable_fixes),
            "applied": applied_count,
            "skipped": skipped_count,
            "errors": error_count,
            "files_modified": len(fixes_by_file) if not dry_run else 0,
            "dry_run": dry_run,
        }

    def get_fixable_issues(self, issues: list[QualityIssue]) -> list[QualityIssue]:
        """Retourne les issues qui peuvent être fixées automatiquement."""
        fixable = []
        for issue in issues:
            fix = self._generate_fix_for_issue(issue)
            if fix and fix.confidence >= 0.7:
                fixable.append(issue)
        return fixable

    def preview_fixes(self, issues: list[QualityIssue]) -> str:
        """Génère un aperçu des fixes qui seraient appliqués."""
        fixes = self.generate_fixes(issues)

        if not fixes:
            return "No automatic fixes available."

        preview = "# Auto-Fix Preview\n\n"
        preview += f"**{len(fixes)} fixes** can be applied automatically:\n\n"

        for i, fix in enumerate(fixes, 1):
            preview += f"## Fix {i}: {fix.issue.title}\n"
            preview += f"- **File**: `{fix.issue.file}:{fix.issue.line}`\n"
            preview += f"- **Confidence**: {fix.confidence * 100:.0f}%\n"
            preview += f"- **Before**:\n```\n{fix.original_line}\n```\n"
            preview += f"- **After**:\n```\n{fix.fixed_line}\n```\n\n"

        return preview
