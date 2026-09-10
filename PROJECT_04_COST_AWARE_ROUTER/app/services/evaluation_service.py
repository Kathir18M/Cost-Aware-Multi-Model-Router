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
	"""Compare Always Haiku, Always Sonnet, and Cost-Aware Router strategies."""

	required = {"always_haiku", "always_sonnet", "cost_aware_router"}
	missing = required - strategies.keys()
	if missing:
		raise ValueError(f"Missing evaluation strategies: {sorted(missing)}")
	return run_evaluation(strategies, dataset_path=dataset_path)
