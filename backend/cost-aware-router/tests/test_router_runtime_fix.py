from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api_server import app, _request_id, _safe_executor
from app.core.config import Settings, load_settings
from app.router.graph import build_graph
from app.tools.routing_logger import log_routing_event
from app.utils.helpers import get_project_root


def test_unique_request_id_per_call() -> None:
    req1 = _request_id()
    req2 = _request_id()
    req3 = _request_id()
    assert req1 != req2
    assert req2 != req3
    assert req1.startswith("req_")


def test_gemini_success_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get_model(name: str) -> Mock:
        mock_wrapper = Mock()
        mock_wrapper.invoke.return_value = Mock(
            success=True,
            content="Gemini test answer",
            model="gemini-2.0-flash",
            input_tokens=100,
            output_tokens=50,
            latency=0.1,
            error=None,
        )
        return mock_wrapper

    monkeypatch.setattr("app.models.model_registry.get_model", fake_get_model)
    res = _safe_executor("gemini", "qa", "What is 2+2?")
    assert res["success"] is True
    assert res["content"] == "Gemini test answer"
    assert res["model"] == "gemini-2.0-flash"


def test_gemini_404_failure_triggers_mistral_fallback() -> None:
    def executor(model: str, task_type: str, user_input: str) -> dict:
        if "gemini" in model.lower():
            return {
                "content": "",
                "success": False,
                "error": "Error calling model 'gemini-2.0-flash' (NOT_FOUND): 404 NOT_FOUND",
                "model": "gemini",
            }
        return {
            "content": "Mistral fallback response",
            "summary": "Mistral fallback response",
            "answer": "Mistral fallback response",
            "confidence": 0.90,
            "success": True,
            "model": "mistral",
        }

    graph = build_graph(executor=executor)
    result = graph.invoke({
        "request_id": "test-req-404",
        "user_input": "Summarize artificial intelligence.",
        "task_type": "summarization",
    })

    assert result["initial_model"] == "gemini"
    assert result["selected_model"] == "mistral"
    assert result["escalation_required"] is True
    assert "Gemini" in str(result.get("escalation_reason"))
    assert result["response"]["content"] == "Mistral fallback response"


def test_both_models_fail_handled_properly() -> None:
    def executor(model: str, task_type: str, user_input: str) -> dict:
        return {
            "content": "",
            "success": False,
            "error": "Provider connection failed",
            "model": model,
        }

    graph = build_graph(executor=executor)
    result = graph.invoke({
        "request_id": "test-req-both-failed",
        "user_input": "Test query",
        "task_type": "qa",
    })

    assert result["response"]["success"] is False


def test_routing_logger_and_user_isolation(tmp_path: Path) -> None:
    log_file = tmp_path / "router_events.jsonl"

    log_routing_event(
        request_id="req_001",
        initial_model="gemini",
        final_model="gemini",
        confidence=0.95,
        escalation_reason=None,
        cost=0.0001,
        user_id="user_A",
        actual_cost=0.0001,
        baseline_cost=0.0003,
        savings=0.0002,
        savings_percentage=66.67,
        log_path=log_file,
    )

    log_routing_event(
        request_id="req_002",
        initial_model="gemini",
        final_model="mistral",
        confidence=0.88,
        escalation_reason="Gemini provider failure",
        cost=0.0005,
        user_id="user_B",
        actual_cost=0.0005,
        baseline_cost=0.0005,
        savings=0.0000,
        savings_percentage=0.0,
        log_path=log_file,
    )

    lines = [json.loads(line) for line in log_file.read_text(encoding="utf-8").splitlines()]
    user_a_events = [e for e in lines if e.get("user_id") == "user_A"]
    user_b_events = [e for e in lines if e.get("user_id") == "user_B"]

    assert len(user_a_events) == 1
    assert user_a_events[0]["final_model"] == "gemini"
    assert user_a_events[0]["savings"] == 0.0002

    assert len(user_b_events) == 1
    assert user_b_events[0]["final_model"] == "mistral"
    assert user_b_events[0]["escalated"] is True


def test_dashboard_api_authenticated_user_isolation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.auth.clerk.verify_clerk_token", lambda token: {"sub": "test_user_isolated"})
    client = TestClient(app)
    resp = client.get("/api/dashboard", headers={"Authorization": "Bearer valid-token"})

    assert resp.status_code == 200
    data = resp.json()
    assert "total_requests" in data
    assert "gemini_requests" in data
    assert "mistral_requests" in data
    assert "total_cost" in data
    assert "total_savings" in data
