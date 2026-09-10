"""Selected application tools exposed through the MCP boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from app.tools.cost_calculator import calculate_cost, get_model_pricing
from app.tools.evaluation_tool import evaluate_response
from app.tools.model_policy_tool import check_model_policy
from app.tools.routing_logger import log_routing_event
from app.tools.statistics_tool import get_router_statistics


@dataclass(frozen=True)
class ToolDefinition:
	name: str
	description: str
	input_schema: dict[str, Any]
	handler: Callable[..., Any]


TOOL_DEFINITIONS = (
	ToolDefinition(
		"calculate_cost",
		"Calculate model cost from input and output tokens.",
		{"type": "object", "required": ["model", "input_tokens", "output_tokens"]},
		calculate_cost,
	),
	ToolDefinition(
		"get_model_pricing",
		"Return configured model pricing.",
		{"type": "object", "properties": {}},
		get_model_pricing,
	),
	ToolDefinition(
		"check_model_policy",
		"Recommend a model without changing LangGraph routing state.",
		{"type": "object", "required": ["task_type", "complexity", "confidence"]},
		check_model_policy,
	),
	ToolDefinition(
		"evaluate_response",
		"Evaluate basic answer relevance and token metadata.",
		{"type": "object", "required": ["question", "answer", "task_type"]},
		evaluate_response,
	),
	ToolDefinition(
		"log_routing_event",
		"Record an append-only routing event.",
		{"type": "object", "required": ["request_id", "initial_model", "final_model", "confidence", "escalation_reason", "cost"]},
		log_routing_event,
	),
	ToolDefinition(
		"get_router_statistics",
		"Return aggregate routing statistics.",
		{"type": "object", "properties": {}},
		get_router_statistics,
	),
)


def list_tool_definitions() -> list[dict[str, Any]]:
	return [
		{"name": tool.name, "description": tool.description, "inputSchema": tool.input_schema}
		for tool in TOOL_DEFINITIONS
	]


def call_tool(name: str, arguments: dict[str, Any] | None = None) -> Any:
	"""Dispatch a named tool and return a JSON-serializable value."""

	for tool in TOOL_DEFINITIONS:
		if tool.name == name:
			return tool.handler(**(arguments or {}))
	raise KeyError(f"Unknown MCP tool: {name}")


def get_langchain_tools() -> list[Any]:
	"""Adapt selected tools for optional LangChain tool-calling clients."""

	from langchain_core.tools import StructuredTool

	return [
		StructuredTool.from_function(
			func=tool.handler,
			name=tool.name,
			description=tool.description,
		)
		for tool in TOOL_DEFINITIONS
		if tool.name in {"calculate_cost", "evaluate_response", "check_model_policy"}
	]
