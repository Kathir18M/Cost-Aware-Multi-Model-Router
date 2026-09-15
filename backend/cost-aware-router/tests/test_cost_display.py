from unittest.mock import Mock

from app.mcp.client import MCPClient
from app.mcp.manager import MCPManager
from app.router.agent_graph import run_agent_request


def _make_manager() -> MCPManager:
    manager = MCPManager()
    transport = Mock()
    transport.list_tools.return_value = [{
        "name": "search_repositories",
        "description": "Search GitHub repositories.",
        "input_schema": {"properties": {"query": {"type": "string"}}, "required": ["query"]},
    }]
    transport.call_tool.return_value = {"items": [{"name": "demo-repo"}]}
    client = MCPClient("github", transport)
    client.connect()
    manager.register_server("github", client)
    manager.connect_server("github")
    return manager


def test_agent_run_returns_numeric_runtime_cost_fields() -> None:
    manager = _make_manager()

    def executor(model: str, task_type: str, user_input: str) -> dict:
        return {
            "content": "Repository found.",
            "summary": "Repository found.",
            "answer": "Repository found.",
            "success": True,
            "confidence": 0.93,
        }

    result = run_agent_request(
        query="Find my latest GitHub repository.",
        manager=manager,
        executor=executor,
        user_id="user-7",
    )

    assert isinstance(result["actual_cost"], (int, float))
    assert isinstance(result["baseline_cost"], (int, float))
    assert isinstance(result["savings"], (int, float))
    assert isinstance(result["savings_percentage"], (int, float))
    assert result["actual_cost"] >= 0
    assert result["baseline_cost"] >= 0
    assert result["savings"] >= 0
    assert not (result["actual_cost"] != result["actual_cost"])
    assert not (result["savings"] != result["savings"])
    assert not (result["savings_percentage"] != result["savings_percentage"])


def test_agent_run_returns_zero_safe_runtime_values() -> None:
    manager = _make_manager()

    def executor(model: str, task_type: str, user_input: str) -> dict:
        return {
            "content": "No tool needed.",
            "summary": "No tool needed.",
            "answer": "No tool needed.",
            "success": True,
            "confidence": 0.91,
        }

    result = run_agent_request(
        query="What is 2 + 2?",
        manager=manager,
        executor=executor,
        user_id="user-8",
    )

    assert isinstance(result["actual_cost"], (int, float))
    assert isinstance(result["baseline_cost"], (int, float))
    assert isinstance(result["savings"], (int, float))
    assert isinstance(result["savings_percentage"], (int, float))
    assert result["actual_cost"] >= 0
    assert result["baseline_cost"] >= 0
    assert result["savings"] >= 0
