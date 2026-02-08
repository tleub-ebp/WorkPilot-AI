#!/usr/bin/env python
"""
Test End-to-End du Quality Scorer
==================================

Valide que tout fonctionne correctement.
"""

import sys
from pathlib import Path

# Ajouter le backend au path
sys.path.insert(0, str(Path(__file__).parent / "apps" / "backend"))

print("=" * 70)
print("🧪 TEST END-TO-END - AI CODE REVIEW QUALITY SCORER")
print("=" * 70)
print()

# Test 1: Import du module
print("[1/5] Test des imports...")
try:
    from review.quality_scorer import (
        QualityScorer,
        QualityScore,
        QualityIssue,
        QualityCategory,
        IssueSeverity,
    )
    print("✅ Imports OK")
except Exception as e:
    print(f"❌ Erreur: {e}")
    sys.exit(1)

# Test 2: Création du scorer
print("\n[2/5] Création du scorer...")
try:
    project_dir = Path(".")
    scorer = QualityScorer(project_dir)
    print(f"✅ Scorer créé: {project_dir.absolute()}")
except Exception as e:
    print(f"❌ Erreur: {e}")
    sys.exit(1)

# Test 3: Scoring d'une PR vide (devrait donner 100/100)
print("\n[3/5] Test: PR vide (score attendu: 100/100)...")
try:
    score = scorer.score_pr("", [], "")
    assert score.overall_score == 100.0, f"Score incorrect: {score.overall_score}"
    assert score.grade == "A+", f"Grade incorrect: {score.grade}"
    assert score.total_issues == 0, f"Issues détectées: {score.total_issues}"
    assert score.is_passing, "PR devrait passer"
    print(f"✅ Score: {score.overall_score}/100, Grade: {score.grade}")
except AssertionError as e:
    print(f"❌ Assertion failed: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Erreur: {e}")
    sys.exit(1)

# Test 4: Analyse du fichier example_bad_code.py
print("\n[4/5] Test: Analyse de example_bad_code.py...")
try:
    example_file = Path("example_bad_code.py")
    if not example_file.exists():
        print("⚠️  Fichier example_bad_code.py introuvable, skip")
    else:
        score = scorer.score_pr("", ["example_bad_code.py"], "")
        print(f"   Score: {score.overall_score}/100")
        print(f"   Grade: {score.grade}")
        print(f"   Issues: {score.total_issues}")
        print(f"   Critical: {score.critical_issues}")
        
        # Vérifications
        assert score.critical_issues > 0, "Devrait détecter des issues critiques"
        assert score.total_issues >= 3, f"Devrait détecter au moins 3 issues, trouvé {score.total_issues}"
        assert not score.is_passing, "PR ne devrait pas passer"
        
        print("✅ Détections fonctionnent correctement")
        
        # Afficher quelques issues
        print("\n   Exemples d'issues détectées:")
        for issue in score.issues[:3]:
            print(f"   - [{issue.severity.value}] {issue.title}")
except AssertionError as e:
    print(f"❌ Assertion failed: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Analyse du quality_scorer lui-même
print("\n[5/5] Test: Analyse de quality_scorer.py...")
try:
    scorer_file = "apps/backend/review/quality_scorer.py"
    score = scorer.score_pr("", [scorer_file], "")
    print(f"   Score: {score.overall_score}/100")
    print(f"   Grade: {score.grade}")
    print(f"   Issues: {score.total_issues}")
    print("✅ Auto-analyse fonctionnelle")
except Exception as e:
    print(f"❌ Erreur: {e}")
    sys.exit(1)

# Résumé
print("\n" + "=" * 70)
print("🎉 TOUS LES TESTS PASSENT !")
print("=" * 70)
print()
print("Le Quality Scorer est fonctionnel et prêt à l'emploi !")
print()
print("Prochaines étapes:")
print("  1. Testez avec vos propres fichiers:")
print("     python quality_cli.py score --files votre_fichier.py")
print()
print("  2. Export JSON:")
print("     python quality_cli.py score --files file.py --format json")
print()
print("  3. Lancez les tests unitaires:")
print("     pytest tests/test_quality_scorer.py -v")
print()

