from api.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["ok"] is True
