"""MCP-aware tool discovery and execution for LangGraph."""

from __future__ import annotations

from typing import Any

from app.mcp.manager import MCPManager
from app.mcp.permissions import Permission
from app.schemas.router_state import RouterState


def discover_available_tools(manager: MCPManager) -> list[dict[str, Any]]:
	"""Discover tools only from enabled, connected MCP servers."""

	available: list[dict[str, Any]] = []
	for server in manager.list_servers():
		if not server["enabled"] or not server["connected"]:
			continue
		try:
			for tool in manager.discover_tools(server["name"]):
				available.append({**tool, "server": server["name"]})
		except Exception:
			continue
	return available


def select_relevant_tool(user_input: str, tools: list[dict[str, Any]]) -> dict[str, Any] | None:
	"""Select from advertised tools using request intent, never a hard-coded server."""

	text = user_input.lower()
	keywords = {
		"github": ("github", "repository", "repo", "code", "pull request", "issue"),
		"gmail": ("email", "gmail", "inbox", "sender", "subject"),
		"google_drive": ("drive", "document", "file", "folder"),
		"cost": ("cost", "price", "savings"),
		"router": ("statistics", "request history"),
		"evaluation": ("evaluate", "metrics", "accuracy"),
		"calculate": ("cost", "price", "savings"),
	}
	for tool in tools:
		server = str(tool.get("server", "")).lower()
		name = str(tool.get("name", "")).lower()
		if any(word in text for word in keywords.get(server, ())):
			return tool
		if any(word in text for word in keywords.get(name.split(".")[0], ())):
			return tool
	return None


def mcp_tool_node(state: RouterState, *, manager: MCPManager | None = None) -> RouterState:
	"""Discover and execute one relevant read tool, preserving failure state."""

	if manager is None:
		return {"tool_required": False, "available_tools": [], "selected_tool": None}
	tools = discover_available_tools(manager)
	selected = select_relevant_tool(state.get("user_input", ""), tools)
	if selected is None:
		return {"tool_required": False, "available_tools": tools, "selected_tool": None}
	try:
		result = manager.call_tool(
			selected["server"], selected["name"], {"query": state.get("user_input", "")},
			required_permission=Permission.READ,
		)
		return {
			"tool_required": True,
			"available_tools": tools,
			"selected_tool": f"{selected['server']}.{selected['name']}",
			"tool_result": result,
			"tool_error": None,
		}
	except Exception as error:
		return {
			"tool_required": True,
			"available_tools": tools,
			"selected_tool": f"{selected['server']}.{selected['name']}",
			"tool_result": None,
			"tool_error": type(error).__name__,
		}