import asyncio
import httpx
import json

class RealWindsurfMCPChecker:
    def __init__(self, oauth_token):
        self.oauth_token = oauth_token
        self.base_url = "https://windsurf.com/api"
        self.headers = {
            "Authorization": f"Bearer {oauth_token}",
            "Content-Type": "application/json"
        }
    
    async def check_real_access(self):
        """Vérifie l'accès réel aux modèles via API chat"""
        print("🔍 Vérification accès réel aux modèles Windsurf...")
        
        # Test des modèles payants un par un
        models_to_test = [
            {"id": "premier", "name": "Windsurf Premier", "expected_access": "paid"},
            {"id": "gpt-4o", "name": "GPT-4o", "expected_access": "paid"},
            {"id": "claude-3.5-sonnet", "name": "Claude 3.5 Sonnet", "expected_access": "paid"},
            {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro", "expected_access": "paid"},
            {"id": "base", "name": "Windsurf Base", "expected_access": "free"},
            {"id": "llama-3.1-70b", "name": "Llama 3.1 70B", "expected_access": "free"}
        ]
        
        accessible_models = {}
        
        for model in models_to_test:
            try:
                async with httpx.AsyncClient() as client:
                    # Test simple avec chaque modèle
                    payload = {
                        "model": model["id"],
                        "messages": [{"role": "user", "content": "test"}],
                        "max_tokens": 1
                    }
                    
                    response = await client.post(
                        f"{self.base_url}/chat",
                        headers=self.headers,
                        json=payload,
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        accessible_models[model["id"]] = {
                            "name": model["name"],
                            "access": model["expected_access"],
                            "status": "accessible",
                            "capabilities": self._get_model_capabilities(model["id"])
                        }
                        print(f"✅ {model['name']} - ACCESSIBLE")
                    elif response.status_code == 403:
                        accessible_models[model["id"]] = {
                            "name": model["name"],
                            "access": model["expected_access"],
                            "status": "forbidden",
                            "capabilities": []
                        }
                        print(f"❌ {model['name']} - INTERDIT")
                    else:
                        print(f"⚠️ {model['name']} - Erreur {response.status_code}")
                        
            except Exception as e:
                print(f"❌ {model['name']} - Exception: {str(e)[:50]}...")
        
        return accessible_models
    
    def _get_model_capabilities(self, model_id):
        """Retourne les capacités basiques selon le modèle"""
        capabilities_map = {
            "premier": ["chat", "code", "reasoning", "advanced"],
            "gpt-4o": ["chat", "code", "vision"],
            "claude-3.5-sonnet": ["chat", "code", "analysis"],
            "gemini-1.5-pro": ["chat", "code", "multimodal"],
            "base": ["chat", "code", "reasoning"],
            "llama-3.1-70b": ["chat", "code"]
        }
        return capabilities_map.get(model_id, ["chat"])

async def main():
    oauth_token = os.getenv('WINDSURF_OAUTH_TOKEN', 'REDACTED_FOR_SECURITY')
    
    checker = RealWindsurfMCPChecker(oauth_token)
    accessible_models = await checker.check_real_access()
    
    print(f"\n🎯 RÉSULTATS - {len(accessible_models)} modèles accessibles:")
    print(json.dumps(accessible_models, indent=2))
    
    # Compter les modèles par type
    accessible_paid = [k for k, v in accessible_models.items() if v["access"] == "paid" and v["status"] == "accessible"]
    accessible_free = [k for k, v in accessible_models.items() if v["access"] == "free" and v["status"] == "accessible"]
    
    print("\n📊 Votre accès réel:")
    print(f"  💳 Modèles payants accessibles: {len(accessible_paid)}")
    if accessible_paid:
        print(f"     🎉 {', '.join(accessible_paid)}")
    print(f"  🆓 Modèles gratuits accessibles: {len(accessible_free)}")
    if accessible_free:
        print(f"     ✨ {', '.join(accessible_free)}")

if __name__ == "__main__":
    asyncio.run(main())
