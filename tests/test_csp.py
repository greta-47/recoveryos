import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

import main


def test_csp_header_present_and_strict(tmp_path, monkeypatch):
    monkeypatch.setenv("CSP_APP_ORIGIN", "https://app.my-domain.com")
    monkeypatch.setenv("CSP_CDN_LIST", "https://cdn.example.com, https://static.example.org")
    monkeypatch.delenv("CSP_REPORT_ONLY", raising=False)

    importlib.reload(main)
    client = TestClient(main.app)
    r = client.get("/healthz")
    assert r.status_code == 200
    h = r.headers.get("content-security-policy")
    assert h is not None
    assert "'unsafe-inline'" not in h.lower()
    assert "'unsafe-eval'" not in h.lower()
    assert "https://app.my-domain.com" in h
    assert "https://cdn.example.com" in h


def test_csp_report_only(monkeypatch):
    monkeypatch.setenv("CSP_REPORT_ONLY", "true")
    importlib.reload(main)
    client = TestClient(main.app)
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.headers.get("content-security-policy") is None
    assert r.headers.get("content-security-policy-report-only") is not None
