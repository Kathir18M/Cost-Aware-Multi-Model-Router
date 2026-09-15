"""Gmail MCP connector factory."""

from app.mcp.client import MCPTransport
from app.mcp.connectors.base import create_connector, connector_tools


def create_gmail_connector(transport: MCPTransport | None = None):
	return create_connector("gmail", transport)


def gmail_tools():
	return connector_tools("gmail")