"""Serializable state passed between LangGraph router nodes."""

from __future__ import annotations

from typing import Any, TypedDict


class RouterState(TypedDict, total=False):
	request_id: str
	user_input: str
	task_type: str
	complexity: str
	selected_model: str
	initial_model: str
	response: dict[str, Any] | None
	confidence: float | None
	escalation_required: bool
	escalation_reason: str | None
	escalation_event: dict[str, Any] | None
	retry_count: int
	actual_cost: float
	baseline_cost: float
	savings: float
	cumulative_savings: float
	status: str
	tool_required: bool
	available_tools: list[dict[str, Any]]
	selected_tool: str | None
	tool_result: Any
	tool_error: str | None
