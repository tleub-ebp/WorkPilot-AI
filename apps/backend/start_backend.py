#!/usr/bin/env python3
"""
Script de démarrage pour le backend avec FastAPI et WebSocket.
"""

import logging
import os
import subprocess
import sys
import threading


# ANSI color codes pour les logs (similaire au script JS)
class Colors:
    reset = "\x1b[0m"
    bright = "\x1b[1m"
    red = "\x1b[31m"
    green = "\x1b[32m"
    yellow = "\x1b[33m"
    blue = "\x1b[34m"
    magenta = "\x1b[35m"
    cyan = "\x1b[36m"


def log(message, color="reset"):
    """Affiche un message avec la couleur spécifiée."""
    colors = Colors()
    color_code = getattr(colors, color, colors.reset)
    print(f"{color_code}{message}{colors.reset}")


# Configuration du logging avec couleurs
class ColoredFormatter(logging.Formatter):
    """Formatter personnalisé avec couleurs pour les logs."""

    COLORS = {
        "DEBUG": Colors.cyan,
        "INFO": Colors.blue,
        "WARNING": Colors.yellow,
        "ERROR": Colors.red,
        "CRITICAL": Colors.red + Colors.bright,
    }

    def format(self, record):
        if record.levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[record.levelname]}{record.levelname}{Colors.reset}"
            )
        return super().format(record)


# Configuration du logging avec couleurs
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Appliquer le formatter coloré à tous les handlers
for handler in logging.root.handlers:
    handler.setFormatter(
        ColoredFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )


def start_websocket_server():
    """Démarre le serveur WebSocket dans un thread séparé."""
    backend_dir = os.path.dirname(os.path.abspath(__file__))

    # Utiliser l'environnement virtuel si disponible
    if os.path.exists(os.path.join(backend_dir, ".venv", "Scripts", "python.exe")):
        python_exe = os.path.join(backend_dir, ".venv", "Scripts", "python.exe")
    else:
        python_exe = sys.executable

    websocket_script = os.path.join(backend_dir, "websocket_server.py")

    try:
        log("🔌 Starting WebSocket server...", "magenta")
        log(f"Using Python: {python_exe}", "cyan")
        process = subprocess.Popen(
            [python_exe, websocket_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            cwd=backend_dir,
        )

        # Logger la sortie du WebSocket en temps réel avec couleurs
        for line in iter(process.stdout.readline, ""):
            if line.strip():
                # Parser les logs WebSocket et ajouter des couleurs
                if "ERROR" in line or "CRITICAL" in line:
                    log(f"🔴 WebSocket: {line.strip()}", "red")
                elif "WARNING" in line:
                    log(f"🟡 WebSocket: {line.strip()}", "yellow")
                elif "started" in line.lower() or "listening" in line.lower():
                    log(f"✅ WebSocket: {line.strip()}", "green")
                else:
                    log(f"🔌 WebSocket: {line.strip()}", "magenta")

    except Exception as e:
        log(f"🔴 WebSocket Error: {e}", "red")


def main():
    """Point d'entrée principal."""
    # Ajouter le répertoire parent au path
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(backend_dir)
    sys.path.insert(0, project_root)

    # Ajouter le dossier src du backend au path
    src_dir = os.path.join(backend_dir, "src")
    sys.path.insert(0, src_dir)

    # Messages colorés de démarrage
    log("🚀 Starting WorkPilot AI Backend Services", "bright")
    log("=============================================", "cyan")

    try:
        # Démarrer le WebSocket dans un thread séparé avec délai
        websocket_thread = threading.Timer(
            3.0, start_websocket_server
        )  # 3 secondes de délai
        websocket_thread.start()

        # Importer et démarrer l'application FastAPI via uvicorn
        import uvicorn

        # Configuration du serveur
        host = "127.0.0.1"
        port = 9000

        log("📡 Starting FastAPI server...", "blue")
        log(f"📊 FastAPI: http://{host}:{port}", "cyan")
        log("🔌 WebSocket: ws://localhost:8765", "cyan")
        log("✨ Backend services starting...", "bright")
        log("", "reset")

        # Démarrer le serveur avec reload pour le développement
        uvicorn.run(
            "provider_api:app", host=host, port=port, reload=True, log_level="info"
        )

    except ImportError as e:
        log(f"❌ Import error: {e}", "red")
        log("Please install dependencies: pip install -r requirements.txt", "yellow")
        sys.exit(1)
    except Exception as e:
        log(f"❌ Startup error: {e}", "red")
        sys.exit(1)


if __name__ == "__main__":
    main()
