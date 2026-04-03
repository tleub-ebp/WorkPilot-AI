"""
Tests unitaires pour la découverte, la configuration et la sélection des providers LLM.
"""
import os

import pytest

from src.connectors.llm_base import BaseLLMProvider
from src.connectors.llm_config import (
    delete_provider_config,
    list_provider_configs,
    load_provider_config,
    save_provider_config,
)
from src.connectors.llm_discovery import discover_llm_providers


class DummyProvider(BaseLLMProvider):
    def __init__(self, key=None):
        self.key = key
    def connect(self):
        if not self.key:
            raise Exception("Missing key")
    def validate(self):
        return self.key == "valid"
    def generate(self, prompt, **kwargs):
        return f"dummy: {prompt}"
    def get_capabilities(self):
        return {"models": ["dummy"]}
    def get_config_schema(self):
        return {"key": "str"}
    def get_name(self):
        return "dummy"

def test_save_and_load_provider_config(tmp_path, monkeypatch):
    monkeypatch.setattr("src.connectors.llm_config.CONFIG_FILE", tmp_path / "llm.json")
    save_provider_config("dummy", {"key": "valid"})
    config = load_provider_config("dummy")
    assert config["key"] == "valid"
    assert "dummy" in list_provider_configs()
    delete_provider_config("dummy")
    assert load_provider_config("dummy") is None

def test_discover_llm_providers(monkeypatch):
    monkeypatch.setattr("src.connectors.llm_discovery.discover_llm_providers", lambda: [DummyProvider])
    providers = discover_llm_providers()
    assert any(p().get_name() == "dummy" for p in providers)

def test_provider_validation():
    provider = DummyProvider(key="valid")
    provider.connect()
    assert provider.validate()
    provider2 = DummyProvider(key="invalid")
    with pytest.raises((ValueError, ConnectionError, RuntimeError)):
        provider2.connect()
