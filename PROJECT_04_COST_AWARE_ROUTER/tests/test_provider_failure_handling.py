"""Unit test suite for provider failure handling, rate limit classification, and HTTP 503 responses."""

import pytest
from fastapi.testclient import TestClient
from api_server import app
from app.models.provider_error_classifier import (
    classify_provider_error,
    ERROR_RATE_LIMITED,
    ERROR_AUTHENTICATION,
    ERROR_PERMISSION,
    ERROR_MODEL_NOT_FOUND,
    ERROR_TIMEOUT,
    ERROR_PROVIDER_FAIL,
)
from app.router.agent_graph import run_agent_request


def test_1_provider_error_classification_mappings():
    # 429 Rate limit
    res_429 = classify_provider_error("429 RESOURCE_EXHAUSTED: Quota exceeded")
    assert res_429["error_type"] == ERROR_RATE_LIMITED

    res_rate_limit = classify_provider_error("Rate limit exceeded")
    assert res_rate_limit["error_type"] == ERROR_RATE_LIMITED

    # 401 Auth
    res_401 = classify_provider_error("HTTP Error 401: Unauthorized")
    assert res_401["error_type"] == ERROR_AUTHENTICATION

    # 403 Permission
    res_403 = classify_provider_error("HTTP Error 403: Forbidden")
    assert res_403["error_type"] == ERROR_PERMISSION

    # 404 Model Not Found
    res_404 = classify_provider_error("404 NOT_FOUND: model is no longer available")
    assert res_404["error_type"] == ERROR_MODEL_NOT_FOUND

    # Timeout
    res_timeout = classify_provider_error("Connection timed out after 10s")
    assert res_timeout["error_type"] == ERROR_TIMEOUT

    # 500 Provider Error
    res_500 = classify_provider_error("500 Internal Server Error")
    assert res_500["error_type"] == ERROR_PROVIDER_FAIL


def test_2_retry_after_extraction():
    res = classify_provider_error("429 Rate limit exceeded. Retry-After: 41")
    assert res["retry_after_seconds"] == 41

    res_alt = classify_provider_error("Quota exceeded. Please try again in 30 s")
    assert res_alt["retry_after_seconds"] == 30


def test_3_gemini_429_invokes_mistral_fallback():
    def gemini_rate_limited_executor(model: str, task_type: str, user_input: str) -> dict:
        if "gemini" in model.lower():
            return {
                "success": False,
                "error": "429 RESOURCE_EXHAUSTED",
                "error_type": ERROR_RATE_LIMITED,
                "retry_after_seconds": 41,
            }
        return {
            "success": True,
            "answer": "Mistral successful response",
            "content": "Mistral successful response",
            "confidence": 0.88,
            "input_tokens": 10,
            "output_tokens": 20,
        }

    res = run_agent_request(query="What is AI?", executor=gemini_rate_limited_executor)
    assert res["model"] == "mistral"
    assert res["escalated"] is True
    assert "Mistral successful response" in res["answer"]


def test_4_both_providers_failed_returns_provider_unavailable():
    def both_failed_executor(model: str, task_type: str, user_input: str) -> dict:
        if "gemini" in model.lower():
            return {
                "success": False,
                "error": "429 RESOURCE_EXHAUSTED",
                "error_type": ERROR_RATE_LIMITED,
                "retry_after_seconds": 41,
            }
        return {
            "success": False,
            "error": "429 Rate limit exceeded",
            "error_type": ERROR_RATE_LIMITED,
            "retry_after_seconds": 30,
        }

    res = run_agent_request(query="What is AI?", executor=both_failed_executor)
    assert res["status"] == "provider_unavailable"
    assert res["all_providers_failed"] is True
    assert res["answer"] is None
    assert res["cost"] == 0
    assert res["savings"] == 0
    assert res["escalation_reason"] == "Gemini rate limited; Mistral rate limited"


def test_5_api_endpoints_return_503_on_all_providers_failed(monkeypatch):
    client = TestClient(app)

    def failing_executor(model_name: str, task_type: str, user_input: str) -> dict:
        return {
            "content": "",
            "answer": "",
            "success": False,
            "error": "429 Rate limit exceeded",
            "error_type": ERROR_RATE_LIMITED,
            "retry_after_seconds": 41,
            "model": model_name,
        }

    monkeypatch.setattr("api_server._safe_executor", failing_executor)

    # Test /api/router/run
    resp_router = client.post("/api/router/run", json={"task_type": "qa", "input": "Hello"})
    assert resp_router.status_code == 503
    body_router = resp_router.json()
    assert body_router["status"] == "provider_unavailable"
    assert body_router["answer"] is None
    assert body_router["error"]["code"] == "ALL_PROVIDERS_UNAVAILABLE"
