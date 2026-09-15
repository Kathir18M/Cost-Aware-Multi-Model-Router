"""Explainable complexity analysis for routing decisions."""

from __future__ import annotations

from app.core.constants import COMPLEXITY_HIGH, COMPLEXITY_LOW, COMPLEXITY_MEDIUM


def analyze_complexity(user_input: str) -> str:
	"""Classify complexity from length, instructions, constraints, and ambiguity."""

	if not isinstance(user_input, str) or not user_input.strip():
		raise ValueError("user_input must be a non-empty string")

	text = user_input.strip()
	words = text.split()
	instruction_count = sum(
		text.lower().count(marker)
		for marker in (" and ", " then ", "after that", "step ")
	)
	constraint_count = sum(
		text.lower().count(marker)
		for marker in ("must", "should", "only", "exactly", "include", "excluding")
	)
	reasoning_count = sum(
		text.lower().count(marker)
		for marker in ("compare", "analyze", "reason", "trade-off", "pros and cons", "why")
	)
	ambiguity_count = sum(
		text.lower().count(marker) for marker in ("maybe", "possibly", "unclear", "ambiguous")
	)

	score = 0
	score += 2 if len(words) > 120 else 1 if len(words) > 60 else 0
	score += min(instruction_count, 3)
	score += min(constraint_count, 2)
	score += min(reasoning_count, 3)
	score += min(ambiguity_count, 2)

	if score >= 5:
		return COMPLEXITY_HIGH
	if score >= 2:
		return COMPLEXITY_MEDIUM
	return COMPLEXITY_LOW
