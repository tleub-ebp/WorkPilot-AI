#!/usr/bin/env python3
"""
Script de démarrage pour le backend avec gestion automatique des ports occupés.
"""

import os
import sys
import subprocess
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Point d'entrée principal."""
    # Ajouter le répertoire parent au path
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(backend_dir)
    sys.path.insert(0, project_root)
    
    # Ajouter le dossier src du backend au path
    src_dir = os.path.join(backend_dir, 'src')
    sys.path.insert(0, src_dir)
    
    logger.info("Démarrage du backend Auto-Claude EBP...")
    
    try:
        # Importer et démarrer l'application FastAPI
        import uvicorn
        from provider_api import app
        
        # Configuration du serveur
        host = "127.0.0.1"
        port = 8000
        
        logger.info(f"Démarrage du serveur sur http://{host}:{port}")
        
        # Démarrer le serveur avec reload pour le développement
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=True,
            log_level="info"
        )
        
    except ImportError as e:
        logger.error(f"Erreur d'import: {e}")
        logger.error("Assurez-vous que toutes les dépendances sont installées:")
        logger.error("pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Erreur au démarrage: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
