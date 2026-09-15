"""MCP server configuration without credential exposure."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class MCPServerConfig:
	name: str
	command: str | None = None
	url: str | None = None
	enabled: bool = True
	permission: str = "READ"
	confirm_writes: bool = True


def load_mcp_config(name: str) -> MCPServerConfig:
	"""Load non-secret connector settings from namespaced environment variables."""

	prefix = "MCP_" + name.upper().replace("-", "_") + "_"
	return MCPServerConfig(
		name=name,
		command=os.getenv(prefix + "COMMAND") or None,
		url=os.getenv(prefix + "URL") or None,
		enabled=os.getenv(prefix + "ENABLED", "true").lower() == "true",
		permission=os.getenv(prefix + "PERMISSION", "READ").upper(),
		confirm_writes=os.getenv(prefix + "CONFIRM_WRITES", "true").lower() == "true",
	)