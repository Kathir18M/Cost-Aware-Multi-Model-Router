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
	status: str
