"""
Windsurf LLM Provider Connector (Codeium)

Fournit l'accès aux modèles LLM via l'API Windsurf/Codeium.
Utilise les endpoints API compatibles OpenAI sur server.codeium.com.
Authentification via service key (Personal Access Token).
"""

import logging
from typing import Any, Dict, Optional
from .llm_base import BaseLLMProvider

logger = logging.getLogger(__name__)


class WindsurfProvider(BaseLLMProvider):
    """Provider pour Windsurf AI (Codeium).

    Authentification via service key (Personal Access Token) depuis le dashboard Windsurf.
    API: https://server.codeium.com/api/v1/
    """

    def __init__(self, api_key: str, model: str = "windsurf-default", base_url: str = "https://server.codeium.com/api/v1"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self._client = None

    def connect(self) -> None:
        """Établit la connexion avec l'API Windsurf."""
        try:
            import openai
        except ImportError:
            raise ImportError("openai package is required. Install with: pip install openai")
        
        self._client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        logger.info(f"Windsurf provider connected with model: {self.model}")

    def validate(self) -> bool:
        """Valide la configuration du provider Windsurf."""
        try:
            self.connect()
            # Test de connexion basique
            response = self._client.models.list()
            available_models = [model.id for model in response.data]
            return self.model in available_models or any("windsurf" in model for model in available_models)
        except Exception as e:
            logger.warning(f"Windsurf provider validation failed: {e}")
            return False

    def generate(self, prompt: str, **kwargs) -> str:
        """Génère une réponse via l'API Windsurf."""
        self.connect()
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Windsurf generation failed: {e}")
            raise

    def get_capabilities(self) -> Dict[str, Any]:
        """Retourne les capacités du provider Windsurf."""
        return {
            "models": [
                "windsurf-default",
                "windsurf-premier",
                "windsurf-cascade",
                "gpt-4o",
                "claude-3.5-sonnet"
            ],
            "provider": "windsurf",
            "features": [
                "chat",
                "autocomplete", 
                "code_generation",
                "context_awareness",
                "mcp_support"
            ],
            "api_compatibility": "openai"
        }

    def get_config_schema(self) -> Dict[str, Any]:
        """Retourne le schéma de configuration pour Windsurf."""
        return {
            "api_key": "str (required — service key / PAT from Windsurf dashboard)",
            "model": "str (optional, default: windsurf-default)",
            "base_url": "str (optional, default: https://server.codeium.com/api/v1)"
        }

    @classmethod
    def get_name(cls) -> str:
        """Nom unique du provider."""
        return "windsurf"
