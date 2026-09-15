"""Connector discovery helpers."""

from __future__ import annotations

from typing import Any

from app.mcp.registry import ConnectorRegistry


def discover_connector_tools(registry: ConnectorRegistry, name: str) -> list[dict[str, Any]]:
	registration = registry.get(name)
	if not registration.enabled:
		return []
	return registration.client.list_tools()