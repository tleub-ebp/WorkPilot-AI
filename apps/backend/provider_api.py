# IMPORTANT : La liste des providers LLM doit être centralisée dans configured_providers.json à la racine du projet.
# Ce fichier est la source unique de vérité pour le frontend ET le backend.
# Toute modification doit être faite dans ce fichier uniquement.

import logging
import sys
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO, stream=sys.stdout, force=True)

import ipaddress
import json
import os
import socket
from typing import Annotated, Any
from urllib.parse import urlparse

import httpx
from fastapi import Body, FastAPI, HTTPException, Path, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# Import specific exception for provider validation failures
try:
    from integrations.graphiti.providers_pkg.exceptions import ProviderError
except ImportError:
    # Fallback if the module is not available
    class ProviderError(Exception):
        """Raised when a provider cannot be initialized or validated."""

        pass


# Constants
PROVIDER_CONFIG_NOT_FOUND = "Provider config not found"
PROVIDER_CLASS_NOT_FOUND = "Provider class not found"
API_KEY_VALIDATION_FAILED_INVALID = "API key validation failed: invalid key"
API_KEY_VALIDATION_FAILED_ERROR = "API key validation failed: {e}"
HOOK_NOT_FOUND = "Hook not found"
PROMPT_REQUIRED = "Prompt is required"
PROVIDER_TEST_FAILED = "Provider test failed: {e}"
GENERATION_FAILED = "Generation failed: {e}"
TEMPLATE_NOT_FOUND = "Template not found"
GITHUB_CLI_AUTH_SUCCESS = "Logged in to github.com"
API_MODELS_ENDPOINT = "/v1/models"

# SSRF Protection - Authorized URLs list
AUTHORIZED_URLS = {
    "anthropic": "https://api.anthropic.com",
    "openai": "https://api.openai.com",
    "google": "https://generativelanguage.googleapis.com",
    "mistral": "https://api.mistral.ai",
    "deepseek": "https://api.deepseek.com",
    "grok": "https://api.x.ai",
    "meta": "https://api.together.xyz",
    "cursor": "https://api.cursor.com",
    "windsurf": "https://server.codeium.com",
}

# Private IP ranges for SSRF protection
PRIVATE_IP_RANGES = [
    ipaddress.IPv4Network("10.0.0.0/8"),
    ipaddress.IPv4Network("172.16.0.0/12"),
    ipaddress.IPv4Network("192.168.0.0/16"),
    ipaddress.IPv4Network("127.0.0.0/8"),
    ipaddress.IPv4Network("169.254.0.0/16"),
    ipaddress.IPv6Network("::1/128"),
    ipaddress.IPv6Network("fc00::/7"),
    ipaddress.IPv6Network("fe80::/10"),
]


# Lazy import: llm_discovery is only needed by endpoint functions, not at module init.
# Importing it eagerly breaks other modules (agent_runner, client) that import
# provider_api just for get_selected_provider() but don't have src.connectors on sys.path.
def get_provider_by_name(name: str):
    from src.connectors.llm_discovery import (
        get_provider_by_name as _get_provider_by_name,
    )

    return _get_provider_by_name(name)


# Lazy imports for llm_config functions (same reason as llm_discovery above)
def _get_llm_config():
    from src.connectors.llm_config import (
        delete_provider_config,
        force_claude_provider_config,
        list_provider_configs,
        load_provider_config,
        save_provider_config,
    )

    return {
        "save_provider_config": save_provider_config,
        "load_provider_config": load_provider_config,
        "delete_provider_config": delete_provider_config,
        "list_provider_configs": list_provider_configs,
        "force_claude_provider_config": force_claude_provider_config,
    }


def save_provider_config(*args, **kwargs):
    return _get_llm_config()["save_provider_config"](*args, **kwargs)


def load_provider_config(*args, **kwargs):
    return _get_llm_config()["load_provider_config"](*args, **kwargs)


def delete_provider_config(*args, **kwargs):
    return _get_llm_config()["delete_provider_config"](*args, **kwargs)


def list_provider_configs(*args, **kwargs):
    return _get_llm_config()["list_provider_configs"](*args, **kwargs)


def force_claude_provider_config(*args, **kwargs):
    return _get_llm_config()["force_claude_provider_config"](*args, **kwargs)


from apps.backend.validated_keys_db import is_validated, set_validated


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan without WebSocket server to prevent blocking issues."""
    # WebSocket disabled temporarily due to connection issues
    # Updated to websockets v16.0 which resolves handshake problems
    # WebSocket is now handled separately in websocket_server.py

    # Initialize analytics database
    try:
        from analytics import init_database

        init_database()
        logging.getLogger(__name__).info("Analytics database initialized")
    except Exception as e:
        logging.getLogger(__name__).warning(
            f"Could not initialize analytics database: {e}"
        )

    logging.getLogger(__name__).info(
        "Backend started without WebSocket (disabled for stability)"
    )

    yield


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
    "app://.",  # Electron custom protocol
    "file://",  # Electron file:// protocol
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
_selected_provider: str | None = None


def get_env_provider_config(name: str) -> dict | None:
    # Anthropic / Claude
    if name in ("claude", "anthropic"):
        token = os.getenv("ANTHROPIC_API_KEY")
        if not token:
            from src.connectors.llm_config import get_claude_token_from_system

            token = get_claude_token_from_system()
        if token:
            return {"api_key": token, "model": "claude-opus-4-6"}
        return None

    # OpenAI
    if name == "openai" and os.getenv("OPENAI_API_KEY"):
        return {
            "api_key": os.getenv("OPENAI_API_KEY"),
            "model": "gpt-5.2",
            "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        }

    # Google Gemini
    if name == "google" and os.getenv("GOOGLE_API_KEY"):
        return {"api_key": os.getenv("GOOGLE_API_KEY"), "model": "gemini-2.5-pro"}

    # Mistral AI
    if name == "mistral" and os.getenv("MISTRAL_API_KEY"):
        return {
            "api_key": os.getenv("MISTRAL_API_KEY"),
            "model": "mistral-large-2",
            "base_url": os.getenv("MISTRAL_BASE_URL", "https://api.mistral.ai/v1"),
        }

    # DeepSeek
    if name == "deepseek" and os.getenv("DEEPSEEK_API_KEY"):
        return {
            "api_key": os.getenv("DEEPSEEK_API_KEY"),
            "model": "deepseek-r2",
            "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        }

    # Grok (xAI)
    if name == "grok" and os.getenv("GROK_API_KEY"):
        return {"api_key": os.getenv("GROK_API_KEY"), "model": "grok-2"}

    # Meta (LLaMA) — via Together AI or Replicate
    if name == "meta" and os.getenv("META_API_KEY"):
        return {
            "api_key": os.getenv("META_API_KEY"),
            "model": "meta-llama/llama-4-scout",
            "base_url": os.getenv("META_BASE_URL", "https://api.together.xyz/v1"),
        }

    # AWS Bedrock
    if name == "aws":
        access_key = os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        if access_key and secret_key:
            return {
                "api_key": access_key,
                "secret_key": secret_key,
                "region": os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
                "model": "anthropic.claude-opus-4-6-v1",
            }
        return None

    # Ollama (local)
    if name == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        # Vérifier si Ollama est accessible
        try:
            import urllib.request

            req = urllib.request.Request(f"{base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=2):
                return {"model": "llama3.3", "base_url": base_url}
        except Exception:
            pass
        return None

    # GitHub Copilot (gh CLI)
    if name == "copilot":
        try:
            import subprocess

            result = subprocess.run(
                ["gh", "auth", "status"], capture_output=True, text=True, timeout=5
            )
            if GITHUB_CLI_AUTH_SUCCESS in (result.stdout + result.stderr):
                return {"authenticated": True, "model": "gpt-4o"}
        except Exception:
            pass
        return None

    # Windsurf (Codeium)
    if name == "windsurf":
        token = (
            os.getenv("WINDSURF_API_KEY")
            or os.getenv("WINDSURF_OAUTH_TOKEN")
            or os.getenv("CODEIUM_API_KEY")
        )
        if token:
            return {"api_key": token, "model": "swe-1.5"}
        return None

    # Cursor
    if name == "cursor" and os.getenv("CURSOR_API_KEY"):
        return {
            "api_key": os.getenv("CURSOR_API_KEY"),
            "model": "cursor-default",
            "base_url": os.getenv("CURSOR_BASE_URL", "https://api.cursor.com/v1"),
        }

    return None


# Correction de la détection dynamique : n'afficher que les providers réellement implémentés
@app.get("/providers/{provider}/status")
def get_provider_status(provider: str):
    """Get the status of a specific provider."""
    try:
        cfg = get_env_provider_config(provider)
        if cfg is None:
            return {"available": False, "authenticated": False}

        # For Windsurf, check OAuth token specifically
        if provider == "windsurf":
            oauth_token = os.getenv("WINDSURF_OAUTH_TOKEN")
            print(
                f"DEBUG: oauth_token = {oauth_token[:20] if oauth_token else 'None'}..."
            )
            print(
                f"DEBUG: bool check = {bool(oauth_token and oauth_token.strip() != '')}"
            )
            return {
                "available": True,
                "authenticated": bool(oauth_token and oauth_token.strip() != ""),
                "oauth": True,
            }

        return {"available": True, "authenticated": True}
    except Exception as e:
        return {"available": False, "authenticated": False, "error": str(e)}


@app.get("/providers")
def get_providers():
    config_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "../../config/configured_providers.json"
        )
    )
    if not os.path.exists(config_path):
        providers = [
            {
                "name": "anthropic",
                "label": "Anthropic (Claude)",
                "description": "Claude, focalisé sur la sécurité et l’IA d’entreprise.",
            },
            {
                "name": "openai",
                "label": "OpenAI",
                "description": "Créateur de la série GPT (ChatGPT, GPT-4/4o/5).",
            },
            {
                "name": "google",
                "label": "Google / Google DeepMind",
                "description": "Modèles Gemini (successeur de PaLM/LaMDA).",
            },
            {
                "name": "meta",
                "label": "Meta (Facebook/Meta AI)",
                "description": "Modèles LLaMA et variantes open source.",
            },
            {
                "name": "mistral",
                "label": "Mistral AI",
                "description": "Startup française, LLM open weight et commercial.",
            },
            {
                "name": "deepseek",
                "label": "DeepSeek",
                "description": "Entreprise chinoise, agent conversationnel.",
            },
            {
                "name": "aws",
                "label": "Amazon Web Services (AWS)",
                "description": "Offre des API LLM intégrées à ses services cloud.",
            },
            {
                "name": "ollama",
                "label": "LLM local (Ollama, LM Studio, etc.)",
                "description": "Exécutez un modèle LLM localement sur votre machine (Ollama, LM Studio, etc.).",
            },
        ]
        status = {}
        for p in providers:
            name = p["name"]
            config = None
            # print(f"DEBUG: provider={name} tentative fichier: fichier absent")
            config = get_env_provider_config(name)
            # print(f"DEBUG: provider={name} tentative env: config={config}")
            if name == "anthropic" or name == "claude":
                token = (
                    os.getenv("ANTHROPIC_API_KEY")
                    or os.getenv("CLAUDE_CODE_OAUTH_TOKEN")
                    or os.getenv("CLAUDE_API_KEY")
                )
                if not token:
                    from src.connectors.llm_config import get_claude_token_from_system

                    token = get_claude_token_from_system()
                status[name] = bool(token)
                # print(f"DEBUG: provider={name} status OAuth/API={status[name]}")
            else:
                status[name] = bool(
                    config and (config.get("api_key") or config.get("base_url"))
                )
                # print(f"DEBUG: provider={name} status final={status[name]}")
        return {"providers": providers, "status": status}
    # Si le fichier existe, on garde la logique mixte
    with open(config_path, encoding="utf-8") as f:
        data = json.load(f)
    providers = data.get("providers", [])
    from src.connectors.llm_config import load_all_provider_configs

    all_configs = load_all_provider_configs()
    status = {}
    for p in providers:
        name = p["name"]
        provider_configs = [cfg for pname, cfg in all_configs.items() if pname == name]
        has_valid_key = any(
            cfg.get("api_key") for cfg in provider_configs if cfg.get("api_key")
        )
        has_oauth_token = any(
            cfg.get("oauth_token") for cfg in provider_configs if cfg.get("oauth_token")
        )
        if name == "anthropic" or name == "claude":
            token = os.getenv("ANTHROPIC_API_KEY")
            if not token:
                from src.connectors.llm_config import get_claude_token_from_system

                token = get_claude_token_from_system()
            status[name] = bool(token) or has_valid_key or has_oauth_token
            # print(f"DEBUG: provider={name} status OAuth/API={status[name]}")
        else:
            env_key = os.getenv(f"{name.upper()}_API_KEY")
            # For Windsurf, check OAuth token instead of API key
            if name == "windsurf":
                env_key = os.getenv("WINDSURF_OAUTH_TOKEN")
            has_valid_key = any(
                cfg.get("api_key") and str(cfg.get("api_key")).strip() != ""
                for cfg in provider_configs
            )
            # For Windsurf, also check oauth_token
            if name == "windsurf":
                has_valid_key = has_valid_key or any(
                    cfg.get("oauth_token") and str(cfg.get("oauth_token")).strip() != ""
                    for cfg in provider_configs
                )
            api_key = None
            for cfg in provider_configs:
                if cfg.get("api_key") and str(cfg.get("api_key")).strip() != "":
                    api_key = cfg.get("api_key")
                    break
                elif (
                    name == "windsurf"
                    and cfg.get("oauth_token")
                    and str(cfg.get("oauth_token")).strip() != ""
                ):
                    api_key = cfg.get("oauth_token")
                    break
            is_valid = False
            if api_key:
                is_valid = is_validated(name, api_key)
            # Cas spécial pour Copilot : vérifier l'authentification gh CLI
            if name == "copilot":
                try:
                    import subprocess

                    result = subprocess.run(
                        ["gh", "auth", "status"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    status[name] = GITHUB_CLI_AUTH_SUCCESS in (
                        result.stdout + result.stderr
                    )
                except Exception:
                    status[name] = False
            else:
                status[name] = is_valid or (
                    env_key is not None and env_key.strip() != ""
                )
    return {"providers": providers, "status": status}


@app.get("/providers/configs")
def get_provider_configs():
    return {"configs": list_provider_configs()}


@app.get(
    "/providers/config/{provider}",
    responses={404: {"description": PROVIDER_CONFIG_NOT_FOUND}},
)
def get_provider_config(provider: str):
    config = load_provider_config(provider) or get_env_provider_config(provider)
    if not config:
        raise HTTPException(status_code=404, detail=PROVIDER_CONFIG_NOT_FOUND)
    return config


@app.post("/providers/config/{provider}")
def set_provider_config(provider: str, config: dict[str, Any]):
    save_provider_config(provider, config)
    return {"status": "ok"}


@app.delete("/providers/config/{provider}")
def delete_provider_config_api(provider: str):
    delete_provider_config(provider)
    return {"status": "deleted"}


@app.post("/providers/select")
def select_provider(provider: Annotated[str, Query(...)]):
    global _selected_provider
    _selected_provider = provider
    return {"selected": provider}


@app.get("/providers/selected")
def get_selected_provider_endpoint():
    """Get the currently selected provider."""
    return {"selected": get_selected_provider()}


def get_selected_provider() -> str | None:
    global _selected_provider
    return _selected_provider


@app.post(
    "/providers/test/{provider}",
    responses={
        404: {"description": PROVIDER_CONFIG_NOT_FOUND},
        400: {"description": "Provider test failed"},
    },
)
@limiter.limit("5/minute")
def test_provider(request: Request, provider: str):
    config = load_provider_config(provider)
    if not config:
        raise HTTPException(status_code=404, detail=PROVIDER_CONFIG_NOT_FOUND)
    provider_cls = get_provider_by_name(provider)
    if not provider_cls:
        raise HTTPException(status_code=404, detail=PROVIDER_CLASS_NOT_FOUND)
    try:
        instance = provider_cls(**config)
        instance.connect()
        if not instance.validate():
            raise ProviderError("Validation failed")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=PROVIDER_TEST_FAILED.format(e=e))


def validate_url_ssrf(provider: str, url: str) -> str:
    """
    Public wrapper for SSRF URL validation - intended for testing purposes.

    Args:
        provider: Provider name for authorized URL lookup
        url: User-provided URL to validate

    Returns:
        Safe, normalized URL string

    Raises:
        ValueError: If URL is invalid or potentially malicious
    """
    return _validate_url_ssrf(provider, url)


def _validate_url_ssrf(provider: str, url: str) -> str:
    """
    Validate URL against SSRF attacks using authorized URLs list and IP verification.

    Args:
        provider: Provider name for authorized URL lookup
        url: User-provided URL to validate

    Returns:
        Safe, normalized URL string

    Raises:
        ValueError: If URL is invalid or potentially malicious
    """
    if not url:
        raise ValueError("URL cannot be empty")

    try:
        parsed = urlparse(url)
    except Exception as e:
        raise ValueError(f"Invalid URL format: {e}")

    # Check scheme
    if parsed.scheme not in ("https", "http"):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")

    # For HTTPS providers, enforce authorized URLs
    if provider in AUTHORIZED_URLS:
        authorized_url = AUTHORIZED_URLS[provider]
        authorized_parsed = urlparse(authorized_url)

        # Check if hostname matches authorized hostname
        if parsed.hostname != authorized_parsed.hostname:
            raise ValueError(
                f"Hostname {parsed.hostname} is not authorized for provider {provider}"
            )

        # Check if port matches authorized port (if specified)
        if (
            authorized_parsed.port
            and parsed.port
            and parsed.port != authorized_parsed.port
        ):
            raise ValueError(
                f"Port {parsed.port} is not authorized for provider {provider}"
            )

        # Rebuild safe URL with authorized scheme and host
        safe_url = f"{authorized_parsed.scheme}://{authorized_parsed.netloc}"
        return safe_url.rstrip("/")

    # For local providers (like Ollama), perform IP validation
    hostname = parsed.hostname or ""
    if hostname in ("localhost", "127.0.0.1"):
        # Allow localhost for local providers
        safe_url = f"{parsed.scheme}://{hostname}"
        if parsed.port:
            safe_url += f":{parsed.port}"
        return safe_url.rstrip("/")

    # For any other hostname, perform IP address validation
    try:
        # Resolve hostname to IP address
        ip = socket.gethostbyname(hostname)

        # Try to parse as IPv4 first, then IPv6
        try:
            ip_obj = ipaddress.IPv4Address(ip)
        except ipaddress.AddressValueError:
            # For IPv6, we'd need the getaddrinfo instead of gethostbyname
            # For now, we'll be conservative and block unknown hostnames
            raise ValueError(
                f"Unable to validate IPv6 address for hostname: {hostname}"
            )

        # Check if IP is in private ranges
        for private_range in PRIVATE_IP_RANGES:
            if ip_obj in private_range:
                raise ValueError(f"IP address {ip} is in private range and not allowed")

    except socket.gaierror:
        raise ValueError(f"Unable to resolve hostname: {hostname}")
    except ValueError:
        # Re-raise our custom ValueError
        raise
    except Exception as e:
        raise ValueError(f"IP validation failed: {e}")

    # If all checks pass, return normalized URL
    safe_url = f"{parsed.scheme}://{parsed.netloc}"
    return safe_url.rstrip("/")


def _validate_openai_base_url(base_url: str | None) -> str:
    """
    Validate a user-provided OpenAI base URL to prevent SSRF.

    Returns a safe base URL string or raises ValueError if invalid.
    """
    # Default official OpenAI API endpoint when no base_url is provided.
    if not base_url:
        return "https://api.openai.com"

    try:
        return _validate_url_ssrf("openai", base_url)
    except ValueError as e:
        raise ValueError(f"Invalid OpenAI base URL: {e}")


@app.post("/providers/test-key/{provider}")
@limiter.limit("5/minute")
async def test_provider_api_key(request: Request, provider: str, payload: dict):
    """Test an API key for any supported provider."""
    api_key = payload.get("api_key")
    base_url = payload.get("base_url")

    async def _test_bearer(url: str, key: str, provider: str) -> dict:
        """Helper: test a Bearer-authenticated API_MODELS_ENDPOINT endpoint."""
        try:
            headers = {"Authorization": f"Bearer {key}"}
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                set_validated(provider, key, True)
                return {"success": True}
            set_validated(provider, key, False)
            return {"success": False, "error": resp.text}
        except Exception as e:
            set_validated(provider, key, False)
            return {"success": False, "error": str(e)}

    # --- Anthropic ---
    if provider in ("anthropic", "claude"):
        try:
            # Use authorized URL for Anthropic
            safe_url = (
                _validate_url_ssrf("anthropic", "https://api.anthropic.com")
                + API_MODELS_ENDPOINT
            )
            headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
            async with httpx.AsyncClient() as client:
                resp = await client.get(safe_url, headers=headers, timeout=10)
            if resp.status_code in (200, 403):
                set_validated(provider, api_key, True)
                return {"success": True}
            set_validated(provider, api_key, False)
            return {"success": False, "error": resp.text}
        except Exception as e:
            set_validated(provider, api_key, False)
            return {"success": False, "error": str(e)}

    # --- OpenAI ---
    if provider == "openai":
        try:
            safe_base_url = _validate_openai_base_url(base_url)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        url = safe_base_url + API_MODELS_ENDPOINT
        return await _test_bearer(url, api_key, provider)

    # --- Google Gemini ---
    if provider == "google":
        try:
            safe_url = (
                _validate_url_ssrf(
                    "google", "https://generativelanguage.googleapis.com"
                )
                + API_MODELS_ENDPOINT
            )
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{safe_url}?key={api_key}", timeout=10)
            if resp.status_code == 200:
                set_validated(provider, api_key, True)
                return {"success": True}
            set_validated(provider, api_key, False)
            return {"success": False, "error": resp.text}
        except Exception as e:
            set_validated(provider, api_key, False)
            return {"success": False, "error": str(e)}

    # --- Mistral AI ---
    if provider == "mistral":
        try:
            safe_base_url = _validate_url_ssrf(
                "mistral", base_url or "https://api.mistral.ai"
            )
            url = safe_base_url + API_MODELS_ENDPOINT
            return await _test_bearer(url, api_key, provider)
        except ValueError as e:
            return {"success": False, "error": str(e)}

    # --- DeepSeek ---
    if provider == "deepseek":
        try:
            safe_base_url = _validate_url_ssrf(
                "deepseek", base_url or "https://api.deepseek.com"
            )
            url = safe_base_url + API_MODELS_ENDPOINT
            return await _test_bearer(url, api_key, provider)
        except ValueError as e:
            return {"success": False, "error": str(e)}

    # --- Grok (xAI) ---
    if provider == "grok":
        try:
            safe_url = (
                _validate_url_ssrf("grok", "https://api.x.ai") + API_MODELS_ENDPOINT
            )
            return await _test_bearer(safe_url, api_key, provider)
        except ValueError as e:
            return {"success": False, "error": str(e)}

    # --- Meta (via Together AI / Replicate — OpenAI-compatible) ---
    if provider == "meta":
        try:
            safe_base_url = _validate_url_ssrf(
                "meta", base_url or "https://api.together.xyz"
            )
            url = safe_base_url + API_MODELS_ENDPOINT
            return await _test_bearer(url, api_key, provider)
        except ValueError as e:
            return {"success": False, "error": str(e)}

    # --- Cursor ---
    if provider == "cursor":
        try:
            safe_base_url = _validate_url_ssrf(
                "cursor", base_url or "https://api.cursor.com"
            )
            url = safe_base_url + API_MODELS_ENDPOINT
            return await _test_bearer(url, api_key, provider)
        except ValueError as e:
            return {"success": False, "error": str(e)}

    # --- Windsurf (Codeium) ---
    if provider == "windsurf":
        oauth_token = payload.get("oauth_token") or payload.get("api_key")
        if not oauth_token:
            return {"success": False, "error": "OAuth token required for Windsurf"}
        try:
            from integrations.windsurf_mcp import get_windsurf_mcp

            mcp = await get_windsurf_mcp()
            status = await mcp.check_status()
            if status.get("connected", False):
                set_validated(provider, oauth_token, True)
                return {"success": True, "method": "MCP"}
        except Exception as mcp_error:
            logging.warning(f"MCP test failed, trying direct API: {mcp_error}")
        try:
            safe_url = (
                _validate_url_ssrf("windsurf", "https://server.codeium.com")
                + "/api"
                + API_MODELS_ENDPOINT
            )
            headers = {"Authorization": f"Bearer {oauth_token}"}
            async with httpx.AsyncClient() as client:
                resp = await client.get(safe_url, headers=headers, timeout=10)
            if resp.status_code in [200, 404]:
                set_validated(provider, oauth_token, True)
                return {"success": True, "method": "direct_api"}
            set_validated(provider, oauth_token, False)
            return {"success": False, "error": resp.text}
        except Exception as e:
            set_validated(provider, oauth_token, False)
            return {"success": False, "error": str(e)}

    # --- Copilot (gh CLI auth — no API key test) ---
    if provider == "copilot":
        try:
            import asyncio

            proc = await asyncio.create_subprocess_exec(
                "gh",
                "auth",
                "status",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5)
            stdout_text = stdout.decode() if stdout else ""
            stderr_text = stderr.decode() if stderr else ""
            if GITHUB_CLI_AUTH_SUCCESS in (stdout_text + stderr_text):
                return {"success": True, "method": "gh_cli"}
            return {
                "success": False,
                "error": "GitHub CLI not authenticated. Run: gh auth login",
            }
        except asyncio.TimeoutError:
            return {"success": False, "error": "GitHub CLI check timed out"}
        except Exception as e:
            return {"success": False, "error": f"GitHub CLI check failed: {e}"}

    # --- Ollama (local — no key needed) ---
    if provider == "ollama":

        def build_ollama_url(raw_base_url: str | None) -> str:
            """
            Build a safe Ollama URL from an optional base URL.

            Only allow localhost/127.0.0.1 on the standard Ollama port.
            Fall back to the default if validation fails.
            """
            default_base = "http://localhost:11434"
            if not raw_base_url:
                return default_base + "/api/tags"

            try:
                parsed = urlparse(raw_base_url)
            except Exception:
                # Malformed URL; use safe default
                return default_base + "/api/tags"

            # Require HTTP scheme
            if parsed.scheme not in ("http",):
                return default_base + "/api/tags"

            # Only allow localhost-style hosts
            hostname = parsed.hostname or ""
            allowed_hosts = {"localhost", "127.0.0.1"}
            if hostname not in allowed_hosts:
                return default_base + "/api/tags"

            # Enforce allowed port (default 11434 if missing)
            port = parsed.port or 11434
            if port != 11434:
                return default_base + "/api/tags"

            safe_base = f"{parsed.scheme}://{hostname}:{port}"
            return safe_base + "/api/tags"

        try:
            url = build_ollama_url(base_url)
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=5)
            if resp.status_code == 200:
                return {"success": True}
            return {
                "success": False,
                "error": f"Ollama returned HTTP {resp.status_code}",
            }
        except Exception as e:
            return {"success": False, "error": f"Ollama not reachable: {e}"}

    return {
        "success": False,
        "error": f"Provider '{provider}' non supporté pour le test",
    }


@app.get("/providers/models/{provider}")
def get_provider_models(provider: str):
    """Returns a list of known models for the given provider."""
    PROVIDER_MODELS: dict[str, list[str]] = {
        "anthropic": [
            "claude-opus-4-5",
            "claude-sonnet-4-5",
            "claude-haiku-4-5",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
        ],
        "claude": [
            "claude-opus-4-5",
            "claude-sonnet-4-5",
            "claude-haiku-4-5",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
        ],
        "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"],
        "google": [
            "gemini-2.0-flash",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-pro",
        ],
        "mistral": [
            "mistral-large-latest",
            "mistral-medium-latest",
            "mistral-small-latest",
            "open-mistral-7b",
        ],
        "meta": ["llama-3.3-70b-instruct", "llama-3.1-8b-instruct"],
        "deepseek": ["deepseek-chat", "deepseek-reasoner"],
        "aws": [
            "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "amazon.titan-text-premier-v1:0",
        ],
        "ollama": [],
    }

    models = PROVIDER_MODELS.get(provider, [])

    # For Ollama, try to fetch available models from local instance
    if provider == "ollama":
        try:
            import httpx

            resp = httpx.get("http://localhost:11434/api/tags", timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
        except Exception:
            models = []

    return {"models": models, "provider": provider}


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


@app.post(
    "/providers/generate/{provider}",
    responses={
        404: {"description": PROVIDER_CONFIG_NOT_FOUND},
        400: {"description": "Generation failed"},
    },
)
@limiter.limit("30/minute")
def generate_with_provider(request: Request, provider: str, payload: dict[str, Any]):
    provider_cls = get_provider_by_name(provider)
    if not provider_cls:
        raise HTTPException(status_code=404, detail=PROVIDER_CLASS_NOT_FOUND)
    config = load_provider_config(provider)
    if not config:
        raise HTTPException(status_code=404, detail=PROVIDER_CONFIG_NOT_FOUND)
    prompt = payload.get("prompt")
    if not prompt:
        raise HTTPException(status_code=400, detail=PROMPT_REQUIRED)
    try:
        instance = provider_cls(**config)
        instance.connect()
        result = instance.generate(prompt, **payload.get("params", {}))
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=GENERATION_FAILED.format(e=e))


@app.post(
    "/providers/validate/{provider}",
    responses={400: {"description": "API key validation failed"}},
)
@limiter.limit("5/minute")
async def validate_provider_key(
    request: Request, provider: str, api_key: Annotated[str, Body(..., embed=True)]
):
    """Validate a provider API key by actually testing it before marking as valid."""
    # Actually test the key before marking it as validated
    if provider in ("openai",):
        try:
            url = "https://api.openai.comAPI_MODELS_ENDPOINT"
            headers = {"Authorization": f"Bearer {api_key}"}
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                set_validated(provider, api_key, False)
                raise HTTPException(
                    status_code=400, detail=API_KEY_VALIDATION_FAILED_INVALID
                )
        except httpx.HTTPError as e:
            set_validated(provider, api_key, False)
            raise HTTPException(
                status_code=400, detail=API_KEY_VALIDATION_FAILED_ERROR.format(e=e)
            )
    elif provider in ("grok",):
        try:
            url = "https://api.x.aiAPI_MODELS_ENDPOINT"
            headers = {"Authorization": f"Bearer {api_key}"}
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                set_validated(provider, api_key, False)
                raise HTTPException(
                    status_code=400, detail=API_KEY_VALIDATION_FAILED_INVALID
                )
        except httpx.HTTPError as e:
            set_validated(provider, api_key, False)
            raise HTTPException(
                status_code=400, detail=API_KEY_VALIDATION_FAILED_ERROR.format(e=e)
            )
    elif provider in ("anthropic", "claude"):
        try:
            headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.anthropic.comAPI_MODELS_ENDPOINT",
                    headers=headers,
                    timeout=10,
                )
            if resp.status_code not in (200, 403):
                set_validated(provider, api_key, False)
                raise HTTPException(
                    status_code=400, detail=API_KEY_VALIDATION_FAILED_INVALID
                )
        except httpx.HTTPError as e:
            set_validated(provider, api_key, False)
            raise HTTPException(
                status_code=400, detail=API_KEY_VALIDATION_FAILED_ERROR.format(e=e)
            )
    elif provider in ("google",):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://generativelanguage.googleapis.comAPI_MODELS_ENDPOINT?key={api_key}",
                    timeout=10,
                )
            if resp.status_code != 200:
                set_validated(provider, api_key, False)
                raise HTTPException(
                    status_code=400, detail=API_KEY_VALIDATION_FAILED_INVALID
                )
        except httpx.HTTPError as e:
            set_validated(provider, api_key, False)
            raise HTTPException(
                status_code=400, detail=API_KEY_VALIDATION_FAILED_ERROR.format(e=e)
            )
    elif provider in ("windsurf",):
        try:
            url = "https://server.codeium.com/apiAPI_MODELS_ENDPOINT"
            headers = {"Authorization": f"Bearer {api_key}"}
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers, timeout=10)
            if resp.status_code not in (200, 404):
                set_validated(provider, api_key, False)
                raise HTTPException(
                    status_code=400, detail=API_KEY_VALIDATION_FAILED_INVALID
                )
        except httpx.HTTPError as e:
            set_validated(provider, api_key, False)
            raise HTTPException(
                status_code=400, detail=API_KEY_VALIDATION_FAILED_ERROR.format(e=e)
            )
    elif provider in ("mistral",):
        try:
            url = "https://api.mistral.aiAPI_MODELS_ENDPOINT"
            headers = {"Authorization": f"Bearer {api_key}"}
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                set_validated(provider, api_key, False)
                raise HTTPException(
                    status_code=400, detail=API_KEY_VALIDATION_FAILED_INVALID
                )
        except httpx.HTTPError as e:
            set_validated(provider, api_key, False)
            raise HTTPException(
                status_code=400, detail=API_KEY_VALIDATION_FAILED_ERROR.format(e=e)
            )
    elif provider in ("deepseek",):
        try:
            url = "https://api.deepseek.comAPI_MODELS_ENDPOINT"
            headers = {"Authorization": f"Bearer {api_key}"}
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                set_validated(provider, api_key, False)
                raise HTTPException(
                    status_code=400, detail=API_KEY_VALIDATION_FAILED_INVALID
                )
        except httpx.HTTPError as e:
            set_validated(provider, api_key, False)
            raise HTTPException(
                status_code=400, detail=API_KEY_VALIDATION_FAILED_ERROR.format(e=e)
            )
    else:
        # For providers without specific validation (meta, cursor, copilot, ollama, aws)
        # Accept the key if it's non-empty
        if api_key and api_key.strip():
            set_validated(provider, api_key, True)
            return {"status": "validated"}
        raise HTTPException(
            status_code=400,
            detail=f"Provider '{provider}': API key is empty",
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
    import platform
    import time

    start = time.monotonic()
    subsystems: dict[str, Any] = {}

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
    provider_status: dict[str, bool] = {}
    for name in [
        "anthropic",
        "openai",
        "google",
        "grok",
        "windsurf",
        "ollama",
        "copilot",
    ]:
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
                "llm_provider": gconfig.llm_provider
                if hasattr(gconfig, "llm_provider")
                else "unknown",
                "embedder_provider": gconfig.embedder_provider
                if hasattr(gconfig, "embedder_provider")
                else "unknown",
            }
        except Exception as e:
            subsystems["graphiti_memory"] = {
                "status": "error",
                "enabled": True,
                "error": str(e),
            }
    else:
        subsystems["graphiti_memory"] = {"status": "disabled", "enabled": False}

    # 4. configured_providers.json file
    config_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "../../config/configured_providers.json"
        )
    )
    subsystems["configured_providers_file"] = {
        "status": "ok" if os.path.exists(config_path) else "missing"
    }

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
                resp = await client.get(
                    "https://api.openai.com/v1/organization/usage",
                    headers=headers,
                    timeout=10,
                )

            if resp.status_code == 200:
                data = resp.json()
                return {
                    "provider": "openai",
                    "usage": data,
                    "fetched_at": "now",
                    "note": "Données d'usage récupérées avec succès",
                }
            else:
                # Si l'endpoint échoue, retourner un message informatif
                return {
                    "provider": "openai",
                    "error": f"Erreur {resp.status_code}: L'endpoint d'usage OpenAI nécessite des permissions spéciales (api.usage.read) ou une clé d'administrateur. Veuillez vérifier votre dashboard OpenAI pour l'usage actuel.",
                    "status_code": resp.status_code,
                    "alternative": "Consultez https://platform.openai.com/settings/organization/billing/overview",
                }
        except Exception as e:
            return {
                "provider": "openai",
                "error": f"Impossible de récupérer l'usage OpenAI: {str(e)}",
                "note": "L'endpoint /v1/usage d'OpenAI nécessite des permissions spéciales depuis 2025",
                "alternative": "Consultez https://platform.openai.com/settings/organization/billing/overview",
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
                    "acceptance_rate_percent": usage_data.get(
                        "acceptance_rate_percent", 0
                    ),
                    "line_acceptance_rate_percent": usage_data.get(
                        "line_acceptance_rate_percent", 0
                    ),
                    "total_tokens": usage_data.get("total_tokens", 0),
                    "organization": usage_data.get("organization"),
                    "level": usage_data.get("level", "organization"),
                },
                "fetched_at": usage_data.get("fetched_at"),
                "copilotUsageDetails": {
                    "suggestions": usage_data.get("total_suggestions", 0),
                    "acceptances": usage_data.get("total_acceptances", 0),
                    "acceptanceRate": usage_data.get("acceptance_rate_percent", 0),
                    "linesSuggested": usage_data.get("total_lines_suggested", 0),
                    "linesAccepted": usage_data.get("total_lines_accepted", 0),
                    "lineAcceptanceRate": usage_data.get(
                        "line_acceptance_rate_percent", 0
                    ),
                },
            }  # Added closing bracket here
        except ImportError as e:
            return {"error": f"Module Copilot non disponible: {e}"}
        except Exception as e:
            return {
                "error": f"Erreur lors de la récupération des métriques Copilot: {e}"
            }
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
                "providerName": "anthropic",
            }
        except ImportError as e:
            return {"error": f"Module Anthropic usage non disponible: {e}"}
        except Exception as e:
            return {
                "error": f"Erreur lors de la récupération des métriques Anthropic: {e}"
            }
    elif provider == "windsurf":
        # Windsurf (Codeium) — multi-strategy auth for GetTeamCreditBalance
        service_key = os.getenv("WINDSURF_API_KEY") or os.getenv("CODEIUM_API_KEY")
        if not service_key:
            return {
                "provider": "windsurf",
                "error": "Clé API Windsurf manquante. Définissez WINDSURF_API_KEY ou CODEIUM_API_KEY.",
                "alternative": "Consultez le dashboard Windsurf pour obtenir votre service key.",
            }
        try:
            async with httpx.AsyncClient() as client:
                # Strategy 1: service_key in body (standard for team service keys)
                resp = await client.post(
                    "https://server.codeium.com/api/v1/GetTeamCreditBalance",
                    json={"service_key": service_key},
                    timeout=10,
                )
                # Strategy 2: Authorization Bearer header (some Codeium API versions)
                if resp.status_code == 401:
                    resp = await client.post(
                        "https://server.codeium.com/api/v1/GetTeamCreditBalance",
                        headers={"Authorization": f"Bearer {service_key}"},
                        json={},
                        timeout=10,
                    )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "provider": "windsurf",
                    "available": True,
                    "usage": data,
                    "fetched_at": "now",
                }
            # Strategy 3: Validate key via GetUser if credit balance unavailable
            try:
                async with httpx.AsyncClient() as client:
                    user_resp = await client.post(
                        "https://server.codeium.com/exa.api_server_pb.ApiServerService/GetUser",
                        headers={
                            "Authorization": f"Bearer {service_key}",
                            "Content-Type": "application/json",
                        },
                        json={},
                        timeout=10,
                    )
                if user_resp.status_code == 200:
                    user_data = user_resp.json()
                    return {
                        "provider": "windsurf",
                        "available": True,
                        "usage": {
                            "user": user_data,
                            "note": "Credit balance unavailable — key validated via GetUser",
                        },
                        "fetched_at": "now",
                    }
            except Exception:
                pass
            return {
                "provider": "windsurf",
                "error": f"Erreur {resp.status_code}: {resp.text[:200]}",
                "status_code": resp.status_code,
                "note": "Vérifiez que votre service key Windsurf est valide.",
            }
        except Exception as e:
            return {
                "provider": "windsurf",
                "error": f"Impossible de récupérer l'usage Windsurf: {str(e)}",
            }
    else:
        return {"error": f"Usage non supporté pour le provider '{provider}'"}


# ---------------------------------------------------------------------------
# Feature API endpoints — Expose backend Python modules to the frontend
# ---------------------------------------------------------------------------


# --- 1.1 Dashboard Metrics ---
def _load_dashboard_snapshot(project_id: str) -> dict:
    """Load dashboard_snapshot.json written by core.usage_tracker.
    project_id is the project path (URL-decoded by FastAPI)."""
    import json as _json
    from pathlib import Path as _Path

    snap_path = _Path(project_id) / ".workpilot" / "dashboard_snapshot.json"
    if snap_path.exists():
        try:
            return _json.loads(snap_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "tasks_by_status": {},
        "avg_completion_by_complexity": {},
        "qa_first_pass_rate": 0.0,
        "qa_avg_score": 0.0,
        "total_tokens": 0,
        "tokens_by_provider": {},
        "total_cost": 0.0,
        "cost_by_model": {},
        "merge_auto_count": 0,
        "merge_manual_count": 0,
    }


@app.get("/api/dashboard/snapshot/{project_id:path}")
def get_dashboard_snapshot(project_id: str):
    try:
        snap = _load_dashboard_snapshot(project_id)
        # Compute merge rate
        auto = snap.get("merge_auto_count", 0)
        manual = snap.get("merge_manual_count", 0)
        total_merges = auto + manual
        merge_rate = (auto / total_merges * 100) if total_merges > 0 else 0.0
        snap["merge_auto_rate"] = merge_rate
        # Flatten avg_completion (list → mean)
        avg_compl = {}
        for k, v in snap.get("avg_completion_by_complexity", {}).items():
            if isinstance(v, list) and v:
                avg_compl[k] = sum(v) / len(v)
            else:
                avg_compl[k] = v or 0.0
        snap["avg_completion_by_complexity"] = avg_compl
        return {"success": True, "snapshot": snap}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/dashboard/stats")
def get_dashboard_stats():
    return {"success": True, "stats": {}}


@app.get("/api/dashboard/export/{project_id:path}")
def export_dashboard(project_id: str, fmt: str = "json"):
    try:
        import csv as _csv
        import io as _io

        snap = _load_dashboard_snapshot(project_id)
        if fmt == "csv":
            buf = _io.StringIO()
            writer = _csv.writer(buf)
            writer.writerow(["metric", "value"])
            for k, v in snap.items():
                if not k.startswith("_"):
                    writer.writerow([k, v])
            return {"success": True, "report": buf.getvalue(), "format": "csv"}
        return {"success": True, "report": snap, "format": "json"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# --- 1.2 Session History ---
@app.get("/api/sessions/{project_id}")
def get_sessions(project_id: str):
    try:
        from agents.session_history import SessionRecorder

        sh = SessionRecorder(project_id=project_id)
        sessions = sh.list_sessions()
        return {
            "success": True,
            "sessions": [
                s.to_dict() if hasattr(s, "to_dict") else s.__dict__ for s in sessions
            ],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# --- 2.1 Refactoring Agent ---
@app.post("/api/refactoring/detect-smells")
def detect_smells(body: Annotated[dict[str, Any], Body(...)]):
    try:
        from agents.refactorer import RefactoringAgent

        agent = RefactoringAgent(thresholds=body.get("thresholds", {}))
        source = body.get("source", "")
        smells = agent.detect_smells_from_source(source)
        return {
            "success": True,
            "smells": [
                s.to_dict() if hasattr(s, "to_dict") else s.__dict__ for s in smells
            ],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/refactoring/propose")
def propose_refactoring(body: Annotated[dict[str, Any], Body(...)]):
    try:
        from agents.refactorer import RefactoringAgent

        agent = RefactoringAgent(thresholds=body.get("thresholds", {}))
        source = body.get("source", "")
        proposals = agent.propose_refactoring(source=source)
        return {
            "success": True,
            "proposals": [
                p.to_dict() if hasattr(p, "to_dict") else p.__dict__ for p in proposals
            ],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# --- 2.2 Documentation Agent ---
@app.post("/api/documentation/coverage")
def check_doc_coverage(body: Annotated[dict[str, Any], Body(...)]):
    try:
        from agents.documenter import DocFormat, DocumentationAgent

        fmt = body.get("format", "google")
        agent = DocumentationAgent(default_format=DocFormat(fmt))
        file_path = body.get("file_path", "")
        coverage = agent.check_documentation_coverage(file_path=file_path)
        return {"success": True, "coverage": coverage}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/documentation/generate-docstrings")
def generate_docstrings(body: Annotated[dict[str, Any], Body(...)]):
    try:
        from agents.documenter import DocFormat, DocumentationAgent

        fmt = body.get("format", "google")
        agent = DocumentationAgent(default_format=DocFormat(fmt))
        file_path = body.get("file_path", "")
        result = agent.generate_docstrings(file_path=file_path)
        return {
            "success": True,
            "result": result.to_dict()
            if hasattr(result, "to_dict")
            else result.__dict__,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/documentation/generate-readme")
def generate_readme(body: Annotated[dict[str, Any], Body(...)]):
    try:
        from agents.documenter import DocFormat, DocumentationAgent

        fmt = body.get("format", "google")
        agent = DocumentationAgent(default_format=DocFormat(fmt))
        dir_path = body.get("dir_path", "")
        result = agent.generate_module_readme(dir_path)
        return {
            "success": True,
            "result": result.to_dict()
            if hasattr(result, "to_dict")
            else result.__dict__,
        }
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
        return {
            "success": True,
            "templates": [
                t.to_dict() if hasattr(t, "to_dict") else t.__dict__ for t in templates
            ],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# --- 3.3 AI Code Review ---
@app.post("/api/code-review/analyze")
def analyze_code_review(body: Annotated[dict[str, Any], Body(...)]):
    try:
        from review.ai_code_review import AICodeReview

        reviewer = AICodeReview()
        diff = body.get("diff", "")
        result = reviewer.review_diff(diff)
        return {
            "success": True,
            "review": result.to_dict()
            if hasattr(result, "to_dict")
            else result.__dict__,
        }
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
        return {
            "success": True,
            "jobs": [
                j.to_dict() if hasattr(j, "to_dict") else j.__dict__ for j in jobs
            ],
        }
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
def get_pr_details(pr_url: Annotated[str, Query(...)]):
    """Get PR details including files and diffs from GitHub."""
    try:
        from runners.github.providers.github_provider import GitHubProvider

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
                "diff": pr_data.diff,
            },
        }

        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


# --- Test Generation Agent API ---
@app.post("/api/test-generation/analyze-coverage")
def analyze_test_coverage(
    file_path: Annotated[str, Body(...)],
    existing_test_path: Annotated[str | None, Body()] = None,
):
    """Analyze test coverage gaps for a source file."""
    try:
        from agents.test_generator import TestGeneratorAgent

        agent = TestGeneratorAgent()
        gaps = agent.analyze_coverage(file_path, existing_test_path)
        return {
            "success": True,
            "gaps": [
                {
                    "function": {
                        "name": gap.function.name,
                        "module": gap.function.module,
                        "class_name": gap.function.class_name,
                        "args": gap.function.args,
                        "return_type": gap.function.return_type,
                        "docstring": gap.function.docstring,
                        "line_number": gap.function.line_number,
                        "is_async": gap.function.is_async,
                        "decorators": gap.function.decorators,
                        "complexity": gap.function.complexity,
                        "full_name": gap.function.full_name,
                        "is_private": gap.function.is_private,
                        "is_dunder": gap.function.is_dunder,
                    },
                    "priority": gap.priority,
                    "reason": gap.reason,
                    "suggested_test_count": gap.suggested_test_count,
                }
                for gap in gaps
            ],
        }  # added closing brace here
    except Exception as e:
        return {"success": False, "error": str(e)}  # added except block here


@app.post("/api/test-generation/generate-unit-tests")
def generate_unit_tests(
    file_path: Annotated[str, Body(...)],
    existing_test_path: Annotated[str | None, Body()] = None,
    max_tests_per_function: int = 3,
):
    """Generate unit tests for a source file."""
    try:
        from agents.test_generator import TestGeneratorAgent

        agent = TestGeneratorAgent()
        result = agent.generate_unit_tests(
            file_path, existing_test_path, max_tests_per_function
        )
        return {
            "success": True,
            "result": {
                "source_file": result.source_file,
                "functions_analyzed": result.functions_analyzed,
                "tests_generated": result.tests_generated,
                "coverage_gaps": [
                    {
                        "function": {
                            "name": gap.function.name,
                            "full_name": gap.function.full_name,
                        },
                        "priority": gap.priority,
                        "reason": gap.reason,
                        "suggested_test_count": gap.suggested_test_count,
                    }
                    for gap in result.coverage_gaps
                ],
                "generated_tests": [
                    {
                        "test_name": test.test_name,
                        "test_code": test.test_code,
                        "target_function": test.target_function,
                        "test_type": test.test_type,
                        "description": test.description,
                        "imports": test.imports,
                        "fixtures": test.fixtures,
                    }
                    for test in result.generated_tests
                ],
                "test_file_content": result.test_file_content,
                "test_file_path": result.test_file_path,
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/test-generation/generate-e2e-tests")
def generate_e2e_tests(
    user_story: Annotated[str, Body(...)], target_module: Annotated[str, Body(...)]
):
    """Generate E2E tests from a user story."""
    try:
        from agents.test_generator import TestGeneratorAgent

        agent = TestGeneratorAgent()
        result = agent.generate_tests_from_user_story(user_story, target_module)
        return {
            "success": True,
            "result": {
                "source_file": result.source_file,
                "functions_analyzed": result.functions_analyzed,
                "tests_generated": result.tests_generated,
                "generated_tests": [
                    {
                        "test_name": test.test_name,
                        "test_code": test.test_code,
                        "target_function": test.target_function,
                        "test_type": test.test_type,
                        "description": test.description,
                        "imports": test.imports,
                        "fixtures": test.fixtures,
                    }
                    for test in result.generated_tests
                ],
                "test_file_content": result.test_file_content,
                "test_file_path": result.test_file_path,
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/test-generation/generate-tdd-tests")
def generate_tdd_tests(spec: Annotated[dict, Body(...)]):
    """Generate tests before implementation (TDD mode)."""
    try:
        from agents.test_generator import TestGeneratorAgent

        agent = TestGeneratorAgent()
        result = agent.generate_tdd_tests(spec)
        return {
            "success": True,
            "result": {
                "source_file": result.source_file,
                "functions_analyzed": result.functions_analyzed,
                "tests_generated": result.tests_generated,
                "generated_tests": [
                    {
                        "test_name": test.test_name,
                        "test_code": test.test_code,
                        "target_function": test.target_function,
                        "test_type": test.test_type,
                        "description": test.description,
                        "imports": test.imports,
                        "fixtures": test.fixtures,
                    }
                    for test in result.generated_tests
                ],
                "test_file_content": result.test_file_content,
                "test_file_path": result.test_file_path,
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/test-generation/run-post-build")
def run_post_build_test_generation(
    project_path: Annotated[str, Body(...)],
    modified_files: Annotated[list[str], Body(...)],
):
    """Run automatic test generation after a build (post-build hook)."""
    try:
        import os

        from agents.test_generator import TestGeneratorAgent

        agent = TestGeneratorAgent()
        results = []

        for file_path in modified_files:
            if file_path.endswith(".py") and os.path.exists(file_path):
                # Skip test files themselves
                if "test_" in file_path or "/tests/" in file_path:
                    continue

                # Find existing test file
                test_file_path = agent._compute_test_file_path(file_path)
                existing_test_path = (
                    test_file_path if os.path.exists(test_file_path) else None
                )

                # Generate tests
                result = agent.generate_unit_tests(file_path, existing_test_path)
                if result.tests_generated > 0:
                    results.append(
                        {
                            "source_file": result.source_file,
                            "tests_generated": result.tests_generated,
                            "test_file_path": result.test_file_path,
                            "test_file_content": result.test_file_content,
                        }
                    )

        return {
            "success": True,
            "results": results,
            "summary": {
                "files_processed": len(modified_files),
                "files_with_tests": len(results),
                "total_tests_generated": sum(r["tests_generated"] for r in results),
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# --- Event-Driven Hooks System API ---
@app.get("/api/hooks")
def list_hooks(project_id: Annotated[str | None, Query()] = None):
    """List all hooks, optionally filtered by project."""
    try:
        from services.hooks.hook_service import HookService

        svc = HookService.get_instance()
        hooks = svc.list_hooks(project_id)
        return {"success": True, "hooks": hooks}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/hooks/stats")
def get_hooks_stats():
    """Get overall hook system statistics."""
    try:
        from services.hooks.hook_service import HookService

        svc = HookService.get_instance()
        stats = svc.get_stats()
        return {"success": True, "stats": stats}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/hooks/templates")
def get_hook_templates():
    """Get all available hook templates."""
    try:
        from services.hooks.hook_service import HookService

        svc = HookService.get_instance()
        templates = svc.get_templates()
        return {"success": True, "templates": templates}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/hooks/{hook_id}", responses={404: {"description": "Hook not found"}})
def get_hook(hook_id: Annotated[str, Path(...)]):
    """Get a single hook by ID."""
    try:
        from services.hooks.hook_service import HookService

        svc = HookService.get_instance()
        hook = svc.get_hook(hook_id)
        if not hook:
            raise HTTPException(status_code=404, detail=HOOK_NOT_FOUND)
        return {"success": True, "hook": hook}
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/hooks")
def create_hook(body: Annotated[dict[str, Any], Body(...)]):
    """Create a new hook."""
    try:
        from services.hooks.hook_service import HookService

        svc = HookService.get_instance()
        hook = svc.create_hook(body)
        return {"success": True, "hook": hook}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.put("/api/hooks/{hook_id}", responses={404: {"description": HOOK_NOT_FOUND}})
def update_hook(
    hook_id: Annotated[str, Path(...)], body: Annotated[dict[str, Any], Body(...)]
):
    """Update an existing hook."""
    try:
        from services.hooks.hook_service import HookService

        svc = HookService.get_instance()
        hook = svc.update_hook(hook_id, body)
        if not hook:
            raise HTTPException(status_code=404, detail=HOOK_NOT_FOUND)
        return {"success": True, "hook": hook}
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.delete("/api/hooks/{hook_id}", responses={404: {"description": "Hook not found"}})
def delete_hook(hook_id: Annotated[str, Path(...)]):
    """Delete a hook."""
    try:
        from services.hooks.hook_service import HookService

        svc = HookService.get_instance()
        deleted = svc.delete_hook(hook_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=HOOK_NOT_FOUND)
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post(
    "/api/hooks/{hook_id}/toggle", responses={404: {"description": "Hook not found"}}
)
def toggle_hook(hook_id: Annotated[str, Path(...)]):
    """Toggle a hook between active and paused."""
    try:
        from services.hooks.hook_service import HookService

        svc = HookService.get_instance()
        hook = svc.toggle_hook(hook_id)
        if not hook:
            raise HTTPException(status_code=404, detail=HOOK_NOT_FOUND)
        return {"success": True, "hook": hook}
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post(
    "/api/hooks/{hook_id}/duplicate", responses={404: {"description": HOOK_NOT_FOUND}}
)
def duplicate_hook(hook_id: Annotated[str, Path(...)]):
    """Duplicate an existing hook."""
    try:
        from services.hooks.hook_service import HookService

        svc = HookService.get_instance()
        hook = svc.duplicate_hook(hook_id)
        if not hook:
            raise HTTPException(status_code=404, detail=HOOK_NOT_FOUND)
        return {"success": True, "hook": hook}
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post(
    "/api/hooks/from-template", responses={404: {"description": TEMPLATE_NOT_FOUND}}
)
def create_hook_from_template(body: Annotated[dict[str, Any], Body(...)]):
    """Create a hook from a template."""
    try:
        from services.hooks.hook_service import HookService

        svc = HookService.get_instance()
        template_id = body.get("template_id", "")
        project_id = body.get("project_id")
        hook = svc.create_from_template(template_id, project_id)
        if not hook:
            raise HTTPException(status_code=404, detail=TEMPLATE_NOT_FOUND)
        return {"success": True, "hook": hook}
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/hooks/emit")
async def emit_hook_event(body: Annotated[dict[str, Any], Body(...)]):
    """Emit an event to trigger matching hooks."""
    try:
        from services.hooks.hook_service import HookService
        from services.hooks.models import HookEvent, TriggerType

        svc = HookService.get_instance()
        event = HookEvent(
            type=TriggerType(body.get("type", "manual")),
            data=body.get("data", {}),
            project_id=body.get("project_id"),
            source=body.get("source", "api"),
        )
        results = await svc.emit_event(event)
        return {"success": True, "executions": results, "hooks_triggered": len(results)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/hooks/executions/history")
def get_hook_executions(
    hook_id: Annotated[str | None, Query()] = None, limit: Annotated[int, Query()] = 50
):
    """Get execution history for hooks."""
    try:
        from services.hooks.hook_service import HookService

        svc = HookService.get_instance()
        executions = svc.get_executions(hook_id, limit)
        return {"success": True, "executions": executions}
    except Exception as e:
        return {"success": False, "error": str(e)}


# --- Analytics API (prefer real DB implementation, fall back to minimal stub) ---
try:
    from analytics.database import init_database as _init_analytics_db

    _init_analytics_db()
    from analytics.api_simple import router as analytics_router

    app.include_router(analytics_router)
except Exception as e:
    print(
        f"Warning: Could not load real analytics router ({e}), falling back to minimal stub"
    )
    try:
        from analytics.api_minimal import router as analytics_router

        app.include_router(analytics_router)
    except ImportError as e2:
        print(f"Warning: Could not import analytics router: {e2}")

# --- Mission Control API ---
try:
    from mission_control.api import router as mission_control_router

    app.include_router(mission_control_router)
except ImportError as e:
    print(f"Warning: Could not import mission control router: {e}")

# --- Agent Replay & Debug Mode API ---
try:
    from replay.api import router as replay_router

    app.include_router(replay_router)
except ImportError as e:
    print(f"Warning: Could not import replay router: {e}")

if __name__ == "__main__":
    import uvicorn

    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    port = int(os.getenv("BACKEND_PORT", 9000))
    uvicorn.run(
        "provider_api:app",
        host="127.0.0.1",
        port=port,
        reload=True,
        reload_excludes=[".venv"],
    )
