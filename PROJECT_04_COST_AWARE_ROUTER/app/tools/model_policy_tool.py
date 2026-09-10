"""Policy recommendation tool; LangGraph remains the policy executor."""

from app.core.constants import COMPLEXITY_HIGH, MODEL_HAIKU, MODEL_SONNET


def check_model_policy(task_type: str, complexity: str, confidence: float) -> dict[str, str]:
	if not task_type.strip():
		raise ValueError("task_type must not be empty")
	if not 0 <= confidence <= 1:
		raise ValueError("confidence must be between 0 and 1")
	if complexity == COMPLEXITY_HIGH:
		return {"recommended_model": MODEL_SONNET, "reason": "High complexity"}
	return {"recommended_model": MODEL_HAIKU, "reason": "Haiku is sufficient for this complexity"}
