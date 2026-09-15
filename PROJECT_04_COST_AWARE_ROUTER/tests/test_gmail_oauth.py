from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from api_server import app


def _auth_headers(user: str = "gmail-user") -> dict[str, str]:
    return {"Authorization": f"Bearer {user}"}


def _state_from_redirect(response):
    location = response.headers.get("location", "")
    if not location:
        raise AssertionError("Expected redirect location")
    query = parse_qs(urlparse(location).query)
    return query["state"][0]


def test_gmail_oauth_state_round_trip_and_callback(monkeypatch):
    monkeypatch.setenv("GMAIL_CLIENT_ID", "demo-google-client")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "demo-google-secret")
    monkeypatch.setenv("GMAIL_REDIRECT_URI", "http://localhost:8000/api/connectors/gmail/callback")
    monkeypatch.setenv("SESSION_SECRET_KEY", "gmail-phase5-secret")
    monkeypatch.setattr("app.auth.clerk.verify_clerk_token", lambda token: {"sub": "gmail-user"})

    def fake_exchange(code: str, redirect_uri: str):
        assert code == "demo-code"
        return {"access_token": "demo-google-token", "refresh_token": "demo-refresh-token", "expires_in": 3600}

    def fake_user(token: str):
        assert token == "demo-google-token"
        return {"email": "user@gmail.com", "name": "Demo User", "picture": "https://example.com/avatar.png"}

    monkeypatch.setattr("api_server._exchange_google_code", fake_exchange)
    monkeypatch.setattr("api_server._fetch_google_user_info", fake_user)

    client = TestClient(app)
    redirect = client.get("/api/connectors/gmail/connect", follow_redirects=False, headers=_auth_headers())
    assert redirect.status_code in {200, 302, 307}

    state = _state_from_redirect(redirect)
    callback = client.get(
        "/api/connectors/gmail/callback",
        params={"code": "demo-code", "state": state},
        follow_redirects=False,
        headers=_auth_headers(),
    )
    assert callback.status_code in {200, 302, 307}

    status = client.get("/api/connectors/gmail/status", headers=_auth_headers())
    assert status.status_code == 200
    payload = status.json()
    assert payload["provider"] == "gmail"
    assert payload["connected"] is True
    assert payload["account"]["email"] == "user@gmail.com"
    assert payload["tool_count"] > 0


def test_gmail_oauth_rejects_invalid_or_expired_state(monkeypatch):
    monkeypatch.setenv("GMAIL_CLIENT_ID", "demo-google-client")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "demo-google-secret")
    monkeypatch.setenv("GMAIL_REDIRECT_URI", "http://localhost:8000/api/connectors/gmail/callback")
    monkeypatch.setenv("SESSION_SECRET_KEY", "gmail-phase5-secret-2")
    monkeypatch.setattr("app.auth.clerk.verify_clerk_token", lambda token: {"sub": "gmail-user"})

    client = TestClient(app)
    redirect = client.get("/api/connectors/gmail/connect", follow_redirects=False, headers=_auth_headers())
    assert redirect.status_code in {200, 302, 307}

    invalid = client.get(
        "/api/connectors/gmail/callback",
        params={"code": "bad-code", "state": "wrong-state"},
        follow_redirects=False,
        headers=_auth_headers(),
    )
    assert invalid.status_code in {400, 401, 302}


def test_gmail_user_isolation_and_disconnect(monkeypatch):
    monkeypatch.setenv("GMAIL_CLIENT_ID", "demo-google-client")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "demo-google-secret")
    monkeypatch.setenv("GMAIL_REDIRECT_URI", "http://localhost:8000/api/connectors/gmail/callback")
    monkeypatch.setenv("SESSION_SECRET_KEY", "gmail-phase5-secret-3")

    def fake_verify(token: str):
        if token == "gmail-user-a":
            return {"sub": "gmail-user-a"}
        if token == "gmail-user-b":
            return {"sub": "gmail-user-b"}
        return {"sub": token}

    monkeypatch.setattr("app.auth.clerk.verify_clerk_token", fake_verify)
    monkeypatch.setattr("api_server._exchange_google_code", lambda code, redirect_uri: {"access_token": "token-a", "refresh_token": "refresh-a", "expires_in": 3600})
    monkeypatch.setattr("api_server._fetch_google_user_info", lambda token: {"email": "user-a@gmail.com", "name": "User A"})

    client_a = TestClient(app)
    client_b = TestClient(app)

    redirect_a = client_a.get("/api/connectors/gmail/connect", follow_redirects=False, headers=_auth_headers("gmail-user-a"))
    state_a = _state_from_redirect(redirect_a)
    client_a.get(
        "/api/connectors/gmail/callback",
        params={"code": "demo-code", "state": state_a},
        follow_redirects=False,
        headers=_auth_headers("gmail-user-a"),
    )

    status_a = client_a.get("/api/connectors/gmail/status", headers=_auth_headers("gmail-user-a"))
    status_b = client_b.get("/api/connectors/gmail/status", headers=_auth_headers("gmail-user-b"))

    assert status_a.json()["connected"] is True
    assert status_b.json()["connected"] is False

    disconnect = client_a.post("/api/connectors/gmail/disconnect", headers=_auth_headers("gmail-user-a"))
    assert disconnect.status_code == 200
    assert client_a.get("/api/connectors/gmail/status", headers=_auth_headers("gmail-user-a")).json()["connected"] is False
