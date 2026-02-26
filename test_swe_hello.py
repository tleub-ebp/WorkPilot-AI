#!/usr/bin/env python3
"""
Test du modèle SWE-1.5 via MCP Windsurf
"""

import asyncio
import sys
import os

# Ajouter le répertoire courant au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from windsurf_mcp_server import WindsurfMCPServer

async def test_swe_model():
    """Test du modèle SWE-1.5"""
    print("🔧 Test du modèle SWE-1.5 (Software Engineering Agent)")
    print("=" * 60)
    
    # Créer le serveur MCP et charger le token
    server = WindsurfMCPServer()
    
    # Charger le token OAuth depuis .env.windsurf
    if os.path.exists(".env.windsurf"):
        with open(".env.windsurf", "r") as f:
            for line in f:
                if line.startswith("WINDSURF_OAUTH_TOKEN="):
                    oauth_token = line.split("=", 1)[1].strip()
                    server.oauth_token = oauth_token
                    print(f"✅ Token OAuth chargé ({len(oauth_token)} caractères)")
                    break
    
    if not server.oauth_token:
        print("❌ Token OAuth non trouvé dans .env.windsurf")
        return None
    
    # Test avec SWE-1.5
    print("\n📝 Envoi de la requête 'hello' au modèle SWE-1.5...")
    
    try:
        chat_args = {
            "prompt": "Dis-moi 'hello' en français en tant qu'agent d'ingénierie logicielle",
            "model": "swe-1.5"
        }
        
        result = await server._windsurf_chat(chat_args)
        response = result.content[0].text
        
        print(f"✅ Réponse du modèle SWE-1.5:")
        print(f"📖 {response}")
        
        return response
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None

if __name__ == "__main__":
    asyncio.run(test_swe_model())
