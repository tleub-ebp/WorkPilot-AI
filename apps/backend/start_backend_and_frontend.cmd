@echo off
REM Script Windows pour lancer backend FastAPI + frontend Electron
cd /d %~dp0
cd ..\backend
if not exist ..\.venv\Scripts\activate.bat (
    echo [ERREUR] L'environnement virtuel Python n'existe pas. Lancez 'python -m venv ..\.venv' puis 'pip install -r requirements.txt'.
    pause
    exit /b 1
)
call ..\.venv\Scripts\activate.bat
where uvicorn >nul 2>nul || (
    echo [ERREUR] uvicorn n'est pas installe. Lancez 'pip install -r requirements.txt'.
    pause
    exit /b 1
)
start "FastAPI" cmd /k "uvicorn provider_api:app --host 127.0.0.1 --port 8000 --reload"
cd ..\frontend
pnpm run dev