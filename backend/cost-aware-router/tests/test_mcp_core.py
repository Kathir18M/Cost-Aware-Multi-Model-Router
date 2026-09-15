from unittest.mock import Mock

import pytest

from app.mcp.client import MCPClient
from app.mcp.discovery import discover_connector_tools
from app.mcp.manager import MCPManager
from app.mcp.permissions import PermissionDenied
from app.mcp.registry import ConnectorRegistry


def make_client(permission="READ"):
	transport = Mock()
	transport.list_tools.return_value = [{"name": "read_data"}, {"name": "write_data"}]
	transport.call_tool.return_value = {"ok": True}
	return MCPClient("test", transport, permission=permission), transport


def test_registration_connection_discovery_and_status():
	client, transport = make_client()
	manager = MCPManager()
	manager.register_server("github", client)
	assert manager.list_servers()[0]["connected"] is False
	manager.connect_server("github")
	assert manager.get_server_status("github")["connected"] is True
	assert manager.discover_tools("github")[0]["name"] == "read_data"
	transport.connect.assert_called_once()


def test_read_invocation_records_metadata():
	client, _ = make_client()
	manager = MCPManager()
	manager.register_server("internal_cost_tools", client)
	manager.connect_server("internal_cost_tools")
	assert manager.call_tool("internal_cost_tools", "read_data") == {"ok": True}
	assert manager.invocations[0]["success"] is True


def test_write_requires_confirmation_and_permission():
	client, _ = make_client("WRITE")
	client.connect()
	with pytest.raises(PermissionDenied):
		client.invoke_tool("write_data", required_permission="WRITE")
	assert client.invoke_tool("write_data", required_permission="WRITE", confirmed=True) == {"ok": True}


def test_read_only_cannot_write():
	client, _ = make_client("READ")
	client.connect()
	with pytest.raises(PermissionDenied):
		client.invoke_tool("write_data", required_permission="WRITE", confirmed=True)


def test_registry_and_disabled_discovery():
	registry = ConnectorRegistry()
	client, _ = make_client()
	registry.register("slack", client)
	assert discover_connector_tools(registry, "slack") == []
	with pytest.raises(ValueError):
		registry.register("unknown", client)


def test_connection_and_tool_errors_are_normalized():
	client, transport = make_client()
	transport.connect.side_effect = RuntimeError("down")
	with pytest.raises(ConnectionError, match="Unable to connect"):
		client.connect()
	with pytest.raises(ConnectionError, match="not connected"):
		client.invoke_tool("read_data")