"""Google Drive MCP connector factory."""

from app.mcp.client import MCPTransport
from app.mcp.connectors.base import create_connector, connector_tools


def create_google_drive_connector(transport: MCPTransport | None = None):
	return create_connector("google_drive", transport)


def google_drive_tools():
	return connector_tools("google_drive")