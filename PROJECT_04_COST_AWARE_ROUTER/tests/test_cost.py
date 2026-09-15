import pytest

from app.core.config import load_settings
from app.services.cost_service import (
	calculate_baseline_cost,
	calculate_cumulative_savings,
	calculate_request_cost,
	calculate_savings,
)


settings = load_settings()
GEMINI = "gemini"
MISTRAL = "mistral"


def test_gemini_only_request() -> None:
	result = calculate_request_cost(GEMINI, 1000, 500)
	pricing = {
		"gemini": {
			"input_price": settings.gemini_input_price,
			"output_price": settings.gemini_output_price,
		},
	}

	assert result["input_tokens"] == 1000
	assert result["output_tokens"] == 500
	assert result["total_tokens"] == 1500
	assert result["cost"] == pytest.approx(
		1000 * pricing["gemini"]["input_price"] + 500 * pricing["gemini"]["output_price"]
	)


def test_mistral_request_and_baseline() -> None:
	result = calculate_request_cost(MISTRAL, 1000, 500)
	baseline = calculate_baseline_cost(1000, 500)
	pricing = {
		"mistral": {
			"input_price": settings.mistral_input_price,
			"output_price": settings.mistral_output_price,
		},
	}

	assert result["cost"] == pytest.approx(baseline["cost"])
	assert result["input_cost"] == pytest.approx(1000 * pricing["mistral"]["input_price"])
	assert result["output_cost"] == pytest.approx(500 * pricing["mistral"]["output_price"])


def test_escalated_request_combines_model_tokens() -> None:
	result = calculate_request_cost([GEMINI, MISTRAL], [1000, 800], [500, 300])
	pricing = {
		"gemini": {
			"input_price": settings.gemini_input_price,
			"output_price": settings.gemini_output_price,
		},
		"mistral": {
			"input_price": settings.mistral_input_price,
			"output_price": settings.mistral_output_price,
		},
	}
	expected_cost = (
		1000 * pricing["gemini"]["input_price"] + 500 * pricing["gemini"]["output_price"]
		+ 800 * pricing["mistral"]["input_price"] + 300 * pricing["mistral"]["output_price"]
	)

	assert result["input_tokens"] == 1800
	assert result["output_tokens"] == 800
	assert result["total_tokens"] == 2600
	assert result["breakdown"][0]["model"] == GEMINI
	assert result["breakdown"][1]["model"] == MISTRAL
	assert result["cost"] == pytest.approx(expected_cost)


def test_savings_and_cumulative_savings() -> None:
	actual = calculate_request_cost(GEMINI, 1000, 500)
	baseline = calculate_baseline_cost(1000, 500)
	savings = calculate_savings(baseline, actual)
	expected_savings = max(0.0, baseline["cost"] - actual["cost"])

	assert savings == pytest.approx(expected_savings)
	assert calculate_cumulative_savings(0.01, savings) == pytest.approx(0.01 + expected_savings)
	assert calculate_savings(actual, baseline) == pytest.approx(
		max(0.0, actual["cost"] - baseline["cost"])
	)


def test_invalid_token_usage() -> None:
	with pytest.raises(ValueError):
		calculate_request_cost(GEMINI, -1, 0)
