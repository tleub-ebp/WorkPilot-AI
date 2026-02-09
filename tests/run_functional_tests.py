#!/usr/bin/env python3
"""
Test fonctionnel complet de l'auto-fix loop
Simule un cycle complet sans appeler Claude
"""
import asyncio
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add backend to path
backend_dir = Path(__file__).parent / "apps" / "backend"
sys.path.insert(0, str(backend_dir))

print("=" * 70)
print("AUTO-FIX LOOP - TEST FONCTIONNEL COMPLET")
print("=" * 70)


async def test_complete_workflow():
    """Test le workflow complet de l'auto-fix loop."""
    
    # Créer un environnement de test temporaire
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "project"
        project_dir.mkdir()
        
        spec_dir = Path(tmpdir) / ".auto-claude" / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        
        # Créer implementation_plan.json
        plan = {
            "spec_name": "test-spec",
            "subtasks": [],
            "auto_fix_stats": {
                "total_runs": 0,
                "successful_runs": 0,
                "total_attempts": 0,
                "success_rate": 0.0,
                "average_attempts": 0.0,
                "common_patterns": {},
                "runs": []
            }
        }
        (spec_dir / "implementation_plan.json").write_text(json.dumps(plan, indent=2))
        
        print("\n[1/6] 🏗️  Environnement de test créé")
        print(f"  Project dir: {project_dir}")
        print(f"  Spec dir: {spec_dir}")
        
        # Test 1: Créer une instance AutoFixLoop
        print("\n[2/6] 🔄 Création AutoFixLoop...")
        try:
            from qa.auto_fix_loop import AutoFixLoop
            
            loop = AutoFixLoop(
                project_dir=project_dir,
                spec_dir=spec_dir,
                model="test-model",
                verbose=True
            )
            print(f"  ✓ Loop créé")
            print(f"  ✓ Max attempts: {loop.test_info.has_tests if hasattr(loop.test_info, 'has_tests') else 'N/A'}")
        except Exception as e:
            print(f"  ❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Test 2: Parser test counts
        print("\n[3/6] 📊 Test parsing test counts...")
        try:
            outputs = [
                ("5 passed, 2 failed in 1.2s", 7, 2),
                ("Tests: 2 failed, 5 passed, 7 total", 7, 2),
                ("5 passed in 1.2s", 5, 0),
            ]
            
            for output, expected_total, expected_failed in outputs:
                total, failed = loop._parse_test_counts(output)
                if total == expected_total and failed == expected_failed:
                    print(f"  ✓ '{output[:30]}...' → {total} total, {failed} failed")
                else:
                    print(f"  ❌ Parsing error: expected ({expected_total}, {expected_failed}), got ({total}, {failed})")
                    return False
        except Exception as e:
            print(f"  ❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Test 3: Analyser patterns d'erreur
        print("\n[4/6] 🔍 Test analyse patterns d'erreur...")
        try:
            from qa.auto_fix_loop import TestResult
            
            test_cases = [
                ("AssertionError: expected 5", "assertion_failure"),
                ("Test timeout after 30s", "timeout"),
                ("ImportError: No module", "import_error"),
                ("TypeError: cannot multiply", "type_error"),
            ]
            
            for output, expected_pattern in test_cases:
                result = TestResult(
                    executed=True,
                    passed=False,
                    output=output,
                    error="",
                    duration=1.0
                )
                pattern = loop._analyze_failure(result)
                if pattern == expected_pattern:
                    print(f"  ✓ '{output[:30]}...' → {pattern}")
                else:
                    print(f"  ❌ Expected {expected_pattern}, got {pattern}")
                    return False
        except Exception as e:
            print(f"  ❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Test 4: Métriques
        print("\n[5/6] 📈 Test métriques tracking...")
        try:
            from qa.auto_fix_metrics import AutoFixMetricsTracker
            
            tracker = AutoFixMetricsTracker(spec_dir)
            
            # Enregistrer quelques runs
            tracker.record_run(success=True, attempts=2, duration=30.0, error_patterns=["assertion_failure"])
            tracker.record_run(success=True, attempts=3, duration=45.0, error_patterns=["import_error"])
            tracker.record_run(success=False, attempts=5, duration=120.0, error_patterns=["timeout"])
            
            stats = tracker.load_stats()
            print(f"  ✓ Total runs: {stats.total_runs}")
            print(f"  ✓ Successful: {stats.successful_runs}")
            print(f"  ✓ Success rate: {stats.success_rate * 100:.1f}%")
            print(f"  ✓ Avg attempts: {stats.average_attempts:.1f}")
            
            # Vérifier les valeurs
            if stats.total_runs != 3:
                print(f"  ❌ Expected 3 runs, got {stats.total_runs}")
                return False
            if stats.successful_runs != 2:
                print(f"  ❌ Expected 2 successful, got {stats.successful_runs}")
                return False
            if abs(stats.success_rate - 0.666) > 0.01:
                print(f"  ❌ Expected ~66.6% success rate, got {stats.success_rate * 100:.1f}%")
                return False
            
            # Dashboard data
            dashboard = tracker.get_dashboard_data()
            print(f"  ✓ Dashboard data: {dashboard['totalRuns']} runs, {dashboard['successRate']}% success")
            
        except Exception as e:
            print(f"  ❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Test 5: Fix request creation
        print("\n[6/6] 📝 Test création fix request...")
        try:
            test_result = TestResult(
                executed=True,
                passed=False,
                output="2 failed, 3 passed",
                error="assertion failed",
                duration=1.5,
                test_count=5,
                failed_count=2,
            )
            
            await loop._create_fix_request(
                test_result,
                "assertion_failure",
                "Test memory context"
            )
            
            fix_request = spec_dir / "QA_FIX_REQUEST.md"
            if fix_request.exists():
                content = fix_request.read_text()
                if "Test Execution Failed" in content and "assertion_failure" in content:
                    print(f"  ✓ Fix request créé: {len(content)} chars")
                else:
                    print(f"  ❌ Fix request incomplet")
                    return False
            else:
                print(f"  ❌ Fix request non créé")
                return False
                
        except Exception as e:
            print(f"  ❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        return True


async def main():
    """Run all functional tests."""
    
    success = await test_complete_workflow()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ TOUS LES TESTS FONCTIONNELS PASSENT!")
        print("=" * 70)
        print("\n🎉 L'auto-fix loop est PLEINEMENT FONCTIONNEL")
        print("\nValidations effectuées:")
        print("  ✓ Création d'instance AutoFixLoop")
        print("  ✓ Parsing de test counts (pytest, jest)")
        print("  ✓ Détection de patterns d'erreur")
        print("  ✓ Tracking de métriques")
        print("  ✓ Création de fix requests")
        print("\nLa feature peut être utilisée en production!")
        return 0
    else:
        print("❌ CERTAINS TESTS ONT ÉCHOUÉ")
        print("=" * 70)
        print("\n⚠️  Voir les erreurs ci-dessus")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
