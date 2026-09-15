from unittest.mock import Mock

import pytest

from app.mcp.client import MCPClient
from app.mcp.connectors.github import create_github_connector, github_tools
from app.mcp.connectors.gmail import create_gmail_connector, gmail_tools
from app.mcp.connectors.google_drive import create_google_drive_connector, google_drive_tools
from app.mcp.connectors.base import ConnectorUnavailable


def transport():
	value = Mock()
	value.list_tools.return_value = [{"name": "search_repositories"}]
	value.call_tool.return_value = {"items": []}
	return value


@pytest.mark.parametrize(
	("factory", "expected"),
	[
		(create_github_connector, "github"),
		(create_gmail_connector, "gmail"),
		(create_google_drive_connector, "google_drive"),
	],
)
def test_connector_factories_use_existing_mcp_client(monkeypatch, factory, expected):
	monkeypatch.setenv(f"MCP_{expected.upper()}_ENABLED", "true")
	client = factory(transport())
	assert isinstance(client, MCPClient)
	assert client.name == expected


def test_connector_tools_are_declared():
	assert "search_repositories" in {tool["name"] for tool in github_tools()}
	assert "send_email" in {tool["name"] for tool in gmail_tools()}
	assert "read_document" in {tool["name"] for tool in google_drive_tools()}


def test_connector_requires_real_transport(monkeypatch):
	monkeypatch.setenv("MCP_GITHUB_ENABLED", "true")
	with pytest.raises(ConnectorUnavailable):
		create_github_connector()


def test_gmail_write_requires_confirmation(monkeypatch):
	monkeypatch.setenv("MCP_GMAIL_ENABLED", "true")
	client = create_gmail_connector(transport())
	client.connect()
	client.discover()
	with pytest.raises(PermissionError):
		client.invoke_tool("send_email", required_permission="WRITE")