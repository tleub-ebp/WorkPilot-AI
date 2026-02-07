"""
Script de diagnostic pour identifier d'où vient 'MeCa Web'.
Affiche toutes les sources de configuration Azure DevOps.
"""

import os
import sys
from pathlib import Path

print("=" * 70)
print("DIAGNOSTIC AZURE DEVOPS - Sources de configuration")
print("=" * 70)
print()

# 1. Variables d'environnement
print("1. Variables d'environnement du système:")
print("-" * 70)
azure_vars = {k: v for k, v in os.environ.items() if 'AZURE' in k.upper()}
if azure_vars:
    for key, value in sorted(azure_vars.items()):
        if 'PAT' in key or 'TOKEN' in key:
            value = value[:10] + "..." if len(value) > 10 else "***"
        print(f"   {key} = {value}")
else:
    print("   Aucune variable AZURE_* trouvée")
print()

# 2. Fichier .env du backend
print("2. apps/backend/.env:")
print("-" * 70)
backend_env = Path(__file__).parent / "apps" / "backend" / ".env"
if backend_env.exists():
    with open(backend_env, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('AZURE_DEVOPS_PROJECT'):
                print(f"   {line}")
                break
        else:
            print("   AZURE_DEVOPS_PROJECT non trouvé dans .env")
else:
    print("   Fichier .env introuvable")
print()

# 3. Test d'extraction depuis Git
print("3. Extraction depuis Git remote:")
print("-" * 70)
try:
    backend_path = Path(__file__).parent / "apps" / "backend"
    sys.path.insert(0, str(backend_path))
    
    from core.git_provider import detect_git_provider, extract_azure_devops_project
    
    provider = detect_git_provider(".")
    print(f"   Provider détecté: {provider}")
    
    if provider == "azure_devops":
        project = extract_azure_devops_project(".")
        print(f"   Projet extrait: {project}")
    else:
        print(f"   Provider n'est pas Azure DevOps")
except Exception as e:
    print(f"   ❌ Erreur: {e}")
print()

# 4. Vérification du remote Git
print("4. URL Git remote:")
print("-" * 70)
try:
    import subprocess
    result = subprocess.run(
        ['git', 'remote', 'get-url', 'origin'],
        capture_output=True,
        text=True,
        timeout=5
    )
    if result.returncode == 0:
        url = result.stdout.strip()
        print(f"   {url}")
        
        # Parse l'URL pour montrer les composants
        import re
        from urllib.parse import unquote
        
        match = re.search(r'https://dev\.azure\.com/([^/]+)/([^/]+)/_git/(.+)', url)
        if match:
            org = match.group(1)
            proj = unquote(match.group(2))
            repo = unquote(match.group(3))
            print()
            print(f"   Décomposition:")
            print(f"     Organisation: {org}")
            print(f"     PROJET:       {proj}  ← Devrait être utilisé")
            print(f"     Repository:   {repo}")
    else:
        print(f"   ❌ Impossible de récupérer le remote")
except Exception as e:
    print(f"   ❌ Erreur: {e}")
print()

print("=" * 70)
print("RECOMMANDATIONS:")
print("=" * 70)
print()
print("Si 'MeCa Web' apparaît quelque part ci-dessus:")
print("1. Vérifiez AZURE_DEVOPS_PROJECT dans apps/backend/.env")
print("2. Vérifiez les variables d'environnement système")
print("3. Redémarrez votre terminal/IDE après modification")
print()
print("Valeur correcte: AZURE_DEVOPS_PROJECT=MéCa")
print("=" * 70)
