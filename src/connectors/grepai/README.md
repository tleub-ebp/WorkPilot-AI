# Utilisation de Grepai

Pour tester l'intégration de Grepai :

1. Lancez Grepai (via Docker ou CLI, accessible sur http://localhost:8000).
2. Exécutez le script de test :

    cd src/connectors/grepai
    python test_grepai.py

Le script effectue une recherche (exemple : "def my_function") et affiche le résultat ou une erreur.

Vous pouvez adapter le script pour intégrer Grepai dans d'autres modules du projet.
