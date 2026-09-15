"""Convenience entry point for held-out evaluation runs."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from app.evaluation.dataset_loader import load_dataset
from app.evaluation.evaluator import Strategy, compare_strategies


def run_evaluation(
	strategies: Mapping[str, Strategy], *, dataset_path: str | Path | None = None
) -> dict[str, Any]:
	examples = load_dataset(dataset_path, minimum_examples=20)
	return compare_strategies(examples, strategies)
