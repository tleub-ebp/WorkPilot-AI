"""
Provider Registry: auto-discovery et validation des providers LLM disponibles
"""
import os
from typing import List, Dict
from core.auth import get_auth_token

def get_providers_dict():
    return {
        "claude_opus": bool(get_auth_token() or os.getenv("ANTHROPIC_API_KEY")),
        "claude_sonnet": bool(get_auth_token() or os.getenv("ANTHROPIC_API_KEY")),
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "ollama": os.path.exists(os.getenv("OLLAMA_BASE_URL", "/usr/bin/ollama")),
        "mistral": bool(os.getenv("MISTRAL_API_KEY")),
        "groq": bool(os.getenv("GROQ_API_KEY")),
        "local": os.path.exists(os.getenv("LOCAL_LLM_PATH", "./local_llm")),
    }

def list_available_providers() -> List[str]:
    """Retourne la liste des providers LLM disponibles sur cette machine."""
    return [name for name, ok in get_providers_dict().items() if ok]

def validate_provider(provider: str) -> bool:
    """Vérifie si le provider est disponible/configuré."""
    return provider in get_providers_dict() and get_providers_dict()[provider]

def get_provider_status() -> Dict[str, bool]:
    """Retourne le statut de disponibilité de chaque provider connu."""
    return get_providers_dict()

print("DEBUG: CLAUDE_CODE_OAUTH_TOKEN =", os.getenv("CLAUDE_CODE_OAUTH_TOKEN"))
print("DEBUG: ANTHROPIC_API_KEY =", os.getenv("ANTHROPIC_API_KEY"))
print("DEBUG: OPENAI_API_KEY =", os.getenv("OPENAI_API_KEY"))

if __name__ == "__main__":
    print("Providers disponibles :")
    for name, status in get_provider_status().items():
        print(f"- {name}: {'OK' if status else 'Non configuré'}")