"""
Extended Quality Scorer with Multi-Language Support
====================================================

Extension du QualityScorer pour supporter Java, Kotlin, C#, Go, Rust.
"""

from __future__ import annotations

from pathlib import Path

from .quality_multilang import get_analyzer
from .quality_scorer import QualityScorer


class ExtendedQualityScorer(QualityScorer):
    """
    QualityScorer étendu avec support multi-langages.
    
    Supporte:
    - Python (hérité)
    - JavaScript/TypeScript (hérité)
    - Java
    - Kotlin
    - C#
    - Go
    - Rust
    """

    def _analyze_file(self, file_path: str) -> None:
        """Analyse un fichier (version étendue avec multi-language)."""
        path = Path(file_path)
        
        # Si le fichier n'existe pas dans le projet dir, skip
        full_path = self.project_dir / path
        if not full_path.exists():
            return
        
        try:
            content = full_path.read_text(encoding='utf-8')
        except Exception:
            # Erreur de lecture, skip
            return
        
        # Détection sécurité (tous langages)
        self._analyze_security_patterns(file_path, content)
        
        # Analyse par langage
        suffix = path.suffix.lower()
        
        # Python
        if suffix == '.py':
            self._analyze_python_file(file_path, content)
        
        # JavaScript/TypeScript
        elif suffix in ['.js', '.jsx', '.ts', '.tsx']:
            self._analyze_javascript_file(file_path, content)
        
        # Multi-language support (Java, Kotlin, C#, Go, Rust)
        else:
            analyzer = get_analyzer(path)
            if analyzer:
                multi_lang_issues = analyzer.analyze(path, content)
                self.issues.extend(multi_lang_issues)


def create_extended_scorer(project_dir: Path) -> ExtendedQualityScorer:
    """Factory pour créer un scorer étendu."""
    return ExtendedQualityScorer(project_dir)

