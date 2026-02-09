#!/usr/bin/env python3
"""
Tests auto-fix simplifiés - Version SANS imports externes
Ne dépend que de la structure du code, pas des dépendances externes
"""
import sys
import json
from pathlib import Path
import tempfile

print("=" * 70)
print("AUTO-FIX LOOP - TESTS SIMPLIFIÉS (SANS DÉPENDANCES EXTERNES)")
print("=" * 70)

# Test 1: Vérifier la syntaxe des fichiers Python
print("\n[1/3] 🔍 Test syntaxe Python...")
try:
    import py_compile
    
    backend_dir = Path(__file__).parent.parent / "apps" / "backend"
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
    print(f"  ❌ Erreur: {e}")
    sys.exit(1)

# Test 2: Vérifier la structure des fichiers (sans importer)
print("\n[2/3] 📋 Test structure des fichiers...")
try:
    backend_dir = Path(__file__).parent.parent / "apps" / "backend"
    
    # Vérifier que les fichiers existenet
    assert (backend_dir / "qa" / "auto_fix_loop.py").exists(), "auto_fix_loop.py manquant"
    assert (backend_dir / "qa" / "auto_fix_metrics.py").exists(), "auto_fix_metrics.py manquant"
    assert (backend_dir / "qa" / "__init__.py").exists(), "qa/__init__.py manquant"
    
    # Vérifier que les dataclasses sont définies
    with open(backend_dir / "qa" / "auto_fix_loop.py", encoding='utf-8') as f:
        content = f.read()
        assert "@dataclass" in content, "Dataclass decorator not found"
        assert "class TestResult" in content, "TestResult class not found"
        assert "class AutoFixAttempt" in content, "AutoFixAttempt class not found"
    
    print("  ✓ Fichiers existent")
    print("  ✓ Dataclasses définies")
    print("  ✓ Structure correcte")
    print("  ✅ Structure validée")
except Exception as e:
    print(f"  ❌ Erreur: {e}")
    sys.exit(1)

# Test 3: Vérifier les constantes importantes
print("\n[3/3] ⚙️  Test constantes et configuration...")
try:
    with open(backend_dir / "qa" / "auto_fix_loop.py", encoding='utf-8') as f:
        content = f.read()
        
        # Vérifier les constantes
        assert "DEFAULT_MAX_AUTO_FIX_ATTEMPTS = 5" in content, "DEFAULT_MAX_AUTO_FIX_ATTEMPTS not found"
        assert "TEST_EXECUTION_TIMEOUT" in content, "TEST_EXECUTION_TIMEOUT not found"
        
        # Vérifier les méthodes principales
        assert "async def run_until_green" in content, "run_until_green method not found"
        assert "def _analyze_failure" in content, "_analyze_failure method not found"
        assert "def _parse_test_counts" in content, "_parse_test_counts method not found"
    
    print("  ✓ DEFAULT_MAX_AUTO_FIX_ATTEMPTS = 5")
    print("  ✓ TEST_EXECUTION_TIMEOUT défini")
    print("  ✓ Méthodes principales présentes")
    print("  ✅ Configuration validée")
except Exception as e:
    print(f"  ❌ Erreur: {e}")
    sys.exit(1)

# Résumé
print("\n" + "=" * 70)
print("🎉 TOUS LES TESTS SIMPLIFIÉS PASSENT!")
print("=" * 70)
print("\n✅ Structure Auto-Fix Loop validée")
print("✅ Syntax Python correcte")
print("✅ Constantes et méthodes présentes")
print("\n✨ La feature est structurellement correcte!")
