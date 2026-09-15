from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from api_server import app


def _auth_headers(user: str = "drive-user") -> dict[str, str]:
    return {"Authorization": f"Bearer {user}"}


def _state_from_redirect(response):
    location = response.headers.get("location", "")
    if not location:
        raise AssertionError("Expected redirect location")
    query = parse_qs(urlparse(location).query)
    return query["state"][0]


def test_google_drive_oauth_state_round_trip_and_callback(monkeypatch):
    monkeypatch.setenv("GOOGLE_DRIVE_CLIENT_ID", "demo-drive-client")
    monkeypatch.setenv("GOOGLE_DRIVE_CLIENT_SECRET", "demo-drive-secret")
    monkeypatch.setenv("GOOGLE_DRIVE_REDIRECT_URI", "http://localhost:8000/api/connectors/google_drive/callback")
    monkeypatch.setenv("SESSION_SECRET_KEY", "drive-phase6-secret")
    monkeypatch.setattr("app.auth.clerk.verify_clerk_token", lambda token: {"sub": "drive-user"})

    def fake_exchange(code: str, redirect_uri: str):
        assert code == "demo-drive-code"
        return {"access_token": "demo-drive-token", "refresh_token": "demo-drive-refresh", "expires_in": 3600}

    def fake_user(token: str):
        assert token == "demo-drive-token"
        return {"email": "user@drive.example", "name": "Drive User", "picture": "https://example.com/avatar.png"}

    monkeypatch.setattr("api_server._exchange_google_code_for_provider", fake_exchange)
    monkeypatch.setattr("api_server._fetch_google_user_info", fake_user)

    client = TestClient(app)
    redirect = client.get("/api/connectors/google_drive/connect", follow_redirects=False, headers=_auth_headers())
    assert redirect.status_code in {200, 302, 307}

    state = _state_from_redirect(redirect)
    callback = client.get(
        "/api/connectors/google_drive/callback",
        params={"code": "demo-drive-code", "state": state},
        follow_redirects=False,
        headers=_auth_headers(),
    )
    assert callback.status_code in {200, 302, 307}

    status = client.get("/api/connectors/google_drive/status", headers=_auth_headers())
    assert status.status_code == 200
    payload = status.json()
    assert payload["provider"] == "google_drive"
    assert payload["connected"] is True
    assert payload["account"]["email"] == "user@drive.example"
    assert payload["tool_count"] > 0


def test_google_drive_user_isolation_and_disconnect(monkeypatch):
    monkeypatch.setenv("GOOGLE_DRIVE_CLIENT_ID", "demo-drive-client")
    monkeypatch.setenv("GOOGLE_DRIVE_CLIENT_SECRET", "demo-drive-secret")
    monkeypatch.setenv("GOOGLE_DRIVE_REDIRECT_URI", "http://localhost:8000/api/connectors/google_drive/callback")
    monkeypatch.setenv("SESSION_SECRET_KEY", "drive-phase6-secret-2")

    def fake_verify(token: str):
        if token == "drive-user-a":
            return {"sub": "drive-user-a"}
        if token == "drive-user-b":
            return {"sub": "drive-user-b"}
        return {"sub": token}

    monkeypatch.setattr("app.auth.clerk.verify_clerk_token", fake_verify)
    monkeypatch.setattr(
        "api_server._exchange_google_code_for_provider",
        lambda code, redirect_uri: {"access_token": "token-a", "refresh_token": "refresh-a", "expires_in": 3600},
    )
    monkeypatch.setattr(
        "api_server._fetch_google_user_info",
        lambda token: {"email": "user-a@drive.example", "name": "User A"},
    )

    client_a = TestClient(app)
    client_b = TestClient(app)

    redirect_a = client_a.get("/api/connectors/google_drive/connect", follow_redirects=False, headers=_auth_headers("drive-user-a"))
    state_a = _state_from_redirect(redirect_a)
    client_a.get(
        "/api/connectors/google_drive/callback",
        params={"code": "demo-drive-code", "state": state_a},
        follow_redirects=False,
        headers=_auth_headers("drive-user-a"),
    )

    assert client_a.get("/api/connectors/google_drive/status", headers=_auth_headers("drive-user-a")).json()["connected"] is True
    assert client_b.get("/api/connectors/google_drive/status", headers=_auth_headers("drive-user-b")).json()["connected"] is False

    disconnect = client_a.post("/api/connectors/google_drive/disconnect", headers=_auth_headers("drive-user-a"))
    assert disconnect.status_code == 200
    assert client_a.get("/api/connectors/google_drive/status", headers=_auth_headers("drive-user-a")).json()["connected"] is False
