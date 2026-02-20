"""
Gestion sécurisée de la configuration des providers LLM (clés API, endpoints, etc.).
Permet l'enregistrement, la récupération et la validation des paramètres providers.
"""
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from apps.backend.core.auth import get_auth_token

logger = logging.getLogger(__name__)

def _mask_secret(value: str) -> str:
    """Masque une clé API pour le logging (affiche seulement les 8 premiers caractères)."""
    if not value or len(value) <= 8:
        return "***"
    return f"{value[:8]}..."

CONFIG_FILE = Path.home() / ".work_pilot_ai_llm_providers.json"

class ProviderConfig:
    """Configuration class for LLM providers."""
    
    def __init__(self, provider: str, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None, **kwargs):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.is_claude_sdk = provider in ['anthropic-sdk', 'claude']
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    @classmethod
    def load_provider_config(cls, phase: str, spec_dir: str, cli_provider: Optional[str] = None, cli_model: Optional[str] = None):
        """Load provider configuration from various sources."""
        # Priority: CLI provider > environment > config file > defaults
        if cli_provider:
            config_data = load_provider_config(cli_provider)
            if config_data:
                return cls(
                    provider=cli_provider,
                    model=config_data.get('model', cli_model or 'default'),
                    api_key=config_data.get('api_key'),
                    base_url=config_data.get('base_url'),
                    **{k: v for k, v in config_data.items() if k not in ['provider', 'model', 'api_key', 'base_url']}
                )
        
        # Fallback to environment or defaults
        provider = cli_provider or 'anthropic'
        model = cli_model or 'claude-3-sonnet-20240229'
        
        if provider == 'anthropic' or provider == 'claude':
            token = get_auth_token()
            if token and token.startswith("sk-"):
                return cls(provider=provider, model=model, api_key=token)
        
        return cls(provider=provider, model=model)

def save_provider_config(name: str, config: Dict[str, Any]) -> None:
    """Enregistre la configuration d'un provider (clé API, endpoint, etc.)."""
    all_configs = load_all_provider_configs()
    all_configs[name] = config
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(all_configs, f, indent=2)

def load_provider_config(name: str) -> Dict[str, Any] | None:
    """Charge la configuration d'un provider donné."""
    all_configs = load_all_provider_configs()
    return all_configs.get(name)

def load_all_provider_configs() -> Dict[str, Any]:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
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