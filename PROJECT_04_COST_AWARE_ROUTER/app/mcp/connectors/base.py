"""Shared connector registration helpers."""

from __future__ import annotations

from typing import Any

from app.mcp.client import MCPClient, MCPTransport
from app.mcp.config import load_mcp_config
from app.mcp.permissions import Permission


class ConnectorUnavailable(ConnectionError):
	"""Raised when a connector has no configured MCP endpoint or transport."""


def create_connector(
	name: str,
	transport: MCPTransport | None = None,
) -> MCPClient:
	config = load_mcp_config(name)
	if not config.enabled:
		raise ConnectorUnavailable(f"MCP connector is disabled: {name}")
	if transport is None:
		raise ConnectorUnavailable(
		f"No MCP transport configured for {name}; set MCP_{name.upper()}_URL or inject a transport"
	)
	return MCPClient(
		name,
		transport,
		permission=config.permission,
		confirm_writes=config.confirm_writes,
	)


def connector_tools(name: str) -> list[dict[str, Any]]:
	return CONNECTOR_TOOLS[name]


CONNECTOR_TOOLS: dict[str, list[dict[str, Any]]] = {
	"github": [
		{"name": "list_my_repositories", "permission": "READ"},
		{"name": "search_repositories", "permission": "READ"},
		{"name": "search_code", "permission": "READ"},
		{"name": "read_file", "permission": "READ"},
		{"name": "list_issues", "permission": "READ"},
		{"name": "read_issue", "permission": "READ"},
		{"name": "list_pull_requests", "permission": "READ"},
		{"name": "read_pull_request", "permission": "READ"},
	],
	"gmail": [
		{"name": "search_emails", "permission": "READ"},
		{"name": "read_email", "permission": "READ"},
		{"name": "list_recent_emails", "permission": "READ"},
		{"name": "search_by_sender", "permission": "READ"},
		{"name": "search_by_subject", "permission": "READ"},
		{"name": "create_draft", "permission": "WRITE"},
		{"name": "send_email", "permission": "WRITE"},
	],
	"google_drive": [
		{"name": "search_files", "permission": "READ"},
		{"name": "get_file_metadata", "permission": "READ"},
		{"name": "read_document", "permission": "READ"},
		{"name": "list_folder", "permission": "READ"},
	],
}