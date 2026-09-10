import json

import pytest

from app.mcp.server import create_server
from app.mcp.tools import get_langchain_tools


def test_mcp_tool_discovery_and_dispatch() -> None:
	server = create_server()
	tools = server.list_tools()
	names = {tool["name"] for tool in tools}

	assert {"calculate_cost", "evaluate_response", "check_model_policy"} <= names
	result = server.call_tool(
		"calculate_cost", {"model": "haiku", "input_tokens": 10, "output_tokens": 5}
	)
	assert result["model"] == "haiku"
	assert json.dumps(result)


def test_mcp_resources_are_serializable() -> None:
	server = create_server()
	resources = server.list_resources()
	assert {resource["uri"] for resource in resources} == {
		"router://pricing",
		"router://statistics",
	}
	assert json.dumps(server.read_resource("router://pricing"))


def test_mcp_rejects_unknown_operations() -> None:
	server = create_server()
	with pytest.raises(KeyError):
		server.call_tool("not_a_tool")
	with pytest.raises(KeyError):
		server.read_resource("router://unknown")


def test_langchain_tool_adapters() -> None:
	tools = get_langchain_tools()
	assert {tool.name for tool in tools} == {
		"calculate_cost",
		"evaluate_response",
		"check_model_policy",
	}
