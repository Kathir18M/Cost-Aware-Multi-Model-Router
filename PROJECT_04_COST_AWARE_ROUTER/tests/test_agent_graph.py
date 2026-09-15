from unittest.mock import Mock

from app.mcp.client import MCPClient
from app.mcp.manager import MCPManager
from app.router.agent_graph import run_agent_request, select_tools_for_query


def make_manager_with_tools() -> MCPManager:
    transport = Mock()
    transport.list_tools.return_value = [{"name": "search_repositories", "description": "Search GitHub repositories."}]
    transport.call_tool.return_value = {"items": [{"name": "demo-repo"}]}
    client = MCPClient("github", transport)
    client.connect()
    manager = MCPManager()
    manager.register_server("github", client)
    manager.connect_server("github")
    return manager


def test_agent_selects_no_tool_for_arithmetic_request() -> None:
    manager = make_manager_with_tools()
    tools = manager.discover_tools("github")
    assert select_tools_for_query("What is 2 + 2?", [{"provider": "github", "tool": "search_repositories", "name": "search_repositories", "description": "Search GitHub repositories.", "input_schema": {"properties": {"query": {"type": "string"}}, "required": ["query"]}}]) == []
    assert tools[0]["name"] == "search_repositories"


def test_agent_selects_github_tool_for_repo_query() -> None:
    manager = make_manager_with_tools()
    tools = [{
        "provider": "github",
        "tool": "search_repositories",
        "name": "search_repositories",
        "description": "Search GitHub repositories.",
        "input_schema": {"properties": {"query": {"type": "string"}}, "required": ["query"]},
    }]
    selected = select_tools_for_query("Find my latest GitHub repository.", tools)
    assert selected[0]["provider"] == "github"
    assert selected[0]["tool"] == "search_repositories"


def test_agent_executes_tool_via_mcp_manager() -> None:
    manager = make_manager_with_tools()

    def executor(model: str, task_type: str, user_input: str) -> dict:
        return {
            "content": "Found the repo.",
            "summary": "Found the repo.",
            "answer": "Found the repo.",
            "success": True,
            "confidence": 0.92,
        }

    result = run_agent_request(
        query="Find my latest GitHub repository.",
        manager=manager,
        executor=executor,
        user_id="user-123",
    )

    assert result["answer"] == "Found the repo."
    assert result["model"] in {"gemini", "mistral"}
    assert result["tools_used"][0]["provider"] == "github"
    assert result["tools_used"][0]["tool"] == "search_repositories"
