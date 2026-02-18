import os
import pytest
from src.connectors.llm_openai import OpenAIProvider
import requests

@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Clé API OpenAI non définie dans les variables d'environnement."
)
def test_openai_provider_validate_and_generate():
    api_key = os.getenv("OPENAI_API_KEY")
    # Vérifie si le crédit est à zéro ou facturation absente
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        resp = requests.get("https://api.openai.com/v1/dashboard/billing/credit_grants", headers=headers, timeout=10)
        if resp.status_code != 200 or resp.json().get("total_available", 0) == 0:
            pytest.skip("Clé OpenAI sans crédit ou facturation inactive : test ignoré.")
    except Exception:
        pytest.skip("Impossible de vérifier le crédit OpenAI : test ignoré.")
    provider = OpenAIProvider(api_key=api_key, model="gpt-3.5-turbo")
    assert provider.validate() is True
    prompt = "Dis bonjour en français."
    result = provider.generate(prompt)
    assert isinstance(result, str)
    assert "bonjour".lower() in result.lower()