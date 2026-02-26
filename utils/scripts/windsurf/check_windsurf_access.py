import asyncio
import httpx
import json
import os

async def check_windsurf_real_access():
    """Vérifie l'accès réel aux modèles Windsurf via API"""
    
    # Votre token OAuth
    oauth_token = "REDACTED_WINDSURF_TOKEN"
    
    print("🔍 Vérification de votre accès Windsurf entreprise...")
    
    # Test 1: Vérifier le statut du token
    print("\n1️⃣ Test du token OAuth...")
    try:
        async with httpx.AsyncClient() as client:
            # Essayer de vérifier le token
            headers = {"Authorization": f"Bearer {oauth_token}"}
            
            # Test sur l'API Windsurf
            response = await client.get(
                "https://server.codeium.com/api/v1/user",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                user_info = response.json()
                print(f"✅ Token valide !")
                print(f"👤 User: {user_info.get('email', 'N/A')}")
                print(f"🏢 Plan: {user_info.get('plan', 'N/A')}")
                print(f"📊 Permissions: {list(user_info.get('permissions', []))}")
            else:
                print(f"❌ Erreur token: {response.status_code}")
                print(f"Response: {response.text}")
                
    except Exception as e:
        print(f"❌ Erreur API: {e}")
    
    # Test 2: Essayer de lister les modèles via différentes APIs
    print("\n2️⃣ Test des endpoints modèles...")
    
    endpoints_to_test = [
        "https://server.codeium.com/api/v1/models",
        "https://windsurf.com/api/models",
        "https://api.windsurf.ai/v1/models",
        "https://server.codeium.com/api/v1/chat/models"
    ]
    
    for endpoint in endpoints_to_test:
        try:
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {oauth_token}"}
                response = await client.get(endpoint, headers=headers, timeout=10)
                
                print(f"\n📍 {endpoint}")
                print(f"   Status: {response.status_code}")
                
                if response.status_code == 200:
                    models = response.json()
                    if isinstance(models, dict) and 'data' in models:
                        model_count = len(models['data'])
                        model_names = [m.get('id', m.get('name', 'N/A')) for m in models['data'][:5]]
                        print(f"   ✅ {model_count} modèles trouvés")
                        print(f"   📝 Exemples: {model_names}")
                    elif isinstance(models, list):
                        print(f"   ✅ {len(models)} modèles trouvés")
                        print(f"   📝 Exemples: {models[:3]}")
                    else:
                        print(f"   ✅ Réponse: {str(models)[:100]}...")
                else:
                    print(f"   ❌ Erreur: {response.text[:100]}")
                    
        except Exception as e:
            print(f"   ❌ Exception: {str(e)[:50]}...")
    
    # Test 3: Essayer un chat simple
    print("\n3️⃣ Test d'accès chat...")
    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {oauth_token}", "Content-Type": "application/json"}
            
            chat_payload = {
                "model": "premier",  # Essayer le modèle payant
                "messages": [{"role": "user", "content": "Hello, test message"}],
                "max_tokens": 10
            }
            
            # Essayer différents endpoints chat
            chat_endpoints = [
                "https://server.codeium.com/api/v1/chat",
                "https://windsurf.com/api/chat",
                "https://api.windsurf.ai/v1/chat"
            ]
            
            for endpoint in chat_endpoints:
                try:
                    response = await client.post(endpoint, headers=headers, json=chat_payload, timeout=10)
                    print(f"\n💬 Chat test - {endpoint}")
                    print(f"   Status: {response.status_code}")
                    
                    if response.status_code == 200:
                        print("   ✅ Accès chat confirmé !")
                        break
                    else:
                        print(f"   ❌ Erreur: {response.text[:100]}")
                        
                except Exception as e:
                    print(f"   ❌ Exception: {str(e)[:50]}...")
                    
    except Exception as e:
        print(f"❌ Erreur chat test: {e}")

if __name__ == "__main__":
    asyncio.run(check_windsurf_real_access())
