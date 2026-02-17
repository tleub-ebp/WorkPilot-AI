#!/bin/bash
# Script Linux/Mac pour lancer backend FastAPI + frontend Electron
cd "$(dirname "$0")"
cd ../backend
if [ ! -f ../.venv/bin/activate ]; then
  echo "[ERREUR] L'environnement virtuel Python n'existe pas. Lancez 'python3 -m venv ../.venv' puis 'pip install -r requirements.txt'."
  exit 1
fi
source ../.venv/bin/activate
if ! command -v uvicorn >/dev/null 2>&1; then
  echo "[ERREUR] uvicorn n'est pas installe. Lancez 'pip install -r requirements.txt'."
  exit 1
fi
uvicorn provider_api:app --host 127.0.0.1 --port 9000 --reload &
cd ../frontend
pnpm run dev