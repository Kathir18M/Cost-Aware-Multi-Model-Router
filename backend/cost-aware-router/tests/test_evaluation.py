import json

import pytest

from app.core.config import load_settings
from app.evaluation.dataset_loader import load_dataset, validate_dataset
from app.evaluation.metrics import calculate_metrics, quality_score
from app.services.evaluation_service import evaluate_heldout

settings = load_settings()
GEMINI = settings.gemini_model
MISTRAL = settings.mistral_model


def test_heldout_dataset_has_balanced_coverage() -> None:
	examples = load_dataset(minimum_examples=20)
	counts = {task: sum(example["task_type"] == task for example in examples) for task in {
		"classification", "extraction", "summarization", "qa"
	}}

	assert len(examples) == 20
	assert counts == {"classification": 5, "extraction": 5, "summarization": 5, "qa": 5}


def test_dataset_validation_rejects_duplicates_and_unknown_tasks() -> None:
	with pytest.raises(ValueError):
		validate_dataset([{"id": "x", "task_type": "qa", "input": "Q", "expected_output": {}},
			{"id": "x", "task_type": "qa", "input": "Q2", "expected_output": {}}])
	with pytest.raises(ValueError):
		validate_dataset([{"id": "x", "task_type": "other", "input": "Q", "expected_output": {}}])


def test_task_aware_quality_scoring() -> None:
	assert quality_score("classification", {"label": "billing"}, {"label": "billing"}) == 1
	assert quality_score("extraction", {"fields": {"a": "1", "b": "2"}}, {"fields": {"a": "1"}}) == 0.5
	assert quality_score("qa", {"answer": "blue sky"}, {"answer": "The sky is blue"}) == 1


def test_metric_calculation() -> None:
	records = [
		{"task_type": "qa", "quality": 1, "final_model": GEMINI, "initial_model": GEMINI, "confidence": 0.9, "actual_cost": 0.01, "baseline_cost": 0.02},
		{"task_type": "qa", "quality": 0.5, "final_model": MISTRAL, "initial_model": GEMINI, "confidence": 0.6, "actual_cost": 0.03, "baseline_cost": 0.02},
	]
	metrics = calculate_metrics(records)

	assert metrics["total_examples"] == 2
	assert metrics["accuracy"] == 0.5
	assert metrics["gemini_usage_pct"] == 0.5
	assert metrics["mistral_usage_pct"] == 0.5
	assert metrics["escalation_rate"] == 0.5
	assert metrics["average_confidence"] == pytest.approx(0.75)
	assert metrics["actual_cost"] == pytest.approx(0.04)
	assert metrics["baseline_cost"] == pytest.approx(0.04)
	assert metrics["total_savings"] == 0


def test_strategy_comparison_reports_all_required_strategies() -> None:
	examples = load_dataset(minimum_examples=20)

	def expected(example: dict) -> dict:
		return {**example["expected_output"], "model": GEMINI, "confidence": 0.9}

	strategies = {
		"always_gemini": expected,
		"always_mistral": lambda example: {**expected(example), "model": MISTRAL},
		"cost_aware_router": expected,
	}
	result = evaluate_heldout(strategies)

	assert set(result) == {"always_gemini", "always_mistral", "cost_aware_router"}
	assert result["always_gemini"]["total_examples"] == 20
	assert result["always_mistral"]["mistral_usage_pct"] == 1.0
	assert json.dumps(result)


def test_evaluation_requires_named_strategies() -> None:
	with pytest.raises(ValueError, match="Missing evaluation strategies"):
		evaluate_heldout({})
