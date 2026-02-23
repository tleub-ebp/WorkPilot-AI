#!/bin/bash
# Script de démarrage pour le backend avec gestion automatique des ports occupés

echo "Démarrage du backend Auto-Claude EBP..."

# Vérifier si Python est installé
if ! command -v python3 &> /dev/null; then
    echo "Python3 n'est pas installé ou n'est pas dans le PATH"
    exit 1
fi

# Se déplacer dans le répertoire backend
cd "$(dirname "$0")"

# Vérifier si les dépendances sont installées
echo "Vérification des dépendances..."
python3 -c "import fastapi, uvicorn, websockets, psutil" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installation des dépendances manquantes..."
    pip3 install fastapi uvicorn websockets psutil
    if [ $? -ne 0 ]; then
        echo "Erreur lors de l'installation des dépendances"
        exit 1
    fi
fi

# Démarrer le backend
echo "Lancement du serveur backend..."
python3 start_backend.py
