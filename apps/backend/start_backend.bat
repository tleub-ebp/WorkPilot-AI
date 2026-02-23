@echo off
REM Script de démarrage pour le backend avec gestion automatique des ports occupés

echo Démarrage du backend Auto-Claude EBP...

REM Vérifier si Python est installé
python --version >nul 2>&1
if errorlevel 1 (
    echo Python n'est pas installé ou n'est pas dans le PATH
    pause
    exit /b 1
)

REM Se déplacer dans le répertoire backend
cd /d "%~dp0"

REM Vérifier si les dépendances sont installées
echo Vérification des dépendances...
python -c "import fastapi, uvicorn, websockets, psutil" >nul 2>&1
if errorlevel 1 (
    echo Installation des dépendances manquantes...
    pip install fastapi uvicorn websockets psutil
    if errorlevel 1 (
        echo Erreur lors de l'installation des dépendances
        pause
        exit /b 1
    )
)

REM Démarrer le backend
echo Lancement du serveur backend...
python start_backend.py

pause
