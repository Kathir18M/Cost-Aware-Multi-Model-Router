import pytest

from app.router.confidence_engine import (
	assess_response,
	calculate_confidence,
	response_is_valid,
)


def test_high_quality_signals_produce_high_confidence() -> None:
	score = calculate_confidence(
		task_certainty=1,
		output_validity=1,
		required_fields_present=1,
		answer_completeness=1,
		response_consistency=1,
		model_reported_confidence=1,
	)

	assert score == 1.0


def test_model_reported_confidence_is_not_ground_truth() -> None:
	score = calculate_confidence(
		task_certainty=0,
		output_validity=0,
		required_fields_present=0,
		answer_completeness=0,
		response_consistency=0,
		model_reported_confidence=1,
	)

	assert score == 0.05


def test_invalid_response_scores_low() -> None:
	response = {"success": False, "error": "API failure"}

	assert response_is_valid(response, "qa") is False
	assert assess_response(response, "qa") == 0.0


@pytest.mark.parametrize(
	("task_type", "field"),
	[
		("classification", "label"),
		("extraction", "fields"),
		("summarization", "summary"),
		("qa", "answer"),
	],
)
def test_required_task_fields_are_checked(task_type: str, field: str) -> None:
	assert response_is_valid({field: "value", "success": True}, task_type)
	assert not response_is_valid({"success": True}, task_type)
