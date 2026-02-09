#!/usr/bin/env python3
"""Test complet de la correction de quality_scorer.py"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "apps" / "backend"))

def test_imports():
    """Test que tous les imports fonctionnent"""
    try:
        from review.quality_scorer import (
            IssueSeverity,
            QualityCategory,
            QualityIssue,
            QualityScore,
            QualityScorer,
        )
        print("✅ Imports réussis")
        return True
    except Exception as e:
        print(f"❌ Erreur d'import: {e}")
        return False

def test_grades():
    """Test que les grades correspondent aux tests attendus"""
    try:
        from review.quality_scorer import QualityScorer
        from pathlib import Path
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            scorer = QualityScorer(Path(tmpdir))
            
            tests = [
                (98, "A+"),
                (95, "A"),
                (91, "A-"),
                (85, "B+"),
                (75, "C"),
                (65, "D"),
                (50, "F"),
            ]
            
            all_passed = True
            for score, expected_grade in tests:
                actual_grade = scorer._calculate_grade(score)
                status = "✅" if actual_grade == expected_grade else "❌"
                print(f"{status} _calculate_grade({score}) = {actual_grade} (expected {expected_grade})")
                if actual_grade != expected_grade:
                    all_passed = False
            
            return all_passed
    except Exception as e:
        print(f"❌ Erreur dans test_grades: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_basic_functionality():
    """Test la fonctionnalité de base du scorer"""
    try:
        from review.quality_scorer import QualityScorer
        from pathlib import Path
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            scorer = QualityScorer(Path(tmpdir))
            
            # Test avec une PR vide
            score = scorer.score_pr("", [], "")
            
            checks = [
                (score.overall_score == 100.0, f"Score vide = 100.0 (got {score.overall_score})"),
                (score.grade == "A+", f"Grade vide = A+ (got {score.grade})"),
                (score.total_issues == 0, f"Issues = 0 (got {score.total_issues})"),
                (score.is_passing, "PR vide doit passer"),
            ]
            
            all_passed = True
            for check, description in checks:
                status = "✅" if check else "❌"
                print(f"{status} {description}")
                if not check:
                    all_passed = False
            
            return all_passed
    except Exception as e:
        print(f"❌ Erreur dans test_basic_functionality: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("TEST 1: Imports")
    print("=" * 60)
    test1 = test_imports()
    
    print("\n" + "=" * 60)
    print("TEST 2: Grades")
    print("=" * 60)
    test2 = test_grades()
    
    print("\n" + "=" * 60)
    print("TEST 3: Fonctionnalité basique")
    print("=" * 60)
    test3 = test_basic_functionality()
    
    print("\n" + "=" * 60)
    if test1 and test2 and test3:
        print("✅✅✅ TOUS LES TESTS PASSED!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("❌ CERTAINS TESTS ONT ÉCHOUÉ")
        print("=" * 60)
        sys.exit(1)
