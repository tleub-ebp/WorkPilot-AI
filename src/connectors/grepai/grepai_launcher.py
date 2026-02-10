import os
import subprocess
import time
import yaml
import requests

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'grepai.yaml')
EXE_PATH = os.path.join(os.path.dirname(__file__), 'grepai.exe')
PORT = 8000
INDEX_PATH = '../../apps/backend'

DEFAULT_CONFIG = {
    'index_path': INDEX_PATH,
    'port': PORT,
    'log_level': 'info',
    'max_results': 10
}


def ensure_config():
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'w') as f:
            yaml.dump(DEFAULT_CONFIG, f)
        print(f"Fichier de configuration généré : {CONFIG_PATH}")
    else:
        print(f"Fichier de configuration déjà présent : {CONFIG_PATH}")


def launch_grepai():
    if not os.path.exists(EXE_PATH):
        raise FileNotFoundError(f"grepai.exe introuvable dans {EXE_PATH}. Téléchargez-le depuis https://yoanbernabeu.github.io/grepai/installation/")
    print("Lancement de grepai...")
    subprocess.Popen([EXE_PATH, 'serve'], cwd=os.path.dirname(EXE_PATH))
    time.sleep(2)  # Laisse le temps à grepai de démarrer


def check_grepai_health():
    try:
        response = requests.get(f"http://localhost:{PORT}/health", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


def main():
    ensure_config()
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
