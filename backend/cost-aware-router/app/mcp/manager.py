"""MCP server lifecycle and invocation manager."""

from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from app.mcp.client import MCPClient
from app.mcp.permissions import Permission, check_permission
from app.mcp.registry import ConnectorRegistry


class MCPManager:
	def __init__(self, *, registry: ConnectorRegistry | None = None) -> None:
		self.registry = registry or ConnectorRegistry()
		self._clients: dict[str, MCPClient] = {}
		self.invocations: list[dict[str, Any]] = []

	def register_server(self, name: str, client: MCPClient, *, enabled: bool = True) -> None:
		key = self._normalize_name(name)
		self.registry.register(key, client, enabled=enabled)
		self._clients[key] = client

	def connect_server(self, name: str) -> None:
		self._clients[self._normalize_name(name)].connect()

	def disconnect_server(self, name: str) -> None:
		self._clients[self._normalize_name(name)].disconnect()

	def list_servers(self) -> list[dict[str, Any]]:
		servers: list[dict[str, Any]] = []
		for item in self.registry.list_connectors():
			key = self._normalize_name(item["id"])
			client = self._clients.get(key)
			servers.append({
				"id": key,
				"name": key,
				"display_name": item["name"],
				"enabled": item["enabled"],
				"connected": bool(client and client.connected),
			})
		return servers

	def get_server_status(self, name: str) -> dict[str, Any]:
		key = self._normalize_name(name)
		client = self._clients[key]
		return {
			"id": key,
			"name": client.name,
			"connected": client.connected,
			"permission": client.permission.name if isinstance(client.permission, Permission) else str(client.permission),
		}

	def discover_tools(self, name: str) -> list[dict[str, Any]]:
		key = self._normalize_name(name)
		return self._clients[key].discover()

	def list_connector_metadata(self) -> list[dict[str, Any]]:
		metadata: list[dict[str, Any]] = []
		for server in self.list_servers():
			client = self._clients.get(server["id"])
			tools = client.list_tools() if client and client.connected else []
			metadata.append({
				"id": server["id"],
				"name": server["display_name"],
				"connected": bool(client and client.connected),
				"tools": [tool.get("name", "") for tool in tools],
			})
		return metadata

	def call_tool(self, name: str, tool: str, arguments: dict[str, Any] | None = None, *, required_permission: str | Permission = Permission.READ, confirmed: bool = False) -> Any:
		key = self._normalize_name(name)
		client = self._clients[key]
		start = perf_counter()
		try:
			check_permission(client.permission, required_permission, confirmed=confirmed, confirm_writes=client.confirm_writes)
			result = client.invoke_tool(tool, arguments, required_permission=required_permission, confirmed=confirmed)
		except Exception as error:
			self.invocations.append({
				"server": key,
				"tool": tool,
				"timestamp": datetime.now(timezone.utc).isoformat(),
				"duration_ms": round((perf_counter() - start) * 1000, 3),
				"success": False,
				"error": type(error).__name__,
			})
			raise
		self.invocations.append({
			"server": key,
			"tool": tool,
			"timestamp": datetime.now(timezone.utc).isoformat(),
			"duration_ms": round((perf_counter() - start) * 1000, 3),
			"success": True,
		})
		return result

	@staticmethod
	def _normalize_name(name: str) -> str:
		return str(name).strip().lower().replace("-", "_").replace(" ", "_")