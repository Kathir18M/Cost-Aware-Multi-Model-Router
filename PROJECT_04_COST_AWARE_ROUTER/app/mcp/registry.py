"""Connector registry with disabled-by-default external integrations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SUPPORTED_CONNECTORS = (
	"github",
	"gmail",
	"google_drive",
	"slack",
	"calendar",
	"database",
	"web_search",
	"internal_cost_tools",
)

DISPLAY_NAMES = {
	"github": "GitHub",
	"gmail": "Gmail",
	"google_drive": "Google Drive",
	"slack": "Slack",
	"calendar": "Calendar",
	"database": "Database",
	"web_search": "Web Search",
	"internal_cost_tools": "Internal Cost Tools",
}


@dataclass(frozen=True)
class ConnectorRegistration:
	name: str
	client: Any
	enabled: bool = False

	@property
	def display_name(self) -> str:
		return DISPLAY_NAMES.get(self.name, self.name.replace("_", " ").title())


class ConnectorRegistry:
	def __init__(self) -> None:
		self._connectors: dict[str, ConnectorRegistration] = {}

	def register(self, name: str, client: Any, *, enabled: bool = False) -> None:
		key = self._normalize_name(name)
		if key not in SUPPORTED_CONNECTORS:
			raise ValueError(f"Unsupported connector: {name}")
		self._connectors[key] = ConnectorRegistration(key, client, enabled)

	def get(self, name: str) -> ConnectorRegistration:
		key = self._normalize_name(name)
		try:
			return self._connectors[key]
		except KeyError as error:
			raise KeyError(f"Connector is not registered: {name}") from error

	def list_connectors(self) -> list[dict[str, Any]]:
		return [{
			"id": item.name,
			"name": item.display_name,
			"enabled": item.enabled,
		} for item in self._connectors.values()]

	@staticmethod
	def _normalize_name(name: str) -> str:
		return str(name).strip().lower().replace("-", "_").replace(" ", "_")