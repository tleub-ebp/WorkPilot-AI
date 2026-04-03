#!/usr/bin/env python3
"""
Script maître - Lance tous les tests de validation
"""
import subprocess
import sys
from pathlib import Path


def run_test(name, script):
    """Execute un script de test."""
    print(f"\n{'=' * 70}")
    print(f"🧪 {name}")
    print('=' * 70)
    
    try:
        result = subprocess.run(
            [sys.executable, script],
            cwd=Path(__file__).parent,
            timeout=60
        )
        
        if result.returncode == 0:
            print(f"\n✅ {name} - SUCCÈS")
            return True
        else:
            print(f"\n❌ {name} - ÉCHEC (code: {result.returncode})")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"\n⏱️  {name} - TIMEOUT")
        return False
    except Exception as e:
        print(f"\n💥 {name} - ERREUR: {e}")
        return False


def main():
    """Lance tous les tests."""
    
    print("=" * 70)
    print("🚀 AUTO-FIX LOOPS - SUITE DE TESTS COMPLÈTE")
    print("=" * 70)
    print("\nCe script va exécuter tous les tests de validation:")
    print("  1. Tests de syntaxe Python")
    print("  2. Tests d'imports et d'intégration")
    print("  3. Tests fonctionnels complets")
    print("  4. Tests CLI")
    print()
    
    tests = [
        ("Syntaxe Python", "check_syntax.py"),
        ("Validation Imports", "test_validation.py"),
        ("Tests Fonctionnels", "run_functional_tests.py"),
        ("Tests CLI", "test_cli.py"),
        ("Tests Multi-Provider LLM", "test_llm_provider.py"),
        ("Tests Providers Concrets LLM", "test_llm_providers_concrets.py"),
    ]
    
    results = []
    
    for name, script in tests:
        script_path = Path(__file__).parent / script
        
        if not script_path.exists():
            print(f"\n⚠️  Script {script} non trouvé, ignoré")
            results.append((name, None))
            continue
        
        success = run_test(name, script_path)
        results.append((name, success))
    
    # Résumé final
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 70)
    
    passed = 0
    failed = 0
    skipped = 0
    
    for name, result in results:
        if result is True:
            print(f"  ✅ {name}")
            passed += 1
        elif result is False:
            print(f"  ❌ {name}")
            failed += 1
        else:
            print(f"  ⚠️  {name} (ignoré)")
            skipped += 1
    
    total = passed + failed
    
    print("\n" + "=" * 70)
    print(f"Résultats: {passed}/{total} tests passés")
    
    if skipped > 0:
        print(f"           {skipped} test(s) ignoré(s)")
    
    print("=" * 70)
    
    if failed == 0 and passed > 0:
        print("\n🎉 TOUS LES TESTS PASSENT!")
        print("\n✨ Feature 3: Auto-Fix Loops Intelligents")
        print("   └─ Status: ✅ VALIDÉE ET FONCTIONNELLE")
        print("\n📚 Documentation:")
        print("   - Guide: docs/features/auto-fix-loops.md")
        print("   - Quick ref: docs/features/auto-fix-loops-quick-ref.md")
        print("   - Tests: VALIDATION_CHECKLIST.md")
        print("\n🎮 Utilisation:")
        print("   python apps/backend/cli/main.py --spec 001 --auto-fix")
        print("   python apps/backend/cli/main.py --spec 001 --auto-fix --auto-fix-max-attempts 10")
        print("\n💡 Prêt pour la production!")
        print()
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) ont échoué")
        print("\nVeuillez corriger les erreurs avant d'utiliser la feature.")
        print("Consultez les logs ci-dessus pour plus de détails.")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
