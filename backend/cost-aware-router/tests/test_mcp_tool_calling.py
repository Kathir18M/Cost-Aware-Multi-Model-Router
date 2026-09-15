from unittest.mock import Mock

from app.mcp.client import MCPClient
from app.mcp.manager import MCPManager
from app.router.graph import build_graph
from app.router.mcp_tools import discover_available_tools, select_relevant_tool


def make_manager() -> MCPManager:
	transport = Mock()
	transport.list_tools.return_value = [{"name": "search_code"}]
	transport.call_tool.return_value = {"matches": ["auth.py"]}
	client = MCPClient("github", transport)
	manager = MCPManager()
	manager.register_server("github", client)
	manager.connect_server("github")
	return manager


def test_runtime_discovery_and_relevant_selection():
	manager = make_manager()
	tools = discover_available_tools(manager)
	assert tools == [{"name": "search_code", "server": "github"}]
	assert select_relevant_tool("Find the authentication code in GitHub", tools) == tools[0]


def test_graph_executes_mcp_result_before_model():
	manager = make_manager()
	received = []

	def executor(model: str, task: str, prompt: str) -> dict:
		received.append(prompt)
		return {"content": "found", "answer": "found", "success": True, "confidence": 0.95}

	result = build_graph(executor=executor, mcp_manager=manager).invoke(
		{"request_id": "mcp-1", "user_input": "Find the authentication code in GitHub"}
	)

	assert result["selected_tool"] == "github.search_code"
	assert result["tool_result"] == {"matches": ["auth.py"]}
	assert "auth.py" in received[0]


def test_mcp_failure_is_recorded_without_fabricating_result():
	manager = make_manager()
	manager._clients["github"].transport.call_tool.side_effect = RuntimeError("down")

	result = build_graph(mcp_manager=manager).invoke(
		{"request_id": "mcp-2", "user_input": "Find the authentication code in GitHub"}
	)

	assert result["tool_error"] == "RuntimeError"
	assert result["tool_result"] is None