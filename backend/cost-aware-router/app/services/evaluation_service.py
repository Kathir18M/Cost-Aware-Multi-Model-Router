"""Service boundary for immutable held-out evaluation."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from app.evaluation.evaluator import Strategy
from app.evaluation.test_runner import run_evaluation


def evaluate_heldout(
	strategies: Mapping[str, Strategy], *, dataset_path: str | Path | None = None
) -> dict[str, Any]:
	"""Compare the active Gemini/Mistral strategies while remaining compatible with legacy names."""

	alias_map = {
		"always_haiku": "always_gemini",
		"always_sonnet": "always_mistral",
		"always_gemini": "always_gemini",
		"always_mistral": "always_mistral",
	}
	required = {"always_gemini", "always_mistral", "cost_aware_router"}
	provided = set(strategies)
	resolved = {alias_map.get(name, name) for name in provided}
	missing = required - resolved
	if missing:
		raise ValueError(f"Missing evaluation strategies: {sorted(missing)}")
	return run_evaluation(strategies, dataset_path=dataset_path)
