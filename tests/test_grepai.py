import pytest

try:
    import grepai
except ImportError:
    pytest.skip("grepai n'est pas installé", allow_module_level=True)


def test_grepai_basic():
    # Test basique : recherche d'un motif dans un fichier
    results = grepai.grep(pattern="TODO", file_path="README.md")
    assert isinstance(results, list)
    # Le résultat peut être vide, mais ne doit pas provoquer d'erreur
