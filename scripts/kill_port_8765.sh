#!/bin/bash
# Script shell pour tuer les processus utilisant le port 8765 avant de démarrer l'application

echo "Vérification du port 8765..."

# Trouver et tuer les processus utilisant le port 8765
if command -v lsof >/dev/null 2>&1; then
    # Utiliser lsof si disponible (Linux/macOS)
    PIDS=$(lsof -ti:8765)
    if [ -n "$PIDS" ]; then
        echo "Arrêt des processus utilisant le port 8765..."
        echo "$PIDS" | xargs kill -9
        echo "Processus arrêtés: $PIDS"
    else
        echo "Aucun processus trouvé utilisant le port 8765"
    fi
elif command -v netstat >/dev/null 2>&1; then
    # Utiliser netstat comme alternative
    PIDS=$(netstat -tulpn 2>/dev/null | grep ":8765 " | grep "LISTEN" | awk '{print $7}' | cut -d'/' -f1)
    if [ -n "$PIDS" ]; then
        echo "Arrêt des processus utilisant le port 8765..."
        echo "$PIDS" | xargs kill -9
        echo "Processus arrêtés: $PIDS"
    else
        echo "Aucun processus trouvé utilisant le port 8765"
    fi
else
    echo "lsof ou netstat non disponible, impossible de vérifier le port"
    exit 1
fi

# Attendre un peu que les processus se terminent
sleep 2

# Vérifier si le port est maintenant disponible
if command -v lsof >/dev/null 2>&1; then
    if lsof -ti:8765 >/dev/null 2>&1; then
        echo "Le port 8765 est toujours occupé"
        exit 1
    else
        echo "Le port 8765 est maintenant disponible"
        exit 0
    fi
else
    echo "Impossible de vérifier si le port est disponible (lsof manquant)"
    exit 0
fi
