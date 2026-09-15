from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api_server import app
from app.auth.clerk import get_authenticated_user


class DummySession:
    def __init__(self, **kwargs: Any) -> None:
        self._data: dict[str, Any] = dict(kwargs)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value


class DummyRequest:
    def __init__(self, headers: dict[str, str] | None = None, session_data: dict[str, Any] | None = None) -> None:
        self.headers = type("HeaderBag", (), {"get": lambda self, key, default=None: (headers or {}).get(key.lower(), default)})()
        self.session = DummySession(**(session_data or {}))
        self.state = SimpleNamespace()


def _make_request(headers: dict[str, str] | None = None, session_data: dict[str, Any] | None = None) -> DummyRequest:
    return DummyRequest(headers=headers, session_data=session_data)


def test_missing_authentication_rejected() -> None:
    request = _make_request()
    with pytest.raises(HTTPException) as exc:
        get_authenticated_user(request)
    assert exc.value.status_code == 401


def test_invalid_token_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    request = _make_request({"authorization": "Bearer invalid-token"})

    def fake_verify(token: str) -> dict[str, Any] | None:
        return None

    monkeypatch.setattr("app.auth.clerk.verify_clerk_token", fake_verify)
    with pytest.raises(HTTPException) as exc:
        get_authenticated_user(request)
    assert exc.value.status_code == 401


def test_authenticated_request_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    request = _make_request({"authorization": "Bearer valid-token"})

    def fake_verify(token: str) -> dict[str, Any] | None:
        assert token == "valid-token"
        return {"sub": "user_123"}

    monkeypatch.setattr("app.auth.clerk.verify_clerk_token", fake_verify)
    user = get_authenticated_user(request)
    assert user["user_id"] == "user_123"


def test_user_id_extracted_correctly(monkeypatch: pytest.MonkeyPatch) -> None:
    request = _make_request({"authorization": "Bearer valid-token"})

    monkeypatch.setattr(
        "app.auth.clerk.verify_clerk_token",
        lambda token: {"sub": "user_456"},
    )
    data = get_authenticated_user(request)
    assert data["user_id"] == "user_456"


def test_verify_clerk_token_skips_audience_check_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLERK_AUDIENCE", raising=False)

    class FakeSigningKey:
        key = "signing-key"

    class FakeJWKClient:
        def get_signing_key_from_jwt(self, token: str) -> FakeSigningKey:
            return FakeSigningKey()

    def fake_decode(token: str, key: str, **kwargs: Any) -> dict[str, Any]:
        assert key == "signing-key"
        assert kwargs["algorithms"] == ["RS256"]
        assert kwargs["issuer"] == "https://fine-eagle-3732.clerk.accounts.dev"
        assert kwargs["options"]["verify_aud"] is False
        return {"sub": "user_999", "iss": "https://fine-eagle-3732.clerk.accounts.dev"}

    monkeypatch.setattr("app.auth.clerk.jwt.PyJWKClient", lambda _url: FakeJWKClient())
    monkeypatch.setattr("app.auth.clerk.jwt.decode", fake_decode)
    monkeypatch.setattr("app.auth.clerk._clerk_issuer", lambda: "https://fine-eagle-3732.clerk.accounts.dev")

    payload = __import__("app.auth.clerk", fromlist=["verify_clerk_token"]).verify_clerk_token("token")
    assert payload is not None
    assert payload["sub"] == "user_999"


def test_agent_receives_authenticated_user_context(monkeypatch: pytest.MonkeyPatch) -> None:
    request = _make_request({"authorization": "Bearer user-token"})

    monkeypatch.setattr("app.auth.clerk.verify_clerk_token", lambda token: {"sub": "user_agent"})
    user = get_authenticated_user(request)
    assert user["user_id"] == "user_agent"
    assert "user_id" in user


def test_fastapi_dependency_authentication(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_safe_executor(model: str, task_type: str, user_input: str) -> dict:
        return {
            "success": True,
            "answer": "Mocked successful model response",
            "content": "Mocked successful model response",
            "confidence": 0.95,
            "input_tokens": 100,
            "output_tokens": 50,
        }

    monkeypatch.setattr("app.auth.clerk.verify_clerk_token", lambda token: {"sub": "user_fastapi"})
    monkeypatch.setattr("api_server._safe_executor", fake_safe_executor)
    client = TestClient(app)
    response = client.post(
        "/api/agent/run",
        json={"query": "hello"},
        headers={"Authorization": "Bearer valid-token"},
    )
    assert response.status_code == 200
    assert response.json()["request_id"]
