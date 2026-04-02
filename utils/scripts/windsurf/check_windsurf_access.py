import asyncio
import httpx
import json
import os

async def check_windsurf_real_access():
    """Vérifie l'accès réel aux modèles Windsurf via API"""
    
    oauth_token = "REDACTED_WINDSURF_TOKEN"
    
    print("🔍 Vérification de votre accès Windsurf entreprise...")
    
    await _check_oauth_token(oauth_token)
    await _test_model_endpoints(oauth_token)
    await _test_chat_access(oauth_token)


async def _check_oauth_token(oauth_token: str) -> None:
    """Vérifie la validité du token OAuth"""
    print("\n1️⃣ Test du token OAuth...")
    
    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {oauth_token}"}
            response = await client.get(
                "https://server.codeium.com/api/v1/user",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                user_info = response.json()
                print("✅ Token valide !")
                print(f"👤 User: {user_info.get('email', 'N/A')}")
                print(f"🏢 Plan: {user_info.get('plan', 'N/A')}")
                print(f"📊 Permissions: {list(user_info.get('permissions', []))}")
            else:
                print(f"❌ Erreur token: {response.status_code}")
                print(f"Response: {response.text}")
                
    except Exception as e:
        print(f"❌ Erreur API: {e}")


async def _test_model_endpoints(oauth_token: str) -> None:
    """Test différents endpoints pour lister les modèles"""
    print("\n2️⃣ Test des endpoints modèles...")
    
    endpoints_to_test = [
        "https://server.codeium.com/api/v1/models",
        "https://windsurf.com/api/models",
        "https://api.windsurf.ai/v1/models",
        "https://server.codeium.com/api/v1/chat/models"
    ]
    
    for endpoint in endpoints_to_test:
        await _test_single_model_endpoint(endpoint, oauth_token)


async def _test_single_model_endpoint(endpoint: str, oauth_token: str) -> None:
    """Test un seul endpoint de modèles"""
    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {oauth_token}"}
            response = await client.get(endpoint, headers=headers, timeout=10)
            
            print(f"\n📍 {endpoint}")
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                _handle_successful_model_response(response)
            else:
                print(f"   ❌ Erreur: {response.text[:100]}")
                
    except Exception as e:
        print(f"   ❌ Exception: {str(e)[:50]}...")


def _handle_successful_model_response(response) -> None:
    """Gère une réponse réussie de l'endpoint modèle"""
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


async def _test_chat_access(oauth_token: str) -> None:
    """Test l'accès aux endpoints de chat"""
    print("\n3️⃣ Test d'accès chat...")
    
    try:
        headers = {"Authorization": f"Bearer {oauth_token}", "Content-Type": "application/json"}
        
        chat_payload = {
            "model": "premier",
            "messages": [{"role": "user", "content": "Hello, test message"}],
            "max_tokens": 10
        }
        
        chat_endpoints = [
            "https://server.codeium.com/api/v1/chat",
            "https://windsurf.com/api/chat",
            "https://api.windsurf.ai/v1/chat"
        ]
        
        await _test_chat_endpoints(chat_endpoints, headers, chat_payload)
                    
    except Exception as e:
        print(f"❌ Erreur chat test: {e}")


async def _test_chat_endpoints(chat_endpoints: list, headers: dict, chat_payload: dict) -> None:
    """Test les différents endpoints de chat"""
    async with httpx.AsyncClient() as client:
        for endpoint in chat_endpoints:
            if await _test_single_chat_endpoint(client, endpoint, headers, chat_payload):
                break


async def _test_single_chat_endpoint(client, endpoint: str, headers: dict, chat_payload: dict) -> bool:
    """Test un seul endpoint de chat, retourne True si succès"""
    try:
        response = await client.post(endpoint, headers=headers, json=chat_payload, timeout=10)
        print(f"\n💬 Chat test - {endpoint}")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✅ Accès chat confirmé !")
            return True
        else:
            print(f"   ❌ Erreur: {response.text[:100]}")
            
    except Exception as e:
        print(f"   ❌ Exception: {str(e)[:50]}...")
    
    return False

if __name__ == "__main__":
    asyncio.run(check_windsurf_real_access())
