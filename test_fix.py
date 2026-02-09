#!/usr/bin/env python3
"""Test que la correction de quality_scorer.py fonctionne"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "apps" / "backend"))

try:
    # Test d'import
    from review.quality_scorer import (
        IssueSeverity,
        QualityCategory,
        QualityIssue,
        QualityScore,
        QualityScorer,
    )
    print("✅ Import réussi!")
    print(f"   - QualityCategory: {QualityCategory}")
    print(f"   - IssueSeverity: {IssueSeverity}")
    print(f"   - QualityIssue: {QualityIssue}")
    print(f"   - QualityScore: {QualityScore}")
    print(f"   - QualityScorer: {QualityScorer}")
    
    # Test d'instanciation
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        scorer = QualityScorer(Path(tmpdir))
        score = scorer.score_pr("", [], "")
        print(f"\n✅ Instanciation et exécution réussies!")
        print(f"   - Score: {score.overall_score}")
        print(f"   - Grade: {score.grade}")
        print(f"   - Is passing: {score.is_passing}")
    
    print("\n✅✅✅ SUCCÈS! Le fichier quality_scorer.py fonctionne correctement!")
    
except SyntaxError as e:
    print(f"❌ ERREUR DE SYNTAXE: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ ERREUR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
