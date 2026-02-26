#!/usr/bin/env python3
"""
Script pour trouver manuellement le token Windsurf OAuth
"""

import os
import json
import base64
from pathlib import Path

def search_windsurf_token():
    """Recherche approfondie du token Windsurf OAuth"""
    print("🔍 Recherche avancée du token Windsurf OAuth...")
    
    # Chemins à explorer
    search_paths = [
        os.path.expandvars(r"%APPDATA%\Windsurf"),
        os.path.expandvars(r"%LOCALAPPDATA%\Windsurf"),
    ]
    
    for base_path in search_paths:
        if not os.path.exists(base_path):
            continue
            
        print(f"\n📁 Exploration de: {base_path}")
        
        # Chercher dans tous les fichiers
        for root, dirs, files in os.walk(base_path):
            for file in files:
                file_path = os.path.join(root, file)
                
                # Ignorer certains fichiers
                if any(skip in file.lower() for skip in ['.log', '.tmp', '.lock']):
                    continue
                
                try:
                    search_file_for_token(file_path)
                except Exception as e:
                    pass  # Ignorer les erreurs de lecture

def search_file_for_token(file_path):
    """Cherche des tokens dans un fichier spécifique"""
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Convertir en texte si possible
        try:
            content_str = content.decode('utf-8', errors='ignore')
        except:
            return
        
        # Patterns de recherche
        patterns = [
            # JWT tokens
            r'eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*',
            # access_token patterns
            r'access_token["\s]*[:=]["\s]*([A-Za-z0-9_-]+)',
            r'"token":\s*"[A-Za-z0-9_-]+"',
            r'"oauth_token":\s*"[A-Za-z0-9_-]+"',
            r'"bearer":\s*"[A-Za-z0-9_-]+"',
            # Autres patterns
            r'"windsurf_token":\s*"[A-Za-z0-9_-]+"',
            r'"codeium_token":\s*"[A-Za-z0-9_-]+"',
        ]
        
        import re
        for pattern in patterns:
            matches = re.findall(pattern, content_str, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                
                if len(match) > 50:  # Token significatif
                    print(f"🎯 Token trouvé dans: {file_path}")
                    print(f"   Token: {match[:50]}...{match[-20:]}")
                    
                    # Sauvegarder le token
                    save_token(match, file_path)
                    return match
    
    except Exception:
        pass

def save_token(token, source_file):
    """Sauvegarde le token trouvé"""
    try:
        # Créer le fichier .env
        env_file = os.path.join(os.getcwd(), ".env.windsurf")
        with open(env_file, "w") as f:
            f.write(f"WINDSURF_OAUTH_TOKEN={token}\n")
            f.write(f"# Source: {source_file}\n")
        
        print(f"✅ Token sauvegardé dans: {env_file}")
        
        # Créer un script de test
        test_script = os.path.join(os.getcwd(), "test_windsurf_token.py")
        with open(test_script, "w") as f:
            f.write(f'''#!/usr/bin/env python3
import os

# Charger le token Windsurf
with open(".env.windsurf", "r") as f:
    for line in f:
        if line.startswith("WINDSURF_OAUTH_TOKEN="):
            token = line.split("=", 1)[1].strip()
            print(f"Token Windsurf: {{token[:20]}}...{{token[-10:]}}")
            
            # Tester avec l'intégration
            os.environ["WINDSURF_OAUTH_TOKEN"] = token
            
            # Importer et tester
            from apps.backend.services.provider_registry import ProviderRegistry
            registry = ProviderRegistry()
            
            # Vérifier le statut
            status = registry.check_provider_status("windsurf")
            print(f"Status Windsurf: {{status}}")
            
            break
''')
        
        print(f"📋 Script de test créé: {test_script}")
        
    except Exception as e:
        print(f"❌ Erreur sauvegarde: {e}")

def check_browser_storage():
    """Vérifie si on peut trouver le token via le navigateur"""
    print("\n🌐 Alternative: Extraction via navigateur")
    print("Ouvrez les outils de développement dans Windsurf et exécutez:")
    print("""
// Dans la console du navigateur dans Windsurf
console.log('Token check:');
console.log(localStorage.getItem('windsurf_token'));
console.log(sessionStorage.getItem('windsurf_token'));
console.log(document.cookie);

// Chercher dans les variables globales
console.log(window.windsurfToken);
console.log(window.codeiumToken);
""")

def manual_instructions():
    """Instructions pour recherche manuelle"""
    print("\n🔧 Instructions manuelles:")
    print("1. Ouvrez Windsurf")
    print("2. Allez dans les paramètres (Settings)")
    print("3. Cherchez 'Account' ou 'Authentication'")
    print("4. Regardez dans les outils de développement (F12)")
    print("5. Cherchez dans Network les requêtes vers windsurf.com")
    print("6. Cherchez 'access_token' dans les en-têtes ou réponses")

if __name__ == "__main__":
    print("🌊 Recherche Manuelle du Token Windsurf OAuth")
    print("=" * 50)
    
    # Recherche automatique
    search_windsurf_token()
    
    # Instructions alternatives
    check_browser_storage()
    manual_instructions()
    
    print("\n📋 Prochaines étapes:")
    print("1. Si un token est trouvé, testez avec: python test_windsurf_integration.py")
    print("2. Sinon, suivez les instructions manuelles")
    print("3. Ou utilisez la méthode du navigateur")
