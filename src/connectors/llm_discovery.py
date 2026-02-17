"""
Découverte dynamique des providers LLM disponibles.
Permet d'auto-détecter les connecteurs installés/configurés (pattern plugin).
"""
import importlib
import pkgutil
from typing import List, Type
from .llm_base import BaseLLMProvider


def discover_llm_providers() -> List[Type[BaseLLMProvider]]:
    """Retourne la liste des classes de providers LLM disponibles dynamiquement."""
    import src.connectors
    providers = []
    for _, module_name, is_pkg in pkgutil.iter_modules(src.connectors.__path__):
        if module_name.startswith('llm_') and module_name != 'llm_base' and not is_pkg:
            module = importlib.import_module(f"src.connectors.{module_name}")
            for attr in dir(module):
                obj = getattr(module, attr)
                if isinstance(obj, type) and issubclass(obj, BaseLLMProvider) and obj is not BaseLLMProvider:
                    providers.append(obj)
    return providers


def get_provider_by_name(name: str) -> Type[BaseLLMProvider] | None:
    """Retourne la classe provider correspondant au nom donné."""
    for provider_cls in discover_llm_providers():
        if provider_cls.get_name() == name:
            return provider_cls
    return None