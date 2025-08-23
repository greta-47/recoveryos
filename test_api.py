from fastapi.testclient import TestClient

from main import app
from test_config import setup_test_environment

setup_test_environment()

client = TestClient(app)


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json().get("ok") is True


def test_agents_endpoint_without_api_key():
    """Test that agents endpoint works in test environment."""
    r = client.post("/agents/run", json={
        "topic": "test optimization strategies",
        "horizon": "30 days", 
        "okrs": "test objectives"
    })
    assert r.status_code in [200, 503]
