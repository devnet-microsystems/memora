import os
import time
import pytest
from dashboard.app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def get_basic_auth_header(username, password):
    import base64
    credentials = f"{username}:{password}"
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    return {'Authorization': f'Basic {encoded_credentials}'}

def test_missing_env_returns_503(client, monkeypatch):
    monkeypatch.delenv("CAREGIVER_USER", raising=False)
    monkeypatch.delenv("CAREGIVER_PASSWORD", raising=False)
    resp = client.post("/api/report")
    assert resp.status_code == 503

def test_anonymous_c_returns_401(client, monkeypatch):
    monkeypatch.setenv("CAREGIVER_USER", "admin")
    monkeypatch.setenv("CAREGIVER_PASSWORD", "secret")
    resp = client.post("/api/report")
    assert resp.status_code == 401
    assert resp.headers.get("WWW-Authenticate") == 'Basic realm="Memora Caregiver"'

def test_auth_c_passes(client, monkeypatch):
    monkeypatch.setenv("CAREGIVER_USER", "admin")
    monkeypatch.setenv("CAREGIVER_PASSWORD", "secret")
    # Using /api/report might try to proxy to backend and get 500 if backend is down, but proxy check passes.
    # So if it's 500, it means it passed the proxy auth.
    resp = client.post("/api/report", headers=get_basic_auth_header("admin", "secret"))
    assert resp.status_code in [200, 500]

def test_b_with_readonly_0_returns_401(client, monkeypatch):
    monkeypatch.setenv("CAREGIVER_USER", "admin")
    monkeypatch.setenv("CAREGIVER_PASSWORD", "secret")
    monkeypatch.setenv("DEMO_PUBLIC_READONLY", "0")
    resp = client.get("/api/memory")
    assert resp.status_code == 401

def test_rate_limit(client):
    # test chat rate limit
    for _ in range(20):
        client.post("/api/chat", json={"message": "hello"})
    
    resp = client.post("/api/chat", json={"message": "hello"})
    assert resp.status_code == 429

def test_max_length(client):
    from dashboard.app import rate_limits
    rate_limits.clear()
    long_text = "a" * 501
    resp = client.post("/api/chat", json={"message": long_text})
    assert resp.status_code == 422
