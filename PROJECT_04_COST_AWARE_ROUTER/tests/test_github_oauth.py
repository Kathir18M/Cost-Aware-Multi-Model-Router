from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from api_server import app


def _auth_headers(user: str = "github-user") -> dict[str, str]:
    return {"Authorization": f"Bearer {user}"}


def _state_from_redirect(response):
    location = response.headers.get("location", "")
    if not location:
        raise AssertionError("Expected redirect location")
    query = parse_qs(urlparse(location).query)
    return query["state"][0]


def test_oauth_state_round_trip_and_callback(monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "demo-client")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "demo-secret")
    monkeypatch.setenv("GITHUB_REDIRECT_URI", "http://localhost:8000/api/connectors/github/callback")
    monkeypatch.setenv("SESSION_SECRET_KEY", "phase4-test-secret")
    monkeypatch.setattr("app.auth.clerk.verify_clerk_token", lambda token: {"sub": "github-user"})

    def fake_exchange(code: str, redirect_uri: str):
        assert code == "demo-code"
        return {"access_token": "demo-token"}

    def fake_user(token: str):
        assert token == "demo-token"
        return {"login": "octocat", "avatar_url": "https://github.com/avatar.png"}

    monkeypatch.setattr("api_server._exchange_github_code", fake_exchange)
    monkeypatch.setattr("api_server._fetch_github_user", fake_user)

    client = TestClient(app)
    redirect = client.get("/api/connectors/github/connect", follow_redirects=False, headers=_auth_headers())
    assert redirect.status_code in {200, 302, 307}

    state = _state_from_redirect(redirect)
    callback = client.get(
        "/api/connectors/github/callback",
        params={"code": "demo-code", "state": state},
        follow_redirects=False,
        headers=_auth_headers(),
    )
    assert callback.status_code in {200, 302, 307}

    status = client.get("/api/connectors/github/status", headers=_auth_headers())
    assert status.status_code == 200
    payload = status.json()
    assert payload["provider"] == "github"
    assert payload["connected"] is True
    assert payload["account"]["login"] == "octocat"
    assert payload["tool_count"] > 0


def test_oauth_rejects_invalid_or_expired_state(monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "demo-client")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "demo-secret")
    monkeypatch.setenv("GITHUB_REDIRECT_URI", "http://localhost:8000/api/connectors/github/callback")
    monkeypatch.setenv("SESSION_SECRET_KEY", "phase4-test-secret-2")
    monkeypatch.setattr("app.auth.clerk.verify_clerk_token", lambda token: {"sub": "github-user"})

    client = TestClient(app)
    redirect = client.get("/api/connectors/github/connect", follow_redirects=False, headers=_auth_headers())
    assert redirect.status_code in {200, 302, 307}

    invalid = client.get(
        "/api/connectors/github/callback",
        params={"code": "bad-code", "state": "wrong-state"},
        follow_redirects=False,
        headers=_auth_headers(),
    )
    assert invalid.status_code in {400, 401, 302}


def test_user_isolation_and_disconnect(monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "demo-client")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "demo-secret")
    monkeypatch.setenv("GITHUB_REDIRECT_URI", "http://localhost:8000/api/connectors/github/callback")
    monkeypatch.setenv("SESSION_SECRET_KEY", "phase4-test-secret-3")

    def fake_verify(token: str):
        if token == "github-user-a":
            return {"sub": "github-user-a"}
        if token == "github-user-b":
            return {"sub": "github-user-b"}
        return {"sub": token}

    monkeypatch.setattr("app.auth.clerk.verify_clerk_token", fake_verify)
    monkeypatch.setattr("api_server._exchange_github_code", lambda code, redirect_uri: {"access_token": "token-a"})
    monkeypatch.setattr("api_server._fetch_github_user", lambda token: {"login": "user-a", "avatar_url": "https://example.com/a.png"})

    client_a = TestClient(app)
    client_b = TestClient(app)

    redirect_a = client_a.get("/api/connectors/github/connect", follow_redirects=False, headers=_auth_headers("github-user-a"))
    state_a = _state_from_redirect(redirect_a)
    client_a.get(
        "/api/connectors/github/callback",
        params={"code": "demo-code", "state": state_a},
        follow_redirects=False,
        headers=_auth_headers("github-user-a"),
    )

    status_a = client_a.get("/api/connectors/github/status", headers=_auth_headers("github-user-a"))
    status_b = client_b.get("/api/connectors/github/status", headers=_auth_headers("github-user-b"))

    assert status_a.json()["connected"] is True
    assert status_b.json()["connected"] is False

    disconnect = client_a.post("/api/connectors/github/disconnect", headers=_auth_headers("github-user-a"))
    assert disconnect.status_code == 200
    assert client_a.get("/api/connectors/github/status", headers=_auth_headers("github-user-a")).json()["connected"] is False


def test_agent_runs_with_dynamic_user_scoped_mcp_manager(monkeypatch):
    def fake_verify(token: str):
        return {"sub": f"user-{token}"}

    def fake_safe_executor(model: str, task_type: str, user_input: str) -> dict:
        return {
            "success": True,
            "answer": "Mocked successful model response",
            "content": "Mocked successful model response",
            "confidence": 0.95,
            "input_tokens": 100,
            "output_tokens": 50,
        }

    monkeypatch.setattr("app.auth.clerk.verify_clerk_token", fake_verify)
    monkeypatch.setattr("api_server._safe_executor", fake_safe_executor)

    client = TestClient(app)
    # Connect user-1 via fallback/OAuth
    connect_resp = client.get("/api/connectors/github/connect", headers=_auth_headers("1"))
    assert connect_resp.status_code == 200
    assert connect_resp.json()["connected"] is True

    # Run agent query for user-1
    run_resp = client.post(
        "/api/agent/run",
        json={"query": "search github repositories for smart farm"},
        headers=_auth_headers("1"),
    )
    assert run_resp.status_code == 200
    res_data = run_resp.json()
    assert res_data["answer"]
    assert "tools_used" in res_data

