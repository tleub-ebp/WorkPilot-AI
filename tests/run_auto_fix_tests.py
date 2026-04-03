#!/usr/bin/env python3
"""
Script complet de tests - Auto-Fix Loops Feature
Lance les tests dans le bon ordre avec les bonnes dépendances
"""
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description, cwd=None):
    """Execute une commande et retourne le résultat."""
    print(f"\n{'='*80}")
    print(f"🧪 {description}")
    print(f"{'='*80}")
    print(f"📍 Working directory: {cwd or Path.cwd()}")
    print(f"📋 Command: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            timeout=300  # 5 minutes timeout
        )
        
        if result.returncode == 0:
            print(f"\n✅ {description} - SUCCÈS")
            return True
        else:
            print(f"\n❌ {description} - ÉCHEC (code: {result.returncode})")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"\n⏱️  {description} - TIMEOUT")
        return False
    except Exception as e:
        print(f"\n💥 {description} - ERREUR: {e}")
        return False

def main():
    repo_root = Path(__file__).parent
    # tests_dir is already the current directory since script is in tests/
    tests_dir = repo_root
    
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║  🚀 TESTS AUTO-FIX LOOPS - VERSION OPTIMISÉE                              ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
    """)
    
    results = []
    
    # Test 1: Syntaxe Python
    results.append((
        "Syntaxe Python",
        run_command(
            [sys.executable, "check_syntax.py"],
            "Test 1: Vérification syntaxe Python",
            cwd=tests_dir
        )
    ))
    
    # Test 2: Tests Auto-Fix Simplifiés (sans dépendances externes)
    results.append((
        "Auto-Fix Simplified Tests",
        run_command(
            [sys.executable, "test_auto_fix_simplified.py"],
            "Test 2: Tests auto-fix simplifiés (fonctionnalité core)",
            cwd=tests_dir
        )
    ))
    
    # Test 3: Validation des imports
    results.append((
        "Validation Imports",
        run_command(
            [sys.executable, "test_validation.py"],
            "Test 3: Validation des imports",
            cwd=tests_dir
        )
    ))
    
    # Résumé
    print(f"\n{'='*80}")
    print("📊 RÉSUMÉ DES TESTS AUTO-FIX")
    print(f"{'='*80}\n")
    
    passed = 0
    failed = 0
    
    for name, success in results:
        if success:
            print(f"  ✅ {name}")
            passed += 1
        else:
            print(f"  ❌ {name}")
            failed += 1
    
    total = passed + failed
    
    print(f"\n{'='*80}")
    print(f"Résultats: {passed}/{total} suites de tests passées")
    print(f"{'='*80}\n")
    
    if failed == 0:
        print("🎉 TOUS LES TESTS AUTO-FIX PASSENT!")
        print("\n✨ La feature Auto-Fix Loops est VALIDÉE!")
        print("\n✅ Features testées:")
        print("   - Import et structure du code")
        print("   - Dataclasses AutoFixTestResult et AutoFixAttempt")
        print("   - Création d'instances AutoFixLoop")
        print("   - Integration avec auto_fix_metrics")
        print("   - Syntaxe Python valide")
        return 0
    else:
        print(f"⚠️  {failed} test(s) ont échoué")
        return 1

if __name__ == "__main__":
    sys.exit(main())
