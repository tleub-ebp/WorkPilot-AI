#!/usr/bin/env python3
"""
Script pour trouver et extraire le token OAuth Windsurf
"""

import os
import json
import sqlite3
import base64
from pathlib import Path

def find_windsurf_token():
    """Cherche le token OAuth Windsurf dans les fichiers locaux"""
    print("🔍 Recherche du token Windsurf OAuth...")
    
    # Chemins possibles pour le token
    windsurf_paths = [
        os.path.expandvars(r"%APPDATA%\Windsurf"),
        os.path.expandvars(r"%LOCALAPPDATA%\Windsurf"),
        os.path.expanduser("~/.windsurf"),
    ]
    
    for base_path in windsurf_paths:
        if not os.path.exists(base_path):
            continue
            
        print(f"📁 Exploration de: {base_path}")
        
        # Chercher dans les fichiers JSON
        for root, dirs, files in os.walk(base_path):
            for file in files:
                if file.endswith(('.json', '.db', '.sqlite', '.ldb')):
                    file_path = os.path.join(root, file)
                    try:
                        search_in_file(file_path)
                    except Exception as e:
                        print(f"   ⚠️  Erreur lecture {file}: {e}")
    
    # Chercher dans les variables d'environnement
    print("\n🔍 Variables d'environnement:")
    env_vars = ['WINDSURF_TOKEN', 'WINDSURF_OAUTH_TOKEN', 'CODEIUM_TOKEN']
    for var in env_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: ****** (set, {len(value)} chars)")
            return value
    
    print("❌ Token non trouvé automatiquement")
    return None

def search_in_file(file_path):
    """Cherche des patterns de token dans un fichier"""
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Patterns de token à chercher
        patterns = [
            b'access_token',
            b'oauth_token', 
            b'windsurf_token',
            b'codeium_token',
            b'Bearer',
            b'eyJ',  # Début de token JWT
        ]
        
        for pattern in patterns:
            if pattern in content:
                print(f"🎯 Pattern trouvé dans: {file_path}")
                
                # Essayer d'extraire le token
                if pattern == b'access_token':
                    extract_token_from_content(content, file_path)
                elif pattern == b'eyJ':
                    extract_jwt_token(content, file_path)
                    
    except Exception as e:
        pass

def extract_token_from_content(content, file_path):
    """Extrait le token du contenu"""
    try:
        content_str = content.decode('utf-8', errors='ignore')
        
        # Chercher access_token=...
        import re
        matches = re.findall(r'access_token["\s]*[:=]["\s]*([^"\s&}]+)', content_str)
        for match in matches:
            if len(match) > 50:  # Token JWT typique
                print(f"✅ Token trouvé: {match[:20]}...{match[-10:]}")
                return match
                
    except Exception:
        pass

def extract_jwt_token(content, file_path):
    """Extrait un token JWT"""
    try:
        content_str = content.decode('utf-8', errors='ignore')
        
        # Chercher des chaînes qui ressemblent à des JWT
        import re
        jwt_pattern = r'eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*'
        matches = re.findall(jwt_pattern, content_str)
        
        for match in matches:
            if len(match) > 100:  # JWT complet
                print(f"✅ JWT trouvé: {match[:20]}...{match[-10:]}")
                return match
                
    except Exception:
        pass

def manual_token_input():
    """Permet à l'utilisateur de saisir manuellement le token"""
    print("\n🔧 Saisie manuelle du token")
    print("Si vous avez trouvé le token manuellement, collez-le ici:")
    
    token = input("Token Windsurf OAuth: ").strip()
    
    if token and len(token) > 50:
        print(f"✅ Token reçu: {token[:20]}...{token[-10:]}")
        
        # Créer le fichier de configuration
        env_file = os.path.join(os.getcwd(), ".env.windsurf")
        with open(env_file, "w") as f:
            f.write(f"WINDSURF_OAUTH_TOKEN={token}\n")
        
        print(f"📁 Token sauvegardé dans: {env_file}")
        print("📋 Utilisez: export WINDSURF_OAUTH_TOKEN=\"your_token\"")
        return token
    else:
        print("❌ Token invalide")
        return None

if __name__ == "__main__":
    print("🌊 Extracteur de Token Windsurf OAuth")
    print("=" * 40)
    
    # Recherche automatique
    token = find_windsurf_token()
    
    if not token:
        # Saisie manuelle
        token = manual_token_input()
    
    if token:
        print("\n🎉 Token Windsurf OAuth configuré!")
        print("📋 Testez l'intégration avec:")
        print("   python test_windsurf_integration.py")
    else:
        print("\n❌ Token non trouvé. Réessayez la recherche manuelle.")
