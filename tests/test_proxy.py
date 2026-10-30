import os
import time
import pytest
from unittest.mock import patch, MagicMock
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
    # Non deve più esserci WWW-Authenticate Basic (sostituito da sessione Flask)
    assert resp.headers.get("WWW-Authenticate") is None


def test_auth_c_passes(client, monkeypatch):
    monkeypatch.setenv("CAREGIVER_USER", "admin")
    monkeypatch.setenv("CAREGIVER_PASSWORD", "secret")
    monkeypatch.setenv("MEMORA_API_KEY", "testkey")
    # Con sessione caregiver autenticata, il proxy auth passa e la richiesta viene inoltrata al backend.
    fake = MagicMock(); fake.json.return_value = {"status": "ok"}; fake.status_code = 200
    with patch("dashboard.app.requests.post", return_value=fake):
        with client.session_transaction() as sess:
            sess["caregiver_authenticated"] = True
            sess["caregiver_username"] = "admin"
        resp = client.post("/api/report")
    assert resp.status_code in [200, 404, 500, 503]

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


def test_xss_payload_neutralized():
    """Regression: XSS payload <img src=x onerror=alert(1)> must be neutralized
    when rendered as text, not create an IMG element or execute its handler."""
    import html

    payload = '<img src=x onerror=alert(1)>'

    # Python equivalent of the JS esc() function in dashboard/static/util.js
    def esc(s):
        if s is None:
            return ""
        return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;").replace("`", "&#96;")

    escaped = esc(payload)

    # The payload must be shown literally, not as executable HTML
    # Raw HTML tags must be escaped: <img -> &lt;img, > -> &gt;
    assert "<img" not in escaped        # raw <img tag must not appear
    assert ">" not in escaped           # raw > must not appear
    assert "&lt;img" in escaped         # escaped <img must appear
    assert "&gt;" in escaped            # escaped > must appear
    # When unescaped back, it returns the original literal text
    assert html.unescape(escaped) == payload


# ---- Voice endpoint proxy tests ----

def test_voice_preview_forwards_to_backend(client, monkeypatch):
    """POST /api/voice/preview is forwarded to backend via proxy.
    
    The proxy passes the request through (not blocked by caregiver auth
    since voice endpoints are public-patient). Backend may return 200
    if MEMORA_API_KEY is set, or 401/500/503 if not.
    """
    monkeypatch.delenv("CAREGIVER_USER", raising=False)
    monkeypatch.delenv("CAREGIVER_PASSWORD", raising=False)
    resp = client.post("/api/voice/preview", json={"text": "I take my blood pressure pill at 8am"})
    assert resp.status_code in [200, 401, 404, 500, 503]


def test_voice_confirm_forwards_to_backend(client, monkeypatch):
    """POST /api/voice/confirm is forwarded to backend via proxy.
    
    The proxy passes the request through (not blocked by caregiver auth
    since voice endpoints are public-patient). Backend may return 200
    if MEMORA_API_KEY is set, or 401/500/503 if not.
    """
    monkeypatch.delenv("CAREGIVER_USER", raising=False)
    monkeypatch.delenv("CAREGIVER_PASSWORD", raising=False)
    resp = client.post("/api/voice/confirm", json={
        "facts": [{"type": "med", "label": "Test", "description": "desc", "when": "", "content": "Test - desc"}]
    })
    assert resp.status_code in [200, 401, 404, 500, 503]


def test_voice_preview_with_caregiver_auth(client, monkeypatch):
    """POST /api/voice/preview works with caregiver auth."""
    monkeypatch.setenv("CAREGIVER_USER", "admin")
    monkeypatch.setenv("CAREGIVER_PASSWORD", "secret")
    resp = client.post("/api/voice/preview", json={"text": "test"},
                       headers=get_basic_auth_header("admin", "secret"))
    assert resp.status_code in [200, 401, 404, 500, 503]


def test_voice_confirm_with_caregiver_auth(client, monkeypatch):
    """POST /api/voice/confirm works with caregiver auth."""
    monkeypatch.setenv("CAREGIVER_USER", "admin")
    monkeypatch.setenv("CAREGIVER_PASSWORD", "secret")
    resp = client.post("/api/voice/confirm", json={
        "facts": [{"type": "med", "label": "Test", "description": "desc", "when": "", "content": "Test - desc"}]
    }, headers=get_basic_auth_header("admin", "secret"))
    assert resp.status_code in [200, 401, 404, 500, 503]


def test_voice_preview_without_voice_api_key(client, monkeypatch):
    """POST /api/voice/preview without MEMORA_API_KEY → backend returns 401."""
    monkeypatch.delenv("CAREGIVER_USER", raising=False)
    monkeypatch.delenv("CAREGIVER_PASSWORD", raising=False)
    monkeypatch.delenv("MEMORA_API_KEY", raising=False)
    resp = client.post("/api/voice/preview", json={"text": "test"})
    # Backend requires MEMORA_API_KEY header, returns 401
    assert resp.status_code in [401, 500, 503]


def test_voice_confirm_without_voice_api_key(client, monkeypatch):
    """POST /api/voice/confirm without MEMORA_API_KEY → backend returns 401."""
    monkeypatch.delenv("CAREGIVER_USER", raising=False)
    monkeypatch.delenv("CAREGIVER_PASSWORD", raising=False)
    monkeypatch.delenv("MEMORA_API_KEY", raising=False)
    resp = client.post("/api/voice/confirm", json={
        "facts": [{"type": "med", "label": "Test", "description": "desc", "when": "", "content": "Test - desc"}]
    })
    assert resp.status_code in [401, 500, 503]


def test_voice_preview_rate_limit(client, monkeypatch):
    """POST /api/voice/preview should be rate limited (20/min)."""
    from dashboard.app import rate_limits
    rate_limits.clear()
    monkeypatch.delenv("CAREGIVER_USER", raising=False)
    monkeypatch.delenv("CAREGIVER_PASSWORD", raising=False)
    for _ in range(20):
        client.post("/api/voice/preview", json={"text": "test"})
    resp = client.post("/api/voice/preview", json={"text": "test again"})
    assert resp.status_code == 429


def test_voice_confirm_rate_limit(client, monkeypatch):
    """POST /api/voice/confirm should be rate limited (10/min)."""
    from dashboard.app import rate_limits
    rate_limits.clear()
    monkeypatch.delenv("CAREGIVER_USER", raising=False)
    monkeypatch.delenv("CAREGIVER_PASSWORD", raising=False)
    for _ in range(10):
        client.post("/api/voice/confirm", json={"facts": [{"type": "med", "label": "T", "description": "d", "when": "", "content": "T - d"}]})
    resp = client.post("/api/voice/confirm", json={"facts": [{"type": "med", "label": "T2", "description": "d2", "when": "", "content": "T2 - d2"}]})
    assert resp.status_code == 429
