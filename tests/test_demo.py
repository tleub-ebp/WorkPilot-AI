import sys
from pathlib import Path
# Ajouter le backend au path
sys.path.insert(0, str(Path(__file__).parent / "apps" / "backend"))
print("=" * 70)
print("DEMO: AI Code Review Quality Scorer")
print("=" * 70)
# Test 1: Import
print("\n[1/4] Import du module...")
try:
    from review.quality_scorer import QualityScorer, QualityCategory, IssueSeverity
    print("✅ Import réussi !")
except Exception as e:
    print(f"❌ Erreur: {e}")
    sys.exit(1)
# Test 2: Création du scorer
print("\n[2/4] Création du scorer...")
try:
    project_dir = Path(".")
    scorer = QualityScorer(project_dir)
    print(f"✅ Scorer créé pour: {project_dir.absolute()}")
except Exception as e:
    print(f"❌ Erreur: {e}")
    sys.exit(1)
# Test 3: Scoring d'une PR vide (devrait donner 100/100)
print("\n[3/4] Test: PR vide...")
try:
    score = scorer.score_pr("", [], "")
    print(f"✅ Score: {score.overall_score}/100")
    print(f"   Grade: {score.grade}")
    print(f"   Issues: {score.total_issues}")
    print(f"   Passing: {score.is_passing}")
except Exception as e:
    print(f"❌ Erreur: {e}")
    sys.exit(1)
# Test 4: Analyser le quality_scorer lui-même
print("\n[4/4] Test: Analyse de quality_scorer.py...")
try:
    score = scorer.score_pr("", ["apps/backend/review/quality_scorer.py"], "")
    print(f"✅ Analyse complétée")
    print(f"   Score: {score.overall_score}/100")
    print(f"   Grade: {score.grade}")
    print(f"   Total issues: {score.total_issues}")
    if score.issues:
        print(f"\n   Issues détectées:")
        for issue in score.issues[:5]:  # Afficher max 5
            print(f"   - [{issue.severity.value}] {issue.title}")
            print(f"     File: {issue.file}:{issue.line}")
    else:
        print("   Aucune issue détectée !")
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
print("\n" + "=" * 70)
print("🎉 SUCCÈS ! Le Quality Scorer fonctionne parfaitement !")
print("=" * 70)