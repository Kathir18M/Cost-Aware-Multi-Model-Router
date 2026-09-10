"""Cost calculation utilities using configured per-token prices."""

from __future__ import annotations

from typing import Any

from app.core.config import load_settings


def get_model_pricing() -> dict[str, dict[str, float]]:
	"""Return configured input/output prices without exposing secrets."""

	settings = load_settings()
	return {
		"haiku": {
			"input_price": settings.haiku_input_price,
			"output_price": settings.haiku_output_price,
		},
		"sonnet": {
			"input_price": settings.sonnet_input_price,
			"output_price": settings.sonnet_output_price,
		},
	}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> dict[str, Any]:
	"""Calculate cost from token counts and configured prices."""

	if input_tokens < 0 or output_tokens < 0:
		raise ValueError("Token counts must not be negative")
	pricing = get_model_pricing()
	key = model.strip().lower()
	if key not in pricing:
		raise ValueError(f"Unsupported model: {model}")
	cost = (
		input_tokens * pricing[key]["input_price"]
		+ output_tokens * pricing[key]["output_price"]
	)
	return {
		"model": key,
		"input_tokens": input_tokens,
		"output_tokens": output_tokens,
		"cost": round(cost, 10),
	}
