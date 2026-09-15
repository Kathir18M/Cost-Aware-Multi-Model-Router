"""Comprehensive test suite for GitHub MCP 'list_my_repositories' workflow."""

import pytest
from app.mcp.manager import MCPManager
from app.mcp.client import MCPClient
from api_server import GitHubOAuthTransport
from app.router.agent_graph import run_agent_request, select_tools_for_query, discover_available_tools


def _make_manager_with_github(account_info: dict | None = None) -> MCPManager:
    manager = MCPManager()
    transport = GitHubOAuthTransport("test_token", account_info=account_info)
    client = MCPClient("github", transport)
    client.connect()
    manager.register_server("github", client, enabled=True)
    return manager


def test_1_show_my_github_repositories_selects_list_my_repositories():
    manager = _make_manager_with_github()
    tools = discover_available_tools(manager)
    selected = select_tools_for_query("Show my GitHub repositories", tools)
    assert len(selected) > 0
    assert selected[0]["tool"] == "list_my_repositories"


def test_2_list_all_my_repos_selects_list_my_repositories():
    manager = _make_manager_with_github()
    tools = discover_available_tools(manager)
    selected = select_tools_for_query("List all my repos", tools)
    assert len(selected) > 0
    assert selected[0]["tool"] == "list_my_repositories"


def test_3_what_repositories_do_i_have_selects_list_my_repositories():
    manager = _make_manager_with_github()
    tools = discover_available_tools(manager)
    selected = select_tools_for_query("What repositories do I have?", tools)
    assert len(selected) > 0
    assert selected[0]["tool"] == "list_my_repositories"


def test_4_find_my_repository_called_x_selects_search_repositories():
    manager = _make_manager_with_github()
    tools = discover_available_tools(manager)
    selected = select_tools_for_query("Find my repository called PROJECT_04_COST_AWARE_ROUTER", tools)
    assert len(selected) > 0
    assert selected[0]["tool"] == "search_repositories"


def test_5_search_github_for_mcp_repositories_selects_search_repositories():
    manager = _make_manager_with_github()
    tools = discover_available_tools(manager)
    selected = select_tools_for_query("Search GitHub for MCP repositories", tools)
    assert len(selected) > 0
    assert selected[0]["tool"] == "search_repositories"


def test_6_github_disconnected_response():
    manager = MCPManager()  # empty manager, GitHub not registered or connected
    result = run_agent_request(query="Show my GitHub repositories", manager=manager)
    assert "not connected" in result["answer"].lower() or "no mcp manager" in result["answer"].lower() or result["status"] in ("disconnected", "accepted")


def test_7_github_connected_user_scoped_execution():
    account_info = {
        "repositories": [
            {
                "name": "my-cool-project",
                "full_name": "user/my-cool-project",
                "description": "Awesome Python project",
                "private": False,
                "html_url": "https://github.com/user/my-cool-project",
                "language": "Python",
                "updated_at": "2026-09-14T12:00:00Z",
            }
        ]
    }
    manager = _make_manager_with_github(account_info)
    result = run_agent_request(query="Show my GitHub repositories", manager=manager)
    assert result["tools_used"][0]["tool"] == "list_my_repositories"
    assert "my-cool-project" in result["answer"]


def test_8_empty_repository_list():
    account_info = {"repositories": []}
    manager = _make_manager_with_github(account_info)
    result = run_agent_request(query="Show my GitHub repositories", manager=manager)
    assert result["tools_used"][0]["tool"] == "list_my_repositories"
    assert "couldn't find any repositories" in result["answer"].lower() or "no repositories" in result["answer"].lower()


def test_9_mcp_failure_handling():
    class FailingTransport:
        def connect(self): pass
        def close(self): pass
        def list_tools(self): return [{"name": "list_my_repositories", "description": "List my repositories"}]
        def call_tool(self, name, args): raise RuntimeError("API Rate Limit Exceeded")

    manager = MCPManager()
    client = MCPClient("github", FailingTransport())
    client.connect()
    manager.register_server("github", client, enabled=True)

    result = run_agent_request(query="Show my GitHub repositories", manager=manager)
    assert result["tools_used"][0]["tool"] == "list_my_repositories"
    assert result["status"] in ("tool_failed", "accepted", "partial", "retrying")


def test_10_gemini_failure_mistral_fallback():
    def failing_gemini_executor(model: str, task_type: str, user_input: str) -> dict:
        if "gemini" in model.lower():
            return {"content": "", "answer": "", "success": False, "confidence": 0.0, "error": "Gemini 404"}
        return {"content": "Mistral answer", "answer": "Mistral answer", "success": True, "confidence": 0.88, "input_tokens": 10, "output_tokens": 20}

    manager = _make_manager_with_github()
    result = run_agent_request(query="Show my GitHub repositories", manager=manager, executor=failing_gemini_executor)
    assert result["model"] == "mistral" or result["escalated"] is True
    assert "Mistral" in result["answer"] or len(result["answer"]) > 0


def test_11_user_isolation():
    user1_repos = [{"name": "user1-private-repo", "full_name": "u1/user1-private-repo", "description": "U1 Repo"}]
    user2_repos = [{"name": "user2-private-repo", "full_name": "u2/user2-private-repo", "description": "U2 Repo"}]

    user1_transport = GitHubOAuthTransport("token1", account_info={"repositories": user1_repos})
    user2_transport = GitHubOAuthTransport("token2", account_info={"repositories": user2_repos})

    user1_client = MCPClient("github", user1_transport)
    user1_client.connect()
    user2_client = MCPClient("github", user2_transport)
    user2_client.connect()

    manager1 = MCPManager()
    manager1.register_server("github", user1_client, enabled=True)

    manager2 = MCPManager()
    manager2.register_server("github", user2_client, enabled=True)

    res1 = run_agent_request(query="Show my GitHub repositories", manager=manager1, user_id="user_1")
    res2 = run_agent_request(query="Show my GitHub repositories", manager=manager2, user_id="user_2")

    assert "user1-private-repo" in res1["answer"]
    assert "user2-private-repo" not in res1["answer"]

    assert "user2-private-repo" in res2["answer"]
    assert "user1-private-repo" not in res2["answer"]


def test_12_unique_request_id_per_request():
    manager = _make_manager_with_github()
    res1 = run_agent_request(query="Show my GitHub repositories", manager=manager)
    res2 = run_agent_request(query="Show my GitHub repositories", manager=manager)

    assert res1["request_id"] != res2["request_id"]
    assert res1["request_id"].startswith("req_")
    assert res2["request_id"].startswith("req_")
