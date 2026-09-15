"""Cost comparison services for routed requests."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.tools.cost_calculator import calculate_cost


def calculate_request_cost(
	model: str | Sequence[str],
	input_tokens: int | Sequence[int],
	output_tokens: int | Sequence[int],
) -> dict[str, Any]:
	"""Calculate actual cost, including both calls for escalated requests."""

	return calculate_cost(model, input_tokens, output_tokens)


def calculate_baseline_cost(input_tokens: int, output_tokens: int) -> dict[str, Any]:
	"""Calculate what the same token usage would cost using Mistral only."""

	return calculate_cost("mistral", input_tokens, output_tokens)


def _cost_value(value: float | dict[str, Any]) -> float:
	return float(value["cost"]) if isinstance(value, dict) else float(value)


def calculate_savings(
	baseline_cost: float | dict[str, Any], actual_cost: float | dict[str, Any]
) -> float:
	"""Return non-negative savings; negative comparisons are reported as zero."""

	return round(max(0.0, _cost_value(baseline_cost) - _cost_value(actual_cost)), 10)


def calculate_cumulative_savings(
	previous_savings: float, current_savings: float | dict[str, Any]
) -> float:
	if previous_savings < 0:
		raise ValueError("previous_savings must not be negative")
	return round(previous_savings + max(0.0, _cost_value(current_savings)), 10)
