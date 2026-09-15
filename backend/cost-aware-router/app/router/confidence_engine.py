"""Measurable confidence signals for model responses."""

from __future__ import annotations

from collections.abc import Mapping


def _bounded(value: float | None) -> float:
	if value is None:
		return 0.0
	return max(0.0, min(1.0, float(value)))


def response_is_valid(response: Mapping[str, object] | None, task_type: str) -> bool:
	"""Check response success and the required task-specific output field."""

	if not response or response.get("success", True) is False or response.get("error"):
		return False
	required_field = {
		"classification": "label",
		"extraction": "fields",
		"summarization": "summary",
		"qa": "answer",
	}.get(task_type)
	if required_field is None:
		return False
	value = response.get(required_field)
	return value is not None and value != ""


def calculate_confidence(
	*,
	task_certainty: float,
	output_validity: float,
	required_fields_present: float,
	answer_completeness: float,
	response_consistency: float,
	model_reported_confidence: float | None = None,
) -> float:
	"""Return a weighted score without treating model confidence as ground truth."""

	signals = [
		(_bounded(task_certainty), 0.20),
		(_bounded(output_validity), 0.25),
		(_bounded(required_fields_present), 0.20),
		(_bounded(answer_completeness), 0.20),
		(_bounded(response_consistency), 0.10),
	]
	score = sum(value * weight for value, weight in signals)
	if model_reported_confidence is not None:
		score += _bounded(model_reported_confidence) * 0.05
	return round(max(0.0, min(1.0, score)), 4)


def assess_response(response: Mapping[str, object] | None, task_type: str) -> float:
	"""Calculate confidence from a response and task-specific validity signals."""

	valid = response_is_valid(response, task_type)
	reported = response.get("confidence") if response else None
	return calculate_confidence(
		task_certainty=1.0 if task_type and valid else 0.0,
		output_validity=1.0 if valid else 0.0,
		required_fields_present=1.0 if valid else 0.0,
		answer_completeness=1.0 if response and response.get("content") else 0.5 if valid else 0.0,
		response_consistency=1.0 if valid else 0.0,
		model_reported_confidence=float(reported) if reported is not None else None,
	)
