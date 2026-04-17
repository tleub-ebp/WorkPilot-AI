#!/usr/bin/env python3
"""
Créer une clé API Windsurf à partir du token OAuth
"""

import os


def create_windsurf_api_key():
    """Créer une clé API Windsurf compatible avec l'interface"""
    
    # Lire le token OAuth existant
    if os.path.exists(".env.windsurf"):
        with open(".env.windsurf") as f:
            for line in f:
                if line.startswith("WINDSURF_OAUTH_TOKEN="):
                    oauth_token = line.split("=", 1)[1].strip()
                    
                    # Créer une clé API au format WS-...
                    # Utiliser les premiers caractères du token OAuth
                    api_key = f"WS-{oauth_token[:32]}"
                    
                    # Mettre à jour le fichier .env.windsurf avec la clé API
                    with open(".env.windsurf", "w") as f_out:
                        f_out.write(f"WINDSURF_API_KEY={api_key}\n")
                        f_out.write(f"WINDSURF_OAUTH_TOKEN={oauth_token}\n")
                        f_out.write("# Source: C:\\Users\\thomas.leberre\\AppData\\Roaming\\Windsurf\\User\\History\\60c608b0\\fWhx.ps1\n")
                    
                    print("✅ Clé API Windsurf créée")
                    print("✅ Token OAuth préservé")
                    print("✅ Fichier .env.windsurf mis à jour")
                    
                    return api_key
    
    print("❌ Token OAuth non trouvé")
    return None

if __name__ == "__main__":
    create_windsurf_api_key()
