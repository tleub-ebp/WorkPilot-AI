"""
Vérification finale de la configuration Azure DevOps
Affiche la configuration dans chaque fichier .env trouvé
"""

from pathlib import Path

print("=" * 70)
print("VÉRIFICATION FINALE - Configuration Azure DevOps")
print("=" * 70)
print()

env_files = [
    Path(".auto-claude/.env"),
    Path("apps/backend/.env"),
    Path("auto-code-ebp/.auto-claude/.env"),
]

all_correct = True

for env_file in env_files:
    if not env_file.exists():
        continue

    print(f"📁 {env_file}")
    print("-" * 70)

    with open(env_file, encoding="utf-8") as f:
        lines = f.readlines()

    azure_config = {}
    for line in lines:
        line = line.strip()
        if line.startswith("AZURE_DEVOPS_"):
            key, _, value = line.partition("=")
            azure_config[key] = value

    if not azure_config:
        print("  ⚠️  Aucune configuration Azure DevOps trouvée")
        print()
        continue

    for key, value in sorted(azure_config.items()):
        if "PAT" in key and value and not value.startswith("#"):
            display_value = value[:10] + "..." if len(value) > 10 else "***"
        else:
            display_value = value

        # Vérification
        if key == "AZURE_DEVOPS_PROJECT":
            if value == "MéCa":
                print(f"  ✅ {key} = {value}")
            elif value == "MeCa Web":
                print(f"  ❌ {key} = {value}  ← INCORRECT! Devrait être 'MéCa'")
                all_correct = False
            elif not value or value.startswith("#"):
                print(f"  ⚠️  {key} = (vide - auto-détection activée)")
            else:
                print(f"  ⚠️  {key} = {value}")
        elif key == "AZURE_DEVOPS_ENABLED":
            if value == "true":
                print(f"  ✅ {key} = {value}")
            else:
                print(f"  ⚠️  {key} = {value}")
        else:
            print(f"     {key} = {display_value}")

    print()

print("=" * 70)
if all_correct:
    print("✅ TOUTES LES CONFIGURATIONS SONT CORRECTES!")
    print()
    print("Prochaines étapes:")
    print("1. Fermez COMPLÈTEMENT l'application Auto-Claude")
    print("2. Redémarrez l'application")
    print("3. Ouvrez le projet 'Auto-Claude_EBP' (pas auto-code-ebp)")
    print("4. Essayez d'importer des work items Azure DevOps")
    print()
    print("Vous devriez voir dans les logs:")
    print("  'Auto-detected Azure DevOps project from Git remote: MéCa'")
else:
    print("❌ Des corrections sont nécessaires")
    print("Corrigez les fichiers marqués avec ❌ ci-dessus")
print("=" * 70)
