"""Lifecycle abstraction for MCP-compatible connector clients."""

from __future__ import annotations

from typing import Any, Protocol
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from app.mcp.permissions import Permission, check_permission


class MCPTransport(Protocol):
	def connect(self) -> Any: ...
	def close(self) -> Any: ...
	def list_tools(self) -> list[dict[str, Any]]: ...
	def call_tool(self, name: str, arguments: dict[str, Any]) -> Any: ...


class MCPClient:
	"""Provider/transport-neutral MCP client with explicit lifecycle."""

	def __init__(self, name: str, transport: MCPTransport, permission: str | Permission = Permission.READ, confirm_writes: bool = True) -> None:
		self.name = name
		self.transport = transport
		self.permission = permission
		self.confirm_writes = confirm_writes
		self.connected = False
		self._tools: list[dict[str, Any]] = []

	def connect(self) -> None:
		if self.connected:
			return
		try:
			self.transport.connect()
			self.connected = True
		except Exception as error:
			raise ConnectionError(f"Unable to connect to MCP server {self.name}") from error

	def disconnect(self) -> None:
		if not self.connected:
			return
		try:
			self.transport.close()
		finally:
			self.connected = False

	def discover(self) -> list[dict[str, Any]]:
		self._require_connection()
		try:
			self._tools = list(self.transport.list_tools())
			return list(self._tools)
		except Exception as error:
			raise RuntimeError(f"Unable to discover tools from {self.name}") from error

	def list_tools(self) -> list[dict[str, Any]]:
		return list(self._tools) if self._tools else self.discover()

	def invoke_tool(self, name: str, arguments: dict[str, Any] | None = None, *, required_permission: str | Permission = Permission.READ, confirmed: bool = False, timeout_seconds: float = 10.0) -> Any:
		self._require_connection()
		check_permission(self.permission, required_permission, confirmed=confirmed, confirm_writes=self.confirm_writes)
		if self._tools and name not in {tool.get("name") for tool in self._tools}:
			raise KeyError(f"Tool {name} is not advertised by {self.name}")
		try:
			with ThreadPoolExecutor(max_workers=1) as executor:
				future = executor.submit(self.transport.call_tool, name, arguments or {})
				return future.result(timeout=timeout_seconds)
		except FutureTimeoutError as error:
			raise TimeoutError(f"MCP tool timed out: {self.name}.{name}") from error
		except Exception as error:
			raise RuntimeError(f"Tool invocation failed on {self.name}: {name}") from error

	def _require_connection(self) -> None:
		if not self.connected:
			raise ConnectionError(f"MCP server {self.name} is not connected")