import importlib

from fastapi.testclient import TestClient

mod = importlib.import_module("main")
app = mod.app

client = TestClient(app)


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["ok"] is True
