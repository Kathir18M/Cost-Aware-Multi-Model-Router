"""Cost calculation utilities using configured per-token prices."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.core.config import load_settings


def get_model_pricing() -> dict[str, dict[str, float]]:
	"""Return configured Gemini/Mistral input/output prices without exposing secrets."""

	settings = load_settings()
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
	pricing["haiku"] = pricing["gemini"]
	pricing["sonnet"] = pricing["mistral"]
	return pricing


def _normalize_model_name(model: str) -> str:
	key = model.strip().lower()
	if key in {"haiku", "gemini"} or key.startswith("gemini"):
		return "gemini"
	if key in {"sonnet", "mistral"} or key.startswith("mistral"):
		return "mistral"
	return key


def calculate_cost(
	model: str | Sequence[str],
	input_tokens: int | Sequence[int],
	output_tokens: int | Sequence[int],
) -> dict[str, Any]:
	"""Calculate input, output, and total cost for one or more model calls."""

	models = [model] if isinstance(model, str) else list(model)
	inputs = [input_tokens] if isinstance(input_tokens, int) else list(input_tokens)
	outputs = [output_tokens] if isinstance(output_tokens, int) else list(output_tokens)
	if not models or len(models) != len(inputs) or len(models) != len(outputs):
		raise ValueError("Model and token usage sequences must have matching lengths")
	pricing = get_model_pricing()
	breakdown = []
	for current_model, current_input, current_output in zip(models, inputs, outputs):
		if current_input < 0 or current_output < 0:
			raise ValueError("Token counts must not be negative")
		key = _normalize_model_name(str(current_model))
		if key not in pricing:
			raise ValueError(f"Unsupported model: {current_model}")
		input_cost = current_input * pricing[key]["input_price"]
		output_cost = current_output * pricing[key]["output_price"]
		breakdown.append(
			{
				"model": key,
				"input_tokens": current_input,
				"output_tokens": current_output,
				"input_cost": input_cost,
				"output_cost": output_cost,
				"cost": input_cost + output_cost,
			}
		)
	input_total = sum(item["input_tokens"] for item in breakdown)
	output_total = sum(item["output_tokens"] for item in breakdown)
	return {
		"model": _normalize_model_name(str(models[0])) if len(models) == 1 else "multi",
		"input_tokens": input_total,
		"output_tokens": output_total,
		"total_tokens": input_total + output_total,
		"input_cost": round(sum(item["input_cost"] for item in breakdown), 10),
		"output_cost": round(sum(item["output_cost"] for item in breakdown), 10),
		"cost": round(sum(item["cost"] for item in breakdown), 10),
		"breakdown": breakdown,
	}
