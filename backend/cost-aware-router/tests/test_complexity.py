import pytest

from app.core.constants import COMPLEXITY_HIGH, COMPLEXITY_LOW, COMPLEXITY_MEDIUM
from app.router.complexity_analyzer import analyze_complexity


def test_low_complexity() -> None:
	assert analyze_complexity("What is the status?") == COMPLEXITY_LOW


def test_medium_complexity() -> None:
	text = "Classify this request and explain the reason."
	assert analyze_complexity(text) == COMPLEXITY_MEDIUM


def test_high_complexity() -> None:
	text = (
		"Analyze and compare these options, then reason about the trade-off. "
		"You must include constraints, only use the supplied facts, and explain why."
	)
	assert analyze_complexity(text) == COMPLEXITY_HIGH


def test_invalid_input() -> None:
	with pytest.raises(ValueError):
		analyze_complexity("")
