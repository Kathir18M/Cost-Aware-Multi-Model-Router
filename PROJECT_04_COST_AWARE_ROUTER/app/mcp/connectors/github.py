"""GitHub MCP connector factory."""

from app.mcp.client import MCPTransport
from app.mcp.connectors.base import create_connector, connector_tools


def create_github_connector(transport: MCPTransport | None = None):
	return create_connector("github", transport)


def github_tools():
	return connector_tools("github")