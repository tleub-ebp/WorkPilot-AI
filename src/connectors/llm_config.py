"""
Gestion sécurisée de la configuration des providers LLM (clés API, endpoints, etc.).
Permet l'enregistrement, la récupération et la validation des paramètres providers.
"""
import json
import logging
from pathlib import Path
from typing import Any

from apps.backend.core.auth import get_auth_token

logger = logging.getLogger(__name__)

def _mask_secret(value: str) -> str:
    """Renvoie un placeholder pour une clé API dans les logs.

    On n'écho aucun caractère du secret : même un préfixe de 8 caractères réduit
    significativement l'entropie pour un attaquant qui aurait accès aux logs.
    """
    if not value:
        return "***"
    return f"<redacted, {len(value)} chars>"

CONFIG_FILE = Path.home() / ".work_pilot_ai_llm_providers.json"

class ProviderConfig:
    """Configuration class for LLM providers."""
    
    def __init__(self, provider: str, model: str, api_key: str | None = None, base_url: str | None = None, **kwargs):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.is_claude_sdk = provider in ['anthropic-sdk', 'claude']
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    @classmethod
    def load_provider_config(cls, phase: str, spec_dir: str, cli_provider: str | None = None, cli_model: str | None = None):
        """Load provider configuration from various sources.
        
        Priority:
        1. CLI provider + config file entry (if provider has saved config)
        2. CLI provider + auth token (for anthropic/claude providers)
        3. CLI provider + cli_model (for other providers like openai, ollama)
        4. Default: anthropic provider with system auth token
        """
        provider = cli_provider or 'anthropic'
        model = cli_model or 'claude-3-sonnet-20240229'
        
        # Try to load saved provider config from ~/.work_pilot_ai_llm_providers.json
        config_data = load_provider_config(provider)
        if config_data:
            return cls(
                provider=provider,
                model=cli_model or config_data.get('model', model),
                api_key=config_data.get('api_key'),
                base_url=config_data.get('base_url'),
                **{k: v for k, v in config_data.items() if k not in ['provider', 'model', 'api_key', 'base_url']}
            )
        
        # No saved config — try system auth token for Anthropic/Claude providers
        if provider in ('anthropic', 'claude'):
            token = get_auth_token()
            if token and token.startswith("sk-"):
                return cls(provider=provider, model=model, api_key=token)
        
        # For other providers (openai, ollama, google, etc.), return config
        # with the model from task_metadata.json — API keys should be in env vars
        # or in the saved provider config file
        return cls(provider=provider, model=model)

def save_provider_config(name: str, config: dict[str, Any]) -> None:
    """Enregistre la configuration d'un provider (clé API, endpoint, etc.)."""
    all_configs = load_all_provider_configs()
    all_configs[name] = config
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(all_configs, f, indent=2)

def load_provider_config(name: str) -> dict[str, Any] | None:
    """Charge la configuration d'un provider donné."""
    all_configs = load_all_provider_configs()
    return all_configs.get(name)

def load_all_provider_configs() -> dict[str, Any]:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}

def delete_provider_config(name: str) -> None:
    all_configs = load_all_provider_configs()
    if name in all_configs:
        del all_configs[name]
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(all_configs, f, indent=2)

def list_provider_configs() -> list[str]:
    return list(load_all_provider_configs().keys())

def get_claude_token_from_system() -> str | None:
    """Récupère le token Claude Code depuis le keychain/credential manager (via core.auth)."""
    token = get_auth_token()
    if token and token.startswith("sk-"):
        return token
    return None

def force_claude_provider_config():
    """Crée ou met à jour la config provider 'claude' à partir du token système."""
    token = get_auth_token()
    if token and token.startswith("sk-"):
        config = {"api_key": token, "model": "claude-3-sonnet-20240229"}
        save_provider_config("claude", config)
        logger.info("force_claude_provider_config - config sauvegardée pour clé %s", _mask_secret(token))
    else:
        logger.warning("force_claude_provider_config - aucun token Claude valide trouvé.")
