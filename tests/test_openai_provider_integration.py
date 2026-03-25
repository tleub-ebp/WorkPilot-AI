import os
import pytest
import sys
import importlib.util
from pathlib import Path

# S'assurer que la racine du projet est dans le chemin
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import direct des modules pour éviter les problèmes d'import imbriqués
def import_module_from_file(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Import des modules dépendants
connectors_dir = project_root / "src" / "connectors"
llm_base = import_module_from_file("src.connectors.llm_base", connectors_dir / "llm_base.py")
sys.modules["src.connectors.llm_base"] = llm_base

# Import du provider OpenAI
OpenAIProvider = import_module_from_file("src.connectors.llm_openai", connectors_dir / "llm_openai.py").OpenAIProvider

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