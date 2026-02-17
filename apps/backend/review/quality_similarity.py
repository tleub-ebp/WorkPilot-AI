"""
Code Similarity Detection
=========================

Détecte les duplications et similarités de code (code clones).
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .quality_scorer import IssueSeverity, QualityCategory, QualityIssue


@dataclass
class CodeClone:
    """Représente un clone de code détecté."""
    
    file1: str
    file2: str
    line1_start: int
    line1_end: int
    line2_start: int
    line2_end: int
    similarity: float  # 0.0 à 1.0
    lines_count: int
    code_snippet: str


class CodeSimilarityDetector:
    """Détecteur de duplication et similarité de code."""

    def __init__(self, min_lines: int = 6, min_similarity: float = 0.85):
        """
        Initialize detector.
        
        Args:
            min_lines: Nombre minimum de lignes pour considérer un clone
            min_similarity: Similarité minimale (0.0-1.0)
        """
        self.min_lines = min_lines
        self.min_similarity = min_similarity
        self.clones: list[CodeClone] = []

    def detect_clones(self, files: list[Path]) -> list[CodeClone]:
        """
        Détecte les clones dans une liste de fichiers.
        
        Returns:
            Liste de clones détectés
        """
        clones = []
        
        # Comparer chaque paire de fichiers
        for i, file1 in enumerate(files):
            for file2 in files[i+1:]:
                file_clones = self._compare_files(file1, file2)
                clones.extend(file_clones)
        
        # Détecter les clones dans le même fichier
        for file in files:
            self_clones = self._detect_self_clones(file)
            clones.extend(self_clones)
        
        self.clones = clones
        return clones

    def _compare_files(self, file1: Path, file2: Path) -> list[CodeClone]:
        """Compare deux fichiers et détecte les clones."""
        if not file1.exists() or not file2.exists():
            return []
        
        try:
            content1 = file1.read_text(encoding='utf-8')
            content2 = file2.read_text(encoding='utf-8')
        except Exception:
            return []
        
        lines1 = self._normalize_lines(content1.split('\n'))
        lines2 = self._normalize_lines(content2.split('\n'))
        
        return self._find_clones(str(file1), str(file2), lines1, lines2)

    def _detect_self_clones(self, file: Path) -> list[CodeClone]:
        """Détecte les clones dans le même fichier."""
        if not file.exists():
            return []
        
        try:
            content = file.read_text(encoding='utf-8')
        except Exception:
            return []
        
        lines = self._normalize_lines(content.split('\n'))
        return self._find_clones(str(file), str(file), lines, lines, same_file=True)

    def _normalize_lines(self, lines: list[str]) -> list[str]:
        """Normalise les lignes pour comparaison."""
        normalized = []
        for line in lines:
            # Retirer les espaces, commentaires simples
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and not stripped.startswith('//'):
                normalized.append(stripped)
            else:
                normalized.append('')  # Ligne vide pour garder les numéros de ligne
        return normalized

    def _find_clones(
        self,
        file1: str,
        file2: str,
        lines1: list[str],
        lines2: list[str],
        same_file: bool = False
    ) -> list[CodeClone]:
        """Trouve les clones entre deux listes de lignes."""
        clones = []
        
        # Utiliser SequenceMatcher pour trouver les blocs similaires
        matcher = difflib.SequenceMatcher(None, lines1, lines2)
        
        for match in matcher.get_matching_blocks():
            i, j, size = match
            
            # Ignorer les petits blocs
            if size < self.min_lines:
                continue
            
            # Si même fichier, ignorer les matchs identiques
            if same_file and i == j:
                continue
            
            # Calculer la similarité exacte pour ce bloc
            block1 = lines1[i:i+size]
            block2 = lines2[j:j+size]
            
            # Filtrer les lignes vides
            block1_clean = [line for line in block1 if line]
            block2_clean = [line for line in block2 if line]
            
            if not block1_clean or not block2_clean:
                continue
            
            # Calculer similarité
            similarity = difflib.SequenceMatcher(None, block1_clean, block2_clean).ratio()
            
            if similarity >= self.min_similarity:
                snippet = '\n'.join(block1_clean[:5])  # Premier 5 lignes
                if len(block1_clean) > 5:
                    snippet += '\n...'
                
                clones.append(CodeClone(
                    file1=file1,
                    file2=file2,
                    line1_start=i + 1,
                    line1_end=i + size,
                    line2_start=j + 1,
                    line2_end=j + size,
                    similarity=similarity,
                    lines_count=len(block1_clean),
                    code_snippet=snippet,
                ))
        
        return clones

    def generate_issues(self, clones: list[CodeClone]) -> list[QualityIssue]:
        """Génère des QualityIssue à partir des clones détectés."""
        issues = []
        
        for clone in clones:
            # Sévérité selon la taille
            if clone.lines_count >= 30:
                severity = IssueSeverity.HIGH
            elif clone.lines_count >= 15:
                severity = IssueSeverity.MEDIUM
            else:
                severity = IssueSeverity.LOW
            
            same_file = clone.file1 == clone.file2
            
            if same_file:
                title = f"Code duplication detected ({clone.lines_count} lines, {clone.similarity*100:.0f}% similar)"
                description = f"Duplicated code found in same file at lines {clone.line1_start}-{clone.line1_end} and {clone.line2_start}-{clone.line2_end}"
            else:
                title = f"Code clone detected ({clone.lines_count} lines, {clone.similarity*100:.0f}% similar)"
                description = f"Similar code found in {clone.file2} at lines {clone.line2_start}-{clone.line2_end}"
            
            issues.append(QualityIssue(
                category=QualityCategory.MAINTAINABILITY,
                severity=severity,
                title=title,
                description=description,
                file=clone.file1,
                line=clone.line1_start,
                suggestion="Extract common code into a reusable function/method to follow DRY principle",
            ))
        
        return issues

    def generate_report(self, clones: list[CodeClone]) -> str:
        """Génère un rapport Markdown des clones."""
        if not clones:
            return "## 🎉 No Code Clones Detected\n\nGreat job keeping your code DRY!"
        
        report = "## 🔍 Code Clone Detection Report\n\n"
        report += f"**Total clones found**: {len(clones)}\n\n"
        
        # Grouper par taille
        large = [c for c in clones if c.lines_count >= 30]
        medium = [c for c in clones if 15 <= c.lines_count < 30]
        small = [c for c in clones if c.lines_count < 15]
        
        if large:
            report += f"### 🚨 Large Clones ({len(large)})\n\n"
            for clone in large[:5]:
                report += self._format_clone(clone)
        
        if medium:
            report += f"### ⚠️ Medium Clones ({len(medium)})\n\n"
            for clone in medium[:5]:
                report += self._format_clone(clone)
        
        if small:
            report += f"### ℹ️ Small Clones ({len(small)})\n\n"
            report += f"*{len(small)} small clones detected (< 15 lines)*\n\n"
        
        report += "\n---\n*💡 Consider refactoring duplicated code into reusable functions*\n"
        
        return report

    def _format_clone(self, clone: CodeClone) -> str:
        """Formate un clone pour le rapport."""
        same_file = clone.file1 == clone.file2
        
        if same_file:
            location = f"`{clone.file1}` lines {clone.line1_start}-{clone.line1_end} and {clone.line2_start}-{clone.line2_end}"
        else:
            location = f"`{clone.file1}:{clone.line1_start}-{clone.line1_end}` and `{clone.file2}:{clone.line2_start}-{clone.line2_end}`"
        
        return f"""
**Clone**: {clone.lines_count} lines ({clone.similarity*100:.0f}% similar)
- **Location**: {location}
- **Preview**:
```
{clone.code_snippet}
```

"""


def detect_clones_in_project(
    project_dir: Path,
    file_patterns: Optional[list[str]] = None,
    min_lines: int = 6,
    min_similarity: float = 0.85,
) -> tuple[list[CodeClone], list[QualityIssue]]:
    """
    Détecte les clones de code dans un projet.
    
    Args:
        project_dir: Répertoire du projet
        file_patterns: Patterns de fichiers à analyser
        min_lines: Minimum de lignes pour un clone
        min_similarity: Similarité minimale
        
    Returns:
        Tuple (clones, issues)
    """
    if file_patterns is None:
        file_patterns = ['**/*.py', '**/*.js', '**/*.ts', '**/*.java']
    
    # Collecter les fichiers
    files = []
    for pattern in file_patterns:
        files.extend(project_dir.glob(pattern))
    
    # Détecter les clones
    detector = CodeSimilarityDetector(min_lines, min_similarity)
    clones = detector.detect_clones(files)
    issues = detector.generate_issues(clones)
    
    return clones, issues
