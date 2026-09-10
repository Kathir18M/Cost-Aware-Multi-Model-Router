"""Execute injected evaluation strategies and collect normalized records."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from app.evaluation.metrics import calculate_metrics, quality_score
from app.services.cost_service import calculate_baseline_cost, calculate_request_cost
from app.tools.token_counter import count_tokens

Strategy = Callable[[dict[str, Any]], Mapping[str, Any]]


def evaluate_strategy(examples: list[dict[str, Any]], strategy: Strategy, name: str) -> dict[str, Any]:
	records = []
	for example in examples:
		prediction = dict(strategy(dict(example)))
		model = str(prediction.get("model", "haiku"))
		input_tokens = int(prediction.get("input_tokens", count_tokens(example["input"])))
		output_field = prediction.get("answer") or prediction.get("summary") or prediction.get("content", "")
		output_tokens = int(prediction.get("output_tokens", count_tokens(str(output_field))))
		actual = calculate_request_cost(model, input_tokens, output_tokens)
		baseline = calculate_baseline_cost(input_tokens, output_tokens)
		records.append({
			"id": example["id"],
			"task_type": example["task_type"],
			"prediction": prediction,
			"quality": quality_score(example["task_type"], example["expected_output"], prediction),
			"initial_model": prediction.get("initial_model", model),
			"final_model": model,
			"confidence": float(prediction.get("confidence", 0.0)),
			"actual_cost": actual["cost"],
			"baseline_cost": baseline["cost"],
		})
	metrics = calculate_metrics(records)
	return {"strategy": name, **metrics, "records": records}


def compare_strategies(examples: list[dict[str, Any]], strategies: Mapping[str, Strategy]) -> dict[str, Any]:
	return {name: evaluate_strategy(examples, strategy, name) for name, strategy in strategies.items()}
