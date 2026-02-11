import os
import subprocess
import time
import yaml
import requests

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'grepai.yaml')
GREPAI_DIR = os.path.join(os.path.dirname(__file__), 'grepai')
PYTHON_PATH = 'python'
PORT = 8000
INDEX_PATH = '../../apps/backend'
GIT_URL = 'https://github.com/yoanbernabeu/grepai.git'
REQUIREMENTS_PATH = os.path.join(GREPAI_DIR, 'requirements.txt')

DEFAULT_CONFIG = {
    'index_path': INDEX_PATH,
    'port': PORT,
    'log_level': 'info',
    'max_results': 10
}

BINARY_PATH = os.path.join(GREPAI_DIR, 'grepai.exe')
GO_BUILD_CMD = ['go', 'build', '-o', BINARY_PATH, './cmd/grepai']


def ensure_config():
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'w') as f:
            yaml.dump(DEFAULT_CONFIG, f)
        print(f"Fichier de configuration généré : {CONFIG_PATH}")
    else:
        print(f"Fichier de configuration déjà présent : {CONFIG_PATH}")


def ensure_grepai_installed():
    if not os.path.exists(GREPAI_DIR):
        print("Clonage du dépôt grepai...")
        subprocess.run(['git', 'clone', GIT_URL, GREPAI_DIR], check=True)
    else:
        print("Dossier grepai déjà présent.")
    if os.path.exists(REQUIREMENTS_PATH):
        print("Installation des dépendances grepai...")
        subprocess.run([PYTHON_PATH, '-m', 'pip', 'install', '-r', REQUIREMENTS_PATH], check=True)
    else:
        print("requirements.txt introuvable dans grepai.")


def ensure_grepai_built():
    if not os.path.exists(BINARY_PATH):
        print("Compilation du binaire grepai...")
        subprocess.run(GO_BUILD_CMD, cwd=GREPAI_DIR, check=True)
    else:
        print("Binaire grepai déjà présent.")


def launch_grepai():
    print("Lancement de grepai...")
    subprocess.Popen([BINARY_PATH, 'serve'], cwd=GREPAI_DIR)
    time.sleep(2)  # Laisse le temps à grepai de démarrer


def check_grepai_health():
    try:
        response = requests.get(f"http://localhost:{PORT}/health", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


def main():
    ensure_config()
    ensure_grepai_installed()
    ensure_grepai_built()
    if not check_grepai_health():
        launch_grepai()
        time.sleep(2)
        if not check_grepai_health():
            print("Erreur : grepai n'a pas démarré correctement.")
        else:
            print("grepai lancé et accessible.")
    else:
        print("grepai déjà accessible.")

if __name__ == "__main__":
    main()