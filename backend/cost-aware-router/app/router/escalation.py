"""Escalation decisions and auditable escalation metadata."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.constants import COMPLEXITY_HIGH, MODEL_GEMINI, MODEL_MISTRAL


def escalation_reason(
	*, confidence: float, threshold: float, complexity: str, response_valid: bool
) -> str | None:
	if not response_valid:
		return "Response validation failed"
	if complexity == COMPLEXITY_HIGH:
		return "High complexity requires Mistral"
	if confidence < threshold:
		return f"Low confidence: {confidence:.2f} < {threshold:.2f}"
	return None


def should_escalate(
	*, confidence: float, threshold: float, complexity: str, response_valid: bool
) -> bool:
	return escalation_reason(
		confidence=confidence,
		threshold=threshold,
		complexity=complexity,
		response_valid=response_valid,
	) is not None


def build_escalation_event(
	*, request_id: str, initial_model: str, confidence: float, threshold: float, reason: str
) -> dict[str, Any]:
	return {
		"request_id": request_id,
		"initial_model": initial_model,
		"final_model": MODEL_MISTRAL,
		"confidence": confidence,
		"threshold": threshold,
		"reason": reason,
		"timestamp": datetime.now(timezone.utc).isoformat(),
	}
