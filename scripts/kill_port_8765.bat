@echo off
REM Script batch pour tuer les processus utilisant le port 8765 avant de démarrer l'application

echo Vérification du port 8765...

REM Trouver les processus utilisant le port 8765
for /f "tokens=5" %%a in ('netstat -ano ^| find ":8765" ^| find "LISTENING"') do (
    echo Arrêt du processus %%a...
    taskkill /F /PID %%a >nul 2>&1
    if !errorlevel! equ 0 (
        echo Processus %%a arrêté avec succès
    ) else (
        echo Échec de l'arrêt du processus %%a
    )
)

REM Attendre un peu que les processus se terminent
timeout /t 2 /nobreak >nul

REM Vérifier si le port est maintenant disponible
netstat -ano | find ":8765" | find "LISTENING" >nul
if !errorlevel! equ 0 (
    echo Le port 8765 est toujours occupé
    exit /b 1
) else (
    echo Le port 8765 est maintenant disponible
    exit /b 0
)
