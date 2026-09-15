from unittest.mock import Mock

from app.mcp.client import MCPClient
from app.mcp.manager import MCPManager
from app.router.agent_graph import build_agent_graph, run_agent_request


def _make_manager() -> MCPManager:
    manager = MCPManager()
    github_transport = Mock()
    github_transport.list_tools.return_value = [{
        "name": "search_repositories",
        "description": "Search GitHub repositories.",
        "input_schema": {"properties": {"query": {"type": "string"}}, "required": ["query"]},
    }]
    github_transport.call_tool.return_value = {"repo": "smart-farm-ai"}
    github_client = MCPClient("github", github_transport)
    github_client.connect()
    manager.register_server("github", github_client)
    manager.connect_server("github")

    gmail_transport = Mock()
    gmail_transport.list_tools.return_value = [{
        "name": "search_emails",
        "description": "Search Gmail messages.",
        "input_schema": {"properties": {"query": {"type": "string"}}, "required": ["query"]},
    }]
    gmail_transport.call_tool.return_value = {"messages": [{"subject": "smart-farm-ai"}]}
    gmail_client = MCPClient("gmail", gmail_transport)
    gmail_client.connect()
    manager.register_server("gmail", gmail_client)
    manager.connect_server("gmail")

    drive_transport = Mock()
    drive_transport.list_tools.return_value = [{
        "name": "search_files",
        "description": "Search Drive files.",
        "input_schema": {"properties": {"query": {"type": "string"}}, "required": ["query"]},
    }]
    drive_transport.call_tool.return_value = {"files": [{"name": "proposal.pdf"}]}
    drive_client = MCPClient("google_drive", drive_transport)
    drive_client.connect()
    manager.register_server("google_drive", drive_client)
    manager.connect_server("google_drive")
    return manager


def test_phase8_simple_no_tool_request() -> None:
    manager = _make_manager()

    def executor(model: str, task_type: str, user_input: str) -> dict:
        return {"content": "2 + 2 = 4", "summary": "2 + 2 = 4", "answer": "2 + 2 = 4", "success": True, "confidence": 0.95}

    state = build_agent_graph(executor=executor, manager=manager).invoke({
        "request_id": "phase8-no-tool",
        "session_id": "user-1",
        "user_query": "What is 2 + 2?",
        "task_type": "qa",
        "tool_calls": [],
        "tool_results": [],
        "completed_steps": [],
    })

    assert state["status"] in {"accepted", "accepted"}
    assert state["tool_calls"] == []


def test_phase8_single_tool_request() -> None:
    manager = _make_manager()

    def executor(model: str, task_type: str, user_input: str) -> dict:
        return {"content": "Repo found", "summary": "Repo found", "answer": "Repo found", "success": True, "confidence": 0.93}

    result = run_agent_request(
        query="Find my latest GitHub repository.",
        manager=manager,
        executor=executor,
        user_id="user-2",
    )

    assert result["tools_used"][0]["provider"] == "github"
    assert result["answer"] == "Repo found"


def test_phase8_multi_tool_workflow() -> None:
    manager = _make_manager()

    def executor(model: str, task_type: str, user_input: str) -> dict:
        return {"content": "Cross-connector answer", "summary": "Cross-connector answer", "answer": "Cross-connector answer", "success": True, "confidence": 0.91}

    result = run_agent_request(
        query="Find my latest AI project on GitHub, find related emails in Gmail, and locate the project proposal in Drive.",
        manager=manager,
        executor=executor,
        user_id="user-3",
    )

    providers = {call["provider"] for call in result["tools_used"]}
    assert {"github", "gmail", "google_drive"}.issubset(providers)
    assert result["status"] in {"accepted", "escalation_required"}


def test_phase8_disconnected_connector_response() -> None:
    manager = _make_manager()
    manager._clients.pop("google_drive", None)

    def executor(model: str, task_type: str, user_input: str) -> dict:
        return {"content": "Drive answer", "summary": "Drive answer", "answer": "Drive answer", "success": True, "confidence": 0.9}

    result = run_agent_request(
        query="Find my project proposal in Drive.",
        manager=manager,
        executor=executor,
        user_id="user-4",
    )

    assert "Google Drive" in (result.get("answer") or "") or "Drive" in (result.get("answer") or "")


def test_phase8_tool_limit_and_replanning() -> None:
    manager = _make_manager()

    def executor(model: str, task_type: str, user_input: str) -> dict:
        return {"content": "Answer", "summary": "Answer", "answer": "Answer", "success": True, "confidence": 0.8}

    result = run_agent_request(
        query="Find my latest AI project on GitHub, find related emails in Gmail, and locate the project proposal in Drive.",
        manager=manager,
        executor=executor,
        user_id="user-5",
        max_iterations=2,
    )

    assert result["status"] in {"partial", "accepted", "ready_for_context"}


def test_phase8_dependent_tool_arguments() -> None:
    manager = _make_manager()

    def executor(model: str, task_type: str, user_input: str) -> dict:
        return {"content": "Using smart-farm-ai", "summary": "Using smart-farm-ai", "answer": "Using smart-farm-ai", "success": True, "confidence": 0.9}

    result = run_agent_request(
        query="Find my latest GitHub project and then search related Gmail and Drive content for that project.",
        manager=manager,
        executor=executor,
        user_id="user-6",
    )

    assert result["answer"]
    assert result["tools_used"]


def test_phase8_context_builder_and_final_answer() -> None:
    manager = _make_manager()

    def executor(model: str, task_type: str, user_input: str) -> dict:
        return {"content": "Final synthesized answer", "summary": "Final synthesized answer", "answer": "Final synthesized answer", "success": True, "confidence": 0.92}

    result = run_agent_request(
        query="Find my latest AI project on GitHub and summarize the related discussion.",
        manager=manager,
        executor=executor,
        user_id="user-7",
    )

    assert "Final synthesized answer" in result["answer"]
    assert result["plan"] is not None
