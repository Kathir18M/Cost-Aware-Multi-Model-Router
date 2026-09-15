"""Deterministic task classification for the routing workflow."""

from __future__ import annotations

from app.core.constants import (
	TASK_CLASSIFICATION,
	TASK_EXTRACTION,
	TASK_QA,
	TASK_SUMMARIZATION,
)


class TaskClassificationError(ValueError):
	"""Raised when user input cannot be classified."""


def classify_task(user_input: str) -> str:
	"""Classify input using transparent keyword signals."""

	if not isinstance(user_input, str) or not user_input.strip():
		raise TaskClassificationError("user_input must be a non-empty string")

	text = user_input.strip().lower()
	if any(word in text for word in ("summarize", "summarise", "summary", "tldr")):
		return TASK_SUMMARIZATION
	if any(word in text for word in ("extract", "entities", "fields", "json")):
		return TASK_EXTRACTION
	if text.endswith("?") or any(
		text.startswith(word) for word in ("who ", "what ", "when ", "where ", "why ", "how ")
	):
		return TASK_QA
	return TASK_CLASSIFICATION
