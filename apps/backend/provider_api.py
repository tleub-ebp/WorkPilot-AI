# IMPORTANT : La liste des providers LLM doit être centralisée dans configured_providers.json à la racine du projet.
# Ce fichier est la source unique de vérité pour le frontend ET le backend.
# Toute modification doit être faite dans ce fichier uniquement.

import logging
import sys
logging.basicConfig(level=logging.INFO, stream=sys.stdout, force=True)

from fastapi import FastAPI, Query, HTTPException, Path, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import os
import sys
import json
import requests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.connectors.llm_discovery import get_provider_by_name
from src.connectors.llm_config import (
    save_provider_config, load_provider_config, delete_provider_config, list_provider_configs,
    force_claude_provider_config
)
from validated_keys_db import set_validated, is_validated

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

selected_provider = None  # Variable globale pour stocker le provider sélectionné

def get_env_provider_config(name: str) -> dict | None:
    if name == "claude":
        token = os.getenv("ANTHROPIC_API_KEY")
        if not token:
            from src.connectors.llm_config import get_claude_token_from_system
            token = get_claude_token_from_system()
        if token:
            return {"api_key": token, "model": "opus-4.6"}
        return None
    if name == "openai" and os.getenv("OPENAI_API_KEY"):
        return {"api_key": os.getenv("OPENAI_API_KEY"), "model": "gpt-5.2"}
    if name == "ollama" and os.getenv("OLLAMA_BASE_URL"):
        return {"model": "llama3", "base_url": os.getenv("OLLAMA_BASE_URL")}
    if name == "google" and os.getenv("GOOGLE_API_KEY"):
        return {"api_key": os.getenv("GOOGLE_API_KEY"), "model": "gemini-3.0"}
    return None

# Correction de la détection dynamique : n'afficher que les providers réellement implémentés
@app.get("/providers")
def get_providers():
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../configured_providers.json'))
    if not os.path.exists(config_path):
        providers = [
            {"name": "anthropic", "label": "Anthropic (Claude)", "description": "Claude, focalisé sur la sécurité et l’IA d’entreprise."},
            {"name": "openai", "label": "OpenAI", "description": "Créateur de la série GPT (ChatGPT, GPT-4/4o/5)."},
            {"name": "google", "label": "Google / Google DeepMind", "description": "Modèles Gemini (successeur de PaLM/LaMDA)."},
            {"name": "meta", "label": "Meta (Facebook/Meta AI)", "description": "Modèles LLaMA et variantes open source."},
            {"name": "mistral", "label": "Mistral AI", "description": "Startup française, LLM open weight et commercial."},
            {"name": "deepseek", "label": "DeepSeek", "description": "Entreprise chinoise, agent conversationnel."},
            {"name": "aws", "label": "Amazon Web Services (AWS)", "description": "Offre des API LLM intégrées à ses services cloud."},
            {"name": "ollama", "label": "LLM local (Ollama, LM Studio, etc.)", "description": "Exécutez un modèle LLM localement sur votre machine (Ollama, LM Studio, etc.)."}
        ]
        status = {}
        for p in providers:
            name = p["name"]
            config = None
            # print(f"DEBUG: provider={name} tentative fichier: fichier absent")
            config = get_env_provider_config(name)
            # print(f"DEBUG: provider={name} tentative env: config={config}")
            if name == "anthropic" or name == "claude":
                token = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_CODE_OAUTH_TOKEN") or os.getenv("CLAUDE_API_KEY")
                if not token:
                    from src.connectors.llm_config import get_claude_token_from_system
                    token = get_claude_token_from_system()
                status[name] = bool(token)
                # print(f"DEBUG: provider={name} status OAuth/API={status[name]}")
            else:
                status[name] = bool(config and (config.get("api_key") or config.get("base_url")))
                # print(f"DEBUG: provider={name} status final={status[name]}")
        return {"providers": providers, "status": status}
    # Si le fichier existe, on garde la logique mixte
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    providers = data.get("providers", [])
    from src.connectors.llm_config import load_all_provider_configs
    all_configs = load_all_provider_configs()
    status = {}
    for p in providers:
        name = p["name"]
        provider_configs = [cfg for pname, cfg in all_configs.items() if pname == name]
        has_valid_key = any(cfg.get("api_key") for cfg in provider_configs if cfg.get("api_key"))
        has_oauth_token = any(cfg.get("oauth_token") for cfg in provider_configs if cfg.get("oauth_token"))
        if name == "anthropic" or name == "claude":
            token = os.getenv("ANTHROPIC_API_KEY")
            if not token:
                from src.connectors.llm_config import get_claude_token_from_system
                token = get_claude_token_from_system()
            status[name] = bool(token) or has_valid_key or has_oauth_token
            # print(f"DEBUG: provider={name} status OAuth/API={status[name]}")
        else:
            env_key = os.getenv(f"{name.upper()}_API_KEY")
            has_valid_key = any(cfg.get("api_key") and str(cfg.get("api_key")).strip() != "" for cfg in provider_configs)
            api_key = None
            for cfg in provider_configs:
                if cfg.get("api_key") and str(cfg.get("api_key")).strip() != "":
                    api_key = cfg.get("api_key")
                    break
            is_valid = False
            if api_key:
                # print(f"[DEBUG] provider={name} api_key (masked)={api_key[:6]}...{api_key[-4:]}")
                is_valid = is_validated(name, api_key)
            # print(f"DEBUG: provider={name} provider_configs={provider_configs}")
            # print(f"DEBUG: provider={name} has_valid_key={has_valid_key} is_validated={is_valid} env_key={env_key}")
            status[name] = is_valid or (env_key is not None and env_key.strip() != "")
            # print(f"DEBUG: provider={name} status final={status[name]}")
    return {"providers": providers, "status": status}

@app.get("/providers/configs")
def get_provider_configs():
    return {"configs": list_provider_configs()}

@app.get("/providers/config/{provider}")
def get_provider_config(provider: str):
    config = load_provider_config(provider) or get_env_provider_config(provider)
    if not config:
        raise HTTPException(status_code=404, detail="Provider config not found")
    return config

@app.post("/providers/config/{provider}")
def set_provider_config(provider: str, config: Dict[str, Any]):
    save_provider_config(provider, config)
    return {"status": "ok"}

@app.delete("/providers/config/{provider}")
def delete_provider_config_api(provider: str):
    delete_provider_config(provider)
    return {"status": "deleted"}

@app.post("/providers/select")
def select_provider(provider: str = Query(...)):
    global selected_provider
    selected_provider = provider
    return {"selected": provider}

def get_selected_provider():
    global selected_provider
    return selected_provider

@app.post("/providers/test/{provider}")
def test_provider(provider: str):
    config = load_provider_config(provider)
    if not config:
        raise HTTPException(status_code=404, detail="Provider config not found")
    provider_cls = get_provider_by_name(provider)
    if not provider_cls:
        raise HTTPException(status_code=404, detail="Provider class not found")
    try:
        instance = provider_cls(**config)
        instance.connect()
        if not instance.validate():
            raise Exception("Validation failed")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Provider test failed: {e}")

@app.post("/providers/test/{provider}")
def test_provider_api_key(provider: str, payload: dict):
    api_key = payload.get("api_key")
    base_url = payload.get("base_url")
    print(f"[TEST] provider={provider} api_key (masked)={api_key[:6]}...{api_key[-4:]}", flush=True)
    from validated_keys_db import hash_key
    print(f"[TEST] hash_key: {hash_key(api_key)}", flush=True)
    if provider == "openai":
        try:
            import requests
            url = (base_url or "https://api.openai.com") + "/v1/models"
            headers = {"Authorization": f"Bearer {api_key}"}
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                set_validated(provider, api_key, True)
                print(f"[TEST] set_validated: provider={provider}, api_key (masked)={api_key[:6]}...{api_key[-4:]}, validated=True", flush=True)
                return {"success": True}
            set_validated(provider, api_key, False)
            print(f"[TEST] set_validated: provider={provider}, api_key (masked)={api_key[:6]}...{api_key[-4:]}, validated=False", flush=True)
            return {"success": False, "error": resp.text}
        except Exception as e:
            set_validated(provider, api_key, False)
            print(f"[TEST] set_validated: provider={provider}, api_key (masked)={api_key[:6]}...{api_key[-4:]}, validated=False, error={e}", flush=True)
            return {"success": False, "error": str(e)}
    # Ajoute ici d’autres providers si besoin
    return {"success": False, "error": "Provider non supporté pour le test"}

@app.get("/providers/capabilities/{provider}")
def get_provider_capabilities(provider: str):
    provider_cls = get_provider_by_name(provider)
    if not provider_cls:
        return {"error": "Provider not found"}
    from src.connectors.llm_config import load_provider_config
    config = load_provider_config(provider) or get_env_provider_config(provider) or {}
    try:
        instance = provider_cls(**config)
        instance.connect()
        return instance.get_capabilities()
    except Exception as e:
        return {"error": str(e)}

@app.get("/providers/schema/{provider}")
def get_provider_schema(provider: str):
    provider_cls = get_provider_by_name(provider)
    if not provider_cls:
        return {"error": "Provider not found"}
    from src.connectors.llm_config import load_provider_config
    config = load_provider_config(provider) or get_env_provider_config(provider) or {}
    try:
        instance = provider_cls(**config)
        return instance.get_config_schema()
    except Exception as e:
        return {"error": str(e)}

@app.post("/providers/generate/{provider}")
def generate_with_provider(provider: str, payload: Dict[str, Any]):
    provider_cls = get_provider_by_name(provider)
    if not provider_cls:
        raise HTTPException(status_code=404, detail="Provider class not found")
    config = load_provider_config(provider)
    if not config:
        raise HTTPException(status_code=404, detail="Provider config not found")
    prompt = payload.get("prompt")
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")
    try:
        instance = provider_cls(**config)
        instance.connect()
        result = instance.generate(prompt, **payload.get("params", {}))
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Generation failed: {e}")

@app.post("/providers/force_claude_config")
def force_claude_config():
    force_claude_provider_config()
    return {"status": "ok"}

@app.get("/ping")
def ping():
    return {"pong": True}

@app.get("/providers/models/{provider}")
def get_provider_models(provider: str = Path(..., description="Nom du provider LLM (ex: claude, anthropic, openai, etc.)")):
    print(f"DEBUG: /providers/models/{provider} called", flush=True)
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return {"models": [], "provider": provider, "error": "Clé API OpenAI manquante."}
        try:
            headers = {"Authorization": f"Bearer {api_key}"}
            resp = requests.get("https://api.openai.com/v1/models", headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            models = [m["id"] for m in data.get("data", [])]
            return {"models": models, "provider": provider}
        except Exception as e:
            return {"models": [], "provider": provider, "error": str(e)}
    if provider == "anthropic" or provider == "claude":
        api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
        if not api_key:
            return {"models": [], "provider": provider, "error": "Clé API Anthropic manquante."}
        try:
            headers = {"x-api-key": api_key}
            resp = requests.get("https://api.anthropic.com/v1/models", headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            models = data.get("models", [])
            return {"models": models, "provider": provider}
        except Exception as e:
            # Fallback sur liste statique
            claude_models = [
                "claude-opus-4-5-20251101",
                "claude-sonnet-4-5-20250929",
                "claude-haiku-4-5-20251001",
                "claude-opus-4-6"
            ]
            return {"models": claude_models, "provider": provider, "error": str(e)}
    # Fallback pour les autres providers
    return {"models": [], "provider": provider, "error": f"Provider '{provider}' non supporté pour la récupération des modèles."}

@app.post("/providers/validate/{provider}")
def validate_provider_key(provider: str, api_key: str = Body(..., embed=True)):
    set_validated(provider, api_key, True)
    return {"status": "validated"}

@app.get("/db/health")
def db_health():
    try:
        from validated_keys_db import get_db
        conn = get_db()
        cur = conn.execute("SELECT 1")
        cur.fetchone()
        conn.close()
        return {"db_up": True}
    except Exception as e:
        return {"db_up": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    port = int(os.getenv("BACKEND_PORT", 9000))
    uvicorn.run("provider_api:app", host="0.0.0.0", port=port, reload=True)