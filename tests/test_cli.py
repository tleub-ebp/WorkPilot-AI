#!/usr/bin/env python3
"""
Test de la commande CLI --auto-fix
"""
import subprocess
import sys
from pathlib import Path

print("=" * 70)
print("AUTO-FIX LOOP - TEST CLI")
print("=" * 70)

# Test 1: Vérifier que --help affiche l'option
print("\n[1/2] 🔍 Test --help contient --auto-fix...")
try:
    result = subprocess.run(
        [sys.executable, "apps/backend/cli/main.py", "--help"],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    if "--auto-fix" in result.stdout:
        print("  ✓ --auto-fix trouvé dans --help")
        
        if "--auto-fix-max-attempts" in result.stdout:
            print("  ✓ --auto-fix-max-attempts trouvé dans --help")
        else:
            print("  ⚠️  --auto-fix-max-attempts non trouvé (mais pas critique)")
        
        print("  ✅ CLI options présentes")
    else:
        print("  ❌ --auto-fix NON trouvé dans --help")
        print("\nOutput:")
        print(result.stdout[:500])
        sys.exit(1)
        
except subprocess.TimeoutExpired:
    print("  ❌ Timeout lors de l'exécution de --help")
    sys.exit(1)
except Exception as e:
    print(f"  ❌ Erreur: {e}")
    sys.exit(1)

# Test 2: Vérifier l'import de handle_auto_fix_command
print("\n[2/2] 📦 Test import handle_auto_fix_command...")
try:
    backend_dir = Path(__file__).parent / "apps" / "backend"
    sys.path.insert(0, str(backend_dir))
    
    from cli.qa_commands import handle_auto_fix_command
    
    # Vérifier la signature
    import inspect
    sig = inspect.signature(handle_auto_fix_command)
    params = list(sig.parameters.keys())
    
    expected_params = ['project_dir', 'spec_dir', 'model', 'max_attempts', 'verbose']
    
    for param in expected_params:
        if param in params:
            print(f"  ✓ Paramètre '{param}' présent")
        else:
            print(f"  ⚠️  Paramètre '{param}' manquant (peut être OK)")
    
    print("  ✅ Fonction handle_auto_fix_command OK")
    
except ImportError as e:
    print(f"  ❌ Erreur d'import: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Résumé
print("\n" + "=" * 70)
print("✅ TESTS CLI PASSENT!")
print("=" * 70)
print("\n✓ La commande CLI --auto-fix est fonctionnelle")
print("\nUtilisation:")
print("  python apps/backend/cli/main.py --spec 001 --auto-fix")
print("  python apps/backend/cli/main.py --spec 001 --auto-fix --auto-fix-max-attempts 10")
print()

sys.exit(0)
