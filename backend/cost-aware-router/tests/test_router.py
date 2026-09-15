import pytest

from app.core.constants import (
	COMPLEXITY_HIGH,
	COMPLEXITY_LOW,
	COMPLEXITY_MEDIUM,
	MODEL_GEMINI,
	MODEL_MISTRAL,
	STATUS_ACCEPTED,
)
from app.router.graph import build_graph
from app.router.model_selector import select_model
from app.router.nodes import check_confidence_node


def test_model_selection_policy() -> None:
	assert select_model(COMPLEXITY_LOW) == MODEL_GEMINI
	assert select_model(COMPLEXITY_MEDIUM) == MODEL_GEMINI
	assert select_model(COMPLEXITY_MEDIUM, medium_complexity_model=MODEL_MISTRAL) == MODEL_MISTRAL
	assert select_model(COMPLEXITY_HIGH) == MODEL_MISTRAL


def test_invalid_complexity_policy() -> None:
	with pytest.raises(ValueError):
		select_model("unknown")


def test_compiled_graph_runs_serializable_state() -> None:
	calls: list[tuple[str, str, str]] = []

	def executor(model: str, task_type: str, user_input: str) -> dict:
		calls.append((model, task_type, user_input))
		return {
			"content": "done",
			"summary": "done",
			"confidence": 0.95,
			"success": True,
		}

	result = build_graph(executor=executor).invoke(
		{"request_id": "req-1", "user_input": "Summarize this report"}
	)

	assert result["task_type"] == "summarization"
	assert result["complexity"] == COMPLEXITY_LOW
	assert result["selected_model"] == MODEL_GEMINI
	assert result["initial_model"] == MODEL_GEMINI
	assert result["confidence"] >= 0.7
	assert result["escalation_required"] is False
	assert result["status"] == STATUS_ACCEPTED
	assert calls == [(MODEL_GEMINI, "summarization", "Summarize this report")]


def test_graph_rejects_invalid_input() -> None:
	with pytest.raises(ValueError):
		build_graph().invoke({"user_input": ""})


def test_failed_response_requires_escalation() -> None:
	state = check_confidence_node(
		{"response": {"success": False, "error": "temporary failure"}}
	)

	assert state["escalation_required"] is True
	assert state["escalation_reason"] == "Response validation failed"
