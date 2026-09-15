"""Small MCP-compatible boundary for selected router tools and resources."""

from __future__ import annotations

from typing import Any

from app.mcp.resources import list_resources, read_resource
from app.mcp.tools import call_tool, list_tool_definitions


class MCPServer:
	"""Serializable MCP operation façade.

	Transport wiring is intentionally kept outside the deterministic router.
	"""

	def list_tools(self) -> list[dict[str, Any]]:
		return list_tool_definitions()

	def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
		return call_tool(name, arguments)

	def list_resources(self) -> list[dict[str, str]]:
		return list_resources()

	def read_resource(self, uri: str) -> dict[str, Any]:
		return read_resource(uri)


def create_server() -> MCPServer:
	"""Create the application MCP façade."""

	return MCPServer()
