import os
from pathlib import Path
from dotenv import dotenv_values

# Chemins des fichiers .env
ROOT_ENV = Path(__file__).parent.parent / ".env-files" / ".env"
FRONTEND_ENV = Path(__file__).parent.parent / "apps" / "frontend" / ".env-files" / ".env"

# Charge la variable BACKEND_PORT du .env racine
root_env_vars = dotenv_values(ROOT_ENV)
backend_port = root_env_vars.get("BACKEND_PORT", "9000")

# Prépare la ligne à écrire dans le .env frontend
backend_url = f"VITE_BACKEND_URL=http://localhost:{backend_port}"

# Crée le dossier .env-files s'il n'existe pas
FRONTEND_ENV.parent.mkdir(parents=True, exist_ok=True)

# Lis le .env frontend existant (s'il existe)
frontend_lines = []
if FRONTEND_ENV.exists():
    with open(FRONTEND_ENV, "r", encoding="utf-8") as f:
        frontend_lines = f.readlines()

# Remplace ou ajoute la ligne VITE_BACKEND_URL
found = False
for i, line in enumerate(frontend_lines):
    if line.startswith("VITE_BACKEND_URL="):
        frontend_lines[i] = backend_url + "\n"
        found = True
        break
if not found:
    frontend_lines.append(backend_url + "\n")

# Écrit le .env frontend synchronisé
with open(FRONTEND_ENV, "w", encoding="utf-8") as f:
    f.writelines(frontend_lines)

print(f"[sync_backend_port_to_frontend_env] VITE_BACKEND_URL synchronisé : {backend_url}")
