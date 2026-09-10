"""Load and validate immutable evaluation datasets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.utils.helpers import get_project_root

TASK_TYPES = {"classification", "extraction", "summarization", "qa"}
REQUIRED_FIELDS = {"id", "task_type", "input", "expected_output"}


def load_dataset(path: str | Path | None = None, *, minimum_examples: int = 0) -> list[dict[str, Any]]:
	"""Load examples without mutating the source dataset."""

	dataset_path = Path(path) if path else get_project_root() / "data" / "heldout" / "heldout_test.json"
	with dataset_path.open("r", encoding="utf-8") as stream:
		payload = json.load(stream)
	examples = payload.get("examples") if isinstance(payload, dict) else None
	if not isinstance(examples, list) or len(examples) < minimum_examples:
		raise ValueError(f"Dataset must contain at least {minimum_examples} examples")
	validate_dataset(examples)
	return [dict(example) for example in examples]


def validate_dataset(examples: list[dict[str, Any]]) -> None:
	seen_ids: set[str] = set()
	for example in examples:
		if not REQUIRED_FIELDS <= example.keys():
			raise ValueError("Each evaluation example needs id, task_type, input, and expected_output")
		if example["id"] in seen_ids or not isinstance(example["id"], str):
			raise ValueError("Evaluation example ids must be unique strings")
		seen_ids.add(example["id"])
		if example["task_type"] not in TASK_TYPES:
			raise ValueError(f"Unsupported task type: {example['task_type']}")
		if not isinstance(example["input"], str) or not example["input"].strip():
			raise ValueError("Evaluation input must be a non-empty string")
