from __future__ import annotations

import pytest
from app.mcp.client import MCPClient
from app.mcp.manager import MCPManager
from fastapi.testclient import TestClient

from api_server import app


def _auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer valid-test-token"}


class DummyTransport:
    def __init__(self):
        self.connected = False

    def connect(self):
        self.connected = True

    def close(self):
        self.connected = False

    def list_tools(self):
        return [
            {"name": "search_repositories", "description": "Search GitHub repositories"},
            {"name": "read_file", "description": "Read a repository file"},
        ]

    def call_tool(self, name, arguments):
        return {"tool": name, "arguments": arguments, "ok": True, "status": "executed"}


def test_manager_tracks_registered_connectors_and_discovers_tools():
    manager = MCPManager()
    client = MCPClient("github", DummyTransport())
    manager.register_server("github", client)

    assert manager.list_servers()[0]["name"] == "github"
    manager.connect_server("github")
    assert manager.get_server_status("github")["connected"] is True
    assert {tool["name"] for tool in manager.discover_tools("github")} == {"search_repositories", "read_file"}


def test_api_exposes_dynamic_connector_state_and_tool_list(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.auth.clerk.verify_clerk_token", lambda token: {"sub": "user_mcp"})
    client = TestClient(app)
    response = client.get("/api/connectors", headers=_auth_headers())
    assert response.status_code == 200

    payload = response.json()
    assert {item["id"] for item in payload["connectors"]} == {"github", "gmail", "google_drive"}
    assert payload["connectors"][0]["name"] in {"GitHub", "Gmail", "Google Drive"}

    status_response = client.get("/api/connectors/github/status", headers=_auth_headers())
    assert status_response.status_code == 200
    assert status_response.json()["connected"] is False
    assert status_response.json()["tools"] == []


def test_tool_execution_requires_connected_connector_and_valid_tool(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.auth.clerk.verify_clerk_token", lambda token: {"sub": "user_mcp"})
    client = TestClient(app)

    connect_response = client.get("/api/connectors/github/connect", headers=_auth_headers())
    assert connect_response.status_code == 200
    payload = connect_response.json()
    assert payload["connected"] is True
    assert "search_repositories" in payload["tools"]

    execute_response = client.post(
        "/api/connectors/github/tools/search_repositories/execute",
        json={"arguments": {"query": "router project"}},
        headers=_auth_headers(),
    )
    assert execute_response.status_code == 200
    assert execute_response.json()["success"] is True

    invalid_tool = client.post(
        "/api/connectors/github/tools/unknown_tool/execute",
        json={"arguments": {}},
        headers=_auth_headers(),
    )
    assert invalid_tool.status_code == 404

    disconnect_response = client.post("/api/connectors/github/disconnect", headers=_auth_headers())
    assert disconnect_response.status_code == 200
    assert disconnect_response.json()["connected"] is False


def test_tool_execution_rejects_unknown_connector_and_cannot_run_without_connection(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.auth.clerk.verify_clerk_token", lambda token: {"sub": "user_mcp"})
    client = TestClient(app)
    response = client.post(
        "/api/connectors/unknown/tools/search_repositories/execute",
        json={"arguments": {"query": "x"}},
        headers=_auth_headers(),
    )
    assert response.status_code == 404

    disconnected = client.post(
        "/api/connectors/gmail/tools/search_emails/execute",
        json={"arguments": {"query": "hello"}},
        headers=_auth_headers(),
    )
    assert disconnected.status_code == 400
