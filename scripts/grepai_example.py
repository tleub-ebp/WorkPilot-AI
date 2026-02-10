# grepai integration example
# This script demonstrates how to use grepai in your workspace.

try:
    import grepai
except ImportError:
    print("grepai n'est pas installé. Veuillez l'ajouter à requirements.txt et installer les dépendances.")
    exit(1)

# Exemple d'utilisation basique (à adapter selon vos besoins)
# Rechercher un motif dans un fichier
results = grepai.grep(pattern="TODO", file_path="README.md")
for result in results:
    print(result)
