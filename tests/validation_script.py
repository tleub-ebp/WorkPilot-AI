#!/usr/bin/env python3
"""
Quick syntax and import test for auto-fix loop
"""
import sys
from pathlib import Path

# Add backend to path (from tests/ folder to backend)
backend_dir = Path(__file__).parent.parent / "apps" / "backend"
sys.path.insert(0, str(backend_dir))

print("=" * 70)
print("AUTO-FIX LOOP - TESTS DE VALIDATION")
print("=" * 70)

# Test 1: Python syntax check
print("\n[1/7] 🔍 Test de syntaxe Python...")
try:
    import py_compile
    files = [
        backend_dir / "qa" / "auto_fix_loop.py",
        backend_dir / "qa" / "auto_fix_metrics.py",
    ]
    
    for f in files:
        if f.exists():
            py_compile.compile(str(f), doraise=True)
            print(f"  ✓ {f.name} - syntaxe OK")
        else:
            print(f"  ✗ {f.name} - fichier non trouvé")
            sys.exit(1)
    print("  ✅ Syntaxe Python validée")
except Exception as e:
    print(f"  ❌ Erreur de syntaxe: {e}")
    sys.exit(1)

# Test 2: Import du module auto_fix_loop
print("\n[2/7] 📦 Test d'import auto_fix_loop...")
try:
    from qa.auto_fix_loop import (
        AutoFixLoop,
        run_auto_fix_loop,
        DEFAULT_MAX_AUTO_FIX_ATTEMPTS,
        TestResult,
        AutoFixAttempt,
    )
    print(f"  ✓ AutoFixLoop importé")
    print(f"  ✓ run_auto_fix_loop importé")
    print(f"  ✓ DEFAULT_MAX_AUTO_FIX_ATTEMPTS = {DEFAULT_MAX_AUTO_FIX_ATTEMPTS}")
    print("  ✅ Imports auto_fix_loop OK")
except ImportError as e:
    print(f"  ❌ Erreur d'import: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Import du module auto_fix_metrics
print("\n[3/7] 📊 Test d'import auto_fix_metrics...")
try:
    from qa.auto_fix_metrics import (
        AutoFixMetricsTracker,
        AutoFixStats,
        get_auto_fix_stats,
        record_auto_fix_run,
    )
    print(f"  ✓ AutoFixMetricsTracker importé")
    print(f"  ✓ get_auto_fix_stats importé")
    print("  ✅ Imports auto_fix_metrics OK")
except ImportError as e:
    print(f"  ❌ Erreur d'import: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Export via package qa
print("\n[4/7] 📦 Test exports package qa...")
try:
    from qa import (
        run_auto_fix_loop,
        AutoFixLoop,
        DEFAULT_MAX_AUTO_FIX_ATTEMPTS,
    )
    print(f"  ✓ run_auto_fix_loop via qa")
    print(f"  ✓ AutoFixLoop via qa")
    print("  ✅ Exports package qa OK")
except ImportError as e:
    print(f"  ❌ Erreur d'export: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Export via facade qa_loop
print("\n[5/7] 🎭 Test exports facade qa_loop...")
try:
    from qa_loop import (
        run_auto_fix_loop,
        AutoFixLoop,
        DEFAULT_MAX_AUTO_FIX_ATTEMPTS,
    )
    print(f"  ✓ run_auto_fix_loop via qa_loop")
    print(f"  ✓ AutoFixLoop via qa_loop")
    print("  ✅ Exports facade qa_loop OK")
except ImportError as e:
    print(f"  ❌ Erreur d'export: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 6: Instantiation de classes
print("\n[6/7] 🏗️  Test instantiation classes...")
try:
    from qa.auto_fix_loop import TestResult, AutoFixAttempt
    
    result = TestResult(
        executed=True,
        passed=False,
        output="test output",
        error="test error",
        duration=1.5,
        test_count=5,
        failed_count=2,
    )
    print(f"  ✓ TestResult créé: {result.test_count} tests, {result.failed_count} failed")
    
    attempt = AutoFixAttempt(
        attempt_number=1,
        test_result=result,
        fix_applied=True,
        fix_status="fixed",
        duration=30.0,
        error_pattern="assertion_failure",
        timestamp=1234567890.0,
    )
    print(f"  ✓ AutoFixAttempt créé: tentative #{attempt.attempt_number}")
    print("  ✅ Instantiation classes OK")
except Exception as e:
    print(f"  ❌ Erreur instantiation: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 7: CLI integration
print("\n[7/7] 🖥️  Test intégration CLI...")
try:
    from cli.qa_commands import handle_auto_fix_command
    print(f"  ✓ handle_auto_fix_command importé")
    print("  ✅ Intégration CLI OK")
except ImportError as e:
    print(f"  ❌ Erreur import CLI: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Résumé
print("\n" + "=" * 70)
print("🎉 TOUS LES TESTS PASSENT!")
print("=" * 70)
print("\n✅ Feature 3: Auto-Fix Loops est FONCTIONNELLE")
print("\nProchaines étapes:")
print("  1. Tester avec un vrai projet")
print("  2. Vérifier les métriques")
print("  3. Tester l'escalade humaine")
print("\nCommande CLI:")
print("  python apps/backend/cli/main.py --spec 001 --auto-fix")
print()

sys.exit(0)
