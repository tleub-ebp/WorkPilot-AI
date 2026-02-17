import requests

def test_api_providers():
    r = requests.get("http://localhost:9000/providers")
    assert r.status_code == 200
    data = r.json()
    assert "providers" in data
    assert "status" in data
    assert isinstance(data["providers"], list)
    assert isinstance(data["status"], dict)

def test_api_select_provider():
    r = requests.post("http://localhost:9000/providers/select", data={"provider": "openai"})
    assert r.status_code == 200
    data = r.json()
    assert data["selected"] == "openai"