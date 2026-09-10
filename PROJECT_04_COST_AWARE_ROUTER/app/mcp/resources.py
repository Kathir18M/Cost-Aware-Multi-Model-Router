"""Read-only MCP resources for pricing and router statistics."""

from __future__ import annotations

from typing import Any

from app.tools.cost_calculator import get_model_pricing
from app.tools.statistics_tool import get_router_statistics


RESOURCE_DEFINITIONS = {
	"router://pricing": "Configured model pricing.",
	"router://statistics": "Aggregated routing statistics.",
}


def list_resources() -> list[dict[str, str]]:
	return [
		{"uri": uri, "description": description}
		for uri, description in RESOURCE_DEFINITIONS.items()
	]


def read_resource(uri: str) -> dict[str, Any]:
	if uri == "router://pricing":
		return get_model_pricing()
	if uri == "router://statistics":
		return get_router_statistics()
	raise KeyError(f"Unknown MCP resource: {uri}")
