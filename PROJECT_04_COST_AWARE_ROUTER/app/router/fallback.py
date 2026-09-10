"""Bounded technical retry and Sonnet fallback behavior."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.core.constants import MODEL_HAIKU, MODEL_SONNET

ModelExecutor = Callable[[str, str, str], dict[str, Any]]


def execute_with_fallback(
	executor: ModelExecutor,
	*,
	task_type: str,
	user_input: str,
	initial_model: str,
	max_retries: int = 1,
) -> tuple[dict[str, Any], str, int, bool]:
	"""Retry once, then use Sonnet exactly once for technical failures."""

	if max_retries < 0:
		raise ValueError("max_retries must not be negative")
	attempts = 0
	for _ in range(max_retries + 1):
		attempts += 1
		try:
			response = executor(initial_model, task_type, user_input)
			if response.get("success", True) and not response.get("error"):
				return response, initial_model, attempts - 1, False
		except Exception:
			response = {"content": "", "success": False, "error": "Model request failed"}
	if initial_model == MODEL_SONNET:
		return response, initial_model, attempts - 1, False

	try:
		fallback = executor(MODEL_SONNET, task_type, user_input)
	except Exception:
		fallback = {"content": "", "success": False, "error": "Fallback request failed"}
	return fallback, MODEL_SONNET, attempts - 1, True
