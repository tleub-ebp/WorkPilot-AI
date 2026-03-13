"""
Provider Registry Backend - Service centralisé pour la gestion des providers LLM
Point d'entrée unique pour le backend
"""

import os
import subprocess
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

class Provider:
    def __init__(
        self,
        name: str,
        label: str,
        description: str,
        category: str,
        requires_api_key: bool = False,
        requires_oauth: bool = False,
        requires_cli: bool = False,
        models: List[Dict[str, Any]] = None
    ):
        self.name = name
        self.label = label
        self.description = description
        self.category = category
        self.requires_api_key = requires_api_key
        self.requires_oauth = requires_oauth
        self.requires_cli = requires_cli
        self.models = models or []

class ProviderStatus:
    def __init__(
        self,
        available: bool = False,
        authenticated: bool = False,
        error: Optional[str] = None,
        last_checked: Optional[datetime] = None
    ):
        self.available = available
        self.authenticated = authenticated
        self.error = error
        self.last_checked = last_checked or datetime.now()

class ProviderRegistry:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._providers = {}
            cls._instance._initialize_providers()
        return cls._instance
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def _initialize_providers(self):
        """Initialise tous les providers disponibles"""
        
        # --- Anthropic (Claude) ---
        self._providers['anthropic'] = Provider(
            name='anthropic',
            label='Anthropic (Claude)',
            description='Claude models via Anthropic API',
            category='anthropic',
            requires_api_key=True,
            requires_oauth=True,
            requires_cli=False,
            models=[
                {'value': 'claude-opus-4-6', 'label': 'Claude Opus 4.6', 'tier': 'flagship', 'supportsThinking': True},
                {'value': 'claude-opus-4-5-20251101', 'label': 'Claude Opus 4.5', 'tier': 'flagship', 'supportsThinking': True},
                {'value': 'claude-sonnet-4-5-20250929', 'label': 'Claude Sonnet 4.5', 'tier': 'standard', 'supportsThinking': True},
                {'value': 'claude-haiku-4-5-20251001', 'label': 'Claude Haiku 4.5', 'tier': 'fast', 'supportsThinking': False},
            ]
        )
        
        # --- OpenAI ---
        self._providers['openai'] = Provider(
            name='openai',
            label='OpenAI (ChatGPT)',
            description='GPT and o-series models via OpenAI API',
            category='openai',
            requires_api_key=True,
            requires_oauth=False,
            requires_cli=False,
            models=[
                {'value': 'gpt-5.2', 'label': 'GPT-5.2', 'tier': 'flagship'},
                {'value': 'gpt-5', 'label': 'GPT-5', 'tier': 'flagship'},
                {'value': 'o3', 'label': 'o3', 'tier': 'flagship', 'supportsThinking': True},
                {'value': 'gpt-4o', 'label': 'GPT-4o', 'tier': 'standard'},
                {'value': 'o3-mini', 'label': 'o3-mini', 'tier': 'standard', 'supportsThinking': True},
                {'value': 'gpt-4o-mini', 'label': 'GPT-4o mini', 'tier': 'fast'},
                {'value': 'gpt-4-turbo', 'label': 'GPT-4 Turbo', 'tier': 'standard'},
            ]
        )
        
        # --- Google Gemini ---
        self._providers['google'] = Provider(
            name='google',
            label='Google (Gemini)',
            description='Gemini models via Google AI',
            category='google',
            requires_api_key=True,
            requires_oauth=False,
            requires_cli=False,
            models=[
                {'value': 'gemini-2.5-pro', 'label': 'Gemini 2.5 Pro', 'tier': 'flagship', 'supportsThinking': True},
                {'value': 'gemini-2.0-flash', 'label': 'Gemini 2.0 Flash', 'tier': 'fast'},
                {'value': 'gemini-2.0-flash-thinking', 'label': 'Gemini 2.0 Flash Thinking', 'tier': 'standard', 'supportsThinking': True},
                {'value': 'gemini-1.5-pro', 'label': 'Gemini 1.5 Pro', 'tier': 'standard'},
                {'value': 'gemini-1.5-flash', 'label': 'Gemini 1.5 Flash', 'tier': 'fast'},
            ]
        )
        
        # --- Meta (LLaMA) ---
        self._providers['meta'] = Provider(
            name='meta',
            label='Meta (LLaMA)',
            description='LLaMA models via Meta API / Replicate',
            category='meta',
            requires_api_key=True,
            requires_oauth=False,
            requires_cli=False,
            models=[
                {'value': 'meta-llama/llama-4-scout', 'label': 'Llama 4 Scout', 'tier': 'flagship'},
                {'value': 'meta-llama/llama-3.3-70b', 'label': 'Llama 3.3 70B', 'tier': 'standard'},
                {'value': 'meta-llama/llama-3.1-70b', 'label': 'Llama 3.1 70B', 'tier': 'standard'},
                {'value': 'meta-llama/llama-3.1-8b', 'label': 'Llama 3.1 8B', 'tier': 'fast'},
            ]
        )
        
        # --- Mistral AI ---
        self._providers['mistral'] = Provider(
            name='mistral',
            label='Mistral AI',
            description='Mistral models via Mistral AI API',
            category='special',
            requires_api_key=True,
            requires_oauth=False,
            requires_cli=False,
            models=[
                {'value': 'mistral-large-2', 'label': 'Mistral Large 2', 'tier': 'flagship'},
                {'value': 'mistral-medium-3', 'label': 'Mistral Medium 3', 'tier': 'standard'},
                {'value': 'mistral-small-3', 'label': 'Mistral Small 3', 'tier': 'fast'},
                {'value': 'codestral', 'label': 'Codestral', 'tier': 'standard'},
                {'value': 'mistral-7b', 'label': 'Mistral 7B', 'tier': 'fast'},
            ]
        )
        
        # --- DeepSeek ---
        self._providers['deepseek'] = Provider(
            name='deepseek',
            label='DeepSeek',
            description='DeepSeek models via DeepSeek API',
            category='special',
            requires_api_key=True,
            requires_oauth=False,
            requires_cli=False,
            models=[
                {'value': 'deepseek-r2', 'label': 'DeepSeek R2', 'tier': 'flagship', 'supportsThinking': True},
                {'value': 'deepseek-v3', 'label': 'DeepSeek V3', 'tier': 'standard'},
                {'value': 'deepseek-r1', 'label': 'DeepSeek R1', 'tier': 'standard', 'supportsThinking': True},
                {'value': 'deepseek-coder-v2', 'label': 'DeepSeek Coder V2', 'tier': 'standard'},
            ]
        )
        
        # --- AWS Bedrock ---
        self._providers['aws'] = Provider(
            name='aws',
            label='AWS (Bedrock)',
            description='Models via AWS Bedrock',
            category='aws',
            requires_api_key=True,
            requires_oauth=False,
            requires_cli=False,
            models=[
                {'value': 'anthropic.claude-opus-4-6-v1', 'label': 'Claude Opus 4.6 (Bedrock)', 'tier': 'flagship', 'supportsThinking': True},
                {'value': 'anthropic.claude-sonnet-4-5-v1', 'label': 'Claude Sonnet 4.5 (Bedrock)', 'tier': 'standard', 'supportsThinking': True},
                {'value': 'amazon.titan-text-premier-v1', 'label': 'Amazon Titan Premier', 'tier': 'standard'},
                {'value': 'meta.llama3-70b-instruct-v1', 'label': 'Llama 3 70B (Bedrock)', 'tier': 'standard'},
            ]
        )
        
        # --- Ollama (Local) ---
        self._providers['ollama'] = Provider(
            name='ollama',
            label='Ollama (Local)',
            description='Locally hosted models via Ollama',
            category='local',
            requires_api_key=False,
            requires_oauth=False,
            requires_cli=False,
            models=[
                {'value': 'llama3.3', 'label': 'Llama 3.3', 'tier': 'local'},
                {'value': 'llama3.2', 'label': 'Llama 3.2', 'tier': 'local'},
                {'value': 'llama3.1', 'label': 'Llama 3.1', 'tier': 'local'},
                {'value': 'mistral', 'label': 'Mistral', 'tier': 'local'},
                {'value': 'mistral-large', 'label': 'Mistral Large', 'tier': 'local'},
                {'value': 'deepseek-r1', 'label': 'DeepSeek R1', 'tier': 'local', 'supportsThinking': True},
                {'value': 'deepseek-coder-v2', 'label': 'DeepSeek Coder V2', 'tier': 'local'},
                {'value': 'qwen2.5-coder', 'label': 'Qwen 2.5 Coder', 'tier': 'local'},
                {'value': 'qwen2.5', 'label': 'Qwen 2.5', 'tier': 'local'},
                {'value': 'phi4', 'label': 'Phi-4', 'tier': 'local'},
                {'value': 'gemma3', 'label': 'Gemma 3', 'tier': 'local'},
                {'value': 'gemma2', 'label': 'Gemma 2', 'tier': 'local'},
                {'value': 'codellama', 'label': 'CodeLlama', 'tier': 'local'},
                {'value': 'yi', 'label': 'Yi', 'tier': 'local'},
                {'value': 'mixtral', 'label': 'Mixtral', 'tier': 'local'},
                {'value': 'vicuna', 'label': 'Vicuna', 'tier': 'local'},
                {'value': 'wizardlm', 'label': 'WizardLM', 'tier': 'local'},
                {'value': 'solar', 'label': 'Solar Pro', 'tier': 'local'},
                {'value': 'custom', 'label': 'Autre (saisie libre)', 'tier': 'local'},
            ]
        )
        
        # --- GitHub Copilot ---
        self._providers['copilot'] = Provider(
            name='copilot',
            label='GitHub Copilot',
            description='GitHub Copilot CLI models (gh copilot)',
            category='special',
            requires_api_key=False,
            requires_oauth=False,
            requires_cli=True,  # Requiert gh CLI
            models=[
                {'value': 'gpt-4o', 'label': 'GPT-4o (Copilot)', 'tier': 'flagship'},
                {'value': 'claude-3.5-sonnet', 'label': 'Claude 3.5 Sonnet (Copilot)', 'tier': 'standard'},
                {'value': 'o3-mini', 'label': 'o3-mini (Copilot)', 'tier': 'standard', 'supportsThinking': True},
                {'value': 'gpt-4o-mini', 'label': 'GPT-4o mini (Copilot)', 'tier': 'fast'},
            ]
        )
        
        # --- Grok (xAI) ---
        self._providers['grok'] = Provider(
            name='grok',
            label='Grok (xAI)',
            description='Grok models via xAI (Elon Musk)',
            category='special',
            requires_api_key=True,
            requires_oauth=False,
            requires_cli=False,
            models=[
                {'value': 'grok-2', 'label': 'Grok 2', 'tier': 'flagship', 'supportsThinking': True},
                {'value': 'grok-2-mini', 'label': 'Grok 2 Mini', 'tier': 'standard'},
                {'value': 'grok-beta', 'label': 'Grok Beta', 'tier': 'fast'}
            ]
        )
        
        # --- Windsurf AI (Codeium) ---
        self._providers['windsurf'] = Provider(
            name='windsurf',
            label='Windsurf (Codeium)',
            description='Windsurf AI models via Codeium platform - Service key or SSO authentication',
            category='special',
            requires_api_key=True,   # Service key (Personal Access Token)
            requires_oauth=True,     # Also supports SSO/OAuth authentication
            requires_cli=False,
            models=[
                {'value': 'swe-1.5', 'label': 'SWE-1.5', 'tier': 'flagship', 'supportsThinking': True},
                {'value': 'claude-opus-4.6', 'label': 'Claude Opus 4.6', 'tier': 'flagship', 'supportsThinking': True},
                {'value': 'claude-sonnet-4.6', 'label': 'Claude Sonnet 4.6', 'tier': 'standard', 'supportsThinking': True},
                {'value': 'gpt-5.2-low-thinking', 'label': 'GPT-5.2 Low Thinking', 'tier': 'standard'},
                {'value': 'swe-1.5-fast', 'label': 'SWE-1.5 Fast', 'tier': 'fast'},
                {'value': 'claude-sonnet-4.5', 'label': 'Claude Sonnet 4.5', 'tier': 'standard', 'supportsThinking': True},
                # Garder les modèles originaux pour compatibilité
                {'value': 'windsurf-codestral', 'label': 'Windsurf Codestral', 'tier': 'flagship'},
                {'value': 'windsurf-sonnet', 'label': 'Windsurf Sonnet', 'tier': 'standard'},
                {'value': 'windsurf-haiku', 'label': 'Windsurf Haiku', 'tier': 'fast'},
                {'value': 'windsurf-custom', 'label': 'Windsurf Custom', 'tier': 'standard'},
            ]
        )
        
        # --- Custom/Enterprise ---
        self._providers['custom'] = Provider(
            name='custom',
            label='Custom/Enterprise',
            description='Custom API endpoints',
            category='special',
            requires_api_key=True,
            requires_oauth=False,
            requires_cli=False,
            models=[
                {'value': 'custom-model-1', 'label': 'Custom Model 1', 'tier': 'flagship', 'supportsThinking': True},
                {'value': 'custom-model-2', 'label': 'Custom Model 2', 'tier': 'standard', 'supportsThinking': True},
                {'value': 'custom-model-3', 'label': 'Custom Model 3', 'tier': 'fast'},
                {'value': 'custom', 'label': 'Autre (saisie libre)', 'tier': 'local', 'supportsThinking': True},
            ]
        )
    
    def get_all_providers(self) -> List[Dict[str, Any]]:
        """Retourne tous les providers au format JSON"""
        return [
            {
                'name': p.name,
                'label': p.label,
                'description': p.description,
                'category': p.category,
                'requiresApiKey': p.requires_api_key,
                'requiresOAuth': p.requires_oauth,
                'requiresCLI': p.requires_cli,
                'models': p.models
            }
            for p in self._providers.values()
        ]
    
    def get_provider(self, name: str) -> Optional[Provider]:
        """Retourne un provider par son nom"""
        return self._providers.get(name)
    
    def check_provider_status(self, name: str, profiles: List[Dict[str, Any]] = None) -> ProviderStatus:
        """Vérifie le statut d'authentification d'un provider"""
        provider = self.get_provider(name)
        if not provider:
            return ProviderStatus(available=False, authenticated=False, error=f"Provider {name} not found")
        
        status = ProviderStatus(available=True, authenticated=False)
        
        try:
            # Cas spécial pour Anthropic (toujours disponible via OAuth/Claude Code)
            if name == 'anthropic':
                from core.auth import get_auth_token
                token = get_auth_token() or os.getenv("ANTHROPIC_API_KEY")
                status.authenticated = bool(token)
                return status
            
            # Cas spécial pour GitHub Copilot (vérification gh CLI)
            if name == 'copilot' and provider.requires_cli:
                status.authenticated = self._check_copilot_auth()
                return status
            
            # Vérification pour les providers requiring API key
            if provider.requires_api_key:
                has_profile = self._has_profile_for_provider(name, profiles or [])
                has_env_key = bool(os.getenv(f"{name.upper()}_API_KEY"))
                status.authenticated = has_profile or has_env_key
            
            # Vérification pour les providers requiring OAuth
            if provider.requires_oauth:
                status.authenticated = self._check_oauth_status(name)
        
        except Exception as e:
            status.error = str(e)
            status.authenticated = False
        
        return status
    
    def check_all_providers_status(self, profiles: List[Dict[str, Any]] = None) -> Dict[str, ProviderStatus]:
        """Vérifie le statut de tous les providers"""
        status = {}
        for name in self._providers.keys():
            status[name] = self.check_provider_status(name, profiles)
        return status
    
    def _check_copilot_auth(self) -> bool:
        """Vérifie si GitHub Copilot CLI est authentifié et fonctionnel"""
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=10
            )
            output = result.stdout + result.stderr
            if "Logged in to github.com" in output:
                copilot_check = subprocess.run(
                    ["gh", "copilot", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return copilot_check.returncode == 0
            return False
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return False
    
    def _has_profile_for_provider(self, provider_name: str, profiles: List[Dict[str, Any]]) -> bool:
        """Vérifie si un profil existe pour le provider"""
        for profile in profiles:
            if self._detect_provider_from_profile(profile) == provider_name:
                return True
        return False
    
    def _detect_provider_from_profile(self, profile: Dict[str, Any]) -> str:
        """Détecte le provider à partir d'un profil"""
        base_url = profile.get('baseUrl', '').lower()
        name = profile.get('name', '').lower()
        
        # Logique de détection
        if 'anthropic.com' in base_url or 'claude' in name:
            return 'anthropic'
        if 'openai.com' in base_url or 'openai' in name:
            return 'openai'
        if 'google.com' in base_url or 'gemini' in name:
            return 'google'
        if 'meta.com' in base_url or 'llama' in name:
            return 'meta'
        if 'mistral.ai' in base_url or 'mistral' in name:
            return 'mistral'
        if 'deepseek.com' in base_url or 'deepseek' in name:
            return 'deepseek'
        if 'aws.amazon.com' in base_url or 'bedrock' in name:
            return 'aws'
        if 'ollama' in base_url or 'ollama' in name:
            return 'ollama'
        if 'x.ai' in base_url or 'grok' in name:
            return 'grok'
        if 'codeium.com' in base_url or 'windsurf' in name or 'api.windsurf.com' in base_url:
            return 'windsurf'

        return 'custom'
    
    def _check_oauth_status(self, provider_name: str) -> bool:
        """Vérifie le statut OAuth/SSO pour un provider"""
        # Logique OAuth spécifique
        if provider_name == 'anthropic':
            # Vérifier le token Claude Code OAuth
            return bool(os.getenv("CLAUDE_CODE_OAUTH_TOKEN") or os.getenv("ANTHROPIC_API_KEY"))
        if provider_name == 'windsurf':
            # Windsurf SSO: check for Codeium OAuth token from local IDE installation
            return bool(os.getenv("WINDSURF_OAUTH_TOKEN") or os.getenv("CODEIUM_API_KEY"))
        return False
    
    def add_provider(self, provider: Provider) -> None:
        """Ajoute dynamiquement un nouveau provider"""
        self._providers[provider.name] = provider
    
    def remove_provider(self, name: str) -> bool:
        """Supprime un provider"""
        return name in self._providers and self._providers.pop(name) is not None
    
    def update_provider(self, name: str, updates: Dict[str, Any]) -> bool:
        """Met à jour un provider existant"""
        existing = self._providers.get(name)
        if not existing:
            return False
        
        for key, value in updates.items():
            if hasattr(existing, key):
                setattr(existing, key, value)
        
        return True

# Singleton instance
provider_registry = ProviderRegistry.get_instance()

# Fonctions utilitaires pour la compatibilité avec l'ancien code
def get_providers_dict():
    """Fonction de compatibilité - retourne le statut des providers au format ancien"""
    status = provider_registry.check_all_providers_status()
    return {name: status.authenticated for name, status in status.items()}

def list_available_providers() -> List[str]:
    """Retourne la liste des providers LLM disponibles sur cette machine."""
    providers_dict = get_providers_dict()
    return [name for name, ok in providers_dict.items() if ok]

def validate_provider(provider: str) -> bool:
    """Vérifie si le provider est disponible/configuré."""
    providers_dict = get_providers_dict()
    return provider in providers_dict and providers_dict[provider]

def get_provider_status() -> Dict[str, bool]:
    """Retourne le statut de disponibilité de chaque provider connu."""
    return get_providers_dict()

def get_providers_with_status(profiles: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Retourne les providers avec leur statut (format compatible avec l'API existante)"""
    status = provider_registry.check_all_providers_status(profiles)
    providers = provider_registry.get_all_providers()
    
    # Convertir le statut au format booléen pour compatibilité
    simplified_status = {name: status.authenticated for name, status in status.items()}
    
    return {
        'providers': providers,
        'status': simplified_status
    }

def get_provider_models(provider_name: str) -> List[Dict[str, Any]]:
    """Retourne les modèles pour un provider"""
    provider = provider_registry.get_provider(provider_name)
    return provider.models if provider else []

if __name__ == "__main__":
    print("Providers disponibles :")
    for name, status in get_provider_status().items():
        print(f"- {name}: {'OK' if status else 'Non configuré'}")