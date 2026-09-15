"""Task-aware metrics for router evaluation."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any


def _words(value: object) -> set[str]:
	return set(re.findall(r"[a-z0-9]+", str(value).lower()))


def quality_score(task_type: str, expected: dict[str, Any], prediction: dict[str, Any]) -> float:
	"""Score exact labels/fields and lexical quality for free-form tasks."""

	if task_type == "classification":
		return float(prediction.get("label") == expected.get("label"))
	if task_type == "extraction":
		expected_fields = expected.get("fields", {})
		actual_fields = prediction.get("fields", {})
		if not expected_fields:
			return 1.0 if not actual_fields else 0.0
		return sum(actual_fields.get(key) == value for key, value in expected_fields.items()) / len(expected_fields)
	field = "summary" if task_type == "summarization" else "answer"
	expected_words = _words(expected.get(field, ""))
	actual_words = _words(prediction.get(field, ""))
	if not expected_words:
		return 0.0
	return len(expected_words & actual_words) / len(expected_words)


def _normalize_model_name(model: object) -> str:
	value = str(model).strip().lower()
	if value in {"haiku", "gemini"} or value.startswith("gemini"):
		return "gemini"
	if value in {"sonnet", "mistral"} or value.startswith("mistral"):
		return "mistral"
	return value


def calculate_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
	"""Aggregate factual quality, model, confidence, cost, and savings metrics."""

	total = len(records)
	correct = sum(record.get("quality", 0) >= 0.999 for record in records)
	by_task: dict[str, list[float]] = defaultdict(list)
	for record in records:
		by_task[record["task_type"]].append(float(record.get("quality", 0)))
	gemini = sum(_normalize_model_name(record.get("final_model")) == "gemini" for record in records)
	mistral = sum(_normalize_model_name(record.get("final_model")) == "mistral" for record in records)
	escalated = sum(_normalize_model_name(record.get("initial_model")) != _normalize_model_name(record.get("final_model")) for record in records)
	actual_cost = sum(float(record.get("actual_cost", 0)) for record in records)
	baseline_cost = sum(float(record.get("baseline_cost", 0)) for record in records)
	return {
		"total_examples": total,
		"accuracy": correct / total if total else 0.0,
		"task_level_accuracy": {
			task: sum(scores) / len(scores) for task, scores in sorted(by_task.items())
		},
		"model_usage": {"gemini": gemini, "mistral": mistral},
		"gemini_usage_pct": gemini / total if total else 0.0,
		"mistral_usage_pct": mistral / total if total else 0.0,
		"escalation_rate": escalated / total if total else 0.0,
		"average_confidence": sum(float(record.get("confidence", 0)) for record in records) / total if total else 0.0,
		"average_cost": actual_cost / total if total else 0.0,
		"actual_cost": round(actual_cost, 10),
		"baseline_cost": round(baseline_cost, 10),
		"total_savings": round(max(0.0, baseline_cost - actual_cost), 10),
	}
