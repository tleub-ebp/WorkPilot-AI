# IMPORTANT : La liste des providers LLM doit être centralisée dans configured_providers.json à la racine du projet.
# Ce fichier est la source unique de vérité pour le frontend ET le backend.
# Toute modification doit être faite dans ce fichier uniquement.

import logging
import sys
import asyncio
from contextlib import asynccontextmanager
logging.basicConfig(level=logging.INFO, stream=sys.stdout, force=True)

from contextvars import ContextVar
from fastapi import FastAPI, Query, HTTPException, Path, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from typing import Dict, Any, Optional
import os
import json
import httpx
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from security.secure_subprocess import run_secure, SubprocessSecurityError

from src.connectors.llm_discovery import get_provider_by_name
from src.connectors.llm_config import (
    save_provider_config, load_provider_config, delete_provider_config, list_provider_configs,
    force_claude_provider_config
)
from validated_keys_db import set_validated, is_validated

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start/stop the streaming WebSocket server alongside uvicorn."""
    streaming_task = None
    try:
        from streaming import start_streaming_server, stop_streaming_server
        streaming_task = asyncio.create_task(start_streaming_server())
        logging.getLogger(__name__).info("Streaming WebSocket server starting on ws://localhost:8765")
    except Exception as e:
        logging.getLogger(__name__).warning(f"Could not start streaming server: {e}")
    
    # Initialize analytics database
    try:
        from analytics import init_database
        init_database()
        logging.getLogger(__name__).info("Analytics database initialized")
    except Exception as e:
        logging.getLogger(__name__).warning(f"Could not initialize analytics database: {e}")
    
    yield
    try:
        from streaming import stop_streaming_server
        await stop_streaming_server()
    except Exception:
        pass

app = FastAPI(lifespan=lifespan)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_ALLOWED_ORIGINS = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "app://.",               # Electron custom protocol
    "file://",               # Electron file:// protocol
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variable to store selected provider (ContextVar doesn't work across HTTP requests)
_selected_provider: Optional[str] = None

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
    if name == "grok" and os.getenv("GROK_API_KEY"):
        return {"api_key": os.getenv("GROK_API_KEY"), "model": "grok-2"}
    if name == "copilot":
        # Pour Copilot, on vérifie juste l'authentification via gh CLI
        try:
            result = run_secure(["gh", "auth", "status"], timeout=10)
            if "Logged in to github.com" in result.output:
                copilot_check = run_secure(["gh", "copilot", "--version"], timeout=5)
                if copilot_check.success:
                    return {"authenticated": True, "model": "copilot"}
            return None
        except (SubprocessSecurityError, Exception):
            return None
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
                is_valid = is_validated(name, api_key)
            # Cas spécial pour Copilot : vérifier l'authentification gh CLI
            if name == "copilot":
                try:
                    result = run_secure(["gh", "auth", "status"], timeout=10)
                    if "Logged in to github.com" in result.output:
                        copilot_check = run_secure(["gh", "copilot", "--version"], timeout=5)
                        status[name] = copilot_check.success
                    else:
                        status[name] = False
                except (SubprocessSecurityError, Exception):
                    status[name] = False
            else:
                status[name] = is_valid or (env_key is not None and env_key.strip() != "")
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
    global _selected_provider
    _selected_provider = provider
    return {"selected": provider}

@app.get("/providers/selected")
def get_selected_provider_endpoint():
    """Get the currently selected provider."""
    return {"selected": get_selected_provider()}

def get_selected_provider() -> Optional[str]:
    global _selected_provider
    return _selected_provider

@app.post("/providers/test/{provider}")
@limiter.limit("5/minute")
def test_provider(request: Request, provider: str):
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

@app.post("/providers/test-key/{provider}")
@limiter.limit("5/minute")
async def test_provider_api_key(request: Request, provider: str, payload: dict):
    api_key = payload.get("api_key")
    base_url = payload.get("base_url")
    if provider == "openai":
        try:
            url = (base_url or "https://api.openai.com") + "/v1/models"
            headers = {"Authorization": f"Bearer {api_key}"}
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                set_validated(provider, api_key, True)
                return {"success": True}
            set_validated(provider, api_key, False)
            return {"success": False, "error": resp.text}
        except Exception as e:
            set_validated(provider, api_key, False)
            return {"success": False, "error": str(e)}
    elif provider == "grok":
        try:
            url = "https://api.x.ai/v1/models"
            headers = {"Authorization": f"Bearer {api_key}"}
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                set_validated(provider, api_key, True)
                return {"success": True}
            set_validated(provider, api_key, False)
            return {"success": False, "error": resp.text}
        except Exception as e:
            set_validated(provider, api_key, False)
            return {"success": False, "error": str(e)}
    # Ajoute ici d'autres providers si besoin
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
@limiter.limit("30/minute")
def generate_with_provider(request: Request, provider: str, payload: Dict[str, Any]):
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
async def get_provider_models(provider: str = Path(..., description="Nom du provider LLM (ex: claude, anthropic, openai, etc.)")):
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return {"models": [], "provider": provider, "error": "Clé API OpenAI manquante."}
        try:
            headers = {"Authorization": f"Bearer {api_key}"}
            async with httpx.AsyncClient() as client:
                resp = await client.get("https://api.openai.com/v1/models", headers=headers, timeout=10)
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
            async with httpx.AsyncClient() as client:
                resp = await client.get("https://api.anthropic.com/v1/models", headers=headers, timeout=10)
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
@limiter.limit("5/minute")
async def validate_provider_key(request: Request, provider: str, api_key: str = Body(..., embed=True)):
    """Validate a provider API key by actually testing it before marking as valid."""
    # Actually test the key before marking it as validated
    if provider in ("openai",):
        try:
            url = "https://api.openai.com/v1/models"
            headers = {"Authorization": f"Bearer {api_key}"}
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                set_validated(provider, api_key, False)
                raise HTTPException(status_code=400, detail="API key validation failed: invalid key")
        except httpx.HTTPError as e:
            set_validated(provider, api_key, False)
            raise HTTPException(status_code=400, detail=f"API key validation failed: {e}")
    elif provider in ("grok",):
        try:
            url = "https://api.x.ai/v1/models"
            headers = {"Authorization": f"Bearer {api_key}"}
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                set_validated(provider, api_key, False)
                raise HTTPException(status_code=400, detail="API key validation failed: invalid key")
        except httpx.HTTPError as e:
            set_validated(provider, api_key, False)
            raise HTTPException(status_code=400, detail=f"API key validation failed: {e}")
    elif provider in ("anthropic", "claude"):
        try:
            headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
            async with httpx.AsyncClient() as client:
                resp = await client.get("https://api.anthropic.com/v1/models", headers=headers, timeout=10)
            if resp.status_code not in (200, 403):
                set_validated(provider, api_key, False)
                raise HTTPException(status_code=400, detail="API key validation failed: invalid key")
        except httpx.HTTPError as e:
            set_validated(provider, api_key, False)
            raise HTTPException(status_code=400, detail=f"API key validation failed: {e}")
    elif provider in ("google",):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://generativelanguage.googleapis.com/v1/models?key={api_key}",
                    timeout=10,
                )
            if resp.status_code != 200:
                set_validated(provider, api_key, False)
                raise HTTPException(status_code=400, detail="API key validation failed: invalid key")
        except httpx.HTTPError as e:
            set_validated(provider, api_key, False)
            raise HTTPException(status_code=400, detail=f"API key validation failed: {e}")
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Provider '{provider}' does not support key validation via this endpoint",
        )

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

@app.get("/health")
def health_check():
    """Comprehensive health check returning the status of all subsystems."""
    import time
    import platform
    start = time.monotonic()
    subsystems: Dict[str, Any] = {}

    # 1. Database (validated_keys_db — SQLite)
    try:
        from validated_keys_db import get_db
        conn = get_db()
        conn.execute("SELECT 1").fetchone()
        conn.close()
        subsystems["database"] = {"status": "ok"}
    except Exception as e:
        subsystems["database"] = {"status": "error", "error": str(e)}

    # 2. LLM Providers — quick availability check (env vars / configs)
    provider_status: Dict[str, bool] = {}
    for name in ["anthropic", "openai", "google", "grok", "ollama", "copilot"]:
        try:
            cfg = get_env_provider_config(name)
            provider_status[name] = cfg is not None
        except Exception:
            provider_status[name] = False
    subsystems["providers"] = {"status": "ok", "available": provider_status}

    # 3. Graphiti Memory (optional — only if enabled)
    graphiti_enabled = os.getenv("GRAPHITI_ENABLED", "").lower() == "true"
    if graphiti_enabled:
        try:
            from integrations.graphiti.config import get_graphiti_config
            gconfig = get_graphiti_config()
            subsystems["graphiti_memory"] = {
                "status": "ok",
                "enabled": True,
                "llm_provider": gconfig.llm_provider if hasattr(gconfig, "llm_provider") else "unknown",
                "embedder_provider": gconfig.embedder_provider if hasattr(gconfig, "embedder_provider") else "unknown",
            }
        except Exception as e:
            subsystems["graphiti_memory"] = {"status": "error", "enabled": True, "error": str(e)}
    else:
        subsystems["graphiti_memory"] = {"status": "disabled", "enabled": False}

    # 4. configured_providers.json file
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../configured_providers.json'))
    subsystems["configured_providers_file"] = {"status": "ok" if os.path.exists(config_path) else "missing"}

    # 5. System info
    subsystems["system"] = {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "pid": os.getpid(),
    }

    elapsed_ms = round((time.monotonic() - start) * 1000, 2)
    all_ok = all(
        s.get("status") in ("ok", "disabled")
        for s in subsystems.values()
        if isinstance(s, dict) and "status" in s
    )

    return {
        "status": "healthy" if all_ok else "degraded",
        "response_time_ms": elapsed_ms,
        "subsystems": subsystems,
    }

@app.get("/providers/usage/{provider}")
async def get_provider_usage(provider: str):
    """
    Récupère l'usage et le crédit restant pour le provider OpenAI, Copilot ou autre si implémenté.
    """
    if provider == "openai":
        # NOTE: L'endpoint /v1/usage d'OpenAI ne fonctionne plus avec les clés API standards
        # depuis 2025. Il nécessite des permissions spéciales (api.usage.read) et souvent
        # une clé d'administrateur. Voir : https://community.openai.com/t/how-to-view-billing-via-api/1362751
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return {"error": "Clé API OpenAI manquante."}
        
        # Essai avec l'endpoint alternatif /v1/organization/usage si disponible
        try:
            headers = {"Authorization": f"Bearer {api_key}"}
            async with httpx.AsyncClient() as client:
                # Tentative avec l'endpoint d'organisation (peut aussi nécessiter des permissions spéciales)
                resp = await client.get("https://api.openai.com/v1/organization/usage", headers=headers, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "provider": "openai",
                    "usage": data,
                    "fetched_at": "now",
                    "note": "Données d'usage récupérées avec succès"
                }
            else:
                # Si l'endpoint échoue, retourner un message informatif
                return {
                    "provider": "openai",
                    "error": f"Erreur {resp.status_code}: L'endpoint d'usage OpenAI nécessite des permissions spéciales (api.usage.read) ou une clé d'administrateur. Veuillez vérifier votre dashboard OpenAI pour l'usage actuel.",
                    "status_code": resp.status_code,
                    "alternative": "Consultez https://platform.openai.com/settings/organization/billing/overview"
                }
        except Exception as e:
            return {
                "provider": "openai", 
                "error": f"Impossible de récupérer l'usage OpenAI: {str(e)}",
                "note": "L'endpoint /v1/usage d'OpenAI nécessite des permissions spéciales depuis 2025",
                "alternative": "Consultez https://platform.openai.com/settings/organization/billing/overview"
            }
    elif provider == "copilot":
        try:
            from src.connectors.llm_copilot import get_copilot_usage_metrics
            
            usage_data = get_copilot_usage_metrics()
            
            # Formater les données pour le frontend
            if "error" in usage_data:
                return usage_data
            
            return {
                "provider": "copilot",
                "available": True,
                "usage": {
                    "total_suggestions": usage_data.get("total_suggestions", 0),
                    "total_acceptances": usage_data.get("total_acceptances", 0),
                    "total_lines_suggested": usage_data.get("total_lines_suggested", 0),
                    "total_lines_accepted": usage_data.get("total_lines_accepted", 0),
                    "acceptance_rate_percent": usage_data.get("acceptance_rate_percent", 0),
                    "line_acceptance_rate_percent": usage_data.get("line_acceptance_rate_percent", 0),
                    "total_tokens": usage_data.get("total_tokens", 0),
                    "organization": usage_data.get("organization"),
                    "level": usage_data.get("level", "organization")
                },
                "fetched_at": usage_data.get("fetched_at"),
                "copilotUsageDetails": {
                    "suggestions": usage_data.get("total_suggestions", 0),
                    "acceptances": usage_data.get("total_acceptances", 0),
                    "acceptanceRate": usage_data.get("acceptance_rate_percent", 0),
                    "linesSuggested": usage_data.get("total_lines_suggested", 0),
                    "linesAccepted": usage_data.get("total_lines_accepted", 0),
                    "lineAcceptanceRate": usage_data.get("line_acceptance_rate_percent", 0)
                }
            }
        except ImportError as e:
            return {"error": f"Module Copilot non disponible: {e}"}
        except Exception as e:
            return {"error": f"Erreur lors de la récupération des métriques Copilot: {e}"}
    elif provider == "anthropic" or provider == "claude":
        try:
            from connectors.llm_anthropic_usage import get_anthropic_usage_metrics
            
            usage_data = get_anthropic_usage_metrics()
            
            # Formater les données pour le frontend
            if "error" in usage_data:
                return usage_data
            
            return {
                "provider": "anthropic",
                "available": True,
                "usage": usage_data.get("usage", {}),
                "fetched_at": usage_data.get("fetched_at"),
                "providerName": "anthropic"
            }
        except ImportError as e:
            return {"error": f"Module Anthropic usage non disponible: {e}"}
        except Exception as e:
            return {"error": f"Erreur lors de la récupération des métriques Anthropic: {e}"}
    else:
        return {"error": f"Usage non supporté pour le provider '{provider}'"}

# ---------------------------------------------------------------------------
# Feature API endpoints — Expose backend Python modules to the frontend
# ---------------------------------------------------------------------------

# --- 1.1 Dashboard Metrics ---
@app.get("/api/dashboard/snapshot/{project_id}")
def get_dashboard_snapshot(project_id: str):
    try:
        from scheduling.dashboard_metrics import DashboardMetrics
        dm = DashboardMetrics()
        snapshot = dm.get_snapshot(project_id)
        return {"success": True, "snapshot": snapshot.to_dict() if hasattr(snapshot, 'to_dict') else snapshot.__dict__}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/dashboard/stats")
def get_dashboard_stats():
    try:
        from scheduling.dashboard_metrics import DashboardMetrics
        dm = DashboardMetrics()
        return {"success": True, "stats": dm.get_stats()}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/dashboard/export/{project_id}")
def export_dashboard(project_id: str, fmt: str = "json"):
    try:
        from scheduling.dashboard_metrics import DashboardMetrics
        dm = DashboardMetrics()
        report = dm.export_report(project_id, fmt=fmt)
        return {"success": True, "report": report, "format": fmt}
    except Exception as e:
        return {"success": False, "error": str(e)}

# --- 1.2 Session History ---
@app.get("/api/sessions/{project_id}")
def get_sessions(project_id: str):
    try:
        from agents.session_history import SessionRecorder
        sh = SessionRecorder(project_id=project_id)
        sessions = sh.list_sessions()
        return {"success": True, "sessions": [s.to_dict() if hasattr(s, 'to_dict') else s.__dict__ for s in sessions]}
    except Exception as e:
        return {"success": False, "error": str(e)}

# --- 2.1 Refactoring Agent ---
@app.post("/api/refactoring/detect-smells")
def detect_smells(body: Dict[str, Any] = Body(...)):
    try:
        from agents.refactorer import RefactoringAgent
        agent = RefactoringAgent(thresholds=body.get("thresholds", {}))
        source = body.get("source", "")
        smells = agent.detect_smells_from_source(source)
        return {"success": True, "smells": [s.to_dict() if hasattr(s, 'to_dict') else s.__dict__ for s in smells]}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/refactoring/propose")
def propose_refactoring(body: Dict[str, Any] = Body(...)):
    try:
        from agents.refactorer import RefactoringAgent
        agent = RefactoringAgent(thresholds=body.get("thresholds", {}))
        source = body.get("source", "")
        proposals = agent.propose_refactoring(source=source)
        return {"success": True, "proposals": [p.to_dict() if hasattr(p, 'to_dict') else p.__dict__ for p in proposals]}
    except Exception as e:
        return {"success": False, "error": str(e)}

# --- 2.2 Documentation Agent ---
@app.post("/api/documentation/coverage")
def check_doc_coverage(body: Dict[str, Any] = Body(...)):
    try:
        from agents.documenter import DocumentationAgent, DocFormat
        fmt = body.get("format", "google")
        agent = DocumentationAgent(default_format=DocFormat(fmt))
        file_path = body.get("file_path", "")
        coverage = agent.check_documentation_coverage(file_path=file_path)
        return {"success": True, "coverage": coverage}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/documentation/generate-docstrings")
def generate_docstrings(body: Dict[str, Any] = Body(...)):
    try:
        from agents.documenter import DocumentationAgent, DocFormat
        fmt = body.get("format", "google")
        agent = DocumentationAgent(default_format=DocFormat(fmt))
        file_path = body.get("file_path", "")
        result = agent.generate_docstrings(file_path=file_path)
        return {"success": True, "result": result.to_dict() if hasattr(result, 'to_dict') else result.__dict__}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/documentation/generate-readme")
def generate_readme(body: Dict[str, Any] = Body(...)):
    try:
        from agents.documenter import DocumentationAgent, DocFormat
        fmt = body.get("format", "google")
        agent = DocumentationAgent(default_format=DocFormat(fmt))
        dir_path = body.get("dir_path", "")
        result = agent.generate_module_readme(dir_path)
        return {"success": True, "result": result.to_dict() if hasattr(result, 'to_dict') else result.__dict__}
    except Exception as e:
        return {"success": False, "error": str(e)}

# --- 2.4 Feedback Learning ---
@app.get("/api/feedback/stats/{project_id}")
def get_feedback_stats(project_id: str):
    try:
        from agents.feedback_learning import FeedbackLearning
        fl = FeedbackLearning()
        stats = fl.get_stats(project_id)
        return {"success": True, "stats": stats}
    except Exception as e:
        return {"success": False, "error": str(e)}

# --- 3.2 Task Templates ---
@app.get("/api/templates")
def list_task_templates():
    try:
        from scheduling.task_templates import TemplateManager
        tm = TemplateManager()
        templates = tm.list_templates()
        return {"success": True, "templates": [t.to_dict() if hasattr(t, 'to_dict') else t.__dict__ for t in templates]}
    except Exception as e:
        return {"success": False, "error": str(e)}

# --- 3.3 AI Code Review ---
@app.post("/api/code-review/analyze")
def analyze_code_review(body: Dict[str, Any] = Body(...)):
    try:
        from review.ai_code_review import AICodeReview
        reviewer = AICodeReview()
        diff = body.get("diff", "")
        result = reviewer.review_diff(diff)
        return {"success": True, "review": result.to_dict() if hasattr(result, 'to_dict') else result.__dict__}
    except Exception as e:
        return {"success": False, "error": str(e)}

# --- 6.1 Intelligent Router ---
@app.get("/api/router/config")
def get_router_config():
    try:
        from scheduling.intelligent_router import IntelligentRouter
        router = IntelligentRouter()
        config = router.get_config()
        return {"success": True, "config": config}
    except Exception as e:
        return {"success": False, "error": str(e)}

# --- 6.2 Local Model Manager ---
@app.get("/api/local-models/status")
def get_local_models_status():
    try:
        from scheduling.local_model_manager import LocalModelManager
        mgr = LocalModelManager()
        status = mgr.get_status()
        return {"success": True, "status": status}
    except Exception as e:
        return {"success": False, "error": str(e)}

# --- 6.3 Cost Estimator ---
@app.get("/api/costs/summary/{project_id}")
def get_cost_summary(project_id: str):
    try:
        from scheduling.cost_estimator import CostEstimator
        ce = CostEstimator()
        summary = ce.get_summary(project_id)
        return {"success": True, "summary": summary}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/costs/budget/{project_id}")
def get_cost_budget(project_id: str):
    try:
        from scheduling.cost_estimator import CostEstimator
        ce = CostEstimator()
        budget = ce.get_budget(project_id)
        return {"success": True, "budget": budget}
    except Exception as e:
        return {"success": False, "error": str(e)}

# --- 7.2 Sandbox ---
@app.get("/api/sandbox/status")
def get_sandbox_status():
    try:
        from security.sandbox import SandboxManager
        mgr = SandboxManager()
        status = mgr.get_status()
        return {"success": True, "status": status}
    except Exception as e:
        return {"success": False, "error": str(e)}

# --- 7.3 Anomaly Detector ---
@app.get("/api/anomaly/status")
def get_anomaly_status():
    try:
        from security.anomaly_detector import AnomalyDetector
        detector = AnomalyDetector()
        status = detector.get_status()
        return {"success": True, "status": status}
    except Exception as e:
        return {"success": False, "error": str(e)}

# --- 8.1 Scheduler ---
@app.get("/api/scheduler/jobs")
def get_scheduler_jobs():
    try:
        from scheduling.scheduler import TaskScheduler
        sched = TaskScheduler()
        jobs = sched.list_jobs()
        return {"success": True, "jobs": [j.to_dict() if hasattr(j, 'to_dict') else j.__dict__ for j in jobs]}
    except Exception as e:
        return {"success": False, "error": str(e)}

# --- 8.2 Auto-Detection ---
@app.get("/api/auto-detect/status")
def get_auto_detect_status():
    try:
        from scheduling.auto_detector import AutoDetector
        detector = AutoDetector()
        status = detector.get_status()
        return {"success": True, "status": status}
    except Exception as e:
        return {"success": False, "error": str(e)}

# --- 9.1 GitHub PR Details ---
@app.get("/api/github/pr-details")
def get_pr_details(pr_url: str = Query(...)):
    """Get PR details including files and diffs from GitHub."""
    try:
        from runners.github.providers.github_provider import GitHubProvider
        from runners.github.protocol import PRData
        
        # Extract PR number and repo from URL
        # Expected format: https://github.com/owner/repo/pull/123
        if "github.com" not in pr_url or "/pull/" not in pr_url:
            return {"success": False, "error": "Invalid GitHub PR URL format"}
        
        # Parse URL to get owner, repo, and PR number
        parts = pr_url.strip("/").split("/")
        if len(parts) < 5 or parts[3] != "pull":
            return {"success": False, "error": "Invalid GitHub PR URL format"}
        
        owner = parts[2]
        repo = parts[3]
        pr_number = parts[4]
        
        # Initialize GitHub provider
        provider = GitHubProvider()
        
        # Fetch PR data
        pr_data = provider.fetch_pr(owner, repo, int(pr_number))
        
        if not pr_data:
            return {"success": False, "error": "Failed to fetch PR data"}
        
        # Convert to dict for JSON serialization
        result = {
            "success": True,
            "data": {
                "number": pr_data.number,
                "title": pr_data.title,
                "body": pr_data.body,
                "state": pr_data.state,
                "author": pr_data.author,
                "createdAt": pr_data.created_at,
                "updatedAt": pr_data.updated_at,
                "url": pr_data.url,
                "baseBranch": pr_data.base_branch,
                "headBranch": pr_data.head_branch,
                "mergeable": pr_data.mergeable,
                "additions": pr_data.additions,
                "deletions": pr_data.deletions,
                "changedFiles": pr_data.changed_files,
                "files": pr_data.files,
                "diff": pr_data.diff
            }
        }
        
        return result
        
    except Exception as e:
        return {"success": False, "error": str(e)}


# --- Analytics API ---
from analytics.api_minimal import router as analytics_router
app.include_router(analytics_router)


if __name__ == "__main__":
    import uvicorn
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    port = int(os.getenv("BACKEND_PORT", 9000))
    uvicorn.run("provider_api:app", host="0.0.0.0", port=port, reload=True, reload_excludes=[".venv"])