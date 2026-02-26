#!/usr/bin/env python3
"""
Test du provider Windsurf avec clé API
"""

import os
import sys

# Ajouter le répertoire courant au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_windsurf_provider():
    """Test du provider Windsurf"""
    print("🧪 Test du provider Windsurf avec clé API")
    print("=" * 50)
    
    # Charger les variables d'environnement depuis .env.windsurf
    if os.path.exists(".env.windsurf"):
        with open(".env.windsurf", "r") as f:
            for line in f:
                if line.startswith("WINDSURF_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
                    os.environ["WINDSURF_API_KEY"] = api_key
                    print(f"✅ Clé API chargée: {api_key[:20]}...")
                elif line.startswith("WINDSURF_OAUTH_TOKEN="):
                    oauth_token = line.split("=", 1)[1].strip()
                    os.environ["WINDSURF_OAUTH_TOKEN"] = oauth_token
                    print(f"✅ Token OAuth chargé: {oauth_token[:20]}...")
    
    # Importer le registry
    try:
        from apps.backend.services.provider_registry import provider_registry
        
        # Vérifier le statut du provider Windsurf
        status = provider_registry.check_provider_status('windsurf')
        
        print(f"\n📊 Statut du provider Windsurf:")
        print(f"   • Available: {status.available}")
        print(f"   • Authenticated: {status.authenticated}")
        if status.error:
            print(f"   • Error: {status.error}")
        
        # Lister les modèles
        provider = provider_registry.get_provider('windsurf')
        if provider:
            print(f"\n📋 Modèles disponibles ({len(provider.models)}):")
            for model in provider.models:
                print(f"   • {model['label']} ({model['tier']})")
        
        return status.authenticated
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

if __name__ == "__main__":
    success = test_windsurf_provider()
    if success:
        print("\n✅ Provider Windsurf configuré et fonctionnel !")
    else:
        print("\n❌ Provider Windsurf non configuré")
