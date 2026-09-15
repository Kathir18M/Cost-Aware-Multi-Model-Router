"""Tool-facing confidence assessment wrapper."""

from app.router.confidence_engine import assess_response


def evaluate_confidence(response: dict, task_type: str) -> dict[str, float | bool]:
	"""Return a serializable confidence score and validity flag."""

	score = assess_response(response, task_type)
	return {"confidence": score, "valid": score > 0}
