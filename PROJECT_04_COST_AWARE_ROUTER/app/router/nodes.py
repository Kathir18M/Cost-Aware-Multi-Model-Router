"""LangGraph node functions for the routing workflow."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.core.config import load_settings
from app.core.constants import STATUS_ACCEPTED, STATUS_ESCALATED, STATUS_FAILED, STATUS_FALLBACK
from app.core.logging_config import get_logger
from app.router.confidence_engine import assess_response, response_is_valid
from app.router.escalation import build_escalation_event, escalation_reason
from app.router.fallback import execute_with_fallback
from app.router.complexity_analyzer import analyze_complexity
from app.router.model_selector import select_model
from app.router.task_classifier import classify_task
from app.schemas.router_state import RouterState

ModelExecutor = Callable[[str, str, str], dict[str, Any]]
logger = get_logger("escalation")


def classify_task_node(state: RouterState) -> RouterState:
	return {"task_type": classify_task(state.get("user_input", ""))}


def analyze_complexity_node(state: RouterState) -> RouterState:
	return {"complexity": analyze_complexity(state.get("user_input", ""))}


def select_model_node(state: RouterState) -> RouterState:
	selected = select_model(state["complexity"])
	return {"selected_model": selected, "initial_model": selected}


def execute_model_node(
	state: RouterState, *, executor: ModelExecutor | None = None
) -> RouterState:
	if executor is None:
		return {
			"response": {
				"content": "",
				"success": False,
				"error": "No model executor configured",
			},
			"status": STATUS_FAILED,
		}
	response, model, retries, technical_fallback = execute_with_fallback(
		executor,
		task_type=state["task_type"],
		user_input=state["user_input"],
		initial_model=state["selected_model"],
	)
	return {
		"response": response,
		"selected_model": model,
		"retry_count": retries,
		"status": STATUS_FALLBACK if technical_fallback else STATUS_ACCEPTED,
	}


def check_confidence_node(state: RouterState) -> RouterState:
	response = state.get("response") or {}
	confidence = assess_response(response, state.get("task_type", ""))
	threshold = load_settings().confidence_threshold
	valid = response_is_valid(response, state.get("task_type", ""))
	reason = escalation_reason(
		confidence=confidence,
		threshold=threshold,
		complexity=state.get("complexity", ""),
		response_valid=valid,
	)
	escalation_required = reason is not None and state.get("selected_model") != "sonnet"
	event = None
	if escalation_required:
		event = build_escalation_event(
			request_id=state.get("request_id", "unknown"),
			initial_model=state.get("initial_model", "haiku"),
			confidence=confidence,
			threshold=threshold,
			reason=reason or "Escalation required",
		)
		logger.info(
			"escalation request_id=%s initial_model=%s final_model=%s confidence=%.4f threshold=%.4f reason=%s",
			event["request_id"], event["initial_model"], event["final_model"],
			event["confidence"], event["threshold"], event["reason"],
		)
	return {
		"confidence": confidence,
		"escalation_required": escalation_required,
		"escalation_reason": reason,
		"escalation_event": event,
		"status": STATUS_ESCALATED if escalation_required else state.get("status", STATUS_ACCEPTED),
	}


def route_after_confidence(state: RouterState) -> str:
	"""Choose one Sonnet escalation or finish without looping."""

	if state.get("escalation_required") and state.get("selected_model") != "sonnet":
		return "execute_sonnet"
	return "finalize_response"


def execute_sonnet_node(
	state: RouterState, *, executor: ModelExecutor | None = None
) -> RouterState:
	"""Execute one intelligent Sonnet escalation without recursive fallback."""

	if executor is None:
		return {
			"selected_model": "sonnet",
			"response": {"content": "", "success": False, "error": "No model executor configured"},
			"status": STATUS_FAILED,
		}
	try:
		response = executor("sonnet", state["task_type"], state["user_input"])
		return {"selected_model": "sonnet", "response": response}
	except Exception:
		return {
			"selected_model": "sonnet",
			"response": {"content": "", "success": False, "error": "Sonnet escalation failed"},
			"status": STATUS_FAILED,
		}


def finalize_response_node(state: RouterState) -> RouterState:
	"""Mark the current response as final for this routing pass."""

	return {"response": state.get("response")}
