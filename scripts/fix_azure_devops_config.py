"""
Script de diagnostic et correction pour Azure DevOps.

Ce script vous aide à :
1. Diagnostiquer le problème de configuration
2. Extraire le nom du projet correct depuis l'URL
3. Afficher la configuration à utiliser
"""

import os
import re
from urllib.parse import unquote


def extract_project_from_url(repo_url: str) -> str | None:
    """Extrait le nom du projet depuis une URL Azure DevOps."""
    pattern = (
        r"https://(?:dev\.azure\.com/[^/]+|[^/]+\.visualstudio\.com)/([^/]+)/_git/"
    )
    match = re.search(pattern, repo_url)
    if match:
        return unquote(match.group(1))
    return None


def main():
    print("=" * 70)
    print("DIAGNOSTIC AZURE DEVOPS")
    print("=" * 70)
    print()

    # 1. Vérifier la configuration actuelle
    print("📋 Configuration actuelle:")
    print("-" * 70)

    pat = os.getenv("AZURE_DEVOPS_PAT")
    org_url = os.getenv("AZURE_DEVOPS_ORG_URL")
    project = os.getenv("AZURE_DEVOPS_PROJECT")

    print(f"AZURE_DEVOPS_PAT:     {'✓ Défini' if pat else '✗ Non défini'}")
    print(f"AZURE_DEVOPS_ORG_URL: {org_url or '✗ Non défini'}")
    print(f"AZURE_DEVOPS_PROJECT: {project or '✗ Non défini'}")
    print()

    # 2. Analyser le problème
    print("🔍 Analyse:")
    print("-" * 70)

    if project == "MeCa Web":
        print("❌ PROBLÈME DÉTECTÉ!")
        print(f"   Valeur actuelle: '{project}'")
        print("   Type: Repository (incorrect)")
        print()
        print("   'MeCa Web' est le nom du REPOSITORY, pas du PROJET.")
        print("   Vous devez utiliser le nom du PROJET.")
        print()

    # 3. Demander l'URL du repository
    print("🔗 URL de votre repository:")
    print("-" * 70)

    example_url = "https://dev.azure.com/ebp-informatique/MéCa/_git/MeCa%20Web"
    print(f"Exemple: {example_url}")
    print()

    repo_url = input("Entrez l'URL de votre repository Azure DevOps: ").strip()

    if not repo_url:
        print("⚠️  Aucune URL fournie. Utilisation de l'exemple par défaut.")
        repo_url = example_url

    print()

    # 4. Extraire le projet
    print("🎯 Extraction du nom du projet:")
    print("-" * 70)

    extracted_project = extract_project_from_url(repo_url)

    if extracted_project:
        print(f"URL fournie:    {repo_url}")
        print(f"Projet extrait: {extracted_project}")
        print()

        # 5. Afficher la configuration correcte
        print("✅ Configuration correcte à utiliser:")
        print("=" * 70)
        print()
        print("# Windows PowerShell:")
        print(f'$env:AZURE_DEVOPS_PROJECT="{extracted_project}"')
        print()
        print("# Linux/Mac Bash:")
        print(f'export AZURE_DEVOPS_PROJECT="{extracted_project}"')
        print()
        print("# Fichier .env:")
        print(f"AZURE_DEVOPS_PROJECT={extracted_project}")
        print()

        # 6. Explication
        print("📚 Explication:")
        print("-" * 70)
        print(f"Dans l'URL: {repo_url}")
        print()

        # Parser l'URL pour montrer les parties
        match = re.search(
            r"https://dev\.azure\.com/([^/]+)/([^/]+)/_git/(.+)", repo_url
        )
        if match:
            org = match.group(1)
            proj = unquote(match.group(2))
            repo = unquote(match.group(3))

            print(f"  Organisation: {org}")
            print(f"  PROJET:       {proj}  ← Utilisez cette valeur")
            print(f"  Repository:   {repo}")
        print()

        # 7. Proposition d'export automatique
        print("🚀 Voulez-vous définir cette variable maintenant?")
        print("-" * 70)
        response = (
            input(f"Définir AZURE_DEVOPS_PROJECT='{extracted_project}' ? (o/n): ")
            .strip()
            .lower()
        )

        if response in ["o", "oui", "y", "yes"]:
            os.environ["AZURE_DEVOPS_PROJECT"] = extracted_project
            print(
                f"✓ Variable définie pour cette session: AZURE_DEVOPS_PROJECT='{extracted_project}'"
            )
            print()
            print(
                "⚠️  ATTENTION: Cette modification n'est valable que pour ce terminal."
            )
            print("   Pour la rendre permanente, ajoutez-la à votre fichier .env")
            print("   ou à votre profil PowerShell/Bash.")
        else:
            print("Variable non modifiée. Copiez la commande ci-dessus manuellement.")

    else:
        print("❌ Impossible d'extraire le projet depuis l'URL fournie.")
        print("   Vérifiez que l'URL est au format:")
        print("   https://dev.azure.com/{org}/{project}/_git/{repo}")

    print()
    print("=" * 70)
    print("Pour plus d'informations, consultez: docs/AZURE_DEVOPS_CONFIG.md")
    print("=" * 70)


if __name__ == "__main__":
    main()
