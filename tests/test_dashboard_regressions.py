"""Regression tests for the Flask proxy (judge-facing behaviour)."""
import time
import pytest
from unittest.mock import patch, MagicMock

import dashboard.app as dash


@pytest.fixture
def client(monkeypatch):
    dash.app.config["TESTING"] = True
    monkeypatch.setenv("CAREGIVER_USER", "admin")
    monkeypatch.setenv("CAREGIVER_PASSWORD", "secret")
    dash.rate_limits.clear()
    with dash.app.test_client() as c:
        yield c


def test_caregiver_page_is_public_for_judges(client):
    """The page itself must open without a login (writes are still protected at the API level)."""
    with patch("dashboard.app.requests.get", side_effect=dash.requests.RequestException("down")):
        assert client.get("/caregiver").status_code == 200
    assert client.get("/judges").status_code == 200
    assert client.get("/patient").status_code == 200


def test_writes_still_need_login(client):
    assert client.post("/api/onboarding", json={"text": "x"}).status_code == 401
    assert client.delete("/api/memory/abc").status_code == 401
    assert client.post("/api/pending/abc/approve", json={}).status_code == 401


def test_non_ascii_credentials_do_not_crash(client):
    import base64
    token = base64.b64encode("àdmin:pässword".encode()).decode()
    resp = client.post("/api/report", headers={"Authorization": f"Basic {token}"})
    assert resp.status_code == 401


def test_med_confirm_accepts_real_memory_payload(client):
    """/memory exposes 'group' (not 'type'): the old check rejected every med with HTTP 400."""
    fake_mem = MagicMock()
    fake_mem.json.return_value = {"nodes": [{"id": "memantina", "label": "Memantina", "group": "med"}]}
    fake_post = MagicMock()
    fake_post.json.return_value = {"status": "ok"}
    fake_post.status_code = 200
    with patch("dashboard.app.requests.get", return_value=fake_mem), \
         patch("dashboard.app.requests.post", return_value=fake_post):
        ok = client.post("/api/med/confirm", json={"med_id": "memantina", "status": "confirmed"})
        bad = client.post("/api/med/confirm", json={"med_id": "nope", "status": "confirmed"})
    assert ok.status_code == 200
    assert bad.status_code == 400


def test_query_string_is_url_encoded(client):
    fake = MagicMock(); fake.json.return_value = {}; fake.status_code = 200
    with patch("dashboard.app.requests.get", return_value=fake) as g:
        client.get("/api/stats?days=7&evil=../admin%26x%3D1")
    _, kwargs = g.call_args
    assert kwargs["params"] == {"days": "7", "evil": "../admin&x=1"}


def test_chat_length_limit_uses_the_real_field(client):
    resp = client.post("/api/chat", json={"user_input": "a" * 501})
    assert resp.status_code == 422


def test_daily_llm_budget_resets_every_day(client, monkeypatch):
    monkeypatch.setenv("MAX_DAILY_LLM_CALLS", "1")
    fake = MagicMock(); fake.json.return_value = {"response": "ok"}; fake.status_code = 200
    dash.daily_llm_calls, dash.daily_llm_day = 5, "1999-01-01"   # yesterday's exhausted counter
    with patch("dashboard.app.requests.post", return_value=fake):
        assert client.post("/api/chat", json={"user_input": "hi"}).status_code == 200
        assert client.post("/api/chat", json={"user_input": "hi again"}).status_code == 429


# ---- Caregiver session auth tests ----

def test_caregiver_login_success(client):
    resp = client.post("/api/caregiver/login", json={"username": "admin", "password": "secret"})
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"
    # Cookie di sessione deve essere presente e HttpOnly
    set_cookie = resp.headers.get("Set-Cookie", "")
    assert "memora_caregiver_session=" in set_cookie
    assert "HttpOnly" in set_cookie


def test_caregiver_login_wrong_password(client):
    resp = client.post("/api/caregiver/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401


def test_caregiver_me_unauthenticated(client):
    resp = client.get("/api/caregiver/me")
    assert resp.status_code == 401
    assert not resp.get_json()["authenticated"]


def test_caregiver_me_authenticated(client):
    with client.session_transaction() as sess:
        sess["caregiver_authenticated"] = True
        sess["caregiver_username"] = "admin"
    resp = client.get("/api/caregiver/me")
    assert resp.status_code == 200
    assert resp.get_json()["authenticated"] is True


def test_acknowledge_anonymous_rejected(client):
    """Visitatore anonimo senza sessione non può acknowledge un'alerta."""
    resp = client.post("/api/alerts/abc/ack", json={})
    assert resp.status_code == 401


def test_acknowledge_authenticated_accepted(client, monkeypatch):
    """Caregiver autenticato può acknowledge un'alerta (proxy al backend restituisce 200)."""
    fake = MagicMock(); fake.json.return_value = {"status": "acknowledged", "id": "abc"}; fake.status_code = 200
    with patch("dashboard.app.requests.post", return_value=fake):
        with client.session_transaction() as sess:
            sess["caregiver_authenticated"] = True
            sess["caregiver_username"] = "admin"
        resp = client.post("/api/alerts/abc/ack", json={})
    assert resp.status_code == 200


def test_acknowledge_expired_session_rejected(client, monkeypatch):
    """Sessione scaduta/inesistente viene rifiutata anche se il backend fosse disponibile."""
    fake = MagicMock(); fake.json.return_value = {"status": "acknowledged"}; fake.status_code = 200
    with patch("dashboard.app.requests.post", return_value=fake) as mock_post:
        # Sessione senza authenticated
        with client.session_transaction() as sess:
            sess["caregiver_username"] = "admin"  # ma non authenticated
        resp = client.post("/api/alerts/abc/ack", json={})
    assert resp.status_code == 401
    mock_post.assert_not_called()
