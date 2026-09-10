import pytest

from app.services.cost_service import (
	calculate_baseline_cost,
	calculate_cumulative_savings,
	calculate_request_cost,
	calculate_savings,
)


def test_haiku_only_request() -> None:
	result = calculate_request_cost("haiku", 1000, 500)

	assert result["input_tokens"] == 1000
	assert result["output_tokens"] == 500
	assert result["total_tokens"] == 1500
	assert result["cost"] == pytest.approx(0.0035)


def test_sonnet_request_and_baseline() -> None:
	result = calculate_request_cost("sonnet", 1000, 500)
	baseline = calculate_baseline_cost(1000, 500)

	assert result["cost"] == pytest.approx(baseline["cost"])
	assert result["input_cost"] == pytest.approx(0.003)
	assert result["output_cost"] == pytest.approx(0.0075)


def test_escalated_request_combines_model_tokens() -> None:
	result = calculate_request_cost(["haiku", "sonnet"], [1000, 800], [500, 300])

	assert result["input_tokens"] == 1800
	assert result["output_tokens"] == 800
	assert result["total_tokens"] == 2600
	assert result["breakdown"][0]["model"] == "haiku"
	assert result["breakdown"][1]["model"] == "sonnet"
	assert result["cost"] == pytest.approx(0.0035 + 0.0069)


def test_savings_and_cumulative_savings() -> None:
	actual = calculate_request_cost("haiku", 1000, 500)
	baseline = calculate_baseline_cost(1000, 500)
	savings = calculate_savings(baseline, actual)

	assert savings == pytest.approx(0.007)
	assert calculate_cumulative_savings(0.01, savings) == pytest.approx(0.017)
	assert calculate_savings(actual, baseline) == 0.0


def test_invalid_token_usage() -> None:
	with pytest.raises(ValueError):
		calculate_request_cost("haiku", -1, 0)
