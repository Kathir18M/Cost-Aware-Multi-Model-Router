import json

import pytest

from app.tools.cost_calculator import calculate_cost, get_model_pricing
from app.tools.evaluation_tool import evaluate_response
from app.tools.model_policy_tool import check_model_policy
from app.tools.routing_logger import log_routing_event
from app.tools.statistics_tool import get_router_statistics
from app.tools.token_counter import count_tokens


def test_cost_calculation_and_pricing() -> None:
	pricing = get_model_pricing()
	result = calculate_cost("haiku", 1000, 2000)

	assert result["model"] == "haiku"
	assert result["total_tokens"] == 3000
	assert result["cost"] == pytest.approx(
		1000 * pricing["haiku"]["input_price"]
		+ 2000 * pricing["haiku"]["output_price"]
	)


@pytest.mark.parametrize("model", ["unknown", ""])
def test_cost_rejects_invalid_model(model: str) -> None:
	with pytest.raises(ValueError):
		calculate_cost(model, 1, 1)


def test_token_counter_and_evaluation_are_serializable() -> None:
	assert count_tokens("hello") >= 1
	result = evaluate_response("What is Paris?", "Paris is a city.", "qa")
	assert json.dumps(result)
	assert result["has_answer"] is True


def test_policy_tool() -> None:
	assert check_model_policy("qa", "high", 0.9)["recommended_model"] == "sonnet"
	assert check_model_policy("qa", "low", 0.9)["recommended_model"] == "haiku"


def test_routing_log_and_statistics(tmp_path) -> None:
	path = tmp_path / "events.jsonl"
	log_routing_event("req-1", "haiku", "sonnet", 0.4, "low confidence", 0.02, log_path=path)
	log_routing_event("req-2", "haiku", "haiku", 0.9, None, 0.01, log_path=path)

	assert len(path.read_text(encoding="utf-8").splitlines()) == 2
	stats = get_router_statistics(log_path=path)
	assert stats["total_requests"] == 2
	assert stats["escalations"] == 1
	assert stats["total_cost"] == pytest.approx(0.03)


def test_tool_input_errors() -> None:
	with pytest.raises(ValueError):
		check_model_policy("qa", "low", 2)
	with pytest.raises(ValueError):
		evaluate_response("", "answer", "qa")
