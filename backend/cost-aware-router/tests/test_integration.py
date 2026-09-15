import pytest

from app.core.config import load_settings
from app.router.graph import build_graph

settings = load_settings()
GEMINI = "gemini"
MISTRAL = "mistral"


def test_complete_workflow_with_cost_and_serializable_result() -> None:
    calls: list[str] = []

    def executor(model: str, task_type: str, user_input: str) -> dict:
        calls.append(model)
        return {
            "answer": "Paris",
            "content": "Paris",
            "confidence": 0.95,
            "input_tokens": 10,
            "output_tokens": 2,
            "success": True,
        }

    result = build_graph(executor=executor).invoke(
        {"request_id": "integration-1", "user_input": "What is the capital of France?"}
    )

    assert result["task_type"] == "qa"
    assert result["response"]["answer"] == "Paris"
    assert result["actual_cost"] >= 0
    assert result["baseline_cost"] >= 0
    assert result["savings"] >= 0
    assert calls[0] == GEMINI


def test_empty_input_fails_gracefully() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        build_graph().invoke({"request_id": "empty", "user_input": ""})


def test_very_long_input_remains_serializable() -> None:
    result = build_graph().invoke(
        {"request_id": "long", "user_input": "Summarize " + ("important detail " * 1000)}
    )

    assert result["complexity"] in {"medium", "high"}
    assert result["status"] == "failed"
    assert result["response"]["success"] is False


def test_malformed_response_escalates_once_to_mistral() -> None:
    calls: list[str] = []

    def executor(model: str, _task_type: str, _user_input: str) -> dict:
        calls.append(model)
        return {"content": "not structured JSON", "confidence": 0.99, "success": True}

    result = build_graph(executor=executor).invoke(
        {"request_id": "malformed", "user_input": "What is the answer?"}
    )

    assert calls[0] == GEMINI
    assert result["escalation_required"] is True
    assert result["selected_model"] == MISTRAL


def test_both_models_unavailable_do_not_loop() -> None:
    calls: list[str] = []

    def executor(model: str, _task_type: str, _user_input: str) -> dict:
        calls.append(model)
        raise RuntimeError("provider unavailable")

    result = build_graph(executor=executor).invoke(
        {"request_id": "unavailable", "user_input": "What is the answer?"}
    )

    assert calls[0] == GEMINI
    assert calls[-1] == MISTRAL
    assert result["selected_model"] == MISTRAL
    assert result["response"]["success"] is False
    assert result["status"] == "fallback"
