#!/usr/bin/env python3
"""
Script simple et direct pour lancer les tests auto-fix
Sans problème de chemins
"""
import subprocess
import sys
from pathlib import Path

def run_test(script_name, description):
    """Exécute un test dans le répertoire courant."""
    print(f"\n{'='*80}")
    print(f"🧪 {description}")
    print(f"{'='*80}\n")
    
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            timeout=300
        )
        
        if result.returncode == 0:
            print(f"\n✅ {description} - SUCCÈS\n")
            return True
        else:
            print(f"\n❌ {description} - ÉCHEC\n")
            return False
    except Exception as e:
        print(f"\n💥 Erreur: {e}\n")
        return False

def main():
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║  🚀 TESTS AUTO-FIX LOOPS                                                   ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
    """)
    
    results = []
    
    # Test 1: Syntaxe Python
    results.append(("Syntaxe Python", run_test(
        "check_syntax.py",
        "Test 1: Vérification syntaxe Python"
    )))
    
    # Test 2: Tests Auto-Fix Simplifiés
    results.append(("Auto-Fix Simplified", run_test(
        "test_auto_fix_simplified.py",
        "Test 2: Tests auto-fix simplifiés"
    )))
    
    # Test 3: Validation imports
    results.append(("Validation Imports", run_test(
        "test_validation.py",
        "Test 3: Validation des imports"
    )))
    
    # Résumé
    print(f"\n{'='*80}")
    print("📊 RÉSUMÉ DES TESTS")
    print(f"{'='*80}\n")
    
    passed = sum(1 for _, result in results if result)
    failed = sum(1 for _, result in results if not result)
    total = len(results)
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"  {status} {name}")
    
    print(f"\nRésultats: {passed}/{total} tests passés")
    print(f"{'='*80}\n")
    
    if failed == 0:
        print("🎉 TOUS LES TESTS AUTO-FIX PASSENT!")
        print("\n✨ La feature Auto-Fix Loops est VALIDÉE!")
        return 0
    else:
        print(f"⚠️  {failed} test(s) ont échoué")
        return 1

if __name__ == "__main__":
    sys.exit(main())
