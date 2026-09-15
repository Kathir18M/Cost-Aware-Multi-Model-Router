"""Selected application tools exposed through the MCP boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from app.services.cost_service import calculate_savings
from app.tools.cost_calculator import calculate_cost, get_model_pricing
from app.tools.evaluation_tool import evaluate_response
from app.tools.model_policy_tool import check_model_policy
from app.tools.routing_logger import log_routing_event
from app.tools.statistics_tool import get_router_statistics


def _calculate_savings_tool(baseline_cost: float, actual_cost: float) -> dict[str, float]:
	return {"savings": calculate_savings(baseline_cost, actual_cost)}


@dataclass(frozen=True)
class ToolDefinition:
	name: str
	description: str
	input_schema: dict[str, Any]
	handler: Callable[..., Any]
	connector: str = "internal"
	permission: str = "READ"
	timeout_seconds: float = 10.0
	confirmation_required: bool = False


TOOL_DEFINITIONS = (
	ToolDefinition(
		"cost.calculate_cost",
		"Calculate model cost from input and output tokens.",
		{"type": "object", "required": ["model", "input_tokens", "output_tokens"]},
		calculate_cost, "cost", "READ", 5.0,
	),
	ToolDefinition(
		"cost.get_model_pricing",
		"Return configured model pricing.",
		{"type": "object", "properties": {}},
		get_model_pricing, "cost", "READ", 5.0,
	),
	ToolDefinition(
		"router.check_model_policy",
		"Recommend a model without changing LangGraph routing state.",
		{"type": "object", "required": ["task_type", "complexity", "confidence"]},
		check_model_policy, "policy", "READ", 5.0,
	),
	ToolDefinition(
		"evaluation.evaluate_response",
		"Evaluate basic answer relevance and token metadata.",
		{"type": "object", "required": ["question", "answer", "task_type"]},
		evaluate_response, "evaluation", "READ", 10.0,
	),
	ToolDefinition(
		"logs.log_routing_event",
		"Record an append-only routing event.",
		{"type": "object", "required": ["request_id", "initial_model", "final_model", "confidence", "escalation_reason", "cost"]},
		log_routing_event, "logs", "WRITE", 5.0, True,
	),
	ToolDefinition(
		"router.get_statistics",
		"Return aggregate routing statistics.",
		{"type": "object", "properties": {}},
		get_router_statistics, "router", "READ", 5.0,
	),
	ToolDefinition(
		"cost.calculate_savings",
		"Calculate non-negative savings from baseline and actual cost.",
		{"type": "object", "required": ["baseline_cost", "actual_cost"]},
		_calculate_savings_tool, "cost", "READ", 5.0,
	),
)


def list_tool_definitions() -> list[dict[str, Any]]:
	definitions = []
	for tool in TOOL_DEFINITIONS:
		definition = {
			"name": tool.name,
			"description": tool.description,
			"inputSchema": tool.input_schema,
			"connector": tool.connector,
			"permission": tool.permission,
			"timeout_seconds": tool.timeout_seconds,
			"confirmation_required": tool.confirmation_required,
		}
		definitions.append(definition)
		if "." in tool.name:
			definitions.append({**definition, "name": tool.name.rsplit(".", 1)[-1]})
	return definitions


def call_tool(name: str, arguments: dict[str, Any] | None = None) -> Any:
	"""Dispatch a named tool and return a JSON-serializable value."""

	for tool in TOOL_DEFINITIONS:
		if tool.name == name or tool.name.rsplit(".", 1)[-1] == name:
			return tool.handler(**(arguments or {}))
	raise KeyError(f"Unknown MCP tool: {name}")


def get_langchain_tools() -> list[Any]:
	"""Adapt selected tools for optional LangChain tool-calling clients."""

	from langchain_core.tools import StructuredTool

	return [
		StructuredTool.from_function(
			func=tool.handler,
			name=tool.name.rsplit(".", 1)[-1],
			description=tool.description,
		)
		for tool in TOOL_DEFINITIONS
		if tool.name in {"cost.calculate_cost", "evaluation.evaluate_response", "router.check_model_policy"}
	]
