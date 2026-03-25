"""
conftest.py for integrations/graphiti tests.
These tests require external services (Ollama, LadybugDB) that are not
available in the standard test environment. All tests are skipped.
"""

import pytest


@pytest.fixture(autouse=True)
def skip_external_service_tests():
    """Skip all tests in this directory — they require Ollama and LadybugDB."""
    pytest.skip("requires external services: Ollama/LadybugDB")


# Fixtures to prevent collection errors from non-standard test signatures
@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path)


@pytest.fixture
def database():
    return "test_db"


@pytest.fixture
def test_db_path(tmp_path):
    return tmp_path
