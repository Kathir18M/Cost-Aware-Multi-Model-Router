"""Dependency-free token estimation for tool and telemetry use."""

from __future__ import annotations


def count_tokens(text: str) -> int:
	"""Estimate tokens using a stable character heuristic.

	This is intentionally an estimate until a provider tokenizer is selected.
	"""

	if not isinstance(text, str):
		raise TypeError("text must be a string")
	return 0 if not text else max(1, (len(text) + 3) // 4)
